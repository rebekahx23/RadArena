# Research scripts

Run scripts from the repository root. Metric recomputation works without the dataset,
credentials, or saved historical artifacts. Other scripts need the inputs listed below.

## Dataset setup (no model calls)

- `bash scripts/download_dataset.sh`: download with curl, extract without replacing
  existing files, then verify. The curl endpoint and ZIP signature were checked;
  a full fresh download remains unverified. The manual Kaggle fallback is in
  `data/README.md`.
- `python3 scripts/verify_dataset.py`: check an existing dataset's CSV hashes,
  PNG count, duplicate filenames, and projection-image coverage.

## Public result reproduction

```bash
python3 scripts/reproduce_results.py
```

The script uses only the Python standard library and makes no model calls. Its
`--from-run` option re-exports text-free metric inputs from the included
historical records. `docs/REPRODUCIBILITY.md` explains how this differs from running new
inference.

## Local analysis and exports (no model calls)

| Script | Purpose |
| --- | --- |
| `analyze_open_online.py` | Summarize the historical online experiment and export private walkthroughs |
| `analyze_ten_study_batch.py` | Analyze the historical Red/Blue/reviewer batch |
| `compare_radgraph_runs.py` | Compare saved graph/no-graph evaluation runs |
| `summarize_indication_pilot.py` | Summarize the saved indication ablation |
| `build_run_walkthrough.py` | Render a saved baseline run as a Markdown walkthrough |
| `build_learning_walkthrough.py` | Export the earlier learning pilot's walkthrough |

These scripts read the corresponding historical records. Some rewrite derived summaries
or create walkthroughs with source report text under `runs/`. Dataset
attribution and terms still apply to their output.

## Experiment execution (paid inference)

| Script | Purpose and dependencies |
| --- | --- |
| `run_open_online.py` | Current gated online runner; requires dataset, private starting memories, and calibration records |
| `run_ten_study_batch.py` | Configurable ten-study batch using included studies and learned memories |
| `run_indication_pilot.py` | Historical fixed-case indication ablation |
| `compare_stronger_blue.py` | Model/evidence-ledger comparison using saved attacks |
| `resume_evaluation.py` | Finish unattempted baseline episodes after verifying frozen inputs |
| `recover_batch_reviews.py` | One bounded recovery attempt for each specified historical failed review |

Execution scripts use your `.env` configuration and may spend provider
credits. Historical recovery requires its original artifacts and configuration. Resuming
an experiment with changed code or settings does not reproduce the original protocol.

`resume_evaluation.py` was formerly named `finish_unattempted.py`; `recover_batch_reviews.py` was
formerly `recover_batch_judges.py`. Only the script names changed; historical output
directories are preserved. All scripts have execution guards, so importing them starts
no runs and writes no artifacts.
