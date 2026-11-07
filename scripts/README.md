# Research scripts

Run scripts from the repository root. Only metric recomputation is guaranteed to
work without the dataset, credentials, or saved historical artifacts.

## Dataset setup — no model calls

- `bash scripts/download_dataset.sh`: download with curl, extract without replacing
  existing files, then verify. The curl endpoint/ZIP signature was checked, but a
  full fresh download remains unverified; see the
  manual Kaggle fallback in `data/README.md`.
- `python3 scripts/verify_dataset.py`: check an existing dataset's CSV hashes,
  PNG count, duplicate filenames, and projection-image coverage.

## Public result reproduction

```bash
python3 scripts/reproduce_results.py
```

This uses only the Python standard library and makes no model calls. With the included
historical records, its `--from-run` option re-exports the text-free metric inputs.
See `docs/REPRODUCIBILITY.md` for the exact distinction between recomputation and
new inference.

## Local analysis and exports — no model calls

| Script | Purpose |
| --- | --- |
| `analyze_open_online.py` | Summarize the historical online experiment and export private walkthroughs |
| `analyze_ten_study_batch.py` | Analyze the historical Red/Blue/reviewer batch |
| `compare_radgraph_runs.py` | Compare saved graph/no-graph evaluation runs |
| `summarize_indication_pilot.py` | Summarize the saved indication ablation |
| `build_run_walkthrough.py` | Render a saved baseline run as a Markdown walkthrough |
| `build_learning_walkthrough.py` | Export the earlier learning pilot's walkthrough |

These scripts require their corresponding included historical records. Some rewrite derived
summaries or create walkthroughs containing source report text under `runs/`.
Their dataset-derived output retains the source attribution and applicable terms.

## Experiment execution — paid inference

| Script | Purpose and dependencies |
| --- | --- |
| `run_open_online.py` | Current gated online runner; requires dataset, private starting memories, and calibration records |
| `run_ten_study_batch.py` | Configurable ten-study batch using included studies and learned memories |
| `run_indication_pilot.py` | Historical fixed-case indication ablation |
| `compare_stronger_blue.py` | Model/evidence-ledger comparison using saved attacks |
| `resume_evaluation.py` | Finish unattempted baseline episodes after verifying frozen inputs |
| `recover_batch_reviews.py` | One bounded recovery attempt for each specified historical failed review |

Execution scripts require your own `.env` configuration and may spend provider
credits. Historical recovery is not a generic fresh-clone example. Do not resume
an experiment with changed implementation/configuration and call it replication.

`resume_evaluation.py` was formerly named `finish_unattempted.py`;
`recover_batch_reviews.py` was formerly `recover_batch_judges.py`. Only the script
names changed; historical output directories are preserved. All scripts have an
explicit execution guard so importing them does not start a run or write artifacts.
