"""Golden saved-artifact adapters: online rewrites, private learning and judges."""

import json

import pytest

from radarena.viewer import RunStore


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def tape(path, stage, role, fields, output, cost=.01, failed=False):
    messages = [{"role": "system", "content": "Your input fields are: " + fields + " Your output fields are:"}]
    records = [{"event": "start", "call_number": 1, "context": {"role": role, "stage": stage},
                "model": "fixture/model", "reserved_cost_usd": .1, "inputs": {"messages": messages}},
               {"event": "end", "call_number": 1, "outputs": [json.dumps(output)],
                "accounted_cost_usd": cost, "cost_known": not failed, "history": [],
                "exception_type": "FixtureFailure" if failed else None}]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in records))


def test_online_rewrites_controls_judges_and_memory_have_distinct_views(tmp_path):
    root = tmp_path / "runs/online"
    source = [{"id": "s1", "text": "Source claim."}, {"id": "s2", "text": "Removed claim."}]
    candidate = [{"id": "s1", "text": "Source claim."}]
    selection = [{"study_id": "7", "sentences": source, "image_paths": ["/fixture.png"]}]
    save(root / "metadata.json", {"initial_memories": {"red": {"initial": ["Prior Red rule"]}},
                                 "judges": ["judge/a", "judge/b"], "version": 1, "protocol": "Online learning"})
    save(root / "selection.json", selection)
    change = {"source_ids": ["s2"], "candidate_ids": [], "category": "omission", "description": "Removed a claim."}
    red = {"study_id": "7", "source": source, "candidate": candidate, "changes": [change], "rationale": "Fixture rationale."}
    blue = {"candidate": candidate, "blue": {"decision": "uncertain", "findings": [], "limitations": "Fixture."}, "observations": []}
    save(root / "stages/01-7-red.json", red)
    save(root / "stages/01-7-blue.json", blue)
    save(root / "stages/01-7-control.json", {**blue, "candidate": source})
    for name, role, fields, out in [
        ("01-7-red", "red", "`source` `images` `own_rules`", {"candidate": candidate, "changes": [change]}),
        ("01-7-blue", "blue", "`candidate` `observations` `own_rules`", {"verdict": blue["blue"]}),
        ("01-7-control", "blue", "`candidate` `observations` `own_rules`", {"verdict": blue["blue"]})]:
        tape(root / "audit" / name / "calls.jsonl", name, role, fields, out)
    for number in (1, 2):
        name = f"01-7-judge{number}"
        review = {"attack_validity": "uncertain", "blue_assessment": "uncertain", "reviewed_flag_ids": [],
                  "blue_explanation": f"Reviewer {number}'s overall explanation.", "confidence": "low"}
        save(root / "stages" / f"{name}.json", {"status": "ok", "model": f"judge/{number}", "review": review})
        tape(root / "audit" / name / "calls.jsonl", name, "judge", "`episode` `actual_blue_flag_ids`", {"review": review})
    memory = {"library": {"omission": ["New private rule"]}, "explanation": "Memory feedback."}
    save(root / "stages/round-1-red-memory.json", memory)
    save(root / "memories/red/v1.json", memory)
    tape(root / "audit/round-1-red-memory/calls.jsonl", "round-1-red-memory", "red", "`trusted_feedback`", memory)
    store = RunStore(tmp_path / "runs", tmp_path / "missing")
    assert list(store.discover()) == ["online"]
    result = store.run("online")
    assert result["kind"] == "Open-ended online"
    assert result["calls_count"] == 6 and result["cost"] == pytest.approx(.06)
    assert result["agent_cost"] == pytest.approx(.04) and result["judge_cost"] == pytest.approx(.02)
    assert len(result["episodes"]) == 3
    attack, control, update = result["episodes"]
    assert attack["candidate"] == candidate and attack["attack"]["changed_sentence_ids"] == ["s2"]
    assert attack["score_scope"] == "open_report" and attack["score"] is None
    assert len(attack["judges"]) == 2
    assert attack["judges"][0]["record"]["analysis"]["blue_explanation"].startswith("Reviewer 1")
    assert "flag_reviews" not in attack["judges"][0]["record"]["analysis"]
    assert attack["judges"][0]["calls"][0]["review_disposition"] == "accepted"
    assert control["attacker_kind"] == "none" and control["candidate"] == source
    assert update["memory_rules"] == ["New private rule"] and update["image_paths"] == []
    assert len({c["id"] for episode in result["episodes"] for c in episode["calls"]}) == 6


