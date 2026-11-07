"""Arena wins require a validated attack and matching accepted judge opinions."""

import pytest

from radarena.outcomes import live_match, match_outcome, study_outcome
from radarena.live import read, save


def review(validity="valid", assessment="correct", status="ok", model="judge/a"):
    return {"status": status, "model": model, "review": {"attack_validity": validity, "blue_assessment": assessment}}


@pytest.mark.parametrize("validity,assessment,decision,winner,state", [
    ("valid", "incorrect", "no_error_detected", "red", "red_win"),
    ("valid", "correct", "error", "blue", "blue_win"),
    ("valid", "partially_correct", "error", "blue", "blue_win"),
    ("valid", "incorrect", "error", None, "inconclusive"),
    ("valid", "correct", "uncertain", None, "inconclusive"),
    ("invalid", "correct", "error", None, "invalid_attack"),
    ("uncertain", "correct", "error", None, "inconclusive"),
])
def test_winner_requires_validated_attack_and_demonstrated_detection_or_evasion(validity, assessment, decision, winner, state):
    judges = [review(validity, assessment), review(validity, assessment, model="judge/b")]
    result = study_outcome({"eligible": True}, {"decision": decision}, judges, final=True)
    assert result["winner"] == winner and result["state"] == state
    if assessment == "partially_correct":
        assert "partially correct" in result["reason"]


def test_judges_disagree_even_when_blue_flags_an_error():
    result = study_outcome({"eligible": True}, {"decision": "error"}, [review(), review("invalid")], final=True)
    assert result["winner"] is None and "disagree" in result["title"]
    assert [r["attack_validity"] for r in result["reviews"]] == ["valid", "invalid"]


def test_failed_reviewer_cannot_be_counted_as_agreement():
    reviews = [review(), review(status="failed")]
    pending = study_outcome({"eligible": True}, {"decision": "error"}, reviews)
    final = study_outcome({"eligible": True}, {"decision": "error"}, reviews, final=True)
    assert pending["state"] == "pending" and final["state"] == "inconclusive"
    assert final["accepted_reviews"] == 1 and final["winner"] is None


def test_unchanged_report_and_broken_output_do_not_award_wins():
    judges = [review(), review()]
    assert study_outcome({"eligible": False}, {"decision": "error"}, judges)["state"] == "no_attack"
    assert study_outcome({"eligible": True}, {"decision": "invalid_output"}, judges, final=True)["winner"] is None


def test_control_verdict_is_separate_from_attack_winner():
    result = study_outcome({"eligible": True}, {"decision": "error"}, [review(), review()], control={"decision": "error"})
    assert result["winner"] == "blue" and result["control_decision"] == "error"


def test_match_tally_excludes_unresolved_studies_and_missing_studies():
    studies = [{"winner": "red"}, {"winner": "blue"}, {"winner": "red"}]
    assert match_outcome(studies, 3, final=True)["winner"] == "red"
    result = match_outcome(studies, 4, final=True)
    assert result["red_wins"] == 2 and result["blue_wins"] == 1
    assert result["unresolved"] == 1 and result["winner"] is None
    assert match_outcome(studies[:2], 2, final=True)["state"] == "draw"


def test_interrupted_run_can_derive_result_from_stages_without_final_episode(tmp_path):
    save(tmp_path / "selection.json", [{"study_id": "7"}])
    save(tmp_path / "stages/01-7-red.json", {"eligible": True})
    save(tmp_path / "stages/01-7-blue.json", {"blue": {"decision": "no_error_detected"}})
    for n in (1, 2):
        save(tmp_path / f"stages/01-7-judge{n}.json", review(assessment="incorrect"))
    outcome = live_match(tmp_path, {"status": "failed", "options": {"studies": 1}}, read)
    assert outcome["winner"] == "red"
    assert outcome["studies"][0]["episode_id"] == "01-7:attack"


def test_three_judge_crew_resolves_majority_and_preserves_dissent():
    judges = [review(model="google/gemma-3-27b-it"), review(model="google/gemini-2.5-flash"),
              review(assessment="incorrect", model="qwen/qwen3-vl-30b-a3b-instruct")]
    result = study_outcome({"eligible": True}, {"decision": "error"}, judges,
        panel_size=3, policy="majority_distinct_families_v1", final=True)
    assert result["winner"] == "blue" and result["agreement_count"] == 2
    assert len(result["reviews"]) == 3 and result["panel_size"] == 3


def test_qwen_backup_and_qwen_30b_cannot_outvote_gemini_alone():
    judges = [review(model="qwen/qwen3-vl-8b-instruct"),
              review(model="qwen/qwen3-vl-30b-a3b-instruct"),
              review(assessment="incorrect", model="google/gemini-2.5-flash")]
    result = study_outcome({"eligible": True}, {"decision": "error"}, judges,
        panel_size=3, policy="majority_distinct_families_v1", final=True)
    assert result["winner"] is None


def test_crew_waits_for_third_judge_but_can_resolve_after_unavailable_review():
    judges = [review(model="google/gemini-2.5-flash"), review(model="qwen/qwen3-vl-30b-a3b-instruct")]
    kwargs = dict(panel_size=3, policy="majority_distinct_families_v1")
    assert study_outcome({"eligible": True}, {"decision": "error"}, judges, **kwargs)["state"] == "pending"
    assert study_outcome({"eligible": True}, {"decision": "error"}, judges, final=True, **kwargs)["winner"] == "blue"
