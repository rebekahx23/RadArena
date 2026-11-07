import json
from pathlib import Path

import dspy
import pytest
from PIL import Image
from dspy.utils.dummies import DummyLM

from radarena.evaluate import verify_case
from radarena.knowledge import KnowledgePack

PACK = Path(__file__).resolve().parents[1] / "knowledge/reporting_v1.json"


def test_versioned_pack_has_shared_cards_role_guidance_and_sources():
    pack = KnowledgePack(PACK)
    assert len(pack.metadata()["card_ids"]) == 9
    assert "Findings and impression" in pack.render("red")
    assert "Findings and impression" in pack.render("verifier")
    assert "Keep the edit record and rationale private" in pack.render("red")
    assert "cite actual observations" in pack.render("verifier")
    assert len(pack.render()) < 8000
    assert len(pack.metadata()["sha256"]) == 64


def test_reference_hash_changes_and_unknown_citations_are_rejected(tmp_path):
    data = json.loads(PACK.read_text())
    path = tmp_path / "pack.json"
    path.write_text(json.dumps(data))
    before = KnowledgePack(path).sha256
    data["cards"][0]["text"] += " Reviewed local revision."
    path.write_text(json.dumps(data))
    assert KnowledgePack(path).sha256 != before
    data["cards"][0]["source_ids"] = ["invented-source"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="known source"):
        KnowledgePack(path)


@pytest.mark.parametrize("variant", ["text_only", "direct_vlm", "blue_tools"])
def test_verifiers_receive_same_knowledge_without_private_case_data(tmp_path, variant):
    pack = KnowledgePack(PACK)
    image = tmp_path / "fixture.png"
    Image.new("RGB", (8, 8), "black").save(image)
    case = {"candidate": [{"id": "s1", "text": "Candidate only."}],
            "image_paths": [str(image)], "source": "SECRET ORIGINAL",
            "private_label": {"secret": "SECRET EDIT RECORD"}}
    verdict = {"decision": "uncertain", "findings": [], "limitations": "Fixture"}
    answers = [{"verdict": verdict}]
    if variant == "blue_tools":
        answers = [{"questions": ["Describe visible abnormalities."]},
                   {"observation": "Synthetic fixture", "limitations": "No clinical evidence"},
                   {"verdict": verdict}]
    lm = DummyLM(answers)
    with dspy.context(lm=lm):
        verify_case(case, variant, lm, lm, knowledge=pack)
    messages = str([h["messages"] for h in lm.history])
    assert "radiology_reporting_v1" in messages
    assert "SECRET ORIGINAL" not in messages and "SECRET EDIT RECORD" not in messages
    if variant == "blue_tools":
        image_messages = str(lm.history[1]["messages"])
        assert "radiology_reporting_v1" not in image_messages
        assert "Candidate only." not in image_messages
