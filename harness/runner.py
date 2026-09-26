"""Drives one full eval pass: for each eval, ask the model, then run checks.

With runs > 1 every eval is asked `runs` times (different seeds) and earns
fractional credit: points x passes / runs. A prompt that only sometimes works
gets partial credit instead of a coin flip, and the report can flag it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
import json
import sys

from . import scoring


@dataclass
class CheckResult:
    kind: str
    passed: bool
    note: str


@dataclass
class Attempt:
    """One model call for one eval, and the checks run against it."""
    raw_response: str
    parsed: Any
    parse_note: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


@dataclass
class EvalResult:
    id: str
    category: str
    name: str
    prompt: str
    points: int = 1
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def runs(self) -> int:
        return len(self.attempts)

    @property
    def pass_count(self) -> int:
        return sum(1 for a in self.attempts if a.passed)

    @property
    def passed(self) -> bool:
        """True only if every run passed."""
        return bool(self.attempts) and self.pass_count == self.runs

    @property
    def flaky(self) -> bool:
        return 0 < self.pass_count < self.runs

    @property
    def earned(self) -> float:
        return self.points * self.pass_count / self.runs if self.runs else 0.0

    @property
    def representative(self) -> Optional[Attempt]:
        """The first failing run if any, else the first run -- what the
        report shows when it prints one response/check list per eval."""
        for a in self.attempts:
            if not a.passed:
                return a
        return self.attempts[0] if self.attempts else None


def load_evals(path: Path) -> tuple[list[dict], str, str]:
    """Return (evals, canary, menu_version)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["evals"], data["canary"], data.get("menu_version", "unknown")


def check_canary_in_prompt(system_prompt: str, canary: str) -> bool:
    return canary in system_prompt


def _run_attempt(eval_def: dict, system_prompt: str, client,
                 ctx: scoring.ScoringContext, run_index: int) -> Attempt:
    if eval_def.get("static"):
        raw = ""
        parsed, parse_note = None, "static eval - no model call"
    else:
        raw = client.chat(system_prompt, eval_def["prompt"],
                          eval_id=eval_def["id"], run_index=run_index)
        parsed, parse_note = scoring.try_parse_json(raw, strict=ctx.strict_json)
    attempt = Attempt(raw_response=raw, parsed=parsed, parse_note=parse_note)
    for check in eval_def["checks"]:
        passed, note = scoring.run_check(check, ctx, raw, parsed, eval_def)
        attempt.checks.append(CheckResult(kind=check["kind"], passed=passed, note=note))
    return attempt


def run_one(eval_def: dict, system_prompt: str, client, ctx: scoring.ScoringContext,
            verbose: bool = False, runs: int = 1) -> EvalResult:
    result = EvalResult(
        id=eval_def["id"],
        category=eval_def["category"],
        name=eval_def["name"],
        prompt=eval_def["prompt"],
        points=int(eval_def.get("points", 1)),
    )
    # Static evals (e.g. E0) inspect the prompt file, not the model: one run.
    n = 1 if eval_def.get("static") else max(1, runs)
    for i in range(n):
        result.attempts.append(_run_attempt(eval_def, system_prompt, client, ctx, i))
    if verbose:
        _print_verbose(result)
    return result


def run_all(evals: list[dict], system_prompt: str, client,
            ctx: scoring.ScoringContext, verbose: bool = False,
            runs: int = 1) -> list[EvalResult]:
    return [run_one(e, system_prompt, client, ctx, verbose, runs) for e in evals]


def _print_verbose(result: EvalResult) -> None:
    if result.passed:
        status = "PASS"
    elif result.flaky:
        status = "FLAKY"
    else:
        status = "FAIL"
    tally = f" {result.pass_count}/{result.runs}" if result.runs > 1 else ""
    print(f"\n--- [{status}{tally}] {result.id} {result.name} ---", file=sys.stderr)
    print(f"prompt : {result.prompt}", file=sys.stderr)
    for i, a in enumerate(result.attempts):
        label = "model  " if result.runs == 1 else f"run {i + 1}  "
        excerpt = a.raw_response.strip().replace("\n", " ")
        if len(excerpt) > 220:
            excerpt = excerpt[:217] + "..."
        print(f"{label}: {excerpt}", file=sys.stderr)
        for c in a.checks:
            mark = "+" if c.passed else "-"
            print(f"  [{mark}] {c.kind}: {c.note}", file=sys.stderr)


def as_json_dicts(results: list[EvalResult]) -> list[dict]:
    """Serializable form for --output. Every run's raw response is kept."""
    out = []
    for r in results:
        d = asdict(r)
        d["runs"] = r.runs
        d["pass_count"] = r.pass_count
        d["passed"] = r.passed
        d["earned"] = r.earned
        for a_dict, a in zip(d["attempts"], r.attempts):
            a_dict["passed"] = a.passed
        out.append(d)
    return out
