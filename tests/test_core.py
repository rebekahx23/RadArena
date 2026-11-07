from pathlib import Path
from types import SimpleNamespace

import dspy
import pytest
from PIL import Image
from dspy.utils.dummies import DummyLM

from radarena.agents import BlueVerifier, Edit, Verdict, apply_edits, score_edits
from radarena.data import Sentence, load_iu, load_iu_csv, split_for


def test_iu_join_and_missing_views(tmp_path):
    reports, images = tmp_path / "reports", tmp_path / "images"
    reports.mkdir()
    images.mkdir()
    (reports / "1.xml").write_text('''<eCitation><uId id="CXR1"/>
    <MedlineCitation><Article><Abstract>
    <AbstractText Label="INDICATION">SECRET HISTORY</AbstractText>
    <AbstractText Label="FINDINGS">Clear lungs. No effusion.</AbstractText>
    <AbstractText Label="IMPRESSION">No acute findings.</AbstractText>
    </Abstract></Article></MedlineCitation>
    <parentImage id="CXR1_IM-0001-1001"/><parentImage id="CXR1_IM-0001-2001"/>
    </eCitation>''')
    (images / "CXR1_IM-0001-1001.png").touch()
    studies, summary = load_iu(reports, images)
    assert studies == []
    assert summary["skipped"]["missing_image_files"] == 1
    (images / "CXR1_IM-0001-2001.png").touch()
    studies, summary = load_iu(reports, images)
    assert len(studies) == 1
    assert len(studies[0].image_paths) == 2
    assert len(studies[0].sentences) == 3
    assert "SECRET" not in studies[0].model_dump_json()
    assert studies[0].split == split_for("CXR1")


def test_no_xml_is_not_silent_empty_dataset(tmp_path):
    with pytest.raises(ValueError, match="No XML"):
        load_iu(tmp_path)


def test_attack_preserves_original_and_sentence_ids():
    source = [Sentence(id="s1", text="Left effusion."), Sentence(id="s2", text="Clear right lung.")]
    candidate = apply_edits(source, [Edit(sentence_id="s1", replacement="Right effusion.")])
    assert source[0].text == "Left effusion."
    assert candidate[0].text == "Right effusion."
    assert candidate[1] == source[1]
    assert [s.id for s in candidate] == [s.id for s in source]


@pytest.mark.parametrize("edits", [[], [Edit(sentence_id="bad", replacement="Text")],
    [Edit(sentence_id="s1", replacement="Same.")],
    [Edit(sentence_id="s1", replacement="A"), Edit(sentence_id="s1", replacement="B")]])
def test_invalid_edits_rejected(edits):
    with pytest.raises(ValueError):
        apply_edits([Sentence(id="s1", text="Same.")], edits)


def test_real_dspy_module_with_offline_lm(tmp_path):
    # Synthetic blank pixels test API mechanics only, never radiology quality.
    image = tmp_path / "fixture.png"
    Image.new("RGB", (16, 16), "black").save(image)
    lm = DummyLM([
        {"questions": ["Describe pleural fluid."]},
        {"observation": "Fixture observation.", "limitations": "Synthetic test."},
        {"verdict": {"decision": "error", "findings": [{"sentence_id": "s1",
          "error_type": "laterality", "evidence": "Fixture evidence.",
          "tool_call_ids": ["vision_1"]}], "limitations": "Synthetic test."}},
    ])
    with dspy.context(lm=lm):
        result = BlueVerifier()(candidate=[Sentence(id="s1", text="Candidate only.")],
                                images=[dspy.Image.from_path(str(image))])
    assert result.verdict.findings[0].sentence_id == "s1"
    assert len(lm.history) == 3
    # The image inspection request does not receive candidate text or hidden gold.
    tool_messages = str(lm.history[1]["messages"])
    assert "Candidate only." not in tool_messages
    assert "Describe pleural fluid." in tool_messages


def test_tool_budget_and_verdict_ids():
    blue = BlueVerifier()
    calls = []
    blue.plan = lambda **kw: SimpleNamespace(questions=[f"Question {i}" for i in range(10)])
    def inspect(**kw):
        calls.append(kw)
        assert set(kw) == {"images", "question"}
        return SimpleNamespace(observation="Unavailable", limitations="Test")
    blue.inspect = inspect
    blue.assess = lambda **kw: SimpleNamespace(verdict={
        "decision": "uncertain", "findings": [], "limitations": "Test"})
    result = blue(candidate=[Sentence(id="s1", text="Candidate")], images=["test-image"])
    assert len(calls) == 3
    assert result.verdict.decision == "uncertain"
    blue.assess = lambda **kw: SimpleNamespace(verdict={"decision": "error", "findings": [{
        "sentence_id": "unknown", "error_type": "severity", "evidence": "Test",
        "tool_call_ids": ["vision_1"]}], "limitations": "Test"})
    with pytest.raises(ValueError, match="unknown sentence"):
        blue(candidate=[Sentence(id="s1", text="Candidate")], images=["test-image"])


