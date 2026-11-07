"""Local, sequential call audit with a conservative pre-request spending reserve."""

import hashlib
import json
import math
import os
import re
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

import dspy

ACTIVE_AUDIT = ContextVar("radarena_audit", default=None)
PILOT_MODEL = "qwen/qwen3-vl-8b-instruct"
# Verified against OpenRouter's models endpoint for this pilot. Provider price
# filters below cap token prices and exclude additional per-image/request fees.
MAX_CONTEXT = 262144
PRICE_CAPS = {"prompt": 0.5, "completion": 1.0, "image": 0, "request": 0}
MODEL_BOUNDS = {
    "qwen/qwen3-vl-30b-a3b-instruct": {"context_length": 262144, "max_images": 8,
        "price_caps": {"prompt": 0.3, "completion": 1.0, "image": 0, "request": 0}},
    "google/gemini-2.5-flash": {"context_length": 1048576, "max_images": 8,
                              "price_caps": {"prompt": 0.3, "completion": 2.5, "image": 0.001, "request": 0}},
    PILOT_MODEL: {"context_length": MAX_CONTEXT, "price_caps": PRICE_CAPS},
    "google/gemma-3-27b-it": {"context_length": 131072,
                            "price_caps": {"prompt": 0.1, "completion": 0.2, "image": 0, "request": 0}},
}


def safe_value(value):
    """Keep inspectable text, redact secrets, and replace inline pixels with hashes."""
    if isinstance(value, type):
        return safe_value(value.model_json_schema()) if hasattr(value, "model_json_schema") else value.__name__
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): ("[REDACTED]" if any(s in str(k).lower() for s in
                ["api_key", "authorization", "password", "secret"]) else safe_value(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_value(v) for v in value]
    if isinstance(value, str):
        key = os.getenv("OPENROUTER_API_KEY", "")
        if key:
            value = value.replace(key, "[REDACTED]")
        value = re.sub(r"sk-or-v1-[A-Za-z0-9_-]+", "[REDACTED]", value)
        return re.sub(r"data:image/[^\s\"']+", lambda m:
            f"[inline image omitted; sha256={hashlib.sha256(m[0].encode()).hexdigest()}; chars={len(m[0])}]", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return safe_value(str(value))


class AuditSession:
    def __init__(self, directory, max_cost_usd=0.5, max_calls=80):
        if not math.isfinite(max_cost_usd) or not 0 < max_cost_usd <= 1:
            raise ValueError("Pilot budget must be greater than zero and at most $1")
        if not 1 <= max_calls <= 100:
            raise ValueError("Pilot max-calls must be 1-100")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "calls.jsonl"
        self.max_cost_usd, self.max_calls = max_cost_usd, max_calls
        self.context = {}
        starts, ends = {}, {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                r = json.loads(line)
                (starts if r["event"] == "start" else ends)[r["call_number"]] = r
        self.calls = len(starts)
        # Unknown/failed/interrupted charges retain the full reserve, including on resume.
        self.accounted_cost = sum(ends[n]["accounted_cost_usd"] if n in ends
                                  else r["reserved_cost_usd"] for n, r in starts.items())
        self._write_ledger()

    def set_context(self, **context):
        self.context = context

    def _append(self, record):
        record = safe_value(record)
        with self.path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        with (self.directory / "trace.md").open("a") as f:
            f.write(f"\n## Call {record['call_number']} - {record['event']}\n\n```json\n")
            f.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n```\n")

    def _write_ledger(self):
        (self.directory / "budget.json").write_text(json.dumps({
            "max_cost_usd": self.max_cost_usd, "max_calls": self.max_calls,
            "started_calls": self.calls, "accounted_cost_usd": self.accounted_cost,
            "unknown_cost_policy": "retain full conservative request reserve",
            "verified_model_bounds": MODEL_BOUNDS,
            "scope": "sequential audited approved-model calls; excludes unrelated account usage and credit-purchase fees",
        }, indent=2) + "\n")

    def invoke(self, lm, invoke, prompt=None, messages=None, **kwargs):
        slug = lm.model.removeprefix("openrouter/")
        tokens = kwargs.get("max_tokens", lm.kwargs.get("max_tokens", 2048))
        if slug not in MODEL_BOUNDS or not 1 <= tokens <= 2048 or kwargs.get("n", 1) != 1:
            raise ValueError("Audited pilot supports only approved models, n=1 and max_tokens<=2048")
        if "extra_body" in kwargs:
            raise ValueError("Cannot override provider price filters during an audited pilot")
        bound = MODEL_BOUNDS[slug]
        caps = bound["price_caps"]
        def image_count(value):
            if isinstance(value, dict):
                return int(value.get("type") in {"image_url", "input_image"}) + sum(image_count(v) for v in value.values())
            if isinstance(value, (list, tuple)):
                return sum(image_count(v) for v in value)
            return 0
        if image_count(messages) > bound.get("max_images", 1000):
            raise ValueError("Request exceeds the approved image-count bound")
        reserve = (bound["context_length"] * caps["prompt"] + tokens * caps["completion"]) / 1e6
        reserve += bound.get("max_images", 0) * caps.get("image", 0)
        if self.calls >= self.max_calls or self.accounted_cost + reserve > self.max_cost_usd:
            raise RuntimeError("Pilot spending/call guard stopped before another model request")
        self.calls += 1
        number, before, start = self.calls, len(lm.history), time.monotonic()
        self.accounted_cost += reserve
        self._append({"event": "start", "call_number": number,
                      "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                      "context": self.context, "model": lm.model,
                      "reserved_cost_usd": reserve,
                      "inputs": {"prompt": prompt, "messages": messages, "kwargs": kwargs},
                      "generation_settings": {k: v for k, v in lm.kwargs.items() if not k.startswith("api_")}})
        self._write_ledger()
        outputs, error, error_message = None, None, None
        try:
            outputs = invoke(prompt, messages=messages, **kwargs)
            return outputs
        except Exception as exc:
            error = type(exc).__name__
            error_message = str(exc)
            raise
        finally:
            history = lm.history[before:]
            costs = [h.get("cost") for h in history]
            known = bool(costs) and all(isinstance(c, (int, float)) and math.isfinite(c) and c >= 0 for c in costs)
            charge = sum(costs) if known else reserve
            self.accounted_cost += charge - reserve
            self._append({"event": "end", "call_number": number, "context": self.context,
                          "elapsed_seconds": round(time.monotonic()-start, 3),
                          "outputs": outputs, "exception_type": error,
                          "exception_message": error_message,
                          "accounted_cost_usd": charge, "cost_known": known,
                          "history": [{k: h.get(k) for k in ["model", "response_model", "usage", "cost", "outputs", "uuid", "timestamp"]} for h in history]})
            self._write_ledger()


class AuditedLM(dspy.LM):
    def __call__(self, prompt=None, *, messages=None, **kwargs):
        audit = ACTIVE_AUDIT.get()
        if audit is None:
            raise RuntimeError("Audited model requires its active budget session")
        return audit.invoke(self, super().__call__, prompt, messages=messages, **kwargs)

    async def acall(self, *args, **kwargs):
        raise RuntimeError("Pilot audit supports sequential synchronous calls only")


@contextmanager
def audit_context(session):
    token = ACTIVE_AUDIT.set(session)
    try:
        yield session
    finally:
        ACTIVE_AUDIT.reset(token)
