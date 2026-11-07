# Reproducing the experiments

Run commands from the repository root. The prototype needs Python 3.12 or 3.13 and
`uv`, but no local GPU. Metric recomputation uses only the Python standard
library.

## Verification performed November 6, 2026

An isolated copy of the prospective public files excluded `.env`, raw
downloads, textbook PDFs, caches, and the existing virtual environment.
`uv sync --offline
--frozen --group dev` created a fresh Python 3.12 environment and installed the 74 locked
packages using the existing dependency cache. `radarena doctor` confirmed no configured
API key and zero network calls. All 155 offline tests passed, and `scripts/reproduce_results.py`
reproduced the saved experiment metrics. No model inference was performed. A full fresh
dataset download and new paid inference remain outside this verification.

## Verification performed November 5, 2026

A fresh temporary source copy contained the package, tests, lockfile, scripts, report
summaries, configuration, and reference handbook, but no `.env`, original
`.venv`, data, or historical run directories. `uv sync --frozen --group dev` installed 74
locked packages using Python 3.12.12. An offline-only attempt could not install one
uncached wheel; the ordinary network-enabled installation succeeded. `radarena doctor`
reported DSPy 3.4.0, no configured provider key, and zero network calls. All 98 tests
passed in the fresh environment. The standalone metric script reproduced the main
experiment's metrics from this copy using only Python's standard library. No paid
inference was performed. Dataset acquisition, live image inference, and full historical
replication have not been validated from a fresh clone.

## 1. Recompute the main experiment's metrics (no data, credentials, or model calls)

```bash
python3 scripts/reproduce_results.py
```

The script reads `reports/online_experiment_results.json`, containing text-free episode decisions, reviewer
validity labels, call-cost numbers, and hashes of the saved source artifacts. It
includes no reports, radiographs, prompts, model explanations, indication text, or API
keys. The script calculates the final-probe F1 values from those decisions.

Expected: 20 studies, 39 images, 20 controls, 40 accepted reviews, 15 consensus-valid
attacks (10 flagged, four missed, one invalid output), seven control flags, and three
memory updates per role. The final probe has three valid attacks flagged by both
memories, control flags 2/5 versus 1/5, and F1 0.750 versus 0.857142857. Audited calls
total 274, known reported costs $0.20620493, and unknown-cost reserves $0.3276928. F1 is
`2*TP/(2*TP+FP+FN)` on consensus-valid probe attacks plus all five reference controls.
This is saved-output arithmetic, not an independent rerun of model predictions or
clinical validation.

The earlier baseline and three-round pilot have separate summaries in `reports/baseline_smoke_results.json`
and `docs/LEARNING_PILOT.md`; they are different experiments, not additional rows of the
online probe.

## 2. Install and verify the prototype (no paid calls)

```bash
uv sync --frozen --group dev
uv run radarena doctor
uv run pytest
```

`doctor` reports key availability without calling a provider or displaying the
key. Tests use fixtures and scripted model outputs. To configure inference, copy
`.env.example` to `.env` only if `.env` does not already
exist, then set your own `OPENROUTER_API_KEY`. Credentials stay local and are not
distributed. Saved records are included; raw CSVs and images are downloaded separately
using `data/README.md`.

## 3. Prepare the dataset and run a small live example

Download the IU export using `bash scripts/download_dataset.sh`, or use the manual fallback in
`data/README.md`. A full fresh download has not been verified. The layout is
`data/raw/iu_xray/`: `indiana_reports.csv`, `indiana_projections.csv`, and `images/`. The
two CSV SHA-256 values are recorded in `reports/benchmark_inventory.json`; a different export may not
reproduce the same study inventory or selection. The original export version and
acquisition date are unknown. Upstream terms and attribution are recorded in
`data/LICENSE.md`.

```bash
uv run radarena prepare --format iu-csv \
  --reports 'data/raw/iu_xray/indiana_reports.csv' \
  --projections 'data/raw/iu_xray/indiana_projections.csv' \
  --images 'data/raw/iu_xray/images'
```

Preparation should retain 3,826 studies and exclude 25 rows. Use the included
`data/processed/synthetic_benchmark_v2.jsonl`: 50/20/30 train/dev/test studies, each with an attack and control
(200 candidates). Do not recreate this frozen file. For a deliberate new benchmark,
supply a new output name:

```bash
uv run radarena make-benchmark --output data/processed/synthetic_benchmark_local.jsonl
```

The builder refuses to overwrite an existing frozen benchmark. Included historical
manifests retain their original absolute paths. The current loader resolves known
dataset paths into this checkout without rewriting the records. New imports store
checkout-relative paths when possible.

After configuring your key, run one unchanged-control demonstration with paid calls. It
does not require learned memory:

```bash
RADARENA_TEXT_MODEL=google/gemini-2.5-flash \
RADARENA_VISION_MODEL=google/gemini-2.5-flash \
uv run radarena demo --control --study-id 113 \
  --indications-csv 'data/raw/iu_xray/indiana_reports.csv' \
  --knowledge-file knowledge/reporting_v1.json \
  --output runs/reproduction-control.json --max-cost .50
uv run radarena viewer
```

Open http://127.0.0.1:8765 and select the new run. The viewer replays saved actions without
model calls. This demonstrates the current prototype; it does not reproduce the
historical online learning protocol. Provider responses/routing, model availability, and
latency can vary.

## 4. Audit the included historical outputs

The original `runs/open-online-20-2026-11-04/` directory is included:

```bash
python3 scripts/reproduce_results.py \
  --from-run runs/open-online-20-2026-11-04 \
  --output /tmp/online-experiment-check.json
uv run python scripts/analyze_open_online.py
```

The first command re-exports metric inputs and computes the main numbers directly from
saved episodes and cost ledgers. The second regenerates `analysis.json`,
`analysis.md`, and the full researcher walkthrough, without provider calls. Compare
the regenerated bundle with the committed one. The `source_file_sha256` values link the
metric inputs to the included source records. Compare these hashes before regenerating
any derived files.

The historical directory also contains selection/image hashes, exact role-private
memories, source snapshots, protocol amendments, stage checkpoints, and request audits.
These records are included; source CSVs and radiographs are downloaded separately. The
current viewer resolves historical absolute image paths against the new dataset layout.
Replaying records does not regenerate hosted model predictions.

## 5. Historical protocol versus the current learning runner

`scripts/run_open_online.py` does not reproduce the historical experiment's metrics. The current
runner uses `memory-policy-v1` and a new output directory; the completed historical run
used an earlier policy and three documented amendments. Changing only the output folder
does not recover the old protocol.

The historical execution depended on both v3 memories from `runs/learning-pilot-2026-11-04/`, its fixed
20-study selection, the exact dataset, the shared reporting pack, model configuration,
and the archived implementation versions. Current gated runs also need calibration
records named by `configs/memory_promotion_cases.json`, including saved source episode/judge artifacts. The
referenced historical records and starting memories are included. See `docs/MEMORY_PROMOTION.md`
before scheduling a new experiment. Resuming historical artifacts with changed code does
not reproduce the original execution.

An independent end-to-end replication requires reconstructing the historical
implementation/configuration and amendment schedule from the included snapshots and
records. The current gated runner cannot substitute for that reconstruction. Hosted
inference is stochastic and exact historical outputs are not guaranteed. The committed
bundle supports exact metric recomputation; new inference tests whether the observed
behavior repeats.

Historical artifact names such as `midpoint-v2` are frozen benchmark identifiers,
not document dependencies. They are preserved so seeds, hashes, and saved selections
continue to match the original experiments.
