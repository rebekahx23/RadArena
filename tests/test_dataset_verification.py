"""Check provenance and incomplete extraction failures without network access."""

import hashlib
import json
import runpy
from pathlib import Path

import pytest


verify = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/verify_dataset.py"))["verify"]


@pytest.fixture
def dataset(tmp_path):
    directory = tmp_path / "dataset"
    images = directory / "images/images_normalized"
    images.mkdir(parents=True)
    (images / "example.png").write_bytes(b"synthetic image fixture")
    reports = directory / "indiana_reports.csv"
    reports.write_text("uid,findings,impression\n1,Clear lungs.,No acute findings.\n")
    projections = directory / "indiana_projections.csv"
    projections.write_text("uid,filename,projection\n1,example.png,Frontal\n")
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"data_inventory": {
        "image_files": 1,
        "source_csv_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in [reports, projections]},
    }}))
    return directory, inventory


def test_valid_nested_export_passes(dataset):
    result = verify(*dataset)
    assert result["csv_checksums"] == "match"
    assert result["image_files"] == result["referenced_images"] == 1


def test_changed_export_is_rejected(dataset):
    directory, inventory = dataset
    with (directory / "indiana_reports.csv").open("a") as stream:
        stream.write("2,Different export.,Changed.\n")
    with pytest.raises(ValueError, match="checksum differs"):
        verify(directory, inventory)


def test_incomplete_extraction_is_rejected(dataset):
    directory, inventory = dataset
    next((directory / "images").rglob("*.png")).unlink()
    with pytest.raises(ValueError, match="Expected 1 PNGs; found 0"):
        verify(directory, inventory)


def test_duplicate_image_names_are_rejected(dataset):
    directory, inventory = dataset
    (directory / "images/example.png").write_bytes(b"duplicate fixture")
    with pytest.raises(ValueError, match="Duplicate image filenames"):
        verify(directory, inventory)


def test_correct_count_with_wrong_image_is_rejected(dataset):
    directory, inventory = dataset
    image = next((directory / "images").rglob("*.png"))
    image.rename(image.with_name("wrong.png"))
    with pytest.raises(ValueError, match="Missing 1 images referenced"):
        verify(directory, inventory)
