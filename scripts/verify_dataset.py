"""Verify the upstream CSV export and image inventory without model calls."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def verify(directory: Path, inventory: Path) -> dict:
    expected = json.loads(inventory.read_text())["data_inventory"]
    for name, checksum in expected["source_csv_sha256"].items():
        path = directory / name
        if not path.is_file():
            raise ValueError(f"Missing dataset file: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
            raise ValueError(f"CSV checksum differs from the recorded export: {path}")

    images = list((directory / "images").rglob("*.png"))
    names = [path.name for path in images]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate image filenames in the extracted dataset")
    if len(images) != expected["image_files"]:
        raise ValueError(f"Expected {expected['image_files']} PNGs; found {len(images)}")
    with (directory / "indiana_projections.csv").open(encoding="utf-8-sig", newline="") as stream:
        referenced = {row["filename"].strip() for row in csv.DictReader(stream)}
    missing = referenced - set(names)
    if missing:
        raise ValueError(f"Missing {len(missing)} images referenced by the projections CSV")
    return {"csv_checksums": "match", "image_files": len(images),
            "referenced_images": len(referenced),
            "scope": "CSV bytes and image inventory; not a full image-byte verification"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/iu_xray"))
    parser.add_argument("--inventory", type=Path, default=Path("reports/benchmark_inventory.json"))
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.data, args.inventory), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Dataset verification failed: {error}\n")


if __name__ == "__main__":
    main()
