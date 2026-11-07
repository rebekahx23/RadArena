"""Freeze a synthetic benchmark independently of the evaluated Blue variants.

The seed attacker is deliberately simple and requires clinical validity review.
It supplies an executable initial benchmark, not learned Red performance.
"""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from .agents import Edit, apply_edits
from .data import Study

FINDINGS = {
    "effusion": r"\beffusions?\b",
    "pneumothorax": r"\bpneumothorax\b",
    "opacity": r"\bopacit(?:y|ies)\b",
    "atelectasis": r"\batelectasis\b",
    "cardiomegaly": r"\bcardiomegaly\b",
    "edema": r"\bedema\b",
    "consolidation": r"\bconsolidation\b",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def seed_attacks(study: Study) -> dict:
    """Return conservative single-token/negation edits with exact edit provenance.

    Avoid findings mentioned in another sentence, mixed-side descriptions,
    negated laterality/severity claims, and explicit temporal descriptions.
    Eligibility is lexical, not an adjudicated medical label.
    """
    attacks = {}
    for sentence in study.sentences:
        text = re.sub(r"^(?:FINDINGS|IMPRESSION):\s*", "", sentence.text)
        other = " ".join(s.text for s in study.sentences if s.id != sentence.id)
        if re.search(r"\b(prior|previous|compared|interval|unchanged|stable)\b", text, re.I):
            continue
        concepts = [pattern for pattern in FINDINGS.values() if re.search(pattern, text, re.I)]
        if not concepts or any(re.search(pattern, other, re.I) for pattern in concepts):
            continue
        negative = re.fullmatch(r"No (pleural effusion|pneumothorax)(?: is (?:seen|identified))?\.?", text, re.I)
        if negative:
            replacement = re.sub(r"\bNo\s+", "", sentence.text, count=1, flags=re.I)
            attacks.setdefault("presence_absence", [Edit(sentence_id=sentence.id, replacement=replacement)])
        if re.search(r"\b(no|without|absent|negative)\b", text, re.I):
            continue
        # Exactly one side or severity term in the whole report avoids changing
        # multiple independent attributes in a single mechanical attack.
        report = " ".join(s.text for s in study.sentences)
        sides = re.findall(r"\b(left|right)\b", report, re.I)
        if len(sides) == 1 and re.search(r"\b(left|right)\b", text, re.I):
            old = sides[0]
            new = "right" if old.lower() == "left" else "left"
            if old[0].isupper():
                new = new.capitalize()
            replacement = re.sub(r"\b(left|right)\b", new, sentence.text, count=1, flags=re.I)
            attacks.setdefault("laterality", [Edit(sentence_id=sentence.id, replacement=replacement)])
        levels = re.findall(r"\b(mild|moderate|severe)\b", report, re.I)
        if len(levels) == 1 and re.search(r"\b(mild|moderate|severe)\b", text, re.I):
            new = "severe" if levels[0].lower() != "severe" else "mild"
            if levels[0][0].isupper():
                new = new.capitalize()
            replacement = re.sub(r"\b(mild|moderate|severe)\b", new, sentence.text, count=1, flags=re.I)
            attacks.setdefault("severity", [Edit(sentence_id=sentence.id, replacement=replacement)])
    return attacks


def build_benchmark(manifest: Path, output: Path, counts: dict, seed="midpoint-v1"):
    if output.exists() or output.with_suffix(".metadata.json").exists():
        raise ValueError("Benchmark already exists. Use a new output filename to create another version.")
    if set(counts) != {"train", "dev", "test"} or any(n < 1 for n in counts.values()):
        raise ValueError("Specify positive train/dev/test study counts.")
    studies = [Study.model_validate_json(s) for s in manifest.read_text().splitlines() if s.strip()]
    studies.sort(key=lambda s: digest([seed, s.study_id]))
    cases = []
    selected_counts = Counter()
    category_counts = {split: Counter() for split in counts}
    seen_ids, seen_reports, seen_images = set(), set(), set()
    excluded = Counter()
    options_by_id = {s.study_id: seed_attacks(s) for s in studies}
    if len(options_by_id) != len(studies):
        raise ValueError("Duplicate source study IDs")
    excluded["no_eligible_seed_attack_in_manifest"] = sum(not o for o in options_by_id.values())

    def select(study, error_type):
        text_hash = digest(" ".join(s.text.lower() for s in study.sentences).split())
        if study.study_id in seen_ids or text_hash in seen_reports:
            excluded["duplicate_id_or_report"] += 1
            return False
        if not study.image_paths:
            excluded["unpaired"] += 1
            return False
        image_hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in study.image_paths]
        if set(image_hashes) & seen_images:
            excluded["duplicate_image_bytes"] += 1
            return False
        edits = options_by_id[study.study_id][error_type]
        changed = apply_edits(study.sentences, edits)
        seen_ids.add(study.study_id)
        seen_reports.add(text_hash)
        seen_images.update(image_hashes)
        selected_counts[study.split] += 1
        category_counts[study.split][error_type] += 1
        for variant, candidate in [("control", study.sentences), ("corrupted", changed)]:
            cases.append({
                "case_id": digest([seed, study.study_id, variant])[:24],
                "study_id": study.study_id, "split": study.split,
                "image_paths": study.image_paths, "image_sha256": image_hashes,
                "candidate": [s.model_dump() for s in candidate],
                "source": [s.model_dump() for s in study.sentences],
                "private_label": {"has_error": variant == "corrupted",
                    "changed_sentence_ids": [e.sentence_id for e in edits] if variant == "corrupted" else [],
                    "error_type": error_type if variant == "corrupted" else None,
                    "edits": [e.model_dump() for e in edits] if variant == "corrupted" else [],
                    "image_adjudication": "pending", "attacker": "lexical_seed_v1"},
            })
        return True

    # Select scarce categories first, then distribute remaining quota across the
    # remaining categories. This avoids filling a split with abundant negations.
    for split, target in counts.items():
        pool = [s for s in studies if s.split == split]
        kinds = sorted(["presence_absence", "laterality", "severity"],
                       key=lambda k: (sum(k in options_by_id[s.study_id] for s in pool), k))
        for i, kind in enumerate(kinds):
            desired = (target - selected_counts[split]) // (len(kinds)-i)
            for study in pool:
                if category_counts[split][kind] >= desired:
                    break
                if study.study_id not in seen_ids and kind in options_by_id[study.study_id]:
                    select(study, kind)
    if any(selected_counts[s] != n for s, n in counts.items()):
        raise ValueError(f"Insufficient eligible studies: selected {dict(selected_counts)}, requested {counts}")
    cases.sort(key=lambda c: digest([seed, c["case_id"]]))
    content = "".join(json.dumps(c, sort_keys=True) + "\n" for c in cases)
    metadata = {
        "seed": seed, "attacker": "lexical_seed_v1", "study_counts": dict(selected_counts),
        "sampler": "scarcity-first error-category strata v2",
        "candidate_counts": dict(Counter(c["split"] for c in cases)),
        "attack_counts": {s: dict(c) for s, c in category_counts.items()},
        "selection_exclusions": dict(excluded),
        "eligibility_counts_before_sampling": {split: dict(Counter(
            k for s in studies if s.split == split for k in options_by_id[s.study_id])) for split in counts},
        "benchmark_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "source_url": "https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university",
        "scope": "source-report-relative synthetic edits; clinical validity unreviewed",
        "grouping": "study; exact selected report and image byte duplicates excluded; patient identity unverified",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content)
    output.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def read_benchmark(path: Path):
    from .paths import resolve_data_path

    metadata = json.loads(path.with_suffix(".metadata.json").read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["benchmark_sha256"]:
        raise ValueError("Benchmark changed after freezing; checksum mismatch.")
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate case IDs in benchmark")
    for case in cases:
        case["image_paths"] = [str(resolve_data_path(p)) for p in case["image_paths"]]
    return cases, metadata
