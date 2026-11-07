import json

import dspy
import pytest
from dspy.utils.dummies import DummyLM
from PIL import Image

from radarena.data import Sentence
from radarena.evaluate import verify_case
from radarena.report_graph import (ReportGraphStore, normalize_annotation, report_hash,
                                   document_input, document_claims, claims_for_graph)


def annotation():
    return {"text": "Possible left effusion .", "entities": {
        "1": {"tokens": "left", "label": "Anatomy::definitely present", "start_ix": 1,
              "relations": [["modify", "2"]]},
        "2": {"tokens": "pleural", "label": "Anatomy::definitely present", "start_ix": 2, "relations": []},
        "3": {"tokens": "effusion", "label": "Observation::uncertain", "start_ix": 3,
              "relations": [["located_at", "2"]]},
    }}


def graph_store(tmp_path):
    sentences = [Sentence(id="s1", text="Possible left pleural effusion.")]
    key = report_hash(sentences)
    graph = {"report_sha256": key, "sentences": [{"sentence_id": "s1",
             "source_text": sentences[0].text, "raw_annotation": annotation(),
             "claims": [{"secret": "DO NOT TRUST PRECOMPUTED CLAIMS"}]}]}
    path = tmp_path / "graphs.json"
    path.write_text(json.dumps({"format_version": 1, "extractor": {"tool": "fixture"},
        "graphs": {key: graph, "PRIVATE ORIGINAL HASH": {"secret": "PRIVATE ORIGINAL GRAPH"}},
        "private_label": "PRIVATE LABEL"}))
    return ReportGraphStore(path), sentences, path


def test_normalization_keeps_uncertainty_and_anatomy_modifiers():
    a = annotation()
    claims = normalize_annotation(a)
    assert claims[0]["status"] == "uncertain"
    assert claims[0]["anatomy"] == ["left pleural"]
    assert claims[0]["relations"][0]["target_entity_id"] == "2"
    a["entities"]["3"]["label"] = "OBS-DA"
    assert normalize_annotation(a)[0]["status"] == "absent"
    a["entities"]["3"]["label"] = "Observation::unrecognized"
    assert normalize_annotation(a)[0]["status"] == "unknown"


def test_bad_relation_and_wrong_report_mapping_fail(tmp_path):
    a = annotation()
    a["entities"]["3"]["relations"] = [["located_at", "999"]]
    with pytest.raises(ValueError, match="relation"):
        normalize_annotation(a)
    store, sentences, path = graph_store(tmp_path)
    with pytest.raises(ValueError, match="exact candidate"):
        store.for_sentences([Sentence(id="s1", text="No effusion.")])
    data = json.loads(path.read_text())
    data["graphs"][report_hash(sentences)]["sentences"][0]["sentence_id"] = "other"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="mapping"):
        ReportGraphStore(path).for_sentences(sentences)


@pytest.mark.parametrize("variant", ["text_only", "direct_vlm", "blue_tools"])
def test_candidate_graph_reaches_verifier_but_not_image_inspector_or_private_data(tmp_path, variant):
    store, sentences, _ = graph_store(tmp_path)
    image = tmp_path / "image.png"
    Image.new("RGB", (8, 8), "black").save(image)
    case = {"candidate": [s.model_dump() for s in sentences], "image_paths": [str(image)],
            "source": "PRIVATE SOURCE", "private_label": "PRIVATE LABEL"}
    verdict = {"decision": "uncertain", "findings": [], "limitations": "Fixture"}
    answers = [{"verdict": verdict}]
    if variant == "blue_tools":
        answers = [{"questions": ["Describe pleural findings."]},
                   {"observation": "Fixture", "limitations": "Synthetic"}, {"verdict": verdict}]
    lm = DummyLM(answers)
    with dspy.context(lm=lm):
        verify_case(case, variant, lm, lm, graph_store=store)
    messages = str([h["messages"] for h in lm.history])
    assert "left pleural" in messages and "uncertain" in messages
    assert "PRIVATE" not in messages and "DO NOT TRUST" not in messages
    if variant == "blue_tools":
        inspection = str(lm.history[1]["messages"])
        assert "report_claims" not in inspection and "Possible left pleural" not in inspection


def test_report_hash_changes_on_sentence_id_and_negation():
    a = [Sentence(id="s1", text="No pneumothorax.")]
    assert report_hash(a) != report_hash([Sentence(id="s1", text="Pneumothorax.")])
    assert report_hash(a) != report_hash([Sentence(id="s2", text=a[0].text)])


def test_whole_report_keeps_sections_and_cross_sentence_relations(tmp_path):
    import re
    sentences = [Sentence(id="s1", text="FINDINGS: Left opacity."),
                 Sentence(id="s2", text="FINDINGS: It persists."),
                 Sentence(id="s3", text="IMPRESSION: Possible pneumonia.")]
    tokenize = lambda text: re.findall(r"\w+|[^\w\s]", text)
    text, tokens, owners = document_input(sentences, tokenize)
    assert text.count("FINDINGS:") == 1 and text.count("IMPRESSION:") == 1
    assert "Left opacity.\nIt persists." in text
    a = {"text": " ".join(tokens), "entities": {
        "1": {"tokens": "opacity", "label": "OBS-DP", "start_ix": tokens.index("opacity"),
              "end_ix": tokens.index("opacity"), "relations": [["suggestive_of", "2"]]},
        "2": {"tokens": "pneumonia", "label": "OBS-U", "start_ix": tokens.index("pneumonia"),
              "end_ix": tokens.index("pneumonia"), "relations": []}}}
    rows, warnings = document_claims(a, owners, sentences)
    assert warnings == []
    assert rows[0]["claims"][0]["relations"][0]["target_sentence_ids"] == ["s3"]
    assert rows[2]["claims"][0]["status"] == "uncertain"
    graph = {"report_sha256": report_hash(sentences), "document_text": text,
             "raw_annotation": a, "token_sentence_ids": owners,
             "sentences": [{"sentence_id": s.id, "source_text": s.text} for s in sentences]}
    assert claims_for_graph(graph) == rows
    path = tmp_path / "whole.json"
    path.write_text(json.dumps({"format_version": 2, "extractor": {},
                               "graphs": {report_hash(sentences): graph}}))
    assert ReportGraphStore(path).for_sentences(sentences) == rows
    graph["document_text"] = "Different report"
    with pytest.raises(ValueError, match="Full-report"):
        claims_for_graph(graph)


def test_invalid_global_entity_spans_cannot_silently_shift_sentence_ids():
    s = [Sentence(id="s1", text="Opacity.")]
    a = {"text": "Opacity .", "entities": {"1": {"tokens": "Opacity", "label": "OBS-DP",
          "start_ix": 0, "end_ix": 5, "relations": []}}}
    with pytest.raises(ValueError, match="span"):
        document_claims(a, ["s1", "s1"], s)
    with pytest.raises(ValueError, match="mapping"):
        document_claims(a, ["private", "private"], s)