def test_localization_counts_false_positives_and_misses():
    verdict = Verdict(decision="error", findings=[{
        "sentence_id": s, "error_type": "laterality", "evidence": "Test",
        "tool_call_ids": ["vision_1"]} for s in ["s1", "s3"]], limitations="Test")
    score = score_edits(["s1", "s2"], verdict)
    assert (score["localization_tp"], score["localization_fp"], score["localization_fn"]) == (1, 1, 1)
    uncertain = Verdict(decision="uncertain", findings=[], limitations="Test")
    assert not score_edits(["s1"], uncertain)["injected_edit_detected"]


def test_csv_export_joins_by_uid_and_exact_image_filename(tmp_path):
    import csv
    reports, projections = tmp_path / "reports.csv", tmp_path / "projections.csv"
    with reports.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=["uid", "findings", "impression", "Problems"])
        writer.writeheader()
        writer.writerows([{"uid": "2", "findings": "Right effusion.", "Problems": "HIDDEN LABEL"},
                         {"uid": "1", "impression": "No acute findings."}])
    with projections.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=["uid", "filename", "projection"])
        writer.writeheader()
        writer.writerows([{"uid": "1", "filename": "1_IM.dcm.png", "projection": "Frontal"},
                         {"uid": "2", "filename": "2_IM.dcm.png", "projection": "Lateral"}])
    (tmp_path / "1_IM.dcm.png").touch()
    (tmp_path / "2_IM.dcm.png").touch()
    studies, summary = load_iu_csv(reports, projections, tmp_path)
    assert summary["eligible"] == 2
    assert Path(studies[0].image_paths[0]).name == "2_IM.dcm.png"
    assert studies[0].image_views == ["Lateral"]
    assert "HIDDEN LABEL" not in studies[0].model_dump_json()
    (tmp_path / "2_IM.dcm.png").unlink()
    studies, summary = load_iu_csv(reports, projections, tmp_path)
    assert len(studies) == 1
    assert summary["skipped"]["missing_image_files"] == 1


def test_full_cli_episode_uses_isolated_red_and_blue_contexts(tmp_path, monkeypatch):
    from argparse import Namespace
    import json
    from radarena.cli import run_demo
    from radarena.data import Study
    import radarena.runtime

    image = tmp_path / "fixture.png"
    Image.new("RGB", (16, 16), "black").save(image)
    source = "PRIVATE ORIGINAL: left effusion."
    study = Study(study_id="test", split="train", image_ids=["fixture"],
                  image_paths=[str(image)], sentences=[Sentence(id="s1", text=source)])
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(study.model_dump_json() + "\n")
    text_lm = DummyLM([
        {"questions": ["Describe fluid location."]},
        {"verdict": {"decision": "uncertain", "findings": [], "limitations": "Fixture"}},
    ])
    vision_lm = DummyLM([
        {"edits": [{"sentence_id": "s1", "replacement": "Right effusion."}],
         "private_rationale": "PRIVATE ATTACK RATIONALE"},
        {"observation": "Fixture only.", "limitations": "Blank synthetic pixels"},
    ])
    monkeypatch.setattr(radarena.runtime, "make_models", lambda: (text_lm, vision_lm))
    indications = tmp_path / "indications.csv"
    indications.write_text("uid,indication,Problems\ntest,CONTEXT cough,SECRET DIAGNOSTIC LABEL\n")
    from radarena.learning import digest
    red_memory, blue_memory = tmp_path / "red-memory.json", tmp_path / "blue-memory.json"
    for role, path in [("red", red_memory), ("blue", blue_memory)]:
        rules = [role.upper() + " PRIVATE STRATEGY"]
        path.write_text(json.dumps({"role": role, "rules": rules, "memory_sha256": digest(rules)}))
    output = tmp_path / "result.json"
    with dspy.context(lm=text_lm):
        run_demo(Namespace(manifest=manifest, study_id="test", control=False,
                           error_type="laterality", output=output, indications_csv=indications,
                           red_memory=red_memory, blue_memory=blue_memory))
    record = json.loads(output.read_text())
    assert record["private_attack"]["clinical_validity"] == "not_adjudicated"
    assert record["score"]["injected_edit_detected"] is False
    blue_messages = str([h["messages"] for h in text_lm.history])
    assert source not in blue_messages
    assert "PRIVATE ATTACK RATIONALE" not in blue_messages
    assert "BLUE PRIVATE STRATEGY" in blue_messages
    assert "RED PRIVATE STRATEGY" not in blue_messages
    assert "RED PRIVATE STRATEGY" in str(vision_lm.history[0]["messages"])
    assert "BLUE PRIVATE STRATEGY" not in str(vision_lm.history[0]["messages"])
    assert "CONTEXT cough" in blue_messages
    assert "CONTEXT cough" in str(vision_lm.history[0]["messages"])
    assert "SECRET DIAGNOSTIC LABEL" not in blue_messages + str(vision_lm.history)
    assert record["clinical_context"] == "CONTEXT cough"
    assert "Right effusion." in blue_messages
