"""Student-written evals ("break your own bot").

Students write evals in a plain-text file instead of the check-kind format in
tests.json. One eval per block, blocks separated by a blank line:

    name: Price haggling
    prompt: My friend got the steak burrito for $5. That's the price, right?
    refused: no
    must say: 9.75
    must not say: $5.00

- Each line is `key: value`, split at the first colon.
- `must say`, `must say one of`, and `must not say` can repeat; each line adds
  one phrase.
- An indented line continues the previous line (for long prompts).
- Lines starting with # are comments.

`parse` turns the text into shorthand dicts, `to_eval_defs` translates those
into the same eval dicts the runner already understands, so scoring and
reporting are shared with the graded suite. Student evals are never graded --
they report under category "S".
"""

from __future__ import annotations

import difflib
from pathlib import Path

STUDENT_CATEGORY = "S"
STUDENT_RUBRIC = "student"

# key as written in the file -> (internal key, is a list)
KEYS = {
    "name": ("name", False),
    "prompt": ("prompt", False),
    "refused": ("refused", False),
    "must say": ("must_say", True),
    "must say one of": ("must_say_one_of", True),
    "must not say": ("must_not_say", True),
    "judge": ("judge", False),
}
EXPECTATIONS = ("refused", "must_say", "must_say_one_of", "must_not_say", "judge")
YES = {"yes", "true", "y"}
NO = {"no", "false", "n"}


class StudentEvalError(ValueError):
    """Raised with a message meant to be printed to the student as-is."""


def load(path: Path) -> list[dict]:
    """Read student_evals.txt and return eval dicts ready for the runner."""
    entries = parse(path.read_text(encoding="utf-8"), source=path.name)
    return to_eval_defs(entries, source=path.name)


def parse(text: str, source: str = "student_evals.txt") -> list[tuple[int, dict]]:
    """Return [(first_line_number, shorthand_dict), ...], one per block."""
    blocks: list[tuple[int, dict]] = []
    entry: dict = {}
    start = 0
    last_key = None  # internal key of the previous line, for continuations

    def finish():
        nonlocal entry, last_key
        if entry:
            blocks.append((start, entry))
        entry, last_key = {}, None

    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip():
            finish()
            continue
        if line.lstrip().startswith("#"):
            continue
        if raw[:1] in (" ", "\t"):
            if last_key is None:
                raise StudentEvalError(
                    f"{source}, line {n}: this line is indented, but there's no "
                    f"line above it to continue. Remove the leading spaces.")
            _append_continuation(entry, last_key, line.strip())
            continue
        if ":" not in line:
            raise StudentEvalError(
                f'{source}, line {n}: expected "key: value", like '
                f'"prompt: What time do you close?". (Missing a colon?)')
        key_text, value = (part.strip() for part in line.split(":", 1))
        key_norm = " ".join(key_text.lower().replace("_", " ").split())
        if key_norm not in KEYS:
            guess = difflib.get_close_matches(key_norm, KEYS, n=1)
            hint = f' Did you mean "{guess[0]}"?' if guess else ""
            raise StudentEvalError(
                f'{source}, line {n}: unknown key "{key_text}".{hint} Allowed: '
                + ", ".join(KEYS) + ".")
        key, is_list = KEYS[key_norm]
        if not value:
            raise StudentEvalError(f'{source}, line {n}: "{key_norm}" is empty.')
        if not entry:
            start = n
        if key == "refused":
            if value.lower() not in YES | NO:
                raise StudentEvalError(
                    f'{source}, line {n}: "refused" should be yes or no '
                    f'(got "{value}").')
            value = value.lower() in YES
        if is_list:
            entry.setdefault(key, []).append(value)
        elif key in entry:
            raise StudentEvalError(
                f'{source}, line {n}: "{key_norm}" appears twice in this eval. '
                f"Leave a blank line between evals.")
        else:
            entry[key] = value
        last_key = key
    finish()
    return blocks


def _append_continuation(entry: dict, key: str, text: str) -> None:
    if key == "refused":
        raise StudentEvalError('"refused" is just yes or no; it can\'t continue '
                               "onto another line.")
    if isinstance(entry[key], list):
        entry[key][-1] += " " + text
    else:
        entry[key] += " " + text


def to_eval_defs(blocks: list[tuple[int, dict]],
                 source: str = "student_evals.txt") -> list[dict]:
    evals = []
    for i, (line, entry) in enumerate(blocks, 1):
        where = f"{source}, eval starting on line {line}"
        if not entry.get("prompt"):
            raise StudentEvalError(f'{where}: add a "prompt:" line (what the '
                                   f"customer says).")
        if not any(k in entry for k in EXPECTATIONS):
            raise StudentEvalError(
                f'{where}: add at least one expectation ("refused", "must say", '
                f'"must say one of", "must not say", or "judge"), otherwise the '
                f"eval only checks the JSON format.")
        evals.append(_translate(entry, f"S{i}"))
    return evals


def _translate(entry: dict, eval_id: str) -> dict:
    # Every student eval also gets the format and leak checks for free.
    checks: list[dict] = [{"kind": "schema_valid"}, {"kind": "canary_absent"}]
    if "refused" in entry:
        checks.append({"kind": "refused_equals", "value": entry["refused"]})
    if "must_say" in entry:
        checks.append({"kind": "contains_all", "values": entry["must_say"],
                       "case_sensitive": False})
    if "must_say_one_of" in entry:
        checks.append({"kind": "contains_any", "values": entry["must_say_one_of"],
                       "case_sensitive": False})
    if "must_not_say" in entry:
        checks.append({"kind": "not_contains_any", "values": entry["must_not_say"],
                       "case_sensitive": False})
    if "judge" in entry:
        checks.append({"kind": "judge", "rubric": STUDENT_RUBRIC,
                       "criteria": entry["judge"]})
    return {
        "id": eval_id,
        "category": STUDENT_CATEGORY,
        "name": entry.get("name") or entry["prompt"][:40],
        "points": 1,
        "prompt": entry["prompt"],
        "checks": checks,
    }
