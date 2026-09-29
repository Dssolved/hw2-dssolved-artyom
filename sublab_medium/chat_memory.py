"""Sublab Medium: memory you choose.

A chat session with a switch in it:
  - uncompressed: every call sends the system message + every turn so far;
  - compressed:   on the `compress` command the model summarises the thread
                  into one JSON state object, the object is validated against
                  data/memory_state.schema.json, the turns are thrown away and
                  the state is sent from then on. If the summary does not parse
                  or does not validate, the history is KEPT.

Run:
  python -m sublab_medium.chat_memory                # scripted A/B comparison
  python -m sublab_medium.chat_memory --interactive  # real chat; type: compress
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

COMPRESS_MARK = "<compress>"


def load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)


POLICY = load("policy.json")
SCHEMA = load("memory_state.schema.json")
VALIDATOR = Draft202012Validator(SCHEMA)

# The assistant gets the RULE but not the applicant records. In this chat it
# has to rely on what the applicant says, so the probes really test memory.
SYSTEM = (
        "You are the assistant of a grant office, answering applicants in chat.\n"
        "Grant scheme: " + POLICY["scheme"] + ".\n"
                                              "Rule: " + POLICY["rule_human"] + "\n"
                                                                                "Amounts in tenge by income band: "
        + json.dumps(POLICY["amount_tenge_by_band"]) + ".\n"
                                                       "Required documents: " + ", ".join(POLICY["required_documents"]) + ".\n\n"
                                                                                                                          "In this chat you have NO access to the applicant records. Use only the "
                                                                                                                          "rule and what the applicant tells you in this conversation. Never invent "
                                                                                                                          "facts. Answer in the language the applicant is writing in, in at most "
                                                                                                                          "three short sentences."
)

COMPRESS_PROMPT = """Summarise the conversation below into ONE JSON object and nothing else (no markdown fences, no text before or after).

The object must follow this schema exactly:
{schema}

Field rules:
- applicant_id: the applicant's id if the conversation established it, else null.
- topic: one short sentence on what the conversation is about.
- facts: things the APPLICANT stated (ids, names, income band, documents sent or not sent, relatives). Not things you worked out.
- decisions: answers or decisions the assistant already gave (for example an amount).
- constraints: conditions on how or when something can happen (a day, a deadline, a requirement the applicant set).
- open_questions: things the applicant asked that were not answered yet.
- language: the language(s) the applicant writes in.
Keep every specific detail (ids, days, amounts, document names). One short string per item. Do not invent anything: a fact that was never said is not a fact. Arrays are empty, never omitted.

