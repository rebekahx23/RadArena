"""Launch guards and the actual demo pipeline with provider calls substituted in tests."""

import io
import json
import uuid
from types import SimpleNamespace

import pytest

from radarena.live import LiveArena, options, read, save
from radarena.viewer import RunStore, make_handler


def config(**overrides):
    return {"studies": 1, "controls": True, "learn": True, "budget": 1,
            "red_rules": [], "blue_rules": [], "launch_id": str(uuid.uuid4()), **overrides}


@pytest.mark.parametrize("overrides", [{"studies": 0}, {"studies": 11}, {"studies": True}, {"budget": float("nan")},
    {"budget": 100}, {"controls": "false"}, {"learn": 1}, {"model": "arbitrary"},
    {"red_rules": ["x" * 351]}, {"launch_id": "../../elsewhere"}])
def test_launch_options_are_bounded(overrides):
    with pytest.raises(ValueError):
        options(config(**overrides))


def test_duplicate_launch_is_idempotent_single_active_run_and_cooperative_stop(tmp_path, monkeypatch):
    spawned = []
    def spawn(args, **kwargs):
        spawned.append(args)
        return SimpleNamespace(pid=12345, poll=lambda: None)
    manager = LiveArena(tmp_path / "runs", tmp_path / "manifest", spawn)
    monkeypatch.setattr(manager, "ready", lambda: {"ready": True})
    cfg = config()
    first = manager.start(cfg)
    assert manager.start(cfg)["id"] == first["id"]
    assert len(spawned) == 1 and "radarena.live_runner" in spawned[0]
    with pytest.raises(ValueError, match="already active"):
        manager.start(config())
    manager.stop(first["id"])
    status = manager.status()["sessions"][0]
    assert status["stop_requested"] and status["status"] == "stopping"
    assert "pid" not in status
    assert (tmp_path / "runs" / first["id"] / "stop.requested").is_file()
    with pytest.raises(ValueError):
        manager.stop("../../escape")


def test_dead_worker_is_interrupted_without_losing_results(tmp_path, monkeypatch):
    manager = LiveArena(tmp_path / "runs", tmp_path / "manifest")
    root = manager.runs / "live-interrupted"
    save(root / "live.json", {"id": root.name, "status": "running", "options": config()})
    save(root / "audit/stage/budget.json", {"accounted_cost_usd": .25, "started_calls": 1})
    session = manager.sessions()[0]
    assert session["status"] == "interrupted" and session["cost"] == .25 and session["calls"] == 1


