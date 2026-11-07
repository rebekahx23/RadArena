import json
from pathlib import Path

import dspy
import pytest
from PIL import Image
from dspy.utils.dummies import DummyLM

from radarena.benchmark import build_benchmark, read_benchmark, seed_attacks
from radarena.data import Sentence, Study
from radarena.evaluate import (failure_tags, metrics, paired_interval, read_records,
                               run_evaluation, summarize_run, verify_case)


def make_studies(tmp_path):
    studies = []
    for split in ["train", "dev", "test"]:
        for kind, text in [("presence_absence", "No pneumothorax."),
                           ("laterality", "Left basilar opacity."),
                           ("severity", "Mild cardiomegaly.")]:
            uid = f"{split}-{kind}"
            path = tmp_path / f"{uid}.png"
            Image.new("RGB", (8, 8), (len(studies)*20, 0, 0)).save(path)
            studies.append(Study(study_id=uid, split=split, image_ids=[uid],
                image_paths=[str(path)], sentences=[Sentence(id="s1", text=f"FINDINGS: {text}"),
                Sentence(id="s2", text=f"IMPRESSION: Fixture identifier {uid}.")]))
    return studies


def benchmark_fixture(tmp_path):
    manifest, benchmark = tmp_path / "manifest.jsonl", tmp_path / "benchmark.jsonl"
    studies = make_studies(tmp_path)
    manifest.write_text("".join(s.model_dump_json()+"\n" for s in studies))
    build_benchmark(manifest, benchmark, {"train": 3, "dev": 3, "test": 3})
    return manifest, benchmark


def test_freeze_reproducibility_balance_and_tamper_detection(tmp_path):
    manifest, benchmark = benchmark_fixture(tmp_path)
    cases, metadata = read_benchmark(benchmark)
    assert len(cases) == 18
    assert metadata["attack_counts"]["test"] == {"laterality": 1, "presence_absence": 1, "severity": 1}
    other = tmp_path / "same-seed.jsonl"
    build_benchmark(manifest, other, {"train": 3, "dev": 3, "test": 3})
    assert benchmark.read_bytes() == other.read_bytes()
    with pytest.raises(ValueError, match="already exists"):
        build_benchmark(manifest, benchmark, {"train": 3, "dev": 3, "test": 3})
    benchmark.write_text(benchmark.read_text()+"\n")
    with pytest.raises(ValueError, match="checksum"):
        read_benchmark(benchmark)


def test_seed_edits_exclude_repeated_or_negated_attributes(tmp_path):
    study = make_studies(tmp_path)[1]
    study.sentences = [Sentence(id="s1", text="No left pleural effusion.")]
    assert "laterality" not in seed_attacks(study)
    study.sentences = [Sentence(id="s1", text="Left pleural effusion."),
                       Sentence(id="s2", text="Pleural effusion is present.")]
    assert seed_attacks(study) == {}


def test_reject_duplicate_images_across_studies(tmp_path):
    manifest, benchmark = benchmark_fixture(tmp_path)
    rows = [Study.model_validate_json(s) for s in manifest.read_text().splitlines()]
    # Deliberately duplicate every image, so nine independent cases cannot be selected.
    for row in rows:
        row.image_paths = rows[0].image_paths
    manifest.write_text("".join(s.model_dump_json()+"\n" for s in rows))
    with pytest.raises(ValueError, match="Insufficient eligible"):
        build_benchmark(manifest, tmp_path / "bad.jsonl", {"train": 3, "dev": 3, "test": 3})


def row(case_id="a", study_id="1", variant="blue_tools", error=True,
        decision="error", flagged=True, kind="laterality"):
    return {"case_id": case_id, "study_id": study_id, "variant": variant, "status": "ok",
        "private_label": {"has_error": error, "changed_sentence_ids": ["s1"] if error else [],
                          "error_type": "laterality" if error else None},
        "verdict": {"decision": decision, "findings": [{"sentence_id": "s1", "error_type": kind,
            "evidence": "Fixture", "tool_call_ids": ["vision_1"]}] if flagged else [],
            "limitations": "Fixture"}, "elapsed_seconds": 1, "model_calls": []}


