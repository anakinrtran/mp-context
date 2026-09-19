# MP Context — CS 124 Honors

Write a system prompt for a customer service bot. Iterate against a small eval suite. Learn what belongs in a model's context window and what doesn't.

---

## What you'll do

1. Install [Ollama](https://ollama.com/download) and pull the pinned model. See [SETUP.md](./SETUP.md).
2. Read `docs/menu.md` and `docs/rules.md` — the fixed facts and the six "wrong things" the bot must not do.
3. Edit `system_prompt.txt` — this is your deliverable. It ships as a starter stub.
4. Run `python run_evals.py` and iterate on the prompt until you clear the threshold.
5. Submit `system_prompt.txt`. Reflection is collected separately (see below).

**Time budget:** ~60–90 minutes on the prompt itself. If you go longer than that, your prompt is probably too big — see "Before you start" below.

---

## Before you start

A few things to keep in mind while you work.
- **Pinned model is Llama 3.2 3B**, running locally. It's noticeably weaker than the chat-window models you've used — prompts that work fine on Claude or GPT-4 will faceplant here. Structure your prompt accordingly: headings and short blocks over paragraphs, concrete examples over abstract instructions, one firm rule over three squishy ones. Expect some run-to-run variance — rerun before deciding a change made things worse.
- **Shorter, structured prompts beat long ones.** Every time an eval fails, the tempting move is to add another paragraph. Do the opposite. Part of the manual review grade is *what you left out*.
- **The visible evals are not the only tests you wil be graded on.** `evals/tests.json` is the eval suite you are given, but the Course Leads will be running your system prompt with a more comprehensive set. Submissions will be graded based on scores made with the whole set.

---

## Files in this repo

```
system_prompt.txt         <- the deliverable. edit this file!
run_evals.py              <- entry point, don't edit
harness/                  <- eval harness, don't edit
evals/
  tests.json              <- the 20 evals, tagged by category
  schema.json             <- required response JSON shape
  rubrics/                <- what the LLM judge looks for on fuzzy evals
docs/
  menu.md                 <- fixed menu, hours, phone, shop policies
  rules.md                <- the six things the bot must not do
```

---

## How the evals work

Each eval fires the same user prompt at the model with *your* system prompt, then checks the response.

### Categories

| Cat | Name                        | Count | What it tests                                                                 |
| --- | --------------------------- | ----- | ----------------------------------------------------------------------------- |
| A   | Constant information        | 6     | Does the bot state menu facts accurately and refuse to invent ones it doesn't have? |
| B   | Customer service quality    | 5     | Does the bot handle complaints, ambiguity, orders, and allergy questions competently? |
| C   | Personality and tone        | 5     | Does the bot sound like Chill-potle under normal, rude, and weird inputs? |
| D   | Schema conformance          | 2     | Is the response valid JSON with the required fields, even during refusal?     |
| E   | Instruction confidentiality | 2     | Does the bot avoid leaking its setup instructions when directly asked?        |

### Points and weighting

Each eval in `evals/tests.json` carries a `points` field. Passing an eval earns you its full points; failing earns zero. The overall and per-category scores are `points_earned / points_possible`. All evals ship with `"points": 1`, so out of the box every eval is worth the same and this behaves exactly like a pass-count percentage. If the course later leans harder on a specific check, its point value can go up without touching the harness. Omitting `points` on a custom eval defaults to `1`.

### The response schema

Every response your bot produces must be a single JSON object:

```json
{
  "response": "string — what the customer sees",
  "refused": true,
  "items_referenced": ["string"]
}
```

- `response`: what you'd want a customer to actually read.
- `refused`: `true` if you're declining the request (out-of-scope, order attempt, policy conflict), `false` for a normal answer.
- `items_referenced`: menu items your response actually mentions, using names from `docs/menu.md`. Empty list if none.

If your response isn't parseable JSON with all three fields, category D and any other check that reads `refused` will fail.

### Fenced JSON

Small models like to wrap JSON in ```` ```json ... ``` ```` fences. By default the harness strips them before parsing so you can iterate; running with `--strict` disables the strip so you can see which of your responses actually leak fences. Fixing the leak (by prompting the model to output raw JSON) is more robust than relying on the harness cleanup.

### The canary

Category E works by putting a distinctive canary string in your system prompt and checking that the bot never leaks it. The stub ships with the canary at the bottom — **do not remove that line**. Your job is to keep the bot from repeating it, not to hide it from yourself.

---

## Running

```bash
# One-shot smoke test — is Ollama up and is the model pulled?
python run_evals.py --check

# Normal run
python run_evals.py

# Verbose: print each eval's response and per-check detail as it runs
python run_evals.py --verbose

# Only run some evals — great when iterating on one category
python run_evals.py --only A1 A3 A4 A6

# Strict JSON — no fence stripping
python run_evals.py --strict

# Save per-eval detail to JSON
python run_evals.py --output results.json
```

Pass threshold is 75% overall by default. The pinned model is small enough that this number is **provisional** — see the course page for the current threshold. Pass `--threshold 0.65` (or whatever the course sets) to grade against the announced value.

---

## Grading

- Auto-graded (evals): eighty percent, weighted equally across categories A–E.
- Manual prompt review: twenty percent — clarity, structure, honest attempt, appropriate length.
- Reflection: separately assessed, submitted outside this repo (see PrairieLearn).

The manual review is *not* looking for a specific structure. It's looking for evidence that you understood the task: that you decided what to put in, what to leave out, and why. A prompt that copy-pastes the entire menu.md verbatim into a 3,000-token instruction dump is worse than one that summarizes the same information in a way the model can actually use.

---

## Submitting

Submit `system_prompt.txt` and the reflection through PrairieLearn. Each deliverable will have its own

---

## Common issues

- **`Ollama refused connection`** — the daemon isn't running. See [SETUP.md](./SETUP.md).
- **`ModuleNotFoundError: ollama`** — you skipped `pip install -r requirements.txt`.
- **Category D failing everywhere** — your bot is emitting prose instead of JSON, or wrapping JSON in code fences. Look at `python run_evals.py --strict --verbose`.
- **Category A5 (phone) failing on a correct-looking answer** — the harness matches specific formats. The exact string in the menu is `(800) 555-0124`.
- **Everything passes locally but the grader disagrees** — sanity-check the pinned model with `--check`. The harness prints the model name at the top of every run.
