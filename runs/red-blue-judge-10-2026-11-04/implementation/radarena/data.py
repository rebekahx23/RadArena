"""IU/OpenI XML ingestion; originals remain separate from public candidates."""

import csv
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Sentence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    text: str


class Study(BaseModel):
    study_id: str
    split: str
    image_ids: list[str]
    image_paths: list[str]
    sentences: list[Sentence]
    image_views: list[str] = Field(default_factory=list)
    source_xml: str | None = None
    source_csv: str | None = None


def split_for(study_id: str, seed: str = "radarena-v1") -> str:
    # Assign originals and every derived variant using the source study ID.
    bucket = int(hashlib.sha256(f"{seed}:{study_id}".encode()).hexdigest(), 16) % 100
    return "train" if bucket < 50 else "dev" if bucket < 70 else "test"


def load_iu(reports: Path, images: Path | None = None) -> tuple[list[Study], dict]:
    files = sorted(reports.rglob("*.xml"))
    if not files:
        raise ValueError(f"No XML reports found under {reports}")
    image_index = {}
    if images is not None:
        for path in images.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                if path.stem in image_index:
                    raise ValueError(f"Ambiguous duplicate image stem: {path.stem}")
                image_index[path.stem] = str(path.resolve())
    studies, seen = [], set()
    skipped = {"missing_text_or_image_ids": 0, "missing_image_files": 0}
    for path in files:
        root = ET.parse(path).getroot()
        sections = []
        for node in root.findall(".//AbstractText"):
            label = (node.get("Label") or "").upper()
            text = " ".join(" ".join(node.itertext()).split())
            if label in {"FINDINGS", "IMPRESSION"} and text:
                sections.extend(f"{label}: {s}" for s in re.split(r"(?<=[.!?])\s+", text))
        image_ids = list(dict.fromkeys(
            node.get("id") for node in root.findall(".//parentImage") if node.get("id")
        ))
        if not sections or not image_ids:
            skipped["missing_text_or_image_ids"] += 1
            continue
        if images is not None and any(image_id not in image_index for image_id in image_ids):
            skipped["missing_image_files"] += 1
            continue
        uid = root.find("uId")
        study_id = uid.get("id") if uid is not None else path.stem
        study_id = study_id or path.stem
        if study_id in seen:
            raise ValueError(f"Duplicate study ID: {study_id}")
        seen.add(study_id)
        studies.append(Study(
            study_id=study_id, split=split_for(study_id), image_ids=image_ids,
            image_paths=[image_index[i] for i in image_ids] if images is not None else [],
            sentences=[Sentence(id=f"s{i+1}", text=s) for i, s in enumerate(sections)],
            source_xml=str(path.resolve()),
        ))
    return studies, {"xml_files": len(files), "eligible": len(studies), "skipped": skipped,
                     "paired_images_checked": images is not None}


def load_iu_csv(reports: Path, projections: Path, images: Path) -> tuple[list[Study], dict]:
    """Join the common Indiana reports/projections CSV export by uid and filename.

    MeSH, Problems, indication, and comparison are not fed into the verifier.
    Existing normalized PNGs are preserved without additional preprocessing.
    """
    with reports.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"uid", "findings", "impression"} <= set(reader.fieldnames or []):
            raise ValueError("Reports CSV needs uid, findings, and impression columns.")
        report_rows = list(reader)
    with projections.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not {"uid", "filename", "projection"} <= set(reader.fieldnames or []):
            raise ValueError("Projections CSV needs uid, filename, and projection columns.")
        projection_rows = list(reader)
    index = {}
    for path in images.rglob("*.png"):
        if path.name in index:
            raise ValueError(f"Ambiguous duplicate image filename: {path.name}")
        index[path.name] = str(path.resolve())
    grouped = {}
    for row in projection_rows:
        grouped.setdefault(row["uid"].strip(), []).append(row)
    studies, seen = [], set()
    skipped = {"missing_text_or_image_ids": 0, "missing_image_files": 0}
    for row in report_rows:
        uid = row["uid"].strip()
        if not uid or uid in seen:
            raise ValueError(f"Missing or duplicate report uid: {uid!r}")
        seen.add(uid)
        sections = []
        for label in ["findings", "impression"]:
            text = " ".join((row.get(label) or "").split())
            if text and text.lower() != "nan":
                sections.extend(f"{label.upper()}: {s}" for s in re.split(r"(?<=[.!?])\s+", text))
        view_rows = grouped.get(uid, [])
        names = [v["filename"].strip() for v in view_rows]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate projection filename for uid {uid}")
        if not sections or not names:
            skipped["missing_text_or_image_ids"] += 1
            continue
        if any(name not in index for name in names):
            skipped["missing_image_files"] += 1
            continue
        studies.append(Study(
            study_id=uid, split=split_for(uid), image_ids=names,
            image_paths=[index[name] for name in names],
            image_views=[v["projection"].strip() for v in view_rows],
            sentences=[Sentence(id=f"s{i+1}", text=s) for i, s in enumerate(sections)],
            source_csv=str(reports.resolve()),
        ))
    return studies, {
        "format": "iu-csv", "report_rows": len(report_rows),
        "projection_rows": len(projection_rows), "image_files": len(index),
        "eligible": len(studies), "skipped": skipped, "paired_images_checked": True,
        "projection_uids_without_report": len(set(grouped) - seen),
        "source_csv_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [reports, projections]},
        "source_download_url": "https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university",
        "source_provenance": "Download page supplied by user; upstream IU/OpenI collection",
    }
