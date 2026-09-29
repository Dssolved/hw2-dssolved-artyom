# HW2 submission

**Name: Artyom Ostanin**

**Student ID: 66803**

**Group: CSS4007-ENG-8**

**Repository: https://github.com/Dssolved/hw2-dssolved-artyom**

## AI tool disclosure

Used Claude (Anthropic) for HW2. For Sublab Easy, Claude wrote the first
version of `sublab_easy/role_prompts.py`, including all four role paragraphs
(policy_officer, front_desk, auditor, bilingual_clerk), the shared record/rule/
format block, and the reporting code. Claude also drafted the written answers
in the Easy, Medium and Hard sections from the output of my runs. In Sublab
Medium, Claude wrote `sublab_medium/chat_memory.py` (session, `compress`
command, scripted A/B run, interactive mode). In Sublab Hard, Claude wrote
`sublab_hard/cv_extract_and_rank.py`, including the extraction and scoring
prompts. All numbers below are from my own runs of the programs.

---

## Sublab Easy — one task, four roles

Model: `gpt-5.6-luna` for all runs. The program was run twice with identical
prompts. Each cell is the `decision` returned; ✓/✗ means whether all four
structured fields (`found`, `decision`, `amount`, `missing_documents`) agree
with `expected`.

### Decisions per role

**Run 1**

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✓ | granted ✓ | granted ✓ | granted ✓ |
| E-02 | more_info ✓ | more_info ✓ | refused ✗ | more_info ✓ |
| E-03 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-04 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-05 | granted ✓ | granted ✓ | granted ✓ | granted ✓ |
| E-06 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-07 | granted ✓ | granted ✓ | granted ✓ | granted ✓ |
| E-08 | not_found ✓ | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-10 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| **agrees with `expected`** | 10/10 | 7/10 | 8/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

**Run 2**

| Enquiry | policy_officer | front_desk | auditor | bilingual_clerk |
|---|---|---|---|---|
| E-01 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-02 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| E-03 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-04 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-05 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-06 | granted ✓ | granted ✓ | more_info ✗ | granted ✓ |
| E-07 | granted ✓ | granted ✓ | granted ✓ | granted ✓ |
| E-08 | not_found ✓ | not_found ✓ | not_found ✓ | not_found ✓ |
| E-09 | refused ✓ | more_info ✗ | refused ✓ | refused ✓ |
| E-10 | more_info ✓ | more_info ✓ | more_info ✓ | more_info ✓ |
| **agrees with `expected`** | 10/10 | 7/10 | 7/10 | 10/10 |
| **parsed** | 10/10 | 10/10 | 10/10 | 10/10 |
| **schema-valid** | 10/10 | 10/10 | 10/10 | 10/10 |

### Which field moved, on which enquiry, under which role

"Moved" means the role's value differs from the policy officer's value on the
same enquiry.

| Field | Enquiries that moved | Role(s) that moved it |
|---|---|---|
| `found` | none (either run) | none |
| `decision` | E-03, E-04, E-09 (both runs); auditor: E-02, E-06 (run 1), E-01, E-05, E-06 (run 2) | front_desk (E-03, E-04, E-09, both runs); auditor (different enquiries per run, E-06 in both) |
| `amount` | auditor: E-06 (run 1); E-01, E-05, E-06 (run 2) | auditor only |
| `missing_documents` | none (either run) | none |

`bilingual_clerk` moved none of the four fields in either run. `found` and
`missing_documents` moved on no enquiry under any role.

### Raw replies

Full reply, front_desk on E-03 (changed `decision` from `refused` to
`more_info`), from `outputs/role_runs.json` (run 2):

```
{"applicant_id":"A-203","found":true,"decision":"more_info","amount":0,"missing_documents":[],"reason":"GPA 2.4 is below the required 2.67; return with evidence of a GPA meeting the minimum."}
```

Full reply, bilingual_clerk on E-07 (the Kazakh enquiry):

