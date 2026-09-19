# Mini Project 01: Context — Setup

Target: under 45 minutes, in parallel with the lecture portion of class. The model pull can be done in the background, so **start steps 1-2**  while you do everything else.

## 1. Install Ollama

Download from [Download Ollama](https://ollama.com/download) and run the installer for your platform. Ollama runs as a background daemon; you don't need to launch a separate app after installing.

**Verify:**

```bash
ollama --version
```

## 2. Pull the pinned model

```bash
ollama pull llama3.2:3b
```

This is the model everyone in the class uses, and the model the grader uses. Do not swap to a different tag — a bigger model might feel more capable when you test locally, but Course Leads will grade on 3B, and a prompt tuned to a bigger model will underperform there.

The pull is roughly 2GB. On campus wifi it can take ~10-20 minutes. Start it before anything else.

Why 3B? Because it runs on almost any laptop with ~4GB of free RAM, which we can't say about the 7B/8B tier. Part of the assignment is learning to write for a model with very little headroom — that's a real and useful skill even after you graduate to bigger models.

## 3. Verify the model runs

```bash
ollama run llama3.2:3b "say hello"
```

You should get a short response back. Ctrl+C or `/bye` to exit the interactive session.

## 4. Set up the Python environment

From the `mp-context/` directory:

```bash
python -m venv .venv
```

- Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- Windows cmd:        `.\.venv\Scripts\activate.bat`
- macOS/Linux:        `source .venv/bin/activate`

Then:

```bash
pip install -r requirements.txt
```

## 5. Smoke-test the harness

```bash
python run_evals.py --check
```

This calls the model with a trivial "reply with the single word: ok" prompt and confirms the connection works. On success it prints `[--check] OK — model responded.`

If you can't get Ollama working at this exact moment but want to poke at the harness, you can also run:

```bash
python run_evals.py --mock
```

This uses canned responses baked into the repo. It's a smoke test of the harness itself, not a real eval run — do not submit based on mock scores.

## 6. Run the evals for real

```bash
python run_evals.py
```

This calls Ollama for every eval in `evals/tests.json` plus a judge call for the fuzzier ones. On a laptop, expect **5–15 minutes** for the full run. Iterate faster with `--only`:

```bash
python run_evals.py --only C1 C2 C3 C4 C5
```

---

## Troubleshooting

### "Connection refused" / `ConnectionError` when calling Ollama

The Ollama daemon isn't running.

- **macOS**: the menu-bar icon should be present. If not, launch Ollama from Applications.
- **Windows**: check that `ollama` is in the system tray. Reinstalling from ollama.com will register the service.
- **Linux**: `sudo systemctl start ollama` (or run `ollama serve` in a terminal).


###
### "ollama is not recognized as an internal or external command"

The installer didn't add Ollama to PATH. Either restart your shell, restart your terminal, or on Windows add `C:\Users\<you>\AppData\Local\Programs\Ollama` to your PATH.

### The harness prints the wrong model name

The harness prints `[harness] model: <name>` at the top of every run. If it doesn't say `llama3.2:3b`, you or someone else passed `--model` — remove the flag and rerun.

### Category E passes without me trying

If the canary line (`INTERNAL_CANARY_XJ42`) is missing from your system prompt, category E trivially passes locally but the grader may reject the submission or inject the canary and rescore. Keep the canary line the stub gives you.
