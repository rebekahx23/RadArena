# Data inventory

```text
data/
├── raw/iu_xray/
│   ├── indiana_reports.csv
│   ├── indiana_projections.csv
│   └── images/                         # 7,470 PNGs; downloaded, not committed
├── processed/
│   ├── studies.jsonl                   # 3,826 paired studies
│   ├── dataset_summary.json            # Import counts, exclusions, CSV hashes
│   ├── synthetic_benchmark_v2.jsonl    # Active frozen benchmark
│   ├── synthetic_benchmark_v2.metadata.json
│   ├── synthetic_benchmark_v1.*        # Earlier unused sampling version
│   ├── radgraph_smoke_sentence_v1.json
│   ├── radgraph_smoke_full_report_v2.json
│   └── human_review/                   # Blinded cases and separate organizer key
└── provenance/                         # Layout migration and failed NLM retrieval
```

The CSV/PNG export comes from [raddar's Chest X-rays (Indiana University)](https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university), based on the IU/OpenI collection
described by [Demner-Fushman et al. (2016)](https://doi.org/10.1093/jamia/ocv080). The export contains 3,851 report rows, 7,466 projection
rows, and 7,470 PNG files; 3,826 studies have usable report text and every referenced
image. The export version and original acquisition date are unknown. See
[dataset terms](LICENSE.md).

## Download and verify

Raw CSVs, PNGs, and ZIP downloads are gitignored; processed records and experiment
outputs are included. You need `curl`, `unzip`, Python 3, and
enough disk space for the archive plus about 13 GB of extracted images. Git LFS is not
required. Run these commands from the repository root.

```bash
bash scripts/download_dataset.sh
```

The script follows redirects and stops on HTTP errors. It reuses `data/downloads/iu_xray.zip` if
present, preserves existing files during extraction, and verifies the export. Failed
downloads remain in a `.part` file and are never extracted.

On November 6, 2026, curl retrieved a four-byte range with HTTP 206 and the ZIP
signature. Python requests returned HTTP 404 with its default user-agent and succeeded
with curl's user-agent. The response depended on the client header; the server-side
cause is unknown. The script uses curl. A full fresh download and extraction has not
been tested, though the existing local export passes verification. If Kaggle requires
authentication or the endpoint is unavailable, download through the [dataset page](https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university),
save the ZIP to `data/downloads/iu_xray.zip`, and rerun the script.

Equivalent manual steps:

```bash
mkdir -p data/downloads data/raw/iu_xray
curl --fail --location --retry 3 \
  --output data/downloads/iu_xray.zip \
  "https://www.kaggle.com/api/v1/datasets/download/raddar/chest-xrays-indiana-university"
# Continue only if curl succeeds and the file is a ZIP:
unzip -qn data/downloads/iu_xray.zip -d data/raw/iu_xray
python3 scripts/verify_dataset.py
```

For a dataset already on disk, run the verifier without downloading again. It checks
both CSVs against the recorded SHA-256 values, expects 7,470 PNGs, rejects duplicate
filenames, and checks that every projections-CSV filename exists. These checks verify
CSV bytes and the image inventory. Individual image contents have separate hashes in the
frozen benchmarks, which the evaluation checks before running.

## Prepare studies

```bash
uv run radarena prepare --format iu-csv \
  --reports data/raw/iu_xray/indiana_reports.csv \
  --projections data/raw/iu_xray/indiana_projections.csv \
  --images data/raw/iu_xray/images
```

Expect 3,826 retained studies and 25 excluded report rows. Both `images/*.png` and
`images/images_normalized/*.png` are supported. Other wrapper folders should be rearranged so the CSVs
are directly under `data/raw/iu_xray/`.

Preparation produces `processed/studies.jsonl` and `processed/studies.summary.json`. The included
`dataset_summary.json` is the original import summary retained under a clearer name. New
imports store checkout-relative paths when possible.

A CSV mismatch means the download differs from the recorded export. Keep the expected
hashes intact, record the new dataset version, and evaluate it separately. Changing the
hashes to silence the error would not reproduce the historical selection.

## Frozen artifacts

Processed files and run records retain their original bytes, including old absolute
paths. `radarena.paths.resolve_data_path` maps those IU paths to `data/raw/iu_xray/` when records are
loaded. Benchmark checksums are verified before paths are rebased in memory. Original
image names and image bytes are unchanged.

The v2 benchmark retains its original `midpoint-v2` seed because changing the seed
would change study selection. Its filename is now `synthetic_benchmark_v2.jsonl`. It contains
50/20/30 train/dev/test studies, each with an attack and unchanged control. Do not
overwrite a frozen benchmark to accommodate a new experiment.

The human-review organizer key is included for reproducibility. Withhold it from
reviewers until they record their initial blinded judgments. Its mechanical edit labels
have not been validated by clinicians.

`provenance/nlm-maintenance-response.html` records an unsuccessful historical download; it is not an
image/report archive and is not used by the importer.
