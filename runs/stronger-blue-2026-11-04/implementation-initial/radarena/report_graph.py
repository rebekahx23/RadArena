"""Optional local RadGraph extraction. Report claims are never image evidence."""

import hashlib
import importlib.metadata
import json
import re
from pathlib import Path

from .data import Sentence

STATUS = {
    "OBS-DP": "present", "OBS-DA": "absent", "OBS-U": "uncertain",
    "Observation::definitely present": "present",
    "Observation::definitely absent": "absent", "Observation::uncertain": "uncertain",
}


def report_hash(sentences):
    rows = [Sentence.model_validate(s).model_dump() for s in sentences]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def normalize_annotation(annotation):
    """Retain all raw labels/edges; derive compact observation claims without guessing."""
    entities = annotation.get("entities", {})
    for entity in entities.values():
        for edge in entity.get("relations", []):
            if len(edge) != 2 or str(edge[1]) not in entities:
                raise ValueError("RadGraph returned an invalid relation target")
    def modifiers(eid, seen=None):
        seen = set() if seen is None else set(seen)
        if eid in seen:
            return []
        seen.add(eid)
        result = []
        for other_id, other in entities.items():
            if ["modify", eid] in other.get("relations", []):
                result += [(other.get("start_ix", 0), other["tokens"])] + modifiers(other_id, seen)
        return result
    def phrase(eid):
        e = entities[eid]
        parts = modifiers(eid) + [(e.get("start_ix", 0), e["tokens"])]
        return " ".join(t for _, t in sorted(set(parts)))
    claims = []
    for eid, entity in entities.items():
        label = entity["label"]
        if label not in STATUS and not label.startswith(("OBS", "Observation")):
            continue
        claims.append({
            "entity_id": eid, "observation": entity["tokens"],
            "qualified_observation": phrase(eid), "status": STATUS.get(label, "unknown"),
            "anatomy": [phrase(str(target)) for relation, target in entity.get("relations", []) if relation == "located_at"],
            "modifiers": [t for _, t in sorted(set(modifiers(eid)))],
            "relations": [{"type": relation, "target_entity_id": str(target),
                           "target_text": phrase(str(target))}
                          for relation, target in entity.get("relations", [])],
        })
    return claims


def report_parts(sentences):
    """Reconstruct the complete ordered report, with each section heading once."""
    parts, section = [], None
    for sentence in sentences:
        match = re.match(r"^(FINDINGS|IMPRESSION):\s*(.*)$", sentence.text, re.DOTALL)
        if match:
            label, body = match.groups()
            if label != section:
                parts.append((label + ":", None))
                section = label
        else:
            body = sentence.text
        parts.append((body, sentence.id))
    return parts


def document_input(sentences, tokenize):
    parts = report_parts(sentences)
    text = "\n".join(part for part, _ in parts)
    tokens, owners = [], []
    for part, sid in parts:
        segment = tokenize(part)
        tokens.extend(segment)
        owners.extend([sid] * len(segment))
    if tokenize(text) != tokens:
        raise ValueError("Cannot align full-report tokenization to sentence IDs")
    return text, tokens, owners


def document_claims(annotation, owners, sentences):
    """Map global entity spans back to sentences while retaining cross-sentence edges."""
    tokens = annotation["text"].split()
    valid = {s.id for s in sentences}
    if len(tokens) != len(owners) or not set(owners) <= valid | {None}:
        raise ValueError("Invalid full-report token-to-sentence mapping")
    entity_sentences, warnings = {}, []
    for eid, entity in annotation.get("entities", {}).items():
        start, end = entity["start_ix"], entity["end_ix"]
        if not 0 <= start <= end < len(tokens):
            raise ValueError("Invalid RadGraph entity span")
        ids = list(dict.fromkeys(s for s in owners[start:end+1] if s is not None))
        entity_sentences[eid] = ids
        if len(ids) != 1:
            warnings.append({"entity_id": eid, "sentence_ids": ids,
                             "reason": "entity crosses sentence boundary or belongs to a heading"})
    claims = normalize_annotation(annotation)
    for claim in claims:
        claim["sentence_ids"] = entity_sentences[claim["entity_id"]]
        for relation in claim["relations"]:
            relation["target_sentence_ids"] = entity_sentences[relation["target_entity_id"]]
    rows = [{"sentence_id": s.id, "claims": [c for c in claims if s.id in c["sentence_ids"]]}
            for s in sentences]
    return rows, warnings


