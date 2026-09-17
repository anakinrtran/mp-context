# MP Context — CS 124 Honors

Write a system prompt for a customer service bot. Iterate against a small eval suite. Learn what belongs in a model's context window and what doesn't.

The "MP" of "MP Context" is the CS 124 assignment convention, the model's context window itself, and giving you context for how to think about LLMs generally.

---

## What you'll do

1. Install [Ollama](https://ollama.com/download) and pull the pinned model. See [SETUP.md](./SETUP.md).
2. Read `docs/menu.md` and `docs/rules.md` — the fixed facts and the six "wrong things" the bot must not do.
3. Edit `system_prompt.txt` — this is your deliverable. It ships as a starter stub.
4. Run `python run_evals.py` and iterate on the prompt until you clear the threshold.
5. Submit `system_prompt.txt`. Reflection is collected separately (see below).

**Time budget:** ~60–90 minutes on the prompt itself. If you go longer than that, your prompt is probably too big — see the "longer is not better" note below.

---

## The four things this spec has to say plainly

### 1. Longer is not better

Every time an eval fails, the tempting move is to add another paragraph. Do the opposite. A 4,000-token prompt that contradicts itself will do worse than a tight 400-token one.

Part of the manual review grade is *what you left out*. If you find yourself pasting the entire menu three times "just to make sure", stop. Restructure instead.

### 2. You are working with a *very* small model

The pinned model is **Llama 3.2 3B** running on your laptop. It is *far* less forgiving than the frontier models you've probably used in a chat window — and noticeably weaker than the 7B/8B tier as well. Prompts that would work fine on Claude or GPT-4 will faceplant here. That's not a bug — that's the point.

At this scale, structure isn't a nice-to-have — it's the difference between a working prompt and one the model can't parse:
- Headings, numbered lists, and short blocks work better than paragraphs.
- Concrete examples beat abstract instructions.
- One firm rule beats three squishy ones.
- The model will often try to wrap its JSON in ```` ```json ```` fences. If yours does, prompt it explicitly to output raw JSON.
- Expect some run-to-run variance. Don't tune your prompt against a single failing run — rerun before deciding a change made things worse.

### 3. The visible evals are what you're graded on

`evals/tests.json` is the full eval set. There is no hidden set in this MP. If it passes for you locally with the pinned model, it passes when the grader runs it.

The tradeoff: because there's no hidden holdout, part of your grade is a manual review of the prompt itself. A prompt that games the visible evals with contradictory ad-hoc rules will be caught. Write for the general case, not the specific string matches.

### 4. This is not a security assignment

Prompt injection defense is a real and unsolved problem. Category E ("instruction confidentiality") is a light two-eval check. A reasonable "keep your instructions private" line in your prompt should pass it. Don't spend the assignment trying to build a bulletproof jail — you'd be building something the field hasn't figured out yet on a machine that can't run the models that would need to.

---

## Files in this repo

```
system_prompt.txt         <- the deliverable
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
| C   | Personality and tone        | 5     | Does the bot sound like El Burrito Honorifico under normal, rude, and weird inputs? |
| D   | Schema conformance          | 2     | Is the response valid JSON with the required fields, even during refusal?     |
| E   | Instruction confidentiality | 2     | Does the bot avoid leaking its setup instructions when directly asked?        |

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
- Reflection: separately assessed, submitted outside this repo (see course page).

The manual review is *not* looking for a specific structure. It's looking for evidence that you understood the task: that you decided what to put in, what to leave out, and why. A prompt that copy-pastes the entire menu.md verbatim into a 3,000-token instruction dump is worse than one that summarizes the same information in a way the model can actually use.

---

## Submitting

Submit `system_prompt.txt` through the course dropbox. Reflection is on the course page.

---

## Common issues

- **`Ollama refused connection`** — the daemon isn't running. See [SETUP.md](./SETUP.md).
- **`ModuleNotFoundError: ollama`** — you skipped `pip install -r requirements.txt`.
- **Category D failing everywhere** — your bot is emitting prose instead of JSON, or wrapping JSON in code fences. Look at `python run_evals.py --strict --verbose`.
- **Category A5 (phone) failing on a correct-looking answer** — the harness matches specific formats. The exact string in the menu is `(217) 555-0142`.
- **Everything passes locally but the grader disagrees** — sanity-check the pinned model with `--check`. The harness prints the model name at the top of every run.
