import json
from types import SimpleNamespace

import pytest

from radarena.tracing import AuditSession, PILOT_MODEL, safe_value


def fake_model():
    return SimpleNamespace(model="openrouter/" + PILOT_MODEL, kwargs={"max_tokens": 2048}, history=[])


def test_native_response_schema_classes_can_be_logged():
    from radarena.judge import JudgeReview
    value = safe_value({"response_format": JudgeReview})
    assert value["response_format"]["type"] == "object"
    assert "attack_validity" in value["response_format"]["properties"]


def test_spending_guard_stops_before_request_and_counts_unknown_cost_on_resume(tmp_path):
    audit, lm = AuditSession(tmp_path, max_cost_usd=0.2), fake_model()
    called = []
    def invoke(*args, **kwargs):
        called.append(True)
        return ["response"]  # Missing provider cost retains the request reserve.
    audit.invoke(lm, invoke, messages=[{"role": "user", "content": "fixture"}])
    resumed = AuditSession(tmp_path, max_cost_usd=0.2)
    assert resumed.calls == 1 and resumed.accounted_cost > 0.13
    with pytest.raises(RuntimeError, match="guard"):
        resumed.invoke(lm, invoke)
    assert len(called) == 1


def test_successful_cost_releases_reserve_and_call_limit_still_holds(tmp_path):
    audit, lm = AuditSession(tmp_path, max_cost_usd=0.2, max_calls=2), fake_model()
    def invoke(*args, **kwargs):
        lm.history.append({"cost": 0.001, "outputs": ["evidence"], "usage": {"prompt_tokens": 10}})
        return ["evidence"]
    for _ in range(2):
        audit.invoke(lm, invoke)
    assert audit.accounted_cost == pytest.approx(0.002)
    with pytest.raises(RuntimeError):
        audit.invoke(lm, invoke)
    records = [json.loads(x) for x in audit.path.read_text().splitlines()]
    assert len(records) == 4 and records[-1]["outputs"] == ["evidence"]


def test_trace_redacts_credentials_and_hashes_inline_images(monkeypatch):
    key = "fixture-private-key"
    monkeypatch.setenv("OPENROUTER_API_KEY", key)
    clean = safe_value({"api_key": key, "messages": [key, "sk-or-v1-dontlogme",
                        {"url": "data:image/png;base64,QUJDRA=="}], "question": "What is visible?"})
    encoded = json.dumps(clean)
    assert key not in encoded and "dontlogme" not in encoded and "QUJDRA" not in encoded
    assert "sha256=" in encoded and "What is visible?" in encoded


def test_failures_keep_reserve_and_unapproved_settings_never_invoke(tmp_path):
    audit, lm = AuditSession(tmp_path), fake_model()
    def fail(*args, **kwargs):
        raise ValueError("fixture")
    with pytest.raises(ValueError):
        audit.invoke(lm, fail)
    assert audit.accounted_cost > 0.13
    end = json.loads(audit.path.read_text().splitlines()[-1])
    assert end["exception_type"] == "ValueError" and not end["cost_known"]
    with pytest.raises(ValueError):
        audit.invoke(lm, fail, max_tokens=9999)
    assert audit.calls == 1
