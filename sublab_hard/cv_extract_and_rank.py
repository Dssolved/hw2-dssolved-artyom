"""Sublab Hard: stories in, CVs out, the winner decided by code.

Pipeline (one model, gpt-5.6-luna):
  1. EXTRACT  story -> CV record (JSON). Rules are in the prompt.
  2. CODE     re-counts what a program can count (published outputs, countable
              months, GPA on a 4.0 scale) and checks the evidence quotes.
  3. SCORE    the model gives a 0-5 score for each of three criteria. Nothing else.
  4. RANK     code computes 0.5*academic + 0.3*research + 0.2*experience and
              names the winner.
  5. PROSE    in a separate call the model is asked in prose who should win.

Run:  python -m sublab_hard.cv_extract_and_rank
"""
import json
import re
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

RUBRIC = json.load(open(DATA / "candidate_rubric.json", encoding="utf-8"))
WEIGHTS = {c["id"]: c["weight"] for c in RUBRIC["criteria"]}   # used by CODE only
CRITERIA = list(WEIGHTS)                                         # academic, research, experience
COUNTED_STATUSES = {"published", "accepted"}
STATUSES = ["published", "accepted", "submitted", "under_review",
            "in_preparation", "in_press", "planned", "other"]

# --------------------------------------------------------------------------
# 1. Extraction prompt. The counting rules live HERE, not in my head.
# --------------------------------------------------------------------------
EXTRACT_SYSTEM = """You extract a structured CV record from a scholarship candidate's written story. The story may be in English or Kazakh. Reply with ONE JSON object and nothing else (no markdown fences, no text around it).

RULES (follow them exactly):
1. A fact the story does not state is null. Never estimate, infer or guess it. No GPA in the story means gpa_original, gpa_scale and gpa_4_scale are all null. Do not infer a GPA from the degree, the university or the impression the story gives.
2. GPA on another scale: record the number as stated in gpa_original and the scale the story used in gpa_scale (for example 5.0). Also give gpa_4_scale = gpa_original / gpa_scale * 4.0, rounded to 2 decimals. If the story already uses a 4.0 scale, gpa_4_scale equals gpa_original.
3. Publications: list every research output in "outputs" with a status. Use status "published" or "accepted" ONLY when the story says the output is published or accepted. "submitted", "under review", "in preparation", "planned" and "in press" are NOT published: give them their own status and do not count them. Posters, talks and other non-paper outputs get status "other". Set peer_reviewed to true only if the story says the output is peer-reviewed (or refereed); otherwise null. published_peer_reviewed_count is the number of outputs with status published/accepted AND peer_reviewed true.
4. Experience: list each work or internship period in "experience_periods". Give start and end as "YYYY-MM" only when the story gives calendar dates; otherwise null. months_stated is the number of months the story states for that period, or null. Set ongoing to true if the story says it continues today. Count months, not jobs. Overlapping periods count once. A period with no calendar dates is not countable: still record it, and put in experience_months_countable only the months you can count.
5. Contradictions: if the story contradicts itself about a fact (two different values, or statements that cannot both be true), do NOT resolve it and do NOT average it. Set that field to null and describe the contradiction in "ambiguities".
6. Evidence: for every field you fill with a non-null value, add a short VERBATIM quote from the story (in the story's own language, at most 200 characters) in "evidence", keyed by the field name. Fields that are null have no evidence.

JSON SHAPE (all keys required):
{
  "full_name": string or null,
  "degree": string or null,
  "graduation_year": integer or null,
  "gpa_original": number or null,
  "gpa_scale": number or null,
  "gpa_4_scale": number or null,
  "languages": [string],
  "outputs": [{"title": string or null (null if the story gives no title), "description": short string saying what the output is, "status": one of published|accepted|submitted|under_review|in_preparation|in_press|planned|other, "peer_reviewed": true or null}],
  "published_peer_reviewed_count": integer,
  "experience_periods": [{"description": string, "start": "YYYY-MM" or null, "end": "YYYY-MM" or null, "ongoing": boolean, "months_stated": integer or null}],
  "experience_months_countable": integer or null,
  "evidence": {"field name": "verbatim quote"},
  "ambiguities": [string]
}"""

