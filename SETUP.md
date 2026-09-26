# MP Context — Setup

Target: under 45 minutes, in parallel with the lecture portion of the Mini. Most of that time is the model download, which runs while you watch the lecture videos.

## When to do each step

| When | Steps | What you're doing |
| --- | --- | --- |
| When the first lecture video introduces Ollama | 1–2 | Pause the video, install Ollama, and start the model pull. Once `ollama pull` shows a progress bar, go back to the video. While you're in the terminal, also run `git --version`; if it fails, install Git now (see step 4). |
| Rest of the lectures | none | Leave the pull running and its terminal open. |
| After the lectures | 3–7 | Verify the model, clone the starter repo, set up Python, and run the smoke test and the evals. |

If the pull hasn't finished when the lectures end, wait for it before step 3. The pull is done when the terminal prints `success`. You can also check from any terminal with `ollama list`: if `llama3.2:3b` is listed, it's ready. If the pull gets interrupted (closed terminal, laptop asleep, wifi drop), run the same `ollama pull` command again.

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

This is the model everyone in the class will use for this Mini, and the model the grader uses. Do not swap to a different tag. A bigger model might feel more capable when you test locally, but Course Leads will grade on 3B, and a prompt tuned to a bigger model will underperform there.

The pull is roughly 2GB. On campus wifi it can take ~10-20 minutes. Once the progress bar appears, you can go back to the video.

Why 3B? Because it runs on almost any laptop with ~4GB of free RAM, which we can't say about the 7B/8B tier. Part of the assignment is learning to write for a model with very little headroom, and that skill still applies once you move to bigger models.

## 3. Verify the model runs

```bash
ollama run llama3.2:3b "say hello"
```

You should get a short response back. Ctrl+C or `/bye` to exit the interactive session.

## 4. Clone the starter repo

The starter code lives in a Git repository (a "repo"): a folder of files plus the history of every change made to them. Cloning downloads your own copy of that folder, history included. You'll edit `system_prompt.txt` inside it.

First check that Git is installed:

```bash
git --version
```

If that prints a version number, you're set. If not:

- **Windows:** install [Git for Windows](https://git-scm.com/downloads), then close and reopen your terminal.
- **macOS:** running `git --version` offers to install the Xcode Command Line Tools, which include Git. Accept, then run it again.
- **Linux:** install the `git` package with your package manager (for example, `sudo apt install git`).

Then `cd` into the folder where you keep your coursework and clone. The repo URL is on the course page:

```bash
git clone <repo-url>
cd mp-context
```

`git clone` creates a new `mp-context/` folder in whatever directory your terminal is in, so pick that directory first. Every command from here on runs inside `mp-context/`.

## 5. Set up the Python environment

From the `mp-context/` folder you just cloned:

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

## 6. Smoke-test the harness

```bash
python run_evals.py --check
```

This calls the model with a trivial "reply with the single word: ok" prompt and confirms the connection works. On success it prints `[--check] OK — model responded.`

If you can't get Ollama working at this exact moment but want to poke at the harness, you can also run:

```bash
python run_evals.py --mock
```

This uses canned responses baked into the repo. It only tests the harness itself, so mock scores say nothing about your prompt. Don't submit based on them.

## 7. Run the evals for real

```bash
python run_evals.py
```

This calls Ollama for every eval in `evals/tests.json` plus a judge call for the fuzzier ones. The suite is 25 evals. Expect roughly **1 minute** for a full run on a machine with a GPU, and **3–10 minutes** on a CPU-only laptop. `--runs 3` takes about 3x as long. Iterate faster with `--only`:

```bash
python run_evals.py --only C1 C2 C3 C4 C5
```

The harness asks Ollama to keep the model loaded for 30 minutes after each run, so re-runs while you're iterating on `system_prompt.txt` skip the ~2 GB reload. To change that window, see "First run is slow but re-runs are fast" under Troubleshooting.

---

## Troubleshooting

### "Connection refused" / `ConnectionError` when calling Ollama

The Ollama daemon isn't running.

- **macOS**: the menu-bar icon should be present. If not, launch Ollama from Applications.
- **Windows**: check that `ollama` is in the system tray. Reinstalling from ollama.com will register the service.
- **Linux**: `sudo systemctl start ollama` (or run `ollama serve` in a terminal).

### "ollama is not recognized as an internal or external command"

The installer didn't add Ollama to PATH. Restart your terminal, or on Windows add `C:\Users\<you>\AppData\Local\Programs\Ollama` to your PATH.

### The harness prints the wrong model name

The harness prints `[harness] model: <name>` at the top of every run. If it doesn't say `llama3.2:3b`, you or someone else passed `--model`; remove the flag and rerun.

### First run is slow but re-runs are fast

That's the model loading into RAM (~2 GB). The harness keeps it resident for 30 minutes after each call, so subsequent runs within that window skip the reload.

If you want a different window, set `MP_OLLAMA_KEEP_ALIVE` in the **same terminal you use to run `python run_evals.py`**, before you run it. The value is a duration string, not a raw number of minutes:

- `30m` — thirty minutes (the default)
- `2h` — two hours
- `90s` — ninety seconds
- `-1` — keep loaded until the Ollama daemon restarts or you reboot
- `0` — unload immediately after each call (useful if RAM is tight)

Set it like this (choose the row for your shell; the value survives until you close the terminal):

- **Windows PowerShell:** `$env:MP_OLLAMA_KEEP_ALIVE = "-1"`
- **Windows cmd:** `set MP_OLLAMA_KEEP_ALIVE=-1`
- **macOS / Linux (bash, zsh):** `export MP_OLLAMA_KEEP_ALIVE=-1`

Then run `python run_evals.py` as normal in that same terminal. Confirm it took effect by looking at the first line of the run's output: the harness prints `[harness] model: llama3.2:3b (num_ctx: <n>, keep_alive: <value>)` at the start of every run, and `<value>` should be whatever you set.

You can also verify from another terminal with `ollama ps`, which lists loaded models and when each is scheduled to unload.

### The bot "forgets" its persona or the menu partway through evals

The harness pins Ollama's `num_ctx` to 4096 tokens. If the whole conversation (your system prompt + the eval question + the JSON response) exceeds `num_ctx`, Ollama silently drops tokens from the *start* of the context, which is exactly where your persona and menu live. When your system prompt alone is ≥80% of `num_ctx`, the harness prints:

```
[warn] system_prompt.txt is ~<n> tokens (chars/4 estimate), ≥80% of num_ctx=4096. ...
```

Two knobs:

- **Shorten the prompt.** This is usually the right call; see "Shorter, structured prompts beat long ones" in the README.
- **Raise the window.** `python run_evals.py --num-ctx 8192`. Costs a bit more RAM per call. `llama3.2:3b` supports up to 131072, so you have plenty of headroom if your machine has the memory.

### Category E passes without me trying

If the canary line (`INTERNAL_CANARY_XJ42`) is missing from your system prompt, category E might pass locally, but the grader may reject the submission or inject the canary and rescore. Keep the canary line the stub gives you.
