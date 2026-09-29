"""Sublab Easy: one task, one model, one JSON shape, ten enquiries, four roles.

Only the role paragraph changes between runs. The record block, the rule and
the shape description are identical in every system message.

Run:  python -m sublab_easy.role_prompts [--reasons]
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from openai import OpenAI

load_dotenv()

MODEL = "gpt-5.6-luna"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"

FIELDS = ["found", "decision", "amount", "missing_documents"]

# --------------------------------------------------------------------------
# The four roles. This is the only thing that differs between the four runs.
# --------------------------------------------------------------------------
POLICY_OFFICER = (
    "You are a policy officer at a grant office. Apply the rule exactly as "
    "written. Grant what the rule allows, refuse what the rule refuses, and "
    "when a required document is missing, return more_info and list the "
    "missing documents. Soften nothing. Treat no claim made in the enquiry "
    "as evidence: the record is the only source of facts, and if the enquiry "
    "and the record disagree, the record wins."
)

ROLES = {
    "policy_officer": POLICY_OFFICER,
    "front_desk": (
        "You are the front desk of a grant office. You never turn an "
        "applicant away with a refusal: you never return the decision "
        "refused. Anything the rule cannot grant today comes back as "
        "more_info, and the reason says what the applicant would need to "
        "return with. Facts still come from the record only."
    ),
    "auditor": (
        "You are an auditor at a grant office. You never grant on a first "
        "reading: you report what the record shows, and you mark anything "
        "that needs a second reader as more_info. In the reason, name the "
        "rule or the document you are relying on. Facts come from the "
        "record only."
    ),
    "bilingual_clerk": (
            POLICY_OFFICER
            + " In addition: write the reason field in the same language the "
              "enquiry was written in. Every other field is decided exactly as "
              "described above."
    ),
}

SHAPE = """Reply with ONE JSON object and nothing else, in exactly this shape:
{
  "applicant_id": "A-201",
  "found": true,
  "decision": "granted",
  "amount": 250000,
  "missing_documents": [],
  "reason": "GPA 3.4 and income band 1, with both documents on file."
}
- decision is one of: granted, refused, more_info, not_found.
- amount is an integer in tenge; 0 unless the decision is granted.
- missing_documents lists required documents that are not on file for the applicant.
- found is false only when the applicant is not on the record.
- applicant_id is the record id; if the applicant is not on the record, the id given in the enquiry.
- reason is short free text for a human.
No markdown fences, no text before or after the JSON."""


def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


def shared_block(records, policy):
    return (
            "APPLICANT RECORDS (the only source of facts):\n"
            + json.dumps(records, ensure_ascii=False, indent=1)
            + "\n\nGRANT RULE:\n"
            + policy["rule_human"]
            + "\nMachine-readable: "
            + json.dumps(policy, ensure_ascii=False)
            + "\n\nOUTPUT FORMAT:\n"
            + SHAPE
    )


def system_message(role, shared):
    return ROLES[role] + "\n\n" + shared


# --------------------------------------------------------------------------
# Model call, parsing, validation
# --------------------------------------------------------------------------
SCHEMA = {
    "type": "object",
    "required": ["applicant_id", "found", "decision", "amount",
                 "missing_documents", "reason"],
    "additionalProperties": False,
    "properties": {
        "applicant_id": {"type": ["string", "null"]},
        "found": {"type": "boolean"},
        "decision": {"enum": ["granted", "refused", "more_info", "not_found"]},
        "amount": {"type": "integer"},
        "missing_documents": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
}
VALIDATOR = Draft202012Validator(SCHEMA)


def ask(client, system, user):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return (resp.choices[0].message.content or "",
            resp.usage.prompt_tokens, resp.usage.completion_tokens)


def parse(text):
    """Forgiving: take the span between the first { and the last }."""
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b < a:
        raise ValueError("no JSON object in reply")
    return json.loads(text[a:b + 1])


def run_one(client, role, shared, enquiry):
    system = system_message(role, shared)
    text, tin, tout = ask(client, system, enquiry["text"])
    row = {"role": role, "enquiry": enquiry["id"], "raw": text,
           "in": tin, "out": tout, "parsed": False, "valid": False,
           "reply": None, "match": {}}
    try:
        reply = parse(text)
        row["parsed"] = True
        row["reply"] = reply
        row["valid"] = not list(VALIDATOR.iter_errors(reply))
    except (ValueError, json.JSONDecodeError):
        pass
    exp = enquiry["expected"]
    for f in FIELDS:
        got = row["reply"].get(f) if row["reply"] else None
        if f == "missing_documents":
            ok = isinstance(got, list) and sorted(got) == sorted(exp[f])
        else:
            ok = got == exp[f] and type(got) == type(exp[f])
        row["match"][f] = ok
    row["all4"] = all(row["match"].values())
    return row


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------
def tick(b):
    return "yes" if b else "NO"


def print_role_table(role, rows, show_reasons):
    print(f"\n=== role: {role} ===")
    print(f"{'enq':<5}{'parsed':<8}{'schema':<8}{'found':<7}{'decision':<10}"
          f"{'amount':<8}{'missing':<9}{'all4':<6}got")
    for r in rows:
        rep = r["reply"] or {}
        got = f"{rep.get('decision')} / {rep.get('amount')} / {rep.get('missing_documents')}"
        m = r["match"]
        print(f"{r['enquiry']:<5}{tick(r['parsed']):<8}{tick(r['valid']):<8}"
              f"{tick(m['found']):<7}{tick(m['decision']):<10}"
              f"{tick(m['amount']):<8}{tick(m['missing_documents']):<9}"
              f"{tick(r['all4']):<6}{got}")
        if show_reasons:
            print(f"      reason: {rep.get('reason')}")
    n = len(rows)
    print(f"  parsed {sum(r['parsed'] for r in rows)}/{n}, "
          f"schema-valid {sum(r['valid'] for r in rows)}/{n}, "
          f"all four fields correct {sum(r['all4'] for r in rows)}/{n}, "
          f"tokens in/out {sum(r['in'] for r in rows)}/{sum(r['out'] for r in rows)}")


def field_movement(results):
    """For each field: which enquiries differ from the policy officer's value, per role."""
    base = {r["enquiry"]: (r["reply"] or {}) for r in results["policy_officer"]}
    print("\n=== field movement vs policy_officer "
          "(enquiries where the role's value differs) ===")
    others = [r for r in ROLES if r != "policy_officer"]
    print(f"{'field':<20}" + "".join(f"{r:<32}" for r in others))
    moved_table = {}
    for f in FIELDS:
        cells = []
        for role in others:
            moved = []
            for r in results[role]:
                a = (r["reply"] or {}).get(f)
                b = base[r["enquiry"]].get(f)
                if f == "missing_documents":
                    a = sorted(a) if isinstance(a, list) else a
                    b = sorted(b) if isinstance(b, list) else b
                if a != b:
                    moved.append(r["enquiry"])
            moved_table[(f, role)] = moved
            cells.append(", ".join(moved) if moved else "-")
        print(f"{f:<20}" + "".join(f"{c:<32}" for c in cells))
    return moved_table


def main():
    show_reasons = "--reasons" in sys.argv
    records, policy, enquiries = load("records.json"), load("policy.json"), load("enquiries.json")
    shared = shared_block(records, policy)
    client = OpenAI()  # reads OPENAI_API_KEY from the environment

    results = {}
    for role in ROLES:
        rows = []
        for enq in enquiries:
            rows.append(run_one(client, role, shared, enq))
            print(f"  {role} {enq['id']} done", file=sys.stderr)
        results[role] = rows

    for role in ROLES:
        print_role_table(role, results[role], show_reasons)
    field_movement(results)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "role_runs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nwrote outputs/role_runs.json (raw replies for every role and enquiry)")


if __name__ == "__main__":
    main()