CV_SCHEMA = {
    "type": "object",
    "required": ["full_name", "degree", "graduation_year", "gpa_original", "gpa_scale",
                 "gpa_4_scale", "languages", "outputs", "published_peer_reviewed_count",
                 "experience_periods", "experience_months_countable", "evidence",
                 "ambiguities"],
    "additionalProperties": False,
    "properties": {
        "full_name": {"type": ["string", "null"]},
        "degree": {"type": ["string", "null"]},
        "graduation_year": {"type": ["integer", "null"]},
        "gpa_original": {"type": ["number", "null"]},
        "gpa_scale": {"type": ["number", "null"]},
        "gpa_4_scale": {"type": ["number", "null"]},
        "languages": {"type": "array", "items": {"type": "string"}},
        "outputs": {"type": "array", "items": {
            "type": "object",
            "required": ["title", "description", "status", "peer_reviewed"],
            "properties": {"title": {"type": ["string", "null"]},
                           "description": {"type": "string"},
                           "status": {"enum": STATUSES},
                           "peer_reviewed": {"type": ["boolean", "null"]}}}},
        "published_peer_reviewed_count": {"type": "integer"},
        "experience_periods": {"type": "array", "items": {
            "type": "object",
            "required": ["description", "start", "end", "ongoing", "months_stated"],
            "properties": {"description": {"type": "string"},
                           "start": {"type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}$"},
                           "end": {"type": ["string", "null"], "pattern": "^\\d{4}-\\d{2}$"},
                           "ongoing": {"type": "boolean"},
                           "months_stated": {"type": ["integer", "null"]}}}},
        "experience_months_countable": {"type": ["integer", "null"]},
        "evidence": {"type": "object", "additionalProperties": {"type": ["string", "null"]}},
        "ambiguities": {"type": "array", "items": {"type": "string"}},
    },
}
CV_VALIDATOR = Draft202012Validator(CV_SCHEMA)

# --------------------------------------------------------------------------
# 3. Scoring prompt: rubric in, three integers out. No totals, no winner.
# --------------------------------------------------------------------------
def score_system():
    lines = ["You score one scholarship candidate against a rubric. You are given the candidate's CV record (already extracted). Score each criterion with an integer from 0 to 5.", ""]
    for c in RUBRIC["criteria"]:
        lines.append(f"- {c['id']} ({c['label']}): 5 means: {c['what_5_means']}. 0 means: {c['what_0_means']}.")
    lines.append("")
    lines.append("Counting rules:")
    for k, v in RUBRIC["counting_rules"].items():
        lines.append(f"- {k}: {v}")
    lines += ["",
              "Use only the CV record. Do not compute any total and do not compare with other candidates; the office does that.",
              'Reply with ONE JSON object and nothing else: {"academic": int, "research": int, "experience": int, "basis": {"academic": short reason, "research": short reason, "experience": short reason}}']
    return "\n".join(lines)


SCORE_SCHEMA = {
    "type": "object",
    "required": CRITERIA + ["basis"],
    "properties": {**{c: {"type": "integer", "minimum": 0, "maximum": 5} for c in CRITERIA},
                   "basis": {"type": "object"}},
}
SCORE_VALIDATOR = Draft202012Validator(SCORE_SCHEMA)


# --------------------------------------------------------------------------
# Model plumbing
# --------------------------------------------------------------------------
def ask(client, system, user):
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return (resp.choices[0].message.content or "",
            resp.usage.prompt_tokens, resp.usage.completion_tokens)


def parse_json(text):
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b < a:
        raise ValueError("no JSON object in reply")
    return json.loads(text[a:b + 1])


# --------------------------------------------------------------------------
# 2. Code checks: what a program can count, it counts.
# --------------------------------------------------------------------------
def month_index(ym):
    y, m = ym.split("-")
    return int(y) * 12 + int(m)


def count_experience(periods):
    """Countable months. A period needs a calendar start to be countable.
    Months = months_stated if given, else the inclusive span of its dates.
    Overlaps (only detectable when both dates exist) are subtracted once."""
    notes, counted, sets = [], 0, []
    for p in periods:
        if not p.get("start"):
            notes.append(f"not countable (no calendar start): {p['description'][:50]}")
            continue
        span = None
        if p.get("end"):
            span = month_index(p["end"]) - month_index(p["start"]) + 1
            sets.append(set(range(month_index(p["start"]), month_index(p["end"]) + 1)))
        stated = p.get("months_stated")
        if stated is not None and span is not None and abs(stated - span) > 1:
            notes.append(f"months_stated {stated} differs from date span {span}: {p['description'][:40]}")
        m = stated if stated is not None else span
        if m is None:
            notes.append(f"not countable (no end date, no months): {p['description'][:50]}")
            continue
        counted += m
    overlap = sum(len(s) for s in sets) - len(set().union(*sets)) if sets else 0
    if overlap:
        notes.append(f"overlap of {overlap} month(s) removed")
    return counted - overlap, notes