```
{"applicant_id":"A-201","found":true,"decision":"granted","amount":250000,"missing_documents":[],"reason":"GPA 3.4 және табыс санаты 1, екі құжат та тіркелген."}
```

### Written answers

**1. Which fields are role-sensitive and which are not?** Point at rows in your
tables.

> `decision` is role-sensitive, and `amount` follows it. `found` and
> `missing_documents` are not role-sensitive: they moved on no enquiry under
> any role in either run. `amount` only moves where a `granted` becomes
> `more_info` (auditor: E-06 in both runs, E-01 and E-05 in run 2), because
> the amount is then 0. It never moved on its own.
>
> front_desk is the role that moves `decision` on purpose: E-03, E-04 and E-09
> change from `refused` to `more_info`, identically in both runs (3 of 10).
> bilingual_clerk is the role that moves only `reason`: all four structured
> fields matched the policy officer on all ten enquiries in both runs, and only
> the language of `reason` changed (Kazakh on E-07).
>
> auditor also moves `decision`, but unstably. E-06 moved in both runs. E-02
> moved only in run 1 (`refused` while `missing_documents` still listed
> `id_card`, which contradicts the rule that a missing document gives
> `more_info`). E-01 and E-05 moved only in run 2. The same prompt gave 8/10
> in run 1 and 7/10 in run 2.

**2. Which enquiries are most sensitive to the role, and why those?** Say what
E-03, E-04, E-07 and E-10 are each testing.

> E-03, E-04 and E-09 are the most sensitive to front_desk: all three are
> refusals, and front_desk turned every one into `more_info` in both runs.
> E-03 tests a hard refusal on GPA (2.4 below 2.67, with good band and
> documents). E-04 tests a hard refusal on income band (3 not allowed, with good
> GPA and documents). E-09 is E-03 asked without the id, and it behaved the
> same, so the effect comes from the decision, not the wording.
>
> E-06 is the most sensitive to auditor: it is the only enquiry the auditor
> moved in both runs. It is a borderline case (GPA 2.7 against a minimum of
> 2.67), which is where "needs a second reader" is easiest to say.
>
> E-07 tests language: the Kazakh enquiry should give the same decision as
> E-01, and it did under every role. Only `reason` changed: bilingual_clerk
> wrote Kazakh in both runs. In run 2 the auditor also wrote Kazakh without
> being told to, so the reply language is partly chosen by the model itself.
>
> E-10 tests a claim against the record: the applicant says the id card was
> uploaded, the record does not show it. Every role kept `more_info` with
> `id_card` missing in both runs, so no role accepted the claim. In run 2 the
> auditor's `reason` says the claimed upload is not in the record.

**3. Where does discretion belong — the role paragraph, or code that reads
`decision` afterwards?** Say what a downstream program can and cannot tell
about which role produced a record.

> In code that reads `decision`. The record has no field for the role, so a
> downstream program cannot tell which role produced it. A front_desk
> `more_info` on E-03 has the same shape as a real `more_info` on E-02.
> The program can only see indirect signs: `more_info` with an empty
> `missing_documents` (front_desk on E-03, E-04, E-09) or `refused` with a
> non-empty `missing_documents` (auditor run 1, E-02). It cannot see why.
> If the role decides, the same applicant gets a different outcome depending
> on which paragraph was used, and the auditor gave different outcomes for the
> same paragraph across two runs. Discretion is safer as an explicit rule in
> code, applied to a decision that the model produced from the record.

**4. Is a role a boundary?** Say in Week 2 terms what the role paragraph is
made of, and what you would put in code — not in the prompt — if a wrong
`decision` were expensive.

