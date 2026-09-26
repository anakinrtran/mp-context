"""Ollama chat client + an offline mock for harness smoke tests.

The pinned model is announced on the first chat call so students and graders
can eyeball the run log and confirm the model was what they expected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional
import json
import os
import re
import sys

DEFAULT_MODEL = "llama3.2:3b"

# Ollama defaults num_ctx to 2048, well below what a bloated student prompt
# can occupy alongside the eval message and the JSON response. Pin it
# explicitly so behavior is consistent across machines. llama3.2:3b
# architecturally supports 131072.
DEFAULT_NUM_CTX = 4096

# Keep the model resident across edit-run-edit iteration so students don't
# pay a ~2 GB reload every time they tweak their prompt. Overridable via
# MP_OLLAMA_KEEP_ALIVE (e.g. "-1" for indefinite, "5m" to reclaim RAM sooner).
DEFAULT_KEEP_ALIVE = os.environ.get("MP_OLLAMA_KEEP_ALIVE", "30m")

# Fixed sampling seed (offset by run index with --runs). Pins results for a
# given prompt on a given machine, so re-running an unchanged prompt can't
# reroll a different score.
BASE_SEED = 124

# Cap on generated tokens per call. A valid reply is well under this; without a
# cap, a model that starts echoing its prompt or looping can run until num_ctx
# fills, and one such eval can stall a run for minutes. A capped runaway ends
# as invalid JSON and fails schema_valid, which it would have anyway.
DEFAULT_NUM_PREDICT = 512


class OllamaClient:
    """Thin wrapper around the ollama python client. Lazy-imports ollama so
    that --mock runs work on machines that don't have ollama installed."""

    def __init__(self, model: str = DEFAULT_MODEL, host: Optional[str] = None,
                 temperature: float = 0.2,
                 keep_alive: str = DEFAULT_KEEP_ALIVE,
                 num_ctx: int = DEFAULT_NUM_CTX):
        self.model = model
        self.host = host
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.num_ctx = num_ctx
        self._client = None
        self._announced = False

    def _connect(self):
        if self._client is not None:
            return
        try:
            import ollama
        except ImportError as e:
            raise RuntimeError(
                "The 'ollama' package is not installed. Install requirements "
                "with `pip install -r requirements.txt`, or pass --mock to "
                "smoke-test the harness without Ollama."
            ) from e
        self._client = ollama.Client(host=self.host) if self.host else ollama.Client()

    def _announce(self):
        if not self._announced:
            print(f"[harness] model: {self.model} "
                  f"(num_ctx: {self.num_ctx}, keep_alive: {self.keep_alive})",
                  file=sys.stderr)
            self._announced = True

    def chat(self, system_prompt: str, user_message: str,
             eval_id: Optional[str] = None, run_index: int = 0,
             temperature: Optional[float] = None) -> str:
        """`run_index` picks the sampling seed, so run k of an eval is
        reproducible on a given machine. `temperature` overrides the bot
        default (the judge passes 0)."""
        del eval_id  # not used by the real client
        self._connect()
        self._announce()
        options = {
            "temperature": self.temperature if temperature is None else temperature,
            "num_ctx": self.num_ctx,
            "seed": BASE_SEED + run_index,
            "num_predict": DEFAULT_NUM_PREDICT,
        }
        resp = self._client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            options=options,
            keep_alive=self.keep_alive,
        )
        return resp["message"]["content"]

    def health_check(self) -> None:
        """Round-trip a trivial call to confirm Ollama is reachable and the
        pinned model is pulled. Raises on failure."""
        self._connect()
        self._announce()
        self._client.chat(
            model=self.model,
            messages=[{"role": "user", "content": "reply with the single word: ok"}],
            options={"temperature": 0.0, "num_ctx": self.num_ctx},
            keep_alive=self.keep_alive,
        )