def norm_text(t):
    t = re.sub(r"[*_`>#]", "", t)
    return re.sub(r"\s+", " ", t).strip().casefold()


def check_evidence(evidence, story):
    body = norm_text(story)
    missing = [k for k, q in evidence.items() if q and norm_text(q) not in body]
    return len(evidence), missing


def code_checks(cv, story):
    c = {}
    # publications
    counted = sum(1 for o in cv["outputs"] if o["status"] in COUNTED_STATUSES and o["peer_reviewed"] is True)
    unstated = sum(1 for o in cv["outputs"] if o["status"] in COUNTED_STATUSES and o["peer_reviewed"] is not True)
    c["published_peer_reviewed"] = counted
    c["published_review_unstated"] = unstated
    c["not_counted_outputs"] = [f"{o['status']}: {(o.get('title') or o['description'])[:40]}" for o in cv["outputs"]
                                if o["status"] not in COUNTED_STATUSES]
    c["count_model_vs_code"] = (cv["published_peer_reviewed_count"], counted)
    # gpa
    if cv["gpa_original"] is not None and cv["gpa_scale"]:
        c["gpa_4_scale"] = round(cv["gpa_original"] / cv["gpa_scale"] * 4.0, 2)
    else:
        c["gpa_4_scale"] = None
    m = cv["gpa_4_scale"]
    c["gpa_model_vs_code"] = (m, c["gpa_4_scale"])
    # experience
    months, notes = count_experience(cv["experience_periods"])
    c["experience_months"] = months
    c["experience_notes"] = notes
    c["months_model_vs_code"] = (cv["experience_months_countable"], months)
    # evidence
    n, missing = check_evidence(cv["evidence"], story)
    c["evidence_total"], c["evidence_not_found"] = n, missing
    # null fields
    c["null_fields"] = [k for k in ("full_name", "degree", "graduation_year", "gpa_original",
                                    "gpa_scale", "gpa_4_scale") if cv[k] is None]
    return c


def cv_for_scoring(cv, chk):
    return {
        "degree": cv["degree"], "graduation_year": cv["graduation_year"],
        "gpa_original": cv["gpa_original"], "gpa_scale": cv["gpa_scale"],
        "gpa_4_scale": chk["gpa_4_scale"],
        "published_peer_reviewed_outputs": chk["published_peer_reviewed"],
        "published_outputs_without_stated_peer_review": chk["published_review_unstated"],
        "outputs_not_counted": chk["not_counted_outputs"],
        "countable_experience_months": chk["experience_months"],
        "experience_periods": cv["experience_periods"],
        "ambiguities": cv["ambiguities"],
    }


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
def load_stories():
    return [(p.stem, p.read_text(encoding="utf-8")) for p in sorted((DATA / "candidates").glob("story-*.md"))]


def extract(client, cid, story):
    rec = {"id": cid, "parsed": False, "valid": False, "cv": None, "raw": None, "errors": [],
           "in": 0, "out": 0}
    text, rec["in"], rec["out"] = ask(client, EXTRACT_SYSTEM, "STORY:\n" + story)
    rec["raw"] = text
    try:
        cv = parse_json(text)
        rec["parsed"] = True
        errs = [e.message for e in CV_VALIDATOR.iter_errors(cv)]
        rec["errors"] = errs[:3]
        rec["valid"] = not errs
        rec["cv"] = cv
    except (ValueError, json.JSONDecodeError) as e:
        rec["errors"] = [str(e)]
    return rec


def score(client, cid, cvs):
    rec = {"id": cid, "ok": False, "scores": None, "basis": None, "raw": None, "in": 0, "out": 0}
    text, rec["in"], rec["out"] = ask(client, score_system(),
                                      "CV RECORD:\n" + json.dumps(cvs, ensure_ascii=False, indent=1))
    rec["raw"] = text
    try:
        d = parse_json(text)
        if not list(SCORE_VALIDATOR.iter_errors(d)):
            rec["ok"] = True
            rec["scores"] = {c: d[c] for c in CRITERIA}
            rec["basis"] = d.get("basis")
    except (ValueError, json.JSONDecodeError):
        pass
    return rec


def weighted_total(sc):
    return round(sum(WEIGHTS[c] * sc[c] for c in CRITERIA), 2)


def prose_winner(client, stories):
    system = ("You are on a scholarship committee. One funded place, six candidates. "
              "Read the stories and the rubric, then say in a short paragraph which candidate should win and why.\n\n"
              "RUBRIC:\n" + json.dumps(RUBRIC, ensure_ascii=False, indent=1))
    body = "\n\n".join(f"=== {cid} ===\n{s}" for cid, s in stories)
    return ask(client, system, body)