> No. The role paragraph is text: tokens that enter the same context as the
> records and the enquiry, and the model continues that whole document. It is
> a strong hint, not an enforced rule. The auditor paragraph says "never grants
> on a first reading", yet the auditor returned `granted` on E-01, E-05 and
> E-07 in run 1 and on E-07 in run 2.
>
> If a wrong decision were expensive I would recompute the four fields in code
> from `records.json` and `policy.json` (GPA at least 2.67, band 1 or 2, both
> documents, amount by band), compare them with the model's reply, and act
> only when they match; otherwise send it to a human. I would also validate the
> schema, reject `more_info` with an empty `missing_documents`, and log the
> role and prompt version with every record.

---

## Sublab Medium — memory you choose

Model: `gpt-5.6-luna`. The assistant gets the grant rule but **not** the
applicant records, so the probes test the conversation memory only. The
scripted run was done twice (Run 1 first, Run 2 after each table). Column A
skips the
`<compress>` turn; column B runs `compress()` there.

### Tokens per call

**Run 1**

Position = place in the twelve scripted turns. "Tokens" = prompt tokens sent,
read from the API response. The replies differ a little between A and B
(the model is not deterministic), so the histories, and the numbers before
turn 10, are not exactly equal.

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 226 | 226 |
| 2 | 344 | 304 |
| 3 | 414 | 375 |
| 4 | 476 | 449 |
| 5 | 540 | 516 |
| 6 | 597 | 592 |
| 7 | 668 | 659 |
| 8 | 736 | 722 |
| 9 | 793 | 794 |
| 10 | — (skipped) | 1149 (the compress call itself) |
| 11 | 846 | 559 |
| 12 | 900 | 609 |
| **peak** | 900 | 1149 |
| **total for the run** | 6540 in / 760 out | 6954 in / 1512 out |

The five probes were asked after the conversation, each one alone (they were
not added to the history). Prompt tokens for the five probes together:
A = 4725, B = 3265. Including the probes, total input tokens: A = 11265,
B = 10219.

**Run 2** (same program, same script, run again)

| Call | A — never compressed | B — compressed at the `compress` turn |
|---|---|---|
| 1 | 226 | 226 |
| 2 | 331 | 324 |
| 3 | 406 | 394 |
| 4 | 490 | 462 |
| 5 | 567 | 528 |
| 6 | 644 | 612 |
| 7 | 715 | 712 |
| 8 | 795 | 789 |
| 9 | 862 | 845 |
| 10 | — (skipped) | 1198 (the compress call itself) |
| 11 | 927 | 548 |
| 12 | 989 | 599 |
| **peak** | 989 | 1198 |
| **total for the run** | 6952 in / 877 out | 7237 in / 1497 out |

Run 2 probes, prompt tokens for the five together: A = 5175, B = 3195.
Including the probes, total input tokens: A = 12127, B = 10432.

### Probes after the conversation

**Run 1**

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You identified yourself as Daniyar Qoshan, applicant A-202. | yes | You are Daniyar Qoshan. Your applicant number is A-202. |
| Q-2 missing document | turn 5 | yes | Based on what you told me, your ID card has not yet been uploaded. I can’t verify the status of the transcript or other records without access to applicant records. | yes | Your ID card is still missing from your file; the transcript was sent, but we cannot verify that it is on file. |
| Q-3 band and amount | turns 3–4 | yes | I can’t verify your income band from the applicant record in this chat. If your recorded band is 2, the amount would be 150,000 tenge, but eligibility is not confirmed. | yes | You stated that your income band is 2, but it has not yet been verified in the record. If verified and you qualify, the grant amount would be 150,000 tenge. |
| Q-4 the constraint | turn 6 | yes | You said you can come to the office on Thursdays. Please confirm the office’s opening hours before visiting. | yes | You can come to the office on Thursday. |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count or whether the original was required. I said the grant rules do not specify the format and advised confirming it with the office. | yes | You asked whether a scanned employer letter would be accepted or whether the original is required. |
| **retrieved** | | 5/5 | | 5/5 | |

**Run 2**

