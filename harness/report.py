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
}


def print_report(results: list[EvalResult], threshold: float = 0.75) -> None:
    print()
    print("=" * 60)
    print(" MP Context -- eval results")
    print("=" * 60)

    by_cat: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    for cat_id in sorted(by_cat.keys()):
        rs = by_cat[cat_id]
        print()
        print(f"[{cat_id}] {CATEGORY_NAMES.get(cat_id, '?')}"
              f"  ({_score(rs)})")
        for r in rs:
            mark = "PASS" if r.passed else "FAIL"
            pts = f" [{r.points} pt{'s' if r.points != 1 else ''}]"
            print(f"  {mark}  {r.id}  {r.name}{pts}")
            for c in r.checks:
                if not c.passed:
                    print(f"          - {c.kind}: {c.note}")

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
              f"{earned}/{total} pts ({pct * 100:5.1f}%)")

    total_earned = sum(r.earned for r in results)
    total_points = sum(r.points for r in results)
    overall = total_earned / total_points if total_points else 0
    print()
    print(f"Overall : {total_earned}/{total_points} pts  ({overall * 100:.1f}%)")
    print(f"Threshold: {threshold * 100:.0f}%   "
          f"=> {'PASSED' if overall >= threshold else 'BELOW THRESHOLD'}")
    print()


def _score(rs: Iterable[EvalResult]) -> str:
    rs = list(rs)
    earned = sum(r.earned for r in rs)
    total = sum(r.points for r in rs)
    return f"{earned}/{total} pts"
