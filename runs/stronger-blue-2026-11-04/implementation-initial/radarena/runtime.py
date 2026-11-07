"""Project-local credentials and caches; no credentials imported from course repos."""

import os
from pathlib import Path

import dspy
from dotenv import load_dotenv


def load_environment():
    load_dotenv(Path.cwd() / ".env", override=False)


def model_config() -> dict:
    return {
        "text": os.getenv("RADARENA_TEXT_MODEL", "qwen/qwen3-vl-8b-instruct"),
        "vision": os.getenv("RADARENA_VISION_MODEL", "qwen/qwen3-vl-8b-instruct"),
        "max_tokens": int(os.getenv("RADARENA_MAX_TOKENS", "2048")),
    }


def make_models():
    load_environment()
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("Set OPENROUTER_API_KEY in this project's .env or shell environment.")
    config = model_config()
    dspy.configure_cache(disk_cache_dir=str(Path(".cache/dspy").resolve()))
    from .tracing import ACTIVE_AUDIT, AuditedLM, MODEL_BOUNDS
    audited = ACTIVE_AUDIT.get() is not None
    kwargs = dict(api_key=key, api_base="https://openrouter.ai/api/v1",
                  engine="litellm", max_tokens=config["max_tokens"],
                  temperature=0.0, cache=True, num_retries=0 if audited else 1)
    cls = AuditedLM if audited else dspy.LM
    models = []
    for role in ("text", "vision"):
        role_kwargs = dict(kwargs)
        if audited:
            if config[role] not in MODEL_BOUNDS:
                raise ValueError("Model needs verified context/price bounds before an audited pilot")
            body = {"provider": {"max_price": MODEL_BOUNDS[config[role]]["price_caps"]}}
            if config[role] == "google/gemini-2.5-flash":
                body["reasoning"] = {"max_tokens": 0}
            role_kwargs.update(extra_body=body, timeout=90 if config[role] == "google/gemini-2.5-flash" else 60)
        models.append(cls(f"openrouter/{config[role]}", **role_kwargs))
    dspy.configure(lm=models[0], track_usage=True, adapter=dspy.JSONAdapter())
    return models


def make_judge_model(model="google/gemini-2.5-flash"):
    """Fresh judge client; never reuses either contestant's conversational context."""
    from .tracing import ACTIVE_AUDIT, AuditedLM, MODEL_BOUNDS
    load_environment()
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key or ACTIVE_AUDIT.get() is None or model not in MODEL_BOUNDS:
        raise ValueError("Judge requires a configured key, active audit budget and approved model")
    dspy.configure_cache(disk_cache_dir=str(Path(".cache/dspy").resolve()))
    body = {"provider": {"max_price": MODEL_BOUNDS[model]["price_caps"]}}
    if model == "google/gemini-2.5-flash":
        body["reasoning"] = {"max_tokens": 0}
    return AuditedLM("openrouter/"+model, api_key=key, api_base="https://openrouter.ai/api/v1",
                     engine="litellm", max_tokens=2048, temperature=0, cache=True,
                     num_retries=0, timeout=90, extra_body=body)