def test_metrics_count_abstentions_false_alarms_and_incomplete_runs():
    rows = [row(), row(case_id="b", error=False),
            row(case_id="c", decision="uncertain", flagged=False)]
    m = metrics(rows, expected=4)
    assert m["detection_f1_completed"] == .5
    assert m["localization_counts"] == {"tp": 1, "fp": 1, "fn": 1}
    assert m["false_positive_rate_completed_controls"] == 1
    assert m["strict_decision_accuracy_all_expected"] == .25
    assert m["not_attempted"] == 1
    assert m["abstention_rate_completed"] == 1/3
    assert set(failure_tags(rows[2])) == {"uncertain", "missed_edit"}
    failed = dict(rows[0], status="failed")
    assert metrics([failed])["runtime_failures"] == 1
    assert metrics([failed])["detection_f1_completed"] is None
    assert failure_tags(row(kind="severity")) == ["wrong_category"]


def test_paired_bootstrap_keeps_control_and_attack_together():
    rows = []
    for sid in ["1", "2", "3"]:
        for variant in ["direct_vlm", "blue_tools"]:
            rows.extend([row(case_id=f"{sid}a", study_id=sid, variant=variant),
                         row(case_id=f"{sid}b", study_id=sid, variant=variant,
                             error=False, decision="no_error_detected", flagged=False)])
    result = paired_interval(rows, "direct_vlm", samples=40)
    assert result["difference"] == 0
    assert result["interval_95_percentile"] == [0, 0]
    assert result["bootstrap_studies"] == 3
    assert not paired_interval(rows[:-1], "direct_vlm")["available"]


@pytest.mark.parametrize("variant,evidence", [("text_only", "report_text"), ("direct_vlm", "direct_image")])
def test_baseline_inputs_exclude_gold_and_private_metadata(tmp_path, variant, evidence):
    _, benchmark = benchmark_fixture(tmp_path)
    case = read_benchmark(benchmark)[0][0]
    case["source"] = "PRIVATE ORIGINAL SENTINEL"
    case["private_label"]["secret"] = "PRIVATE LABEL SENTINEL"
    lm = DummyLM([{"verdict": {"decision": "uncertain", "findings": [], "limitations": "Fixture"}}])
    with dspy.context(lm=lm):
        verdict, _ = verify_case(case, variant, lm, lm)
    assert verdict.decision == "uncertain"
    sent = str(lm.history[0]["messages"])
    assert "PRIVATE ORIGINAL SENTINEL" not in sent and "PRIVATE LABEL SENTINEL" not in sent
    if variant == "text_only":
        assert "data:image" not in sent


def test_resume_reuses_completed_predictions_and_summary_keeps_missing_denominator(tmp_path, monkeypatch):
    import radarena.runtime
    _, benchmark = benchmark_fixture(tmp_path)
    lm = DummyLM([{"verdict": {"decision": "uncertain", "findings": [], "limitations": "Fixture"}}]*6)
    monkeypatch.setattr(radarena.runtime, "make_models", lambda: (lm, DummyLM([])))
    output = tmp_path / "run"
    with dspy.context(lm=lm):
        summary = run_evaluation(benchmark, output, "dev", ["text_only"])
        assert summary["complete"]
        assert len(lm.history) == 6
        run_evaluation(benchmark, output, "dev", ["text_only"])
        assert len(lm.history) == 6
    records = read_records(output / "predictions.jsonl")
    (output / "predictions.jsonl").write_text(json.dumps(records[0])+"\n")
    partial = summarize_run(output)
    assert not partial["complete"]
    assert partial["variants"]["text_only"]["not_attempted"] == 5
