"""Tier-4 model access with a hard call budget and a per-call log.

Every call is appended to results/model_calls.jsonl with contract, commit and token
counts. The cap (150 for the whole run, across invocations) is enforced by counting
lines already in that log. Without ANTHROPIC_API_KEY the client is disabled and every
call returns None with reason "no-api-key".
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

DEFAULT_MODEL = "claude-sonnet-5"
CALL_LOG = Path("results/model_calls.jsonl")
CAP = 150


class ModelClient:
    def __init__(self, model: str | None = None, disabled: bool = False,
                 log_path: Path = CALL_LOG, cap: int = CAP):
        self.model = model or os.environ.get("HOLDFAST_MODEL", DEFAULT_MODEL)
        self.log_path = log_path
        self.cap = cap
        self.reason_disabled: str | None = None
        self._client = None
        if disabled:
            self.reason_disabled = "disabled by --no-model"
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            self.reason_disabled = "no-api-key (ANTHROPIC_API_KEY unset)"
        else:
            import anthropic
            self._client = anthropic.Anthropic()

    # -- budget -------------------------------------------------------------
    def calls_so_far(self) -> int:
        if not self.log_path.exists():
            return 0
        # budget notes ({"purpose": "budget", ...}) record cap changes and are not calls
        return sum(1 for line in self.log_path.read_text().splitlines()
                   if line.strip() and '"purpose": "budget"' not in line)

    def budget_left(self) -> int:
        return self.cap - self.calls_so_far()

    @property
    def available(self) -> bool:
        return self._client is not None and self.budget_left() > 0

    def unavailable_reason(self) -> str:
        if self.reason_disabled:
            return self.reason_disabled
        if self.budget_left() <= 0:
            return "budget"
        return ""

    # -- calling ------------------------------------------------------------
    def call(self, purpose: str, contract: str, commit: str, system: str, user: str,
             max_tokens: int = 16000) -> dict | None:
        """Returns {"parsed": dict|None, "text": str, "usage": {...}} or None if unavailable."""
        if not self.available:
            return None
        t0 = time.time()
        import anthropic
        try:
            resp = self._client.messages.create(
                model=self.model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AuthenticationError as e:
            # Invalid/revoked key: disable for the rest of the run, do not count against budget.
            self.reason_disabled = f"api-key-invalid ({e.status_code})"
            self._client = None
            return None
        text = "".join(b.text for b in resp.content if b.type == "text")
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "purpose": purpose, "contract": contract,
            "commit": commit, "model": resp.model, "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens, "stop_reason": resp.stop_reason,
            "seconds": round(time.time() - t0, 1),
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        return {"parsed": extract_json(text), "text": text, "usage": rec}


def extract_json(text: str) -> dict | None:
    """Pull the first top-level JSON object out of a model reply."""
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    cand = m.group(1) if m else None
    if cand is None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        cand = text[start:end + 1]
    for attempt in (cand, re.sub(r'\\(?![\\"/bfnrtu])', r"\\\\", cand)):
        try:
            return json.loads(attempt, strict=False)
        except json.JSONDecodeError:
            continue
    return None