def test_interrupted_online_stage_remains_visible_without_an_episode_file(tmp_path):
    root = tmp_path / "runs/online"
    save(root / "metadata.json", {"initial_memories": {"red": {"initial": []}}, "judges": ["judge/a"]})
    (root / "stages").mkdir()
    save(root / "selection.json", [{"study_id": "8", "sentences": [{"id": "s1", "text": "Source."}]}])
    tape(root / "audit/02-8-red/calls.jsonl", "02-8-red", "red", "`source`", {}, cost=.1, failed=True)
    result = RunStore(tmp_path / "runs", tmp_path / "missing").run("online")
    assert result["completed_studies"] == 0
    assert result["episodes"][0]["status"] == "failed"
    assert result["episodes"][0]["verdict"] is None
    assert result["unknown_calls"] == 1 and result["cost"] == pytest.approx(.1)


def test_learning_stages_do_not_collapse_and_red_train_role_is_recovered(tmp_path):
    root = tmp_path / "runs/learning"
    source = [{"id": "s1", "text": "Source."}]
    candidate = [{"id": "s1", "text": "Changed."}]
    case = {"case_id": "case-a", "study_id": "7", "source": source, "candidate": candidate}
    save(root / "metadata.json", {"learning": "Three private strategy rounds"})
    save(root / "organizer/selection.json", [case])
    generated = {"study_id": "7", "source": source, "candidate": candidate,
                 "changed_sentence_ids": ["s1"], "edits": [{"sentence_id": "s1", "replacement": "Changed."}]}
    saved_blue = {**case, "blue": {"decision": "uncertain", "findings": []}, "observations": [], "changed_sentence_ids": ["s1"]}
    save(root / "train/round-1/red_attack.json", generated)
    save(root / "train/round-1/blue_attack.json", saved_blue)
    save(root / "train/round-1/blue_control.json", {**saved_blue, "candidate": source, "changed_sentence_ids": []})
    save(root / "blue_eval/before/case-a.json", saved_blue)
    save(root / "blue_eval/after/case-a.json", saved_blue)
    records = []
    stage_names = ["train/round-1/red_attack", "train/round-1/blue_attack", "train/round-1/blue_control",
                   "blue_eval/before/case-a", "blue_eval/after/case-a"]
    for number, stage in enumerate(stage_names, 1):
        records.extend([{"event": "start", "call_number": number, "context": {"role": stage.split('/')[0], "stage": stage},
            "inputs": {"messages": [{"role": "system", "content": "Your input fields are: `source_sentences` Your output fields"}]}, "model": "fixture", "reserved_cost_usd": .1},
            {"event": "end", "call_number": number, "outputs": [], "history": [], "cost_known": True, "accounted_cost_usd": .01}])
    path = root / "audit/calls.jsonl"; path.parent.mkdir()
    path.write_text("".join(json.dumps(r) + '\n' for r in records))
    store = RunStore(tmp_path / "runs", tmp_path / "missing")
    run = store.run("learning")
    assert run["kind"] == "Learning pilot" and len(run["episodes"]) == 4
    attack = next(e for e in run["episodes"] if e["variant"] == "learned_attack")
    assert attack["calls"][0]["role"] == "red" and attack["calls"][0]["name"] == "MakeAttack"
    assert len(attack["calls"]) == 2
    assert {e["checkpoint"] for e in run["episodes"] if e["variant"].startswith("blue_eval")} == {"before", "after"}
    assert run["cost"] == pytest.approx(.05)
