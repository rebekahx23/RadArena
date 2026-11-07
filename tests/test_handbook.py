import json
from pathlib import Path

import dspy
import pytest
from PIL import Image
from dspy.utils.dummies import DummyLM

from radarena.evaluate import verify_case
from radarena.handbook import RadiologyHandbook, UNAVAILABLE
from radarena.knowledge import load_pack

ROOT = Path(__file__).resolve().parents[1] / "handbooks/radiology-handbook"
MEDICAL = "references/medical-library/pleural-effusion.md"
DOMAIN = "references/blue-team/workflow.md"


@pytest.mark.parametrize("condition,domain_allowed,medical_allowed", [
    ("full", True, True), ("no_domain", False, True),
    ("no_medical", True, False), ("none", False, False)])
def test_ablation_hides_catalog_entries_and_blocks_direct_reads(condition, domain_allowed, medical_allowed):
    book = RadiologyHandbook(ROOT, condition=condition)
    catalog = {e["path"] for e in book.catalog()}
    assert (DOMAIN in catalog) == domain_allowed
    assert (MEDICAL in catalog) == medical_allowed
    assert (book.read(DOMAIN) != UNAVAILABLE) == domain_allowed
    assert (book.read(MEDICAL) != UNAVAILABLE) == medical_allowed
    assert "contracts" in book.read("references/tools/contracts.md").lower()


def test_role_boundaries_path_traversal_and_unlisted_files():
    book = RadiologyHandbook(ROOT)
    for path in ["../README.md", "/etc/passwd", "references/../../README.md", "handbook.json",
                 "references/red-team/workflow.md"]:
        with pytest.raises(ValueError):
            book.read(path, "verifier")
    tool = book.tool_for("red")
    assert "Red workflow" in tool("references/red-team/workflow.md")["text"]
    with pytest.raises(ValueError):
        tool(DOMAIN)


def test_bootstrap_is_small_and_does_not_eagerly_include_medical_chapters():
    book = RadiologyHandbook(ROOT)
    text = book.render()
    assert (ROOT / "references/blue-team/SKILL.md").read_text() in text
    assert (ROOT / "references/red-team/SKILL.md").read_text() not in text
    assert "Source-grounded background" not in text
    assert len(text) < 5000


def test_lazy_chapter_read_returns_exact_source_and_logs_selected_paths():
    book = RadiologyHandbook(ROOT)
    lm = DummyLM([{"chapter_paths": [MEDICAL]}])
    with dspy.context(lm=lm):
        text = book.context_for("verifier", "Candidate mentions fluid", lm)
    assert (ROOT / MEDICAL).read_text() in text
    assert "# Pneumothorax\n" not in text
    assert book.last_access[-1]["path"] == MEDICAL
    assert len(lm.history) == 1


@pytest.mark.parametrize("paths", [["../README.md"], ["references/red-team/workflow.md"],
    [DOMAIN, MEDICAL, "references/reporting/claims.md", "SOURCES.md"]])
def test_selector_cannot_escape_role_or_exceed_budget(paths):
    book = RadiologyHandbook(ROOT)
    lm = DummyLM([{"chapter_paths": paths}])
    with dspy.context(lm=lm), pytest.raises(ValueError):
        book.context_for("verifier", "Candidate", lm)


def test_changed_handbook_and_symlink_escape_are_rejected(tmp_path):
    import shutil
    copied = tmp_path / "book"
    shutil.copytree(ROOT, copied)
    book = RadiologyHandbook(copied)
    path = copied / DOMAIN
    path.write_text(path.read_text()+"\nNew version\n")
    with pytest.raises(ValueError, match="changed"):
        book.read(DOMAIN)
    path.unlink()
    external = tmp_path / "outside.md"
    external.write_text("Private")
    path.symlink_to(external)
    with pytest.raises(ValueError, match="escapes"):
        RadiologyHandbook(copied)


def test_handbook_selection_sees_candidate_only_and_flows_into_blue(tmp_path):
    book = load_pack(ROOT)
    path = tmp_path / "fixture.png"
    Image.new("RGB", (8, 8), "black").save(path)
    case = {"candidate": [{"id": "s1", "text": "Candidate only"}],
            "image_paths": [str(path)], "source": "PRIVATE ORIGINAL",
            "private_label": {"secret": "PRIVATE EDIT LABEL"}}
    lm = DummyLM([
        {"chapter_paths": [DOMAIN]}, {"questions": ["Describe abnormalities."]},
        {"observation": "Fixture", "limitations": "Synthetic pixels"},
        {"verdict": {"decision": "uncertain", "findings": [], "limitations": "Fixture"}},
    ])
    with dspy.context(lm=lm):
        verdict, _ = verify_case(case, "blue_tools", lm, lm, knowledge=book)
    assert verdict.decision == "uncertain"
    all_messages = str([h["messages"] for h in lm.history])
    assert "PRIVATE ORIGINAL" not in all_messages and "PRIVATE EDIT LABEL" not in all_messages
    assert "Blue verification workflow" in str(lm.history[1]["messages"])
    assert "Blue verification workflow" not in str(lm.history[2]["messages"])


def test_json_pack_cannot_silently_ignore_handbook_ablation():
    with pytest.raises(ValueError, match="directory"):
        load_pack(None, condition="none")
    with pytest.raises(ValueError, match="JSON"):
        load_pack(ROOT.parents[1] / "knowledge/reporting_v1.json", condition="no_medical")
