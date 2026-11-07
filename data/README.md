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

The raw CSV/PNG export is from
[raddar's Chest X-rays (Indiana University)](https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university),
based on the IU/OpenI collection described by
[Demner-Fushman et al. (2016)](https://doi.org/10.1093/jamia/ocv080).
The export contains 3,851 report rows, 7,466 projection rows, and 7,470 PNG files;
3,826 studies have usable report text and all referenced images. Export version
and original acquisition date were not recorded. See [dataset terms](LICENSE.md).

## Download and verify

Raw CSVs, PNGs, and ZIP downloads are gitignored. Processed records and experiment
outputs are included. No Git LFS installation is required. Use `curl`, `unzip`,
Python 3, and enough free disk space for the archive plus about 13 GB of extracted
images. Commands below run from the repository root.

```bash
bash scripts/download_dataset.sh
```

The script follows redirects, fails on HTTP errors, extracts without overwriting
existing files, and verifies the downloaded export. It reuses an existing
`data/downloads/iu_xray.zip`. An unsuccessful download stays in a `.part` file
and is not extracted.

**Verification limit:** on November 6, 2026, the actual curl client retrieved a
four-byte range with HTTP 206 and the ZIP signature. Python requests using its
default user-agent returned HTTP 404, while the same request with a curl
user-agent succeeded. This establishes a client-header-dependent response in the
tested environment, not its underlying server-side cause. The script uses curl.
A complete fresh download/extraction has not been tested. The existing local
export passes the verifier. If Kaggle requires authentication or the endpoint is unavailable, download
through the [dataset page](https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university),
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

For a dataset already on disk, skip downloading and run the verifier. It checks
both CSVs against the recorded SHA-256 values, expects 7,470 PNGs, rejects duplicate
filenames, and checks that every projections-CSV filename exists. These checks
cover CSV bytes and image inventory, not all image contents. Frozen benchmarks
have separate per-image content hashes checked before evaluation.

## Prepare studies

```bash
uv run radarena prepare --format iu-csv \
  --reports data/raw/iu_xray/indiana_reports.csv \
  --projections data/raw/iu_xray/indiana_projections.csv \
  --images data/raw/iu_xray/images
```

Expected: 3,826 retained studies and 25 excluded report rows. Both
`images/*.png` and `images/images_normalized/*.png` are supported. Other wrapper
folders should be rearranged so the CSVs are directly under `data/raw/iu_xray/`.

Preparation produces `processed/studies.jsonl` and `processed/studies.summary.json`.
The included `dataset_summary.json` is the original import summary retained under
a clearer name. New imports store checkout-relative paths when possible.

If verification reports a CSV mismatch, the downloaded export differs from the
recorded one. Do not change the expected hashes simply to suppress the error or
claim the historical selection is reproduced. Record the new version and evaluate
it as a separate dataset version.

## Frozen artifacts

Existing processed files and run records retain their exact bytes, including old
absolute paths. `radarena.paths.resolve_data_path` maps those known IU paths to
`data/raw/iu_xray/` when records are loaded. Benchmark checksums are verified before
paths are rebased in memory. Original image names and image bytes are unchanged.

The v2 benchmark retains its original `midpoint-v2` seed because changing the seed
would change study selection. Its filename is now `synthetic_benchmark_v2.jsonl`.
It contains 50/20/30 train/dev/test studies, each with an attack and unchanged control.
Do not overwrite a frozen benchmark to accommodate a new experiment.

The human-review organizer key is published for reproducibility, but should be
withheld from a reviewer until their initial blinded judgments are recorded.
Its mechanical edit labels are not clinician-validated truth.

`provenance/nlm-maintenance-response.html` records an unsuccessful historical
download; it is not an image/report archive and is not used by the importer.
