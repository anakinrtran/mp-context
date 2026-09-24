#!/usr/bin/env python3
"""MP Context — entry point.

Usage examples:
  python run_evals.py                       # normal run against pinned Ollama model
  python run_evals.py --check               # smoke-test model reachability only
  python run_evals.py --mock                # run harness with canned responses (no Ollama)
  python run_evals.py --verbose             # print per-eval detail as it runs
  python run_evals.py --output results.json # save machine-readable results

You are not expected to edit this file — the deliverable is system_prompt.txt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow "python run_evals.py" from the mp-context directory to find `harness`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import client as client_mod
from harness import scoring
from harness import runner
from harness.report import print_report


HERE = Path(__file__).resolve().parent
DEFAULT_TESTS = HERE / "evals" / "tests.json"
DEFAULT_SCHEMA = HERE / "evals" / "schema.json"
DEFAULT_RUBRICS = HERE / "evals" / "rubrics"
DEFAULT_PROMPT = HERE / "system_prompt.txt"
DEFAULT_MOCK_FIXTURE = HERE / "harness" / "mock_responses.json"


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the MP Context eval suite.")
    p.add_argument("--system-prompt", type=Path, default=DEFAULT_PROMPT,
                   help="Path to system_prompt.txt (default: ./system_prompt.txt)")
    p.add_argument("--tests", type=Path, default=DEFAULT_TESTS,
                   help="Path to evals/tests.json.")
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA,
                   help="Path to evals/schema.json.")
    p.add_argument("--rubrics-dir", type=Path, default=DEFAULT_RUBRICS,
                   help="Directory of judge rubrics (*.md).")
    p.add_argument("--model", default=client_mod.DEFAULT_MODEL,
                   help=f"Ollama model tag (default: {client_mod.DEFAULT_MODEL}).")
    p.add_argument("--host", default=None,
                   help="Ollama host URL, e.g. http://localhost:11434.")
    p.add_argument("--check", action="store_true",
                   help="Skip evals — just verify Ollama is reachable and the "
                        "model is pulled, then exit.")
    p.add_argument("--mock", action="store_true",
                   help="Do not call Ollama; use canned responses from "
                        "harness/mock_responses.json. For smoke tests only.")
    p.add_argument("--strict", action="store_true",
                   help="Do not strip markdown code fences from model output "
                        "before JSON parsing. Off by default — flip on to see "
                        "how many of your responses would fail without the "
                        "harness cleaning up.")
    p.add_argument("--threshold", type=float, default=0.75,
                   help="Pass threshold (fraction, e.g. 0.75).")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print per-eval prompt/response/check detail.")
    p.add_argument("--output", type=Path, default=None,
                   help="Write machine-readable results as JSON to this path.")
    p.add_argument("--only", nargs="*", default=None,
                   help="Run only these eval ids (e.g. --only A1 A3 C2).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)

    # 1) Load config.
    tests_data = json.loads(args.tests.read_text(encoding="utf-8"))
    all_evals = tests_data["evals"]
    canary = tests_data["canary"]
    menu_version = tests_data.get("menu_version", "unknown")
    schema = json.loads(args.schema.read_text(encoding="utf-8"))

    if args.only:
        wanted = set(args.only)
        evals = [e for e in all_evals if e["id"] in wanted]
        if not evals:
            print(f"error: --only matched no evals (looked for {sorted(wanted)})",
                  file=sys.stderr)
            return 2
    else:
        evals = all_evals

    # 2) Build client + judge.
    if args.mock:
        mock = client_mod.build_mock_client(DEFAULT_MOCK_FIXTURE)
        chat_client = mock
        judge_fn = client_mod.make_mock_judge()
    else:
        chat_client = client_mod.OllamaClient(model=args.model, host=args.host)
        judge_fn = client_mod.make_ollama_judge(chat_client)

    # 3) --check: just prove the model is reachable and bail out.
    if args.check:
        try:
            chat_client.health_check()
        except Exception as e:
            print(f"[--check] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
        print("[--check] OK — model responded.", file=sys.stderr)
        return 0

    # 4) Load the student's system prompt.
    if not args.system_prompt.exists():
        print(f"error: system prompt not found: {args.system_prompt}",
              file=sys.stderr)
        return 2
    system_prompt = args.system_prompt.read_text(encoding="utf-8")

    # 5) Warn (but don't fail) if the canary is missing from the prompt.
    if not runner.check_canary_in_prompt(system_prompt, canary):
        print(f"[warn] canary string {canary!r} is NOT in your system prompt. "
              f"Category E will trivially pass locally but the grader may "
              f"inject it or penalize the omission — check the README.",
              file=sys.stderr)

    print(f"[harness] tests={args.tests.name}  menu_version={menu_version}  "
          f"evals={len(evals)}  strict={args.strict}", file=sys.stderr)

    # 6) Run.
    ctx = scoring.ScoringContext(
        schema=schema,
        canary=canary,
        strict_json=args.strict,
        judge=judge_fn,
        rubrics_dir=args.rubrics_dir,
        system_prompt=system_prompt,
    )
    results = runner.run_all(evals, system_prompt, chat_client, ctx,
                             verbose=args.verbose)

    # 7) Report.
    print_report(results, threshold=args.threshold)

    if args.output:
        args.output.write_text(
            json.dumps(runner.as_json_dicts(results), indent=2),
            encoding="utf-8",
        )
        print(f"[harness] wrote {args.output}", file=sys.stderr)

    earned = sum(r.earned for r in results)
    total_points = sum(r.points for r in results)
    overall = earned / total_points if total_points else 0
    return 0 if overall >= args.threshold else 1


if __name__ == "__main__":
    sys.exit(main())