def test_launch_requires_same_origin_small_json_and_only_explicit_start(tmp_path):
    invocations = []
    live = SimpleNamespace(start=lambda body: invocations.append(body) or {"id": "live-test"})
    handler_class = make_handler(RunStore(tmp_path, tmp_path / "manifest"), live)
    def post(origin="http://127.0.0.1:8765", host="127.0.0.1:8765", content_type="application/json", path="/api/live/start", body=None):
        handler = object.__new__(handler_class)
        payload = json.dumps(body or config()).encode()
        handler.path = path
        handler.headers = {"Origin": origin, "Host": host, "Content-Type": content_type, "Content-Length": str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        result = []
        handler.send_content = lambda data, content_type, status=200: result.append(status)
        handler.do_POST()
        return result[0]
    assert post(origin="https://evil.example") == 403
    assert post(origin="") == 403
    assert post(origin="http://evil.example", host="evil.example") == 403
    assert post(content_type="text/plain") == 400
    assert post(path="/api/run") == 400
    assert not invocations
    assert post() == 200 and len(invocations) == 1


@pytest.mark.parametrize("controls,learn", [(True, True), (False, True), (False, False)])
def test_fresh_pipeline_controls_private_memories_and_uncached_clients(tmp_path, monkeypatch, controls, learn):
    import dspy
    from radarena import live_runner as runner
    root = tmp_path / "runs/live-test"
    rules = {"red": ["Red private guidance"], "blue": ["Blue private guidance"]}
    cfg = config(controls=controls, learn=learn, red_rules=rules["red"], blue_rules=rules["blue"])
    save(root / "live.json", {"id": "live-test", "status": "starting", "options": cfg, "created_at": "fixture"})
    image = tmp_path / "scan.png"
    image.write_bytes(b"test image")
    source = [{"id": "s1", "text": "Source claim."}]
    row = {"study_id": "7", "split": "train", "image_ids": ["a"], "image_paths": [str(image)], "sentences": source}
    manifest = tmp_path / "manifest"
    manifest.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(runner, "Indications", lambda _: SimpleNamespace(get=lambda _: "Indication"))
    monkeypatch.setattr(runner, "load_pack", lambda _: SimpleNamespace(render=lambda _: "Reference"))
    monkeypatch.setattr(runner.DemoRunner, "images", lambda *args: [])
    clients = []
    def model(name, *, cache):
        assert cache is False
        clients.append(name)
        return dspy.LM("openrouter/" + name, cache=False)
    monkeypatch.setattr(runner, "make_judge_model", model)
    inputs = []
    def predict(self, signature, lm, **kwargs):
        self.check_stop()
        inputs.append((signature.__name__, kwargs))
        name = signature.__name__
        if name == "LiveAttack":
            assert kwargs["own_rules"] == rules["red"]
            return SimpleNamespace(candidate=[{"id": "s1", "text": "Fresh runtime change."}],
                changes=[{"source_ids": ["s1"], "candidate_ids": ["s1"], "category": "test", "description": "Runtime edit"}], rationale="Generated now")
        if name == "PlanChecks":
            assert kwargs["strategies"] == rules["blue"]
            assert "source" not in kwargs and "changes" not in kwargs
            return SimpleNamespace(questions=["What is visible?"])
        if name == "InspectImage":
            return SimpleNamespace(observation="Observation", limitations="Fallible")
        if name == "OpenAssess":
            assert kwargs["own_rules"] == rules["blue"]
            return SimpleNamespace(verdict={"decision": "no_error_detected", "findings": [], "limitations": "Uncertain"})
        if name == "ReviewOpen":
            assert "own_rules" not in kwargs
            return SimpleNamespace(review={"attack_validity": "valid", "attack_explanation": "Fixture review", "blue_assessment": "incorrect", "reviewed_flag_ids": [], "blue_explanation": "Missed", "failure_modes": [], "confidence": "low", "limitations": "Fixture"})
        if name == "UpdateLessons":
            assert kwargs["previous_own_rules"] == rules[kwargs["role"]]
            return SimpleNamespace(lessons=[], explanation="No new rule warranted.")
        raise AssertionError(name)
    monkeypatch.setattr(runner.DemoRunner, "predict", predict)
    runner.DemoRunner(root, manifest).run()
    record = read(next((root / "episodes").glob("*.json")))
    assert record["source"] == source
    assert record["candidate"][0]["text"] == "Fresh runtime change."
    assert ("control" in record) is controls
    assert len(record["reviews"]) == 3
    assert read(root / "live.json")["status"] == "complete"
    assert bool(list((root / "memories").glob("*/v1.json"))) is learn
    assert len([name for name, _ in inputs if name == "PlanChecks"]) == (2 if controls else 1)
    assert bool([name for name, _ in inputs if name == "UpdateLessons"]) is (controls and learn)
    result = RunStore(tmp_path / "runs", manifest).run("live-test")
    assert result["live_demo"] and result["complete"]
    assert result["episodes"][0]["candidate"] == record["candidate"]


def test_stop_before_first_request_never_creates_client(tmp_path, monkeypatch):
    from radarena.live_runner import DemoRunner
    root = tmp_path / "live-stop"
    save(root / "live.json", {"options": config()})
    (root / "stop.requested").touch()
    DemoRunner(root, tmp_path / "missing").run()
    assert read(root / "live.json")["status"] == "stopped"
    assert not (root / "audit").exists()


def test_judge_rate_limit_retries_once_and_retains_failed_stage(tmp_path, monkeypatch):
    import dspy
    from radarena import live_runner as runner
    root = tmp_path / "live-retry"
    save(root / "live.json", {"options": config()})
    monkeypatch.setattr(runner, "make_judge_model", lambda *args, **kwargs: dspy.LM("openrouter/test", cache=False))
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    attempts = []
    class LMRateLimitError(Exception):
        pass
    def unavailable(lm):
        attempts.append(lm)
        raise LMRateLimitError("fixture")
    demo = runner.DemoRunner(root, tmp_path / "unused")
    result = demo.stage("01-7-judge1", "judge", "judge1", unavailable, optional=True)
    assert len(attempts) == 2
    assert result["status"] == "failed" and "review" not in result
    assert read(root / "stages/01-7-judge1.json")["error_type"] == "LMRateLimitError"
    assert read(root / "live.json")["unavailable_reviews"] == 1
    # The next independent reviewer is still executable.
    second = demo.stage("01-7-judge2", "judge", "judge2", lambda _: {"status": "ok", "review": "fixture"}, optional=True)
    assert second["status"] == "ok"


@pytest.mark.parametrize("backup_works", [True, False])
def test_gemma_unavailable_uses_distinct_uncached_backup(tmp_path, monkeypatch, backup_works):
    import dspy
    from radarena import live_runner as runner
    from radarena.live import JUDGE_BACKUPS, JUDGES
    primary = JUDGES[0]
    backup = JUDGE_BACKUPS[primary]
    root = tmp_path / "live-backup"
    save(root / "live.json", {"options": config()})
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    models = []
    def make_model(model, *, cache):
        assert cache is False
        models.append(model)
        return dspy.LM("openrouter/" + model, cache=False)
    monkeypatch.setattr(runner, "make_judge_model", make_model)
    class LMRateLimitError(Exception):
        pass
    def judge(lm):
        if lm.model == "openrouter/" + primary or not backup_works:
            raise LMRateLimitError("fixture capacity limit")
        return {"status": "ok", "model": lm.model.removeprefix("openrouter/"), "review": {"attack_validity": "valid"}}
    demo = runner.DemoRunner(root, tmp_path / "unused")
    result = demo.stage("01-7-judge1", "judge", "judge1", judge, primary, optional=True, fallback_model=backup)
    assert models == [primary, primary, backup] + ([] if backup_works else [backup])
    assert result["status"] == ("ok" if backup_works else "failed")
    assert result["model"] == backup and result["requested_model"] == primary
    assert result["fallback_used"] is True
    assert read(root / "stages/01-7-judge1.json")["model"] == backup
    assert backup != JUDGES[1]


def test_validation_failure_does_not_trigger_model_shopping(tmp_path, monkeypatch):
    import dspy
    from radarena import live_runner as runner
    root = tmp_path / "live-invalid"
    save(root / "live.json", {"options": config()})
    calls = []
    monkeypatch.setattr(runner, "make_judge_model", lambda model, **_: calls.append(model) or dspy.LM("openrouter/" + model))
    def invalid(_):
        raise ValueError("schema invalid")
    result = runner.DemoRunner(root, tmp_path / "unused").stage("judge", "judge", "judge1", invalid,
        "google/gemma-3-27b-it", optional=True, fallback_model="qwen/qwen3-vl-8b-instruct")
    assert len(calls) == 1 and result["fallback_used"] is False