def claims_for_graph(graph):
    sentences = [Sentence(id=r["sentence_id"], text=r["source_text"]) for r in graph["sentences"]]
    if "raw_annotation" in graph:
        expected = "\n".join(part for part, _ in report_parts(sentences))
        if graph.get("document_text") != expected:
            raise ValueError("Full-report text does not match the original sentences")
        return document_claims(graph["raw_annotation"], graph["token_sentence_ids"], sentences)[0]
    # Historical sentence-level artifacts remain inspectable.
    return [{"sentence_id": r["sentence_id"], "claims": normalize_annotation(r["raw_annotation"])}
            for r in graph["sentences"]]


class RadGraphExtractor:
    def __init__(self, model_type="radgraph-xl", cache_dir=Path(".cache/radgraph")):
        if model_type not in {"radgraph", "radgraph-xl"}:
            raise ValueError("Choose radgraph or radgraph-xl")
        try:
            import torch
            from radgraph import RadGraph
        except ImportError as exc:
            raise RuntimeError("Install optional dependencies with: uv sync --extra radgraph") from exc
        torch.set_num_threads(4)
        self.model_type, self.cache_dir = model_type, Path(cache_dir)
        self.backend = RadGraph(model_type=model_type, cuda=-1,
                                model_cache_dir=str(self.cache_dir),
                                tokenizer_cache_dir=str(Path(".cache/huggingface")))
        model_dir = self.cache_dir / model_type
        files = {str(p.relative_to(model_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(model_dir.rglob("*")) if p.is_file()}
        self.metadata = {"tool": "RadGraph", "package_version": importlib.metadata.version("radgraph"),
                         "model_type": model_type, "device": "cpu", "model_files_sha256": files,
                         "scope": "whole-report extraction; global spans mapped to sentence IDs; cross-sentence edges retained",
                         "adapter_version": 2,
                         "evidence_type": "report text claims, not image observations"}
        self.fingerprint = hashlib.sha256(json.dumps(self.metadata, sort_keys=True).encode()).hexdigest()
        self.results_dir = self.cache_dir / "extractions" / self.fingerprint
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def extract(self, sentences):
        sentences = [Sentence.model_validate(s) for s in sentences]
        if len({s.id for s in sentences}) != len(sentences):
            raise ValueError("Sentence IDs must be unique")
        from radgraph.utils import preprocess_reports
        def tokenize(text):
            return preprocess_reports([text], self.model_type)[0]["sentences"][0]
        text, tokens, owners = document_input(sentences, tokenize)
        path = self.results_dir / (hashlib.sha256(text.encode()).hexdigest() + ".json")
        if path.exists():
            annotation = json.loads(path.read_text())
        else:
            import torch
            with torch.inference_mode():
                output = self.backend([text])  # Exactly one complete report, not one call per sentence.
            if set(output) != {"0"}:
                raise ValueError("Unexpected RadGraph output indices")
            annotation = output["0"]
            normalize_annotation(annotation)
            path.write_text(json.dumps(annotation, indent=2) + "\n")
        if annotation["text"].split() != tokens:
            raise ValueError("RadGraph tokenization changed; cannot safely map sentence IDs")
        rows, warnings = document_claims(annotation, owners, sentences)
        parsed = [dict(row, source_text=s.text) for row, s in zip(rows, sentences, strict=True)]
        return {"report_sha256": report_hash(sentences), "extractor_fingerprint": self.fingerprint,
                "document_text": text, "raw_annotation": annotation,
                "token_sentence_ids": owners, "alignment_warnings": warnings, "sentences": parsed}


class ReportGraphStore:
    """Lookup by exact candidate text; never expose the store or other report graphs."""
    def __init__(self, path):
        self.path = Path(path)
        self.sha256 = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.data = json.loads(self.path.read_text())
        if self.data.get("format_version") not in {1, 2}:
            raise ValueError("Unknown report graph format")

    def for_sentences(self, sentences):
        sentences = [Sentence.model_validate(s) for s in sentences]
        key = report_hash(sentences)
        graph = self.data["graphs"].get(key)
        if graph is None or graph.get("report_sha256") != key:
            raise ValueError("No RadGraph extraction for this exact candidate report")
        originals = [Sentence(id=r["sentence_id"], text=r["source_text"]) for r in graph["sentences"]]
        if report_hash(originals) != key:
            raise ValueError("Graph-to-report sentence mapping does not match")
        # Recompute compact claims from raw tool output, ignoring arbitrary extra fields.
        return claims_for_graph(graph)

    def metadata(self):
        return {"sha256": self.sha256, "extractor": self.data["extractor"],
                "scope": "exact candidate report only; no original/candidate difference"}