| Probe | Tests | A retrieved? | A answer | B retrieved? | B answer |
|---|---|---|---|---|---|
| Q-1 identity | turn 1 | yes | You are Daniyar Qoshan, applicant **A-202**. | yes | You are Daniyar Qoshan, and your applicant number is A-202. |
| Q-2 missing document | turn 5 | yes | The **ID card** is still missing based on what you told me. The transcript was reported as submitted, but I cannot verify its presence in the record. | yes | Your ID card is still missing from your file; the transcript is already on file. |
| Q-3 band and amount | turns 3–4 | yes | I can’t verify your income band from the applicant record; you only stated that it is band 2. If band 2 is verified and all other requirements are met, the grant amount is **150,000 теңге**. | yes | Your income band is 2, which corresponds to 150,000 теңге if your application is approved. |
| Q-4 the constraint | turn 6 | yes | You said you can come to the office on **Thursday**. I don’t have access to the office’s schedule, so I can’t confirm that Thursday is an official reception day. | yes | You can come to the office on Thursdays. |
| Q-5 the open question | turn 7 | yes | You asked whether a scanned letter from your employer would count, or whether the original was required. I explained that the grant rules only specify a transcript and ID card, so I couldn’t confirm the office’s requirements for that letter. | yes | You asked whether a scanned employer letter is acceptable or whether the original is required. |
| **retrieved** | | 5/5 | | 5/5 | |

### The state my compression produced

Run 1:

```json
{
  "applicant_id": "A-202",
  "topic": "Eligibility and application requirements for a study grant.",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent a transcript last week.",
    "The applicant stated that their income band is 2, according to their family's certificate.",
    "The applicant could not upload their ID card because the scanner at home broke.",
    "The applicant can come to the office only on Thursdays because they have lab all week otherwise.",
    "The applicant's sister Aruzhan applied last year and is on file."
  ],
  "decisions": [
    "The grant amount would be 150,000 tenge if the applicant qualifies and their verified income band is 2.",
    "The applicant can bring their ID card to the grant office on Thursday for assistance with uploading it.",
    "The rules specify the transcript and ID card as required documents.",
    "Eligibility and the applicant's records cannot currently be verified."
  ],
  "constraints": [
    "Eligibility requires a GPA of at least 2.67.",
    "Eligibility requires a verified income band of 1 or 2.",
    "Both the transcript and ID card must be on file.",
    "The applicant can visit the office only on Thursdays.",
    "The decision timeline is not specified in the grant rules."
  ],
  "open_questions": [
    "Whether a scanned employer letter is accepted or the original is required.",
    "Whether a decision would be made on the same day if the ID card is brought on Thursday.",
    "Whether the applicant ultimately qualifies for the grant."
  ],
  "language": "Kazakh and English"
}
```

Run 2:

```json
{
  "applicant_id": "A-202",
  "topic": "Eligibility and document requirements for a study grant.",
  "facts": [
    "The applicant's name is Daniyar Qoshan.",
    "The applicant sent a transcript last week.",
    "The applicant's income band is 2 according to the family's certificate.",
    "The applicant could not upload the ID card because the scanner at home broke.",
    "The applicant can only come to the office on Thursdays because of lab work during the rest of the week.",
    "The applicant has a sister named Aruzhan who applied last year and is on file."
  ],
  "decisions": [
    "Eligibility could not be confirmed because applicant records were inaccessible.",
    "The grant amount would be 150,000 tenge if approved with income band 2.",
    "The application currently does not meet the document requirement because the ID card is not on file.",
    "Aruzhan's application or record does not affect the applicant's eligibility."
  ],
  "constraints": [
    "Eligibility requires a recorded GPA of at least 2.67.",
    "Eligibility requires income band 1 or 2.",
    "Eligibility requires both the transcript and ID card to be on file.",
    "The applicant can visit the office only on Thursdays."
  ],
  "open_questions": [
    "Does a scanned employer letter count, or must it be the original?",
    "If the applicant brings the ID card on Thursday, will the decision be made the same day?",
    "Does the applicant qualify for the study grant?"
  ],
  "language": "Kazakh and English"
}
```

