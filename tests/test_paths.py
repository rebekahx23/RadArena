"""Dataset relocation must preserve frozen records and image identity."""

import hashlib
import json
from pathlib import Path

from radarena.benchmark import read_benchmark
from radarena.data import Study, load_iu_csv
from radarena.paths import portable_data_path, resolve_data_path


def image_file(tmp_path):
    path = tmp_path / "data/raw/iu_xray/images/example.png"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"unchanged image fixture")
    return path


def test_historical_absolute_paths_resolve_in_a_different_checkout(tmp_path, monkeypatch):
    local = image_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    historical = "/other/computer/project/data/archive (1)/images/images_normalized/example.png"

    resolved = resolve_data_path(historical)

    assert resolved == Path("data/raw/iu_xray/images/example.png")
    assert resolved.read_bytes() == local.read_bytes()
    assert resolve_data_path("/different/root/data/raw/iu_xray/images/example.png") == resolved


def test_missing_and_unrelated_paths_are_not_guessed(tmp_path, monkeypatch):
    image_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    for original in [
        "/unrelated/example.png",
        "data/archive (1)/images/images_normalized/missing.png",
        "data/archive (1)/images/images_normalized/../../images/example.png",
    ]:
        assert resolve_data_path(original) == Path(original)


def test_historical_paths_support_the_nested_upstream_zip_layout(tmp_path, monkeypatch):
    image = tmp_path / "data/raw/iu_xray/images/images_normalized/example.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"original fixture")
    monkeypatch.chdir(tmp_path)

    historical = "/old/root/data/archive (1)/images/images_normalized/example.png"

    assert resolve_data_path(historical).resolve() == image


def test_frozen_benchmark_rebases_in_memory_without_changing_bytes(tmp_path, monkeypatch):
    image_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    historical = "/old/root/data/archive (1)/images/images_normalized/example.png"
    benchmark = tmp_path / "benchmark.jsonl"
    original = (json.dumps({"case_id": "case-1", "image_paths": [historical]}) + "\n").encode()
    benchmark.write_bytes(original)
    checksum = hashlib.sha256(original).hexdigest()
    benchmark.with_suffix(".metadata.json").write_text(json.dumps({"benchmark_sha256": checksum}))

    cases, metadata = read_benchmark(benchmark)

    assert Path(cases[0]["image_paths"][0]).is_file()
    assert benchmark.read_bytes() == original
    assert metadata["benchmark_sha256"] == checksum


def test_study_load_resolves_images_without_changing_record(tmp_path, monkeypatch):
    image_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    raw = {"study_id": "1", "split": "train", "image_ids": ["example.png"],
           "image_paths": ["/old/root/data/archive (1)/images/images_normalized/example.png"],
           "sentences": [{"id": "s1", "text": "Synthetic fixture."}]}

    study = Study.model_validate(raw)

    assert Path(study.image_paths[0]).is_file()
    assert raw["image_paths"][0].startswith("/old/root/")


def test_new_import_uses_checkout_relative_paths(tmp_path, monkeypatch):
    image = image_file(tmp_path)
    monkeypatch.chdir(tmp_path)
    raw = image.parent.parent
    reports = raw / "indiana_reports.csv"
    reports.write_text("uid,findings,impression\n1,Clear lungs.,No acute findings.\n")
    projections = raw / "indiana_projections.csv"
    projections.write_text("uid,filename,projection\n1,example.png,Frontal\n")

    studies, _ = load_iu_csv(reports, projections, image.parent)

    assert studies[0].image_paths == ["data/raw/iu_xray/images/example.png"]
    assert studies[0].source_csv == "data/raw/iu_xray/indiana_reports.csv"
    assert portable_data_path(tmp_path.parent / "external.png") == str(tmp_path.parent / "external.png")