def main():
    client = OpenAI()
    stories = load_stories()
    results = {"extract": [], "checks": {}, "score": [], "totals": {}, "prose": None}

    print("=== 1. extraction ===")
    for cid, story in stories:
        r = extract(client, cid, story)
        results["extract"].append(r)
        print(f"  {cid} extracted", file=sys.stderr)
        if r["cv"] is None:
            print(f"{cid}: parsed=NO valid=NO  {r['errors']}")
            continue
        chk = code_checks(r["cv"], story) if r["valid"] else None
        results["checks"][cid] = chk
        print(f"\n{cid}: parsed={'yes' if r['parsed'] else 'NO'} valid={'yes' if r['valid'] else 'NO ' + str(r['errors'])}")
        if chk is None:
            continue
        cv = r["cv"]
        print(f"  name={cv['full_name']!r} degree={cv['degree']!r} grad={cv['graduation_year']}")
        print(f"  null fields: {chk['null_fields'] or 'none'}")
        print(f"  gpa: original={cv['gpa_original']} scale={cv['gpa_scale']} | model 4.0={chk['gpa_model_vs_code'][0]} | code 4.0={chk['gpa_4_scale']}")
        print(f"  published peer-reviewed: model={chk['count_model_vs_code'][0]} code={chk['count_model_vs_code'][1]} "
              f"(published, review not stated: {chk['published_review_unstated']}); not counted: {chk['not_counted_outputs'] or 'none'}")
        print(f"  countable months: model={chk['months_model_vs_code'][0]} code={chk['months_model_vs_code'][1]}; notes: {chk['experience_notes'] or 'none'}")
        print(f"  evidence quotes: {chk['evidence_total']}, not found verbatim in story: {chk['evidence_not_found'] or 'none'}")
        print(f"  ambiguities: {cv['ambiguities'] or 'none'}")

    print("\n=== 2. scores from the model, totals from code ===")
    print(f"{'id':<10}{'academic':<10}{'research':<10}{'experience':<12}{'total (code)':<14}")
    ranked = []
    for r in results["extract"]:
        chk = results["checks"].get(r["id"])
        if not chk:
            print(f"{r['id']:<10}(no valid CV, not scored)")
            continue
        s = score(client, r["id"], cv_for_scoring(r["cv"], chk))
        results["score"].append(s)
        print(f"  {r['id']} scored", file=sys.stderr)
        if not s["ok"]:
            print(f"{r['id']:<10}score reply did not validate: {s['raw'][:80]!r}")
            continue
        # Rubric: "A story with no GPA scores 0 on academic." The code enforces it
        # and keeps the model's own score so the override is visible.
        applied = dict(s["scores"])
        s["overrides"] = []
        if chk["gpa_4_scale"] is None and applied["academic"] != 0:
            s["overrides"].append(f"academic {applied['academic']} -> 0 (no usable GPA)")
            applied["academic"] = 0
        s["applied"] = applied
        total = weighted_total(applied)
        results["totals"][r["id"]] = total
        ranked.append((total, r["id"]))
        sc = s["scores"]
        acad = f"{sc['academic']}->0" if s["overrides"] else str(sc["academic"])
        print(f"{r['id']:<10}{acad:<10}{sc['research']:<10}{sc['experience']:<12}{total:<14}")
    ranked.sort(key=lambda x: (-x[0], x[1]))
    for s in results["score"]:
        if s.get("overrides"):
            print(f"  override for {s['id']}: {'; '.join(s['overrides'])}")
    print("\nranking by computed total:")
    for i, (t, cid) in enumerate(ranked, 1):
        print(f"  {i}. {cid}  {t}")
    if ranked:
        top = ranked[0][0]
        tied = [cid for t, cid in ranked if t == top]
        winner = tied[0] if len(tied) == 1 else "TIE: " + ", ".join(tied)
        print(f"winner (code): {winner}")
        if len(ranked) > 1:
            gap = round(ranked[0][0] - ranked[1][0], 2)
            print(f"gap between first and second: {gap}" + ("  <= 0.05, too close" if gap <= 0.05 else ""))
        results["winner"] = winner
    print("\nbasis given by the model for each score:")
    for s in results["score"]:
        if s["ok"]:
            print(f"  {s['id']}: {json.dumps(s['basis'], ensure_ascii=False)}")

    print("\n=== 3. prose answer (separate call, sees the stories and the rubric) ===")
    text, tin, tout = prose_winner(client, stories)
    results["prose"] = text
    print(text)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "cv_runs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nwrote outputs/cv_runs.json (raw replies and CV records)")


if __name__ == "__main__":
    main()