### What I saw in `--interactive`

I typed five short messages (name and id, income band 2, "only Thursdays", a
question about a scanned employer letter, and my mother's phone number), then
`compress`, then three questions.

- Tokens sent per call before compress: 219, 282, 334, 376, 429. The compress
  call itself sent 798 tokens, more than any normal call in that short chat.
- After compress: 414, 460, 495. The first call after compress was only 15
  tokens cheaper than the last one before it (429), because the state (about
  as long as five short turns) replaced only five short turns.
- The state kept the id, the band, Thursday and the employer question, and even
  the phone number. Nothing I said was lost.
- What was lost is the assistant's earlier judgement. Before compress the bot
  said it could not use or verify a family member's phone number. After
  compress, asked "What is my phone number?", it said "The phone number on
  record is your mother's". The state stored the number as a plain fact, so the
  bot treated a claim as a record. The employer question was also shortened
  from "does it count" to "was it required".

### Written answers

**1. What did compression buy?** Peak tokens both ways, probes retrieved both
ways, and — if a probe was lost — which one and which turn it came from.

> Peak tokens (one call): 900 without compression and 1149 with it in run 1;
> 989 and 1198 in run 2. The peak got higher both times, because the compress
> call has to send the whole conversation plus the schema. Probes retrieved:
> 5/5 both ways in both runs, so no probe was lost, including Q-4 (turn 6) and
> Q-5 (turn 7).
>
> What compression bought is cheaper calls afterwards. Call 11 and call 12 cost
> 846 / 900 without compression and 559 / 609 with it in run 1 (about 290
> less), and 927 / 989 vs 548 / 599 in run 2 (about 385 less). The five probes
> cost 3265 instead of 4725 in run 1 (31% less) and 3195 instead of 5175 in run
> 2 (38% less). The compress call costs 1149-1198 tokens and makes the output
> longer (1497-1512 vs 760-877 output tokens), so it pays back after about
> three or four more calls. Over the twelve turns alone, B sent more input
> (6954 vs 6540, and 7237 vs 6952). Counting the probes, B sent less: 10219 vs
> 11265 in run 1 and 10432 vs 12127 in run 2. The longer the conversation goes
> on after compress, the bigger the gain.

**2. Why must the state be structured rather than a paragraph?** You could have
asked for "a summary". Say what changes when the summary is an object with
named fields.

> With named fields the model has to decide where each thing goes, and there is
> a slot for constraints and one for open questions. A free paragraph follows
> the main story and can drop a small thing like "only Thursdays" without any
> sign. In my run both were kept, in `constraints` and `open_questions`. A
> structured state can also be checked by code: the schema check rejects a
> summary with missing fields or wrong types, and my program keeps the history
> when this happens. Code can also read `applicant_id` directly. A paragraph
> cannot be validated or parsed. The limit is that the schema checks the shape,
> not the meaning: in my state the model put grant rules (GPA, documents) in
> `constraints`, and the applicant's sister in `facts`, and both passed.

**3. What is missing from your state that you would add?** Name what you would
add and what you would drop to pay for it.

> I would add a mark for where each fact comes from: stated by the applicant,
> or checked in a record. In the interactive test the bot turned "my mother's
> phone number is ..." into "the number on record" after compress, because the
> state did not say it was only a claim. Run 2 shows the same thing: on Q-2
> the uncompressed bot said it could not verify the transcript, but the
> compressed bot said "the transcript is already on file", and on Q-3 it
> dropped the warning that the band was only stated by the applicant. I would also add a `documents` field
> (sent / not sent), because now it is buried in sentences in `facts`. To pay
> for it I would drop `topic` (one sentence that nothing used), and I would tell
> the model to skip facts that do not matter for the grant, such as the sister,
> and not to copy the grant rules into `constraints`.

**4. When is compression the wrong choice?** Name a conversation where it would
lose something that cannot be recovered, and say whether your program would
notice.

> When the exact words matter or when every detail may be needed later, for
> example a legal or medical conversation, a negotiation, or a conversation
> with ids, amounts and dates that someone may need to quote. Once the turns
> are thrown away, a detail that the summary dropped is gone. My program would
> not notice: it only checks that the JSON matches the schema, and a state
> that forgot a fact is still valid (an empty `open_questions` also passes).
> In my run I only know that nothing was lost because I asked five probe
> questions whose answers I knew. A safer design keeps the full transcript in a
> log and sends only the state to the model, so nothing is lost for good.

---

## Sublab Hard — stories in, CVs out, the best candidate by code

Model: `gpt-5.6-luna`. Pipeline: the model extracts a CV from each story (the
rules are in the prompt); my code re-counts publications, converts the GPA and
counts months, and checks that every evidence quote is in the story; the model
gives three 0–5 scores from the checked CV; my code computes the weighted total
and the winner. Final version of the program, run twice (run 1 / run 2).
An earlier version of the program was also run twice; see written answer 1.

### Part 1 — extraction

| Story | Parsed? | Valid? | Fields that came back `null` | Traps hit |
|---|---|---|---|---|
| story-01 | yes / yes | yes / yes | none | none of the four: two published peer-reviewed papers, 8 months match the dates |
| story-02 | yes / yes | yes / yes | graduation_year, gpa_original, gpa_scale, gpa_4_scale | no GPA stated (left null, not estimated). Also: 36 months with no calendar dates (my code counted 0), and one published paper with no peer review stated |
| story-03 | yes / yes | yes / yes | none | GPA on another scale (4.6 of 5.0, model and code both 3.68); a paper under review (not counted) |
| story-04 | yes / yes | yes / yes | none | papers that are not published: 1 under review and 2 in preparation, so 1 counted out of 4 |
| story-05 | yes / yes | yes / yes | none | a paper in preparation (not counted); the story is in Kazakh and was extracted correctly |
| story-06 | yes / yes | yes / yes | graduation_year, gpa_original, gpa_scale, gpa_4_scale | the story contradicts itself: GPA 3.2 vs 3.5 and "graduated 2024" vs "graduating 2026" (both left null and written in `ambiguities`); a poster (not counted); "about forty months" (flagged as approximate in run 2 only) |

The four traps, for reference: no GPA stated · a GPA on another scale · a paper
that is not published · a story that contradicts itself.

Checks by code, both runs: the model's GPA and publication count matched my
code's on every story. The model's own month count differed from my code's on
one story: story-02 in run 1 (model 36, code 0, because the period has no
calendar start date). Evidence quotes that were not found word for word in the
story: run 1, `outputs[2].status` (story-04); run 2, `experience_months_countable`
(story-03) and `experience_periods[0].description` (story-04). All other quotes
(more than 150) were found.

The extraction for **story-06** (run 2), the one that contradicts itself:

```json
{
  "full_name": "Nurzhan Abilov",
  "degree": "BSc in Statistics",
  "graduation_year": null,
  "gpa_original": null,
  "gpa_scale": null,
  "gpa_4_scale": null,
  "languages": [
    "Kazakh",
    "Russian",
    "English"
  ],
  "outputs": [
    {
      "title": null,
      "description": "Paper on survey weighting published in peer-reviewed proceedings",
      "status": "published",
      "peer_reviewed": true
    },
    {
      "title": null,
      "description": "Poster presented at a local event",
      "status": "other",
      "peer_reviewed": null
    }
  ],
  "published_peer_reviewed_count": 1,
  "experience_periods": [
    {
      "description": "Insurance analytics team",
      "start": "2023-02",
      "end": null,
      "ongoing": true,
      "months_stated": 40
    }
  ],
  "experience_months_countable": 40,
  "evidence": {
    "full_name": "Nurzhan Abilov",
    "degree": "I graduated in 2024 with a BSc in Statistics.",
    "languages": "Languages: Kazakh, Russian, English.",
    "outputs[0].description": "One paper published, in a peer-reviewed proceedings, on survey weighting.",
    "outputs[0].status": "One paper published, in a peer-reviewed proceedings",
    "outputs[0].peer_reviewed": "in a peer-reviewed proceedings",
    "outputs[1].description": "One poster at a local event",
    "outputs[1].status": "One poster at a local event, which I do not think counts.",
    "published_peer_reviewed_count": "one paper published, in a peer-reviewed proceedings",
    "experience_periods[0].description": "I have been at an insurance analytics team since February 2023",
    "experience_periods[0].start": "since February 2023",
    "experience_periods[0].ongoing": "I have been at an insurance analytics team since February 2023",
    "experience_periods[0].months_stated": "which is about forty months",
    "experience_months_countable": "which is about forty months"
  },
  "ambiguities": [
    "GPA is contradictory: the story states both 3.2 and 3.5, so GPA fields are null.",
    "Graduation status and year are contradictory: the story says the candidate graduated in 2024 and also is a final-year student graduating in 2026.",
    "The stated experience duration is approximate: \"about forty months.\""
  ]
}
```

### Part 2 — scores and the winner

Cells are run 1 / run 2. "1→0" means the model gave 1 and my code changed it to
0 (see written answer 1).

| Candidate | academic (0–5) | research (0–5) | experience (0–5) | weighted total (code) |
|---|---|---|---|---|
| story-01 | 5 / 5 | 5 / 5 | 2 / 2 | 4.4 / 4.4 |
| story-02 | 0 / 1→0 | 0 / 0 | 0 / 0 | 0.0 / 0.0 |
| story-03 | 4 / 4 | 3 / 3 | 4 / 4 | 3.7 / 3.7 |
| story-04 | 4 / 4 | 3 / 3 | 5 / 5 | 3.9 / 3.9 |
| story-05 | 5 / 5 | 3 / 3 | 2 / 2 | 3.8 / 3.8 |
| story-06 | 1→0 / 1→0 | 3 / 1 | 5 / 5 | 1.9 / 1.3 |

Total = 0.5 × academic + 0.3 × research + 0.2 × experience, computed in code.

**Winner, computed by my code:** story-01 (Aziza Bekova), total 4.4 in both
runs. Ranking in both runs: story-01 (4.4), story-04 (3.9), story-05 (3.8),
story-03 (3.7), story-06 (1.9 / 1.3), story-02 (0.0).

**The model's prose answer, asked separately ("who should win?"):**

Run 1:

> Aziza Bekova should receive the scholarship. She has the strongest academic record, with a 3.8/4.0 GPA, and is the only candidate with two clearly published peer-reviewed outputs, satisfying the top research criterion. Although her directly relevant experience is limited to eight months, her substantial academic and research strengths carry the greatest weight in the rubric and make her the strongest overall candidate.

Run 2:

> Aziza Bekova should win the scholarship. She has the strongest academic record, with a 3.8/4.0 GPA, and the strongest research profile, with two clearly published peer-reviewed papers. Although her directly relevant work experience is only eight months, these advantages outweigh the longer experience of candidates whose academic records or publication output are weaker.

### Part 3 — written answers

**1. Which rule did you have to add, and what broke without it?** Name the
story that forced it.

> I added a rule in code: if a candidate has no usable GPA, `academic` is set
> to 0, as the rubric says. Without it the model gave a non-zero academic
> score to stories with no usable GPA: story-02 (no GPA) and story-06
> (contradicted GPA). Counting my first two runs (an earlier version of the
> program) and my last two, this happened in 6 of 8 story-runs, for example
> story-06 got academic 1 in both of the last two runs. Story-06 forced it,
> because a story with a GPA of "3.2 or 3.5" tempts the model to give partial
> credit. The code now applies the rule and prints the override.
>
> I also had to change my schema. In the earlier version `title` had to be a
> string, but story-03 gives no paper titles, so the model correctly wrote
> `null`, and the record failed validation in both runs (story-01 also failed
> in one run). The story that forced it was story-03. I made `title` nullable
> and added a `description` field.

**2. Where did the model guess, and where did your code have to decide?** One
example of each, from your run.

> The model guessed on story-06's `academic` score: the GPA was null, and the
> rubric says 0, but the model gave 1 in both runs. It also guessed on the
> middle of the scale, where the rubric has no anchors: for story-06, with one
> published paper, `research` was 3 in run 1 and 1 in run 2. My code decided on
> story-02's experience: the model reported 36 months in run 1, but the period
> has no calendar start date, so the rubric says it is not countable and my code
> counted 0. Code also recomputed story-03's GPA (4.6 / 5.0 × 4 = 3.68), and
> that matched the model.

**3. Did your prose ranking and your computed ranking agree?** Say which one
you trust and why — and if they agreed, what you would need to see before
trusting the prose one alone.

> They agreed in both runs: both chose story-01. I trust the computed one,
> because I can check each number behind it (counts, months, GPA, scores). The
> prose answer only names a winner; it gives no counts for the other five
> candidates, so I cannot see why the others lost. To trust the prose answer
> alone I would need it to give per-candidate figures that I can check, the same
> winner over many runs, and a changed answer when I change a story (for example
> remove a paper). One more reason for care: in my earlier version, story-01 and
> story-03 failed validation and were not scored, so the computed winner was
> story-04 while the prose answer still chose story-01. A computed ranking is
> only as good as the records that reach it.

**4. The rubric has no anchor for a contradicted field.** The stories say 3.2
and then 3.5; the rubric defines a 0 and a 5 and nothing in between for this
case. Say what I did and what the rule should be.

> I told the model to set the contradicted field to null and write the
> contradiction in `ambiguities`, which it did for story-06 (GPA and graduation
> year). Then the rubric's "no GPA scores 0" applied, so story-06 got academic
> 0, even though its degree is stated. That is not fair, and it hides the
> problem: a 0 looks like a weak record. I think the rule should be: do not
> give a score, mark the field "contradicted", score the candidate at both
> values (3.2 and 3.5), and if the ranking does not change, say so; if it does,
> the committee decides. Neither averaging nor choosing one value is allowed.

**5. How close were your top two candidates?** If they were within 0.05, say
what you would tell the committee and what you would change in the extraction
to make that call defensible.

> Story-01 (4.4) and story-04 (3.9) were 0.5 apart in both runs, so not close.
> With integer scores and these weights, the smallest possible gap between two
> different totals is 0.1, so a gap of 0.05 cannot happen; it is either a tie or
> at least 0.1. The closest pairs in my results were story-04 / story-05 (3.9 vs
> 3.8) and story-05 / story-03 (3.8 vs 3.7). A 0.1 gap is one point on one
> criterion, and the model moved scores by more than that between runs
> (story-06 research 3 vs 1 changes the total by 0.6), so those gaps are not
> reliable. For a tie I would tell the committee that the ranking cannot
> separate them, and show the facts (GPA, counted papers, counted months) for
> them to decide. To make it defensible I would define anchors for the middle
> scores, score each candidate several times and report the spread, and keep
> the counts and dates in the record next to each score.

---

## Reflection (optional, one short paragraph)

Having now written a role prompt, compressed a conversation, and ranked six
extractions — what will you do differently the next time you build something
that has to get reliable structured output out of a model?

> I will let code count and check everything a program can count, and use the
> model only to read and to judge. I will also validate every reply and read
> the failures before trusting a table: my first schema rejected a correct
> `null`, and two candidates silently dropped out of the ranking. And I will
> run every experiment at least twice, because the same prompt gave
> different scores each time.