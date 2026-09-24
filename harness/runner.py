"""Drives one full eval pass: for each eval, ask the model, then run checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
import json
import sys

from . import scoring


@dataclass
class CheckResult:
    kind: str
    passed: bool
    note: str


@dataclass
class EvalResult:
    id: str
    category: str
    name: str
    prompt: str
    raw_response: str
    parsed: Any
    parse_note: str
    points: int = 1
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def earned(self) -> int:
        return self.points if self.passed else 0


def load_evals(path: Path) -> tuple[list[dict], str, str]:
    """Return (evals, canary, menu_version)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["evals"], data["canary"], data.get("menu_version", "unknown")


def check_canary_in_prompt(system_prompt: str, canary: str) -> bool:
    return canary in system_prompt


def run_one(eval_def: dict, system_prompt: str, client, ctx: scoring.ScoringContext,
            verbose: bool = False) -> EvalResult:
    if eval_def.get("static"):
        raw = ""
        parsed, parse_note = None, "static eval — no model call"
    else:
        raw = client.chat(system_prompt, eval_def["prompt"], eval_id=eval_def["id"])
        parsed, parse_note = scoring.try_parse_json(raw, strict=ctx.strict_json)
    result = EvalResult(
        id=eval_def["id"],
        category=eval_def["category"],
        name=eval_def["name"],
        prompt=eval_def["prompt"],
        raw_response=raw,
        parsed=parsed,
        parse_note=parse_note,
        points=int(eval_def.get("points", 1)),
    )
    for check in eval_def["checks"]:
        passed, note = scoring.run_check(check, ctx, raw, parsed, eval_def)
        result.checks.append(CheckResult(kind=check["kind"], passed=passed, note=note))
    if verbose:
        _print_verbose(result)
    return result


def run_all(evals: list[dict], system_prompt: str, client,
            ctx: scoring.ScoringContext, verbose: bool = False) -> list[EvalResult]:
    return [run_one(e, system_prompt, client, ctx, verbose) for e in evals]


def _print_verbose(result: EvalResult) -> None:
    status = "PASS" if result.passed else "FAIL"
    print(f"\n--- [{status}] {result.id} {result.name} ---", file=sys.stderr)
    print(f"prompt : {result.prompt}", file=sys.stderr)
    excerpt = result.raw_response.strip().replace("\n", " ")
    if len(excerpt) > 220:
        excerpt = excerpt[:217] + "..."
    print(f"model  : {excerpt}", file=sys.stderr)
    for c in result.checks:
        mark = "+" if c.passed else "-"
        print(f"  [{mark}] {c.kind}: {c.note}", file=sys.stderr)


def as_json_dicts(results: list[EvalResult]) -> list[dict]:
    """Serializable form for --output."""
    out = []
    for r in results:
        d = asdict(r)
        d["passed"] = r.passed
        out.append(d)
    return out
