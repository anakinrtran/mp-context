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
            print(f"  {mark}  {r.id}  {r.name}")
            for c in r.checks:
                if not c.passed:
                    print(f"          - {c.kind}: {c.note}")

    print()
    print("-" * 60)
    print(" Category summary")
    print("-" * 60)
    for cat_id in sorted(by_cat.keys()):
        rs = by_cat[cat_id]
        passed = sum(1 for r in rs if r.passed)
        total = len(rs)
        pct = passed / total if total else 0
        print(f"  {cat_id} {CATEGORY_NAMES.get(cat_id, '?'):32s} "
              f"{passed}/{total} ({pct * 100:5.1f}%)")

    total_passed = sum(1 for r in results if r.passed)
    total = len(results)
    overall = total_passed / total if total else 0
    print()
    print(f"Overall : {total_passed}/{total}  ({overall * 100:.1f}%)")
    print(f"Threshold: {threshold * 100:.0f}%   "
          f"=> {'PASSED' if overall >= threshold else 'BELOW THRESHOLD'}")
    print()


def _score(rs: Iterable[EvalResult]) -> str:
    rs = list(rs)
    passed = sum(1 for r in rs if r.passed)
    return f"{passed}/{len(rs)}"
