# Evaluation validation and trace guide

The [first live pilot](PILOT_FINDINGS.md) is complete. It exposed false
alarms and evidence-handling failures; it did not establish that Blue improves on
direct image verification. Use the case walkthrough before expanding the run grid.

The baseline evaluation checks whether focused image inspections help Blue locate
report errors. Strategy-memory learning and RadGraph have separate experiments;
see [the learning pilot](LEARNING_PILOT.md), [online experiment](OPEN_ONLINE_20.md),
and [RadGraph ablation](RADGRAPH_ABLATION_2026-11-04.md). These pilots do not
establish clinical accuracy or general improvement.

## Required evidence

1. **A real, traceable execution.** Show an unchanged report and an edited report,
   the available X-rays, Blue's selected references and image questions, image-tool
   observations, and its final sentence-level decision. Include a failure example.
   A model-generated Red attack should be reviewed for validity before using it as
   a convincing demonstration; the deterministic seed benchmark is a separate test.
2. **A fixed comparison.** Compare text-only, direct image verification, and Blue
   on exactly the same paired controls and corruptions. Use one fixed model first.
   Keep all variants of a study in the same split. Report the larger call budget
   of Blue alongside its quality, rather than claiming a compute-matched effect.
3. **Trustworthy task labels.** Verify that edits change the intended attribute,
   preserve unrelated claims, and are contradicted by the available images. Review
   a category-balanced subset with a qualified reader where possible. Record invalid
   and ambiguous attacks separately; a source report is not an image-adjudicated label.
   Audit text-only success for lexical, anatomical, or internal-consistency shortcuts.
4. **Useful denominators and errors.** Report detection and localization F1,
   control false alarms, category recall, uncertainty, completion, calls, latency,
   and provider cost. Keep study-level paired confidence intervals exploratory.
   Categorize misses into visual-recognition errors, bad question selection,
   evidence-to-verdict errors, attack ambiguity, and report-only shortcuts.
5. **One isolated intervention if time permits.** Compare Blue with and without
   the medical handbook on a fixed development subset, holding other settings fixed.
   This tests reference usefulness; it does not test learning. Full/no-medical is
   a useful initial comparison before expanding to four ablations or multiple models.

## Staged runs within the $10 project budget

- First, six candidate reports from three development studies, one study per error
  category, with all three verifier methods. This is a smoke test, not an estimate
  of general performance. Selection is frozen before completions in the run plan.
- After inspecting traces and fixing runtime issues, expand to the 20 development
  studies (40 candidates) to select settings and examine category failures.
- Freeze settings and reference hashes, then evaluate once on the 30 held-out test
  studies (60 candidates), budget permitting. Do not tune on these results. Treat the
  set as a small synthetic pilot and disclose unverified patient independence.
- Add the handbook comparison only after the basic execution and scoring work.
  Log every run and maintain a project-wide total; a per-run guard is not a global
  $10 allowance. Prioritize fixed comparisons before expanding the model grid.

Useful validation means an executable prototype, interpretable comparisons, and
an explicit analysis of the limitations. Null results remain informative.
The proposed positive result is better localization at an acceptable false-alarm
and cost tradeoff; the experiment must also be capable of finding no improvement.

## Local traces and spending controls

`evaluate` and `demo` now use an audited, sequential pilot by default. The
default local allowance is $0.50 and at most 80 LM calls. The runtime disables
automatic LM retries and requests OpenRouter provider price ceilings: $0.50/M input,
$1/M output, and no separate per-image or per-request fee. Each call must fit a
conservative reserve derived from the verified 262,144-token model context and the
output cap before it starts. Gemma 3 27B is also supported, with its verified
131,072-token bound and ceilings of $0.10/M input and $0.20/M output (no separate
image/request fee). Known costs release the unused reserve; failed,
interrupted, or unknown-cost requests keep it, including after a restart.

The guard currently supports `qwen/qwen3-vl-8b-instruct` and
`google/gemma-3-27b-it`, one completion, and at most 2,048 output tokens.
Other models require explicitly verified bounds before
using this pilot path. It excludes unrelated account activity and credit-purchase
fees. The provider's usage ledger remains authoritative. The key's account settings
are not modified. Provider routing and model revisions are not pinned.

```bash
RADARENA_TEXT_MODEL=google/gemma-3-27b-it \
RADARENA_VISION_MODEL=google/gemma-3-27b-it \
uv run radarena evaluate --split dev --study-ids 1094 1106 2036 \
  --variants text_only direct_vlm blue_tools \
  --knowledge-file knowledge/reporting_v1.json --max-cost 0.10 --max-calls 60 \
  --output runs/my-dev-smoke
```

The output directory contains:

| Artifact | What to inspect |
| --- | --- |
| `pilot_plan.json` | Predeclared smoke-test selection and source hashes, when provided by the run organizer |
| `metadata.json`, `cases.jsonl` | Model/reference hashes, exact reports, local image paths, researcher-only labels |
| `audit/trace.md` | Ordered prompts, explicit model responses, context, usage, and failures |
| `audit/calls.jsonl` | Same call events in machine-readable form |
| `audit/budget.json` | Requests started, cost accounting, conservative reserve policy |
| `predictions.jsonl` | Verdicts, tool observations, selected reference chapters, scoring labels |
| `results.md`, `summary.json`, `failure_cases.jsonl` | Metrics and failure categories after a completed run or `summarize` |

The trace is a **researcher-only** artifact and is never fed to either agent as a
shared memory. Red and Blue get independently constructed inputs. Reference selection,
questions, observations, concise evidence, limitations, and outputs are inspectable;
they do not expose a model's hidden internal reasoning or prove its understanding.
Inline image bytes are replaced with hashes to keep logs readable; image paths and
content checksums remain in the case snapshot. API credentials are redacted. `runs/`
remains the local working directory; publish reviewed experiment exports with
credentials removed. `.env` stays out of Git.

For the demo, set the same Gemma environment variables and use `radarena demo
--study-id 113 --error-type laterality --knowledge-file knowledge/reporting_v1.json
--max-cost 0.02 --output runs/demo.json`; ordered calls appear in `runs/demo.audit/`.
That is a model-generated attack, unlike the frozen lexical tests. The completed
core pilot uses the fixed pack because the dynamic handbook selector failed its
path/budget checks; reliable handbook selection remains separate work.