CONVERSATION:
{transcript}"""


class Session:
    def __init__(self, client, compress_enabled=True):
        self.client = client
        self.compress_enabled = compress_enabled
        self.turns = []        # list of {"role": "user"/"assistant", "content": ...}
        self.state = None      # dict once compressed
        self.last_usage = (0, 0)
        self.usage_log = []    # (label, prompt_tokens, completion_tokens)

    # ----- what gets sent -------------------------------------------------
    def system_message(self):
        if self.state is None:
            return SYSTEM
        return (SYSTEM + "\n\nEarlier turns of this conversation were compressed "
                         "into the state below. Treat it as what has been said so far.\n"
                         "STATE: " + json.dumps(self.state, ensure_ascii=False))

    def messages(self, extra_user=None):
        msgs = [{"role": "system", "content": self.system_message()}] + list(self.turns)
        if extra_user is not None:
            msgs.append({"role": "user", "content": extra_user})
        return msgs

    def _call(self, msgs, label):
        resp = self.client.chat.completions.create(model=MODEL, messages=msgs)
        text = resp.choices[0].message.content or ""
        tin, tout = resp.usage.prompt_tokens, resp.usage.completion_tokens
        self.last_usage = (tin, tout)
        self.usage_log.append((label, tin, tout))
        return text, tin, tout

    # ----- normal turn ----------------------------------------------------
    def say(self, user_text, label=None):
        msgs = self.messages(extra_user=user_text)
        text, tin, tout = self._call(msgs, label or f"turn {len(self.turns)//2 + 1}")
        self.turns.append({"role": "user", "content": user_text})
        self.turns.append({"role": "assistant", "content": text})
        return text, tin, tout

    # ----- probe: ask without changing the history -------------------------
    def probe(self, question):
        return self._call(self.messages(extra_user=question), "probe")

    # ----- compression ----------------------------------------------------
    def compress(self):
        """Returns (ok, message, tin, tout). On failure the history is kept."""
        if not self.turns:
            return False, "nothing to compress yet", 0, 0
        transcript = "\n".join(
            ("Applicant: " if t["role"] == "user" else "Assistant: ") + t["content"]
            for t in self.turns)
        if self.state is not None:
            transcript = "(earlier state: " + json.dumps(self.state, ensure_ascii=False) + ")\n" + transcript
        prompt = COMPRESS_PROMPT.format(schema=json.dumps(SCHEMA, ensure_ascii=False, indent=1),
                                        transcript=transcript)
        text, tin, tout = self._call([{"role": "user", "content": prompt}], "compress")
        a, b = text.find("{"), text.rfind("}")
        if a == -1 or b < a:
            return False, "summary has no JSON object; history kept", tin, tout
        try:
            state = json.loads(text[a:b + 1])
        except json.JSONDecodeError as e:
            return False, f"summary is not valid JSON ({e}); history kept", tin, tout
        errors = sorted(VALIDATOR.iter_errors(state), key=lambda e: list(e.path))
        if errors:
            return False, "summary fails the schema: " + errors[0].message + "; history kept", tin, tout
        self.state = state
        self.turns = []        # throw the turns away
        return True, "compressed", tin, tout


# --------------------------------------------------------------------------
# Scripted comparison
# --------------------------------------------------------------------------
def norm(t):
    return re.sub(r"[,\s_\u00a0\u202f]", "", t.lower())


def retrieved(answer, expect):
    a = norm(answer)
    return any(norm(e) in a for e in expect)


def run_script(client, compress_enabled):
    script = load("chat_script.json")
    s = Session(client, compress_enabled)
    calls = []            # one entry per script position 1..12
    for i, text in enumerate(script["conversation"], start=1):
        if text == COMPRESS_MARK:
            if not compress_enabled:
                calls.append({"pos": i, "kind": "skipped", "in": None, "out": None})
                continue
            ok, msg, tin, tout = s.compress()
            calls.append({"pos": i, "kind": "compress", "in": tin, "out": tout,
                          "ok": ok, "msg": msg})
            print(f"  [compress] {msg}", file=sys.stderr)
        else:
            reply, tin, tout = s.say(text)
            calls.append({"pos": i, "kind": "turn", "in": tin, "out": tout,
                          "user": text, "reply": reply})
        print(f"  {'B' if compress_enabled else 'A'} position {i} done", file=sys.stderr)
    probes = []
    for p in script["probes"]:
        text, tin, tout = s.probe(p["question"])
        probes.append({"id": p["id"], "tests": p["tests"], "answer": text,
                       "retrieved": retrieved(text, p["expect_contains"]),
                       "in": tin, "out": tout})
    return {"calls": calls, "probes": probes, "state": s.state,
            "compressed": s.state is not None}


def summarise(run):
    ins = [c["in"] for c in run["calls"] if c["in"] is not None]
    outs = [c["out"] for c in run["calls"] if c["out"] is not None]
    return {"peak": max(ins), "total_in": sum(ins), "total_out": sum(outs),
            "probe_in": sum(p["in"] for p in run["probes"]),
            "retrieved": sum(p["retrieved"] for p in run["probes"])}


def print_report(A, B):
    print("\n=== tokens sent per call (prompt tokens) ===")
    print(f"{'pos':<5}{'A: never compressed':<24}{'B: compressed':<24}")
    for ca, cb in zip(A["calls"], B["calls"]):
        la = "-" if ca["in"] is None else str(ca["in"])
        lb = "-" if cb["in"] is None else str(cb["in"])
        if cb["kind"] == "compress":
            lb += "  (compress call)"
        if ca["kind"] == "skipped":
            la += "  (skipped)"
        print(f"{ca['pos']:<5}{la:<24}{lb:<24}")
    sa, sb = summarise(A), summarise(B)
    print(f"{'peak':<5}{sa['peak']:<24}{sb['peak']:<24}")
    print(f"{'total in':<9}{sa['total_in']:<20}{sb['total_in']:<24}")
    print(f"{'total out':<9}{sa['total_out']:<20}{sb['total_out']:<24}")
    print(f"probe prompt tokens (5 probes): A {sa['probe_in']}, B {sb['probe_in']}")
    print(f"B compression succeeded: {B['compressed']}")

    print("\n=== probes ===")
    for pa, pb in zip(A["probes"], B["probes"]):
        print(f"{pa['id']} ({pa['tests']})")
        print(f"   A {'retrieved' if pa['retrieved'] else 'LOST':<10} {pa['answer']!r}")
        print(f"   B {'retrieved' if pb['retrieved'] else 'LOST':<10} {pb['answer']!r}")
    print(f"retrieved: A {sa['retrieved']}/5, B {sb['retrieved']}/5")

    print("\n=== state produced by compression ===")
    print(json.dumps(B["state"], ensure_ascii=False, indent=2))


def scripted():
    client = OpenAI()
    A = run_script(client, compress_enabled=False)
    B = run_script(client, compress_enabled=True)
    print_report(A, B)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "chat_runs.json", "w", encoding="utf-8") as f:
        json.dump({"A": A, "B": B}, f, ensure_ascii=False, indent=2)
    print("\nwrote outputs/chat_runs.json")


# --------------------------------------------------------------------------
# Interactive
# --------------------------------------------------------------------------
def interactive():
    client = OpenAI()
    s = Session(client, True)
    print("Commands: compress | tokens | state | quit. Anything else is sent to the assistant.")
    while True:
        try:
            line = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line == "quit":
            break
        if line == "tokens":
            print(f"last call: {s.last_usage[0]} tokens sent, {s.last_usage[1]} tokens received")
            continue
        if line == "state":
            print(json.dumps(s.state, ensure_ascii=False, indent=2) if s.state else "(no state yet)")
            continue
        if line == "compress":
            before = len(s.turns)
            ok, msg, tin, tout = s.compress()
            print(f"[compress] {msg} (call sent {tin} tokens)")
            if ok:
                print(json.dumps(s.state, ensure_ascii=False, indent=2))
                print(f"[{before} messages thrown away; the state is sent from now on]")
            continue
        reply, tin, tout = s.say(line)
        print(f"bot> {reply}")
        print(f"[sent {len(s.turns) - 1} history messages + system, {tin} tokens]")


if __name__ == "__main__":
    if "--interactive" in sys.argv:
        interactive()
    else:
        scripted()