class MockClient:
    """Offline canned-response client for smoke-testing the harness.

    Loads a dict of {eval_id: response_json_string} at init and replays it in
    lieu of a real model call. If an eval id isn't in the fixture, returns a
    small default JSON response.
    """

    _DEFAULT = '{"response": "Mock reply.", "refused": false, "items_referenced": []}'

    def __init__(self, canned_by_id: dict[str, str], label: str = "mock"):
        self.model = label
        self._canned = canned_by_id
        self._announced = False

    def _announce(self):
        if not self._announced:
            print(f"[harness] model: {self.model} (offline -- no Ollama call)",
                  file=sys.stderr)
            self._announced = True

    def chat(self, system_prompt: str, user_message: str,
             eval_id: Optional[str] = None, run_index: int = 0,
             temperature: Optional[float] = None) -> str:
        del system_prompt, user_message, run_index, temperature
        self._announce()
        return self._canned.get(eval_id, self._DEFAULT)

    def health_check(self) -> None:
        self._announce()


def build_mock_client(fixture_path: Path) -> MockClient:
    """Load a mock fixture from JSON. Fixture format:
    {"canned": {"A1": "<json string>", ...}}"""
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    return MockClient(data["canned"])


# The judge is a separate model call; we abstract it as a function so the
# instructor grader can swap the pinned Ollama for a stronger judge model
# without touching the runner.
JudgeFn = Callable[[str, str, str, str], tuple[bool, str]]
# The judge should be a fixed ruler: same response in, same verdict out.
JUDGE_TEMPERATURE = 0.0
"""JudgeFn(rubric_text, criteria, eval_prompt, response_text) -> (pass, reason)"""


def make_ollama_judge(client: OllamaClient) -> JudgeFn:
    """Build a JudgeFn that runs the judge as an Ollama chat call. Returns
    (True, reason) on parse-pass, (False, reason) on parse-fail — a judge
    whose output we can't parse counts as a failure so students see it."""

    def judge(rubric_text: str, criteria: str, eval_prompt: str,
              response_text: str) -> tuple[bool, str]:
        # Reason before verdict: a small judge that commits to "pass" first
        # tends to rationalize it. (Forcing it to quote the response was tried
        # and made the 3B judge worse -- it copied phrases from the criteria.
        # On 79 hand-labeled responses: verdict-first 66, reason-first+quote 59,
        # reason-first plain 71.)
        judge_system = (
            "You are an impartial grader. Read the rubric, the eval criteria, "
            "the customer message, and the bot's response. Return exactly one "
            'JSON object, reason first: {"reason": "one short sentence", '
            '"pass": true|false} — no markdown fences, no extra text.'
        )
        judge_user = (
            f"<rubric>\n{rubric_text}\n</rubric>\n\n"
            f"<eval_criteria>\n{criteria}\n</eval_criteria>\n\n"
            f"<customer_message>\n{eval_prompt}\n</customer_message>\n\n"
            f"<bot_response>\n{response_text}\n</bot_response>\n\n"
            'Answer with only the JSON object.'
        )
        raw = client.chat(judge_system, judge_user,
                          temperature=JUDGE_TEMPERATURE)
        parsed = _extract_first_json_object(raw)
        if parsed is None:
            # Unescaped quotes inside "reason" break json.loads; the verdict
            # itself is usually still readable.
            m = re.search(r'"pass"\s*:\s*(true|false)', raw)
            if m is None:
                return False, f"judge output not parseable: {raw[:120]!r}"
            parsed = {"pass": m.group(1) == "true", "reason": raw[:200]}
        return bool(parsed.get("pass")), str(parsed.get("reason", ""))[:200]

    return judge


def make_mock_judge() -> JudgeFn:
    """A judge that always passes. For --mock harness runs only."""
    def judge(rubric_text, criteria, eval_prompt, response_text):
        del rubric_text, criteria, eval_prompt, response_text
        return True, "mock judge — always passes"
    return judge


def _extract_first_json_object(text: str) -> Optional[dict]:
    """Try hard to pull one JSON object out of possibly-fenced, possibly-noisy
    model output. Returns None if nothing parses."""
    import re

    # 1) Try the whole thing.
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass

    # 2) Try inside a code fence.
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence:
        try:
            obj = json.loads(fence.group(1))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass

    # 3) Grab the first {...} block by bracket-matching.
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None
