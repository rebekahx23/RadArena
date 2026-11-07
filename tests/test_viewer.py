"""Observer accounting, incomplete traces, and read-only routing; no model calls."""

import json
from pathlib import Path

import pytest

from radarena.viewer import RunStore, clean, judge_warnings, make_handler, normalize_calls, read_rows


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def start(number, role="verifier", **context):
    return {"event": "start", "call_number": number, "context": {"role": role, **context},
            "model": "fixture/model", "reserved_cost_usd": .1,
            "inputs": {"messages": [{"role": "user", "content": "fixture"}]}}


def end(number, cost=.002, known=True, **extra):
    return {"event": "end", "call_number": number, "cost_known": known,
            "accounted_cost_usd": cost, "outputs": ['{"verdict":{"decision":"uncertain","findings":[]}}'],
            "history": [{"usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}], **extra}


def test_retries_failures_and_unfinished_calls_keep_separate_costs():
    calls = normalize_calls([start(1), end(1, .1, False, exception_type="ParseError"),
                             start(2), end(2), start(3)])
    assert [c["status"] for c in calls] == ["failed", "complete", "pending"]
    assert sum(c["cost"] for c in calls) == pytest.approx(.202)
    assert sum(c["cost"] for c in calls if c["cost_known"]) == pytest.approx(.002)
    assert calls[1]["usage"]["total_tokens"] == 15


def test_in_progress_demo_recovers_report_context_without_final_file(tmp_path):
    audit = tmp_path / "runs/new-demo.audit/calls.jsonl"
    original = [{"id": "s1", "text": "Right lung opacity."}]
    attack = start(1, "red", study_id="7")
    attack["inputs"]["messages"] = [
        {"role": "system", "content": "Your input fields are: source_sentences Your output fields"},
        {"role": "user", "content": f"[[ ## source_sentences ## ]]\n{json.dumps(original)}\n\n[[ ## error_type ## ]]\nlaterality"}]
    completed = end(1, outputs=[json.dumps({"edits": [{"sentence_id": "s1", "replacement": "Left lung opacity."}]})])
    write_rows(audit, [attack, completed])
    with audit.open("a") as file:
        file.write('{"event":"start",')  # Concurrent writer has not finished this line.
    write_rows(tmp_path / "manifest.jsonl", [{"study_id": "7", "image_paths": ["/study.png"]}])
    store = RunStore(tmp_path / "runs", tmp_path / "manifest.jsonl")
    episode = store.run("new-demo")["episodes"][0]
    assert episode["source"] == original
    assert episode["candidate"] == [{"id": "s1", "text": "Left lung opacity."}]
    assert episode["image_paths"] == ["/study.png"]
    assert episode["status"] == "recording"
    assert len(read_rows(audit)) == 2


def test_evaluation_groups_case_condition_and_run_costs(tmp_path):
    run = tmp_path / "runs/evaluation"
    rows = [start(1, case_id="a", variant="text_only"), end(1),
            start(2, case_id="a", variant="blue_tools"), end(2, .003),
            start(3, case_id="b", variant="blue_tools")]
    write_rows(run / "audit/calls.jsonl", rows)
    store = RunStore(tmp_path / "runs", tmp_path / "missing-manifest")
    result = store.run("evaluation")
    assert len(result["episodes"]) == 3
    assert result["cost"] == pytest.approx(.105)
    assert result["known_cost"] == pytest.approx(.005)
    assert result["unknown_calls"] == 1
    assert result["episodes"][0]["calls"][0]["name"] == "TextOnlyCheck"
    with pytest.raises(KeyError):
        store.run("../evaluation")


def test_http_routes_only_serve_registered_images_and_assets(tmp_path):
    image = tmp_path / "scan.png"
    image.write_bytes(b"fixture PNG bytes")
    write_rows(tmp_path / "runs/demo.audit/calls.jsonl", [start(1, "red", study_id="7")])
    write_rows(tmp_path / "manifest", [{"study_id": "7", "image_paths": [str(image)]}])
    handler_type = make_handler(RunStore(tmp_path / "runs", tmp_path / "manifest"))

    def request(path):
        handler = object.__new__(handler_type)
        handler.path = path
        response = []
        handler.send_content = lambda data, content_type, status=200: response.append((status, data, content_type))
        handler.do_GET()
        return response[0]

    assert request("/api/image?run=demo&episode=demo&index=0")[:2] == (200, b"fixture PNG bytes")
    for path in ["/.env", "/../../.env", "/api/image?path=/etc/passwd",
                 "/api/image?run=demo&episode=demo&index=-1", "/api/run?id=../demo"]:
        assert request(path)[0] == 404
    status, payload, _ = request("/api/run?id=demo")
    assert status == 200
    episode = json.loads(payload)["episodes"][0]
    assert "image_paths" not in episode
    assert episode["images"][0]["name"] == "scan.png"
    assert request("/")[0] == 200
    assert request("/live.js")[0] == 200


def test_responses_redact_credentials_and_inline_image_payloads():
    value = clean({"authorization": "private", "messages": ["sk-or-v1-example", "data:image/png;base64,aGVsbG8="]})
    text = json.dumps(value)
    assert "private" not in text and "sk-or-v1-example" not in text and "aGVsbG8=" not in text


def test_multiple_judges_are_attached_to_the_same_episode_once(tmp_path):
    root = tmp_path / "runs"
    write_rows(root / "demo.audit/calls.jsonl", [start(1, "red", study_id="7"), end(1, .01)])
    (root / "demo.json").write_text(json.dumps({"study_id": "7", "source": [], "candidate": [], "private_attack": {}}))
    write_rows(root / "demo.judge.audit/calls.jsonl", [start(1, "judge"), end(1, .02)])
    (root / "demo.judge.json").write_text(json.dumps({"status": "ok", "judge_model": "judge/one", "analysis": {}}))
    write_rows(root / "demo.judges/second.audit/calls.jsonl", [start(1, "judge"), end(1, .03)])
    (root / "demo.judges/second.json").write_text(json.dumps({"status": "ok", "judge_model": "judge/two", "analysis": {}}))
    store = RunStore(root, tmp_path / "missing")
    assert list(store.discover()) == ["demo"]
    run = store.run("demo")
    episode = run["episodes"][0]
    assert len(episode["judges"]) == 2
    assert len(episode["calls"]) == run["calls_count"] == 3
    assert run["agent_cost"] == pytest.approx(.01)
    assert run["judge_cost"] == pytest.approx(.05)
    assert run["cost"] == pytest.approx(.06)
    assert len({c["judge_id"] for c in episode["calls"] if c["role"] == "judge"}) == 2


def test_saved_review_without_tape_retains_analysis_and_accounted_spend(tmp_path):
    root = tmp_path / "runs"
    write_rows(root / "demo.audit/calls.jsonl", [start(1, "red", study_id="7"), end(1, .01)])
    (root / "demo.judge.json").write_text(json.dumps({"status": "ok", "analysis": {"confidence": "low"},
                                                   "accounted_cost_usd": .04, "calls": 1}))
    run = RunStore(root, tmp_path / "missing").run("demo")
    review = run["episodes"][0]["judges"][0]
    assert review["record"]["analysis"]["confidence"] == "low"
    assert not review["has_trace"] and not review["cost_known"]
    assert run["cost"] == pytest.approx(.05)
    assert run["calls_count"] == 2
    assert run["untraced_judge_calls"] == 1


def test_review_tensions_describe_explicit_statements_without_changing_them():
    verdict = {"decision": "error", "findings": [{"sentence_id": "s2"}, {"sentence_id": "s5"}]}
    record = {"status": "ok", "analysis": {"blue_assessment": "partially_correct", "flag_reviews": [
        {"sentence_id": "s2", "evidence_relation": "contradicts_report"},
        {"sentence_id": "s5", "evidence_relation": "supports_report"}]}}
    original = json.dumps(record)
    warnings = judge_warnings(record, verdict)
    assert [w["sentence_id"] for w in warnings] == ["s5"]
    assert json.dumps(record) == original
    assert judge_warnings({**record, "status": "failed"}, verdict) == []


def test_earlier_judge_responses_are_not_presented_as_the_accepted_assessment(tmp_path):
    root = tmp_path / "runs"
    write_rows(root / "demo.audit/calls.jsonl", [start(1, "red", study_id="7"), end(1, .01)])
    earlier = {"blue_assessment": "correct"}
    accepted = {"blue_assessment": "partially_correct"}
    write_rows(root / "demo.judge.audit/calls.jsonl", [
        start(1, "judge"), end(1, .02, outputs=[json.dumps({"review": earlier})]),
        start(2, "judge"), end(2, .03, outputs=[json.dumps({"review": accepted})])])
    (root / "demo.judge.json").write_text(json.dumps({"status": "ok", "analysis": accepted}))
    episode = RunStore(root, tmp_path / "missing").run("demo")["episodes"][0]
    assert episode["calls"][-2]["review_disposition"] == "superseded"
    assert episode["calls"][-1]["review_disposition"] == "accepted"
    assert episode["judges"][0]["record"]["analysis"] == accepted
