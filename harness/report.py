"""Report rendering — per-eval, per-category, overall.

Kept ASCII-only so Windows terminals don't garble the output.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .runner import EvalResult


CATEGORY_NAMES = {
    "A": "Constant information",
    "B": "Customer service quality",
    "C": "Personality and tone",
    "D": "Schema conformance",
    "E": "Instruction confidentiality",
    "S": "Your evals (not graded)",
}


def print_report(results: list[EvalResult], threshold: float = 0.75,
                 graded: bool = True) -> None:
    multi_run = any(r.runs > 1 for r in results)

    print()
    print("=" * 60)
    print(" MP Context -- eval results" if graded
          else " MP Context -- your evals (not graded)")
    print("=" * 60)
    if multi_run:
        runs = max(r.runs for r in results)
        print(f" Each eval ran {runs} times; credit = points x passes / runs.")

    by_cat: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    for cat_id in sorted(by_cat.keys()):
        rs = by_cat[cat_id]
        print()
        print(f"[{cat_id}] {CATEGORY_NAMES.get(cat_id, '?')}"
              f"  ({_score(rs)})")
        for r in rs:
            pts = f" [{r.points} pt{'s' if r.points != 1 else ''}]"
            print(f"  {_mark(r, multi_run)}  {r.id}  {r.name}{pts}")
            rep = r.representative
            if rep is not None and not rep.passed:
                prefix = "(first failing run) " if r.runs > 1 else ""
                for c in rep.checks:
                    if not c.passed:
                        print(f"          - {prefix}{c.kind}: {c.note}")

    print()
    print("-" * 60)
    print(" Category summary (weighted by per-eval points)")
    print("-" * 60)
    for cat_id in sorted(by_cat.keys()):
        rs = by_cat[cat_id]
        earned = sum(r.earned for r in rs)
        total = sum(r.points for r in rs)
        pct = earned / total if total else 0
        print(f"  {cat_id} {CATEGORY_NAMES.get(cat_id, '?'):32s} "
              f"{_fmt(earned)}/{total} pts ({pct * 100:5.1f}%)")

    total_earned = sum(r.earned for r in results)
    total_points = sum(r.points for r in results)
    overall = total_earned / total_points if total_points else 0
    print()
    if multi_run:
        flaky = [r.id for r in results if r.flaky]
        print(f"Flaky    : {', '.join(flaky) if flaky else 'none'}"
              + ("   <- passed some runs but not all; your prompt only"
                 " sometimes works here" if flaky else ""))
    if not graded:
        print(f"Your evals: {_fmt(total_earned)}/{total_points} passed. Each failure "
              f"is a way you broke your bot -- worth a look.")
        print()
        return
    print(f"Overall : {_fmt(total_earned)}/{total_points} pts  ({overall * 100:.1f}%)")
    print(f"Threshold: {threshold * 100:.0f}%   "
          f"=> {'PASSED' if overall >= threshold else 'BELOW THRESHOLD'}")
    print()


def _mark(r: EvalResult, multi_run: bool) -> str:
    if not multi_run:
        return "PASS" if r.passed else "FAIL"
    word = "PASS " if r.passed else ("FLAKY" if r.flaky else "FAIL ")
    return f"{word} {r.pass_count}/{r.runs}"


def _fmt(x: float) -> str:
    """Whole numbers print as ints (single-run output looks unchanged)."""
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}"


def _score(rs: Iterable[EvalResult]) -> str:
    rs = list(rs)
    earned = sum(r.earned for r in rs)
    total = sum(r.points for r in rs)
    return f"{_fmt(earned)}/{total} pts"
