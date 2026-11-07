# Experiment guide

Detailed commands and historical pilot context. Run commands from the repository
root. For the current project overview, see the [root README](../README.md).

Experimental chest X-ray report verification using **DSPy + OpenRouter + IU/OpenI**.

Start with the [experiment reproduction guide](REPRODUCIBILITY.md). It separates
offline recomputation of the reported numbers, a small current prototype run,
and the archived source artifacts used for historical experiment auditing.

Implemented: IU XML/CSV parsing and image matching, stable study splits, constrained Red edits,
Blue question planning and at most three image inspections, typed verdict validation,
frozen synthetic benchmarks, three baseline conditions, aggregate metrics, paired
study-bootstrap comparisons, failure exports, pending human-review templates, and local
episode traces and a local arena observer UI. Role-private strategy-memory adaptation
and two-model review have completed pilots, including a 20-study online run. A newer
memory-promotion policy is implemented but not yet evaluated live. GEPA optimization
and clinical adjudication remain pending. This is research software; model output is not
clinical ground truth.

Recompute the main online experiment results without data, API keys, or model calls:

```bash
python3 scripts/reproduce_results.py
```

## Install

Model choices and the user's **$10 total budget** are documented in
[docs/MODELS_AND_BUDGET.md](MODELS_AND_BUDGET.md) and
`configs/model_budget.json`. The initial lineup is Qwen3-VL 8B, Gemma 3 27B, and Gemini
2.5 Flash. Plan an $8 model-usage ceiling plus a $2 fees/contingency reserve. The planning
file does not enforce spending; configure a provider-side key limit before paid runs.

Install the locked environment with `uv`:

```bash
uv sync --frozen --group dev
# Only if you do not already have a local .env:
cp -n .env.example .env
```

Put your OpenRouter key in `.env`. The default is the image-capable
`qwen/qwen3-vl-8b-instruct` for both
roles; change `RADARENA_TEXT_MODEL` and `RADARENA_VISION_MODEL` independently.
Red and the image tool require image-capable models. These defaults are engineering
starting points, not validated radiology models. The gateway is hosted, so inference
does not require a local GPU.

```bash
uv run radarena doctor
uv run pytest
```

`doctor` reports whether a key is configured without displaying it or calling a model.
Tests use fixtures and scripted DSPy replies, make no paid calls, and do not measure
medical accuracy. Dependencies are constrained in `pyproject.toml` and the resolved
environment is captured in `uv.lock`. The project environment has been installed locally.

## Obtain the IU/OpenI data

IU is the Indiana University chest X-ray collection with paired source reports.
Original publication: https://doi.org/10.1093/jamia/ocv080

Historical NLM archive locations:

- Reports: https://openi.nlm.nih.gov/imgs/collections/NLMCXR_reports.tgz
- PNG images: https://openi.nlm.nih.gov/imgs/collections/NLMCXR_png.tgz

**Retrieval status, November 3, 2026:** a direct request to the reports URL returned
an NLM maintenance HTML page, not a gzip archive. Do not extract it or count it as
downloaded data. The URLs given earlier in planning are not currently a tested route.
Use the restored NLM download or a documented IU mirror after checking provenance,
contents, and terms. That download did not obtain data; the supplied local copy below
now provides paired studies.

The loader expects original-format XML records containing `AbstractText` with `Label`
attributes and `parentImage` identifiers, plus PNG/JPEG filenames matching those IDs.
The CSV export below has its own importer; other benchmark-annotation formats need
an additional importer.
Download CSVs and PNGs separately to `data/raw/iu_xray/` using [the dataset guide](../data/README.md).
The XML instructions below describe an alternative input format. Record the source/version and archive hashes when acquired.

### Local CSV dataset already available

A local export is available at `data/raw/iu_xray`, downloaded by the user from
[raddar's IU dataset on Kaggle](https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university).
The export's dataset version/download date remain unrecorded; source terms are
documented in `data/LICENSE.md`.
The data can stay in this folder; no move is necessary. It contains 3,851 report rows,
7,466 image-projection rows, and 7,470 PNG files. The CSV importer successfully retained
3,826 studies with report text and all referenced image files; 25 rows lacked report
text or image references. This does not mean all retained cases are clinically suitable
for a particular error family. A manifest and CSV hashes have been generated locally.

Reproduce that preparation with:

```bash
uv run radarena prepare --format iu-csv \
  --reports 'data/raw/iu_xray/indiana_reports.csv' \
  --projections 'data/raw/iu_xray/indiana_projections.csv' \
  --images 'data/raw/iu_xray/images'
```

This joins reports and images using UID and exact filenames, preserves view metadata,
and excludes MeSH/Problems labels from model inputs. It uses the existing normalized
images without additional resizing. After preparation, supply your own provider key
to run an episode. Development pilots and online learning have completed locally;
see [the validation guide](VALIDATION.md) and
[the online experiment](OPEN_ONLINE_20.md).

After obtaining and extracting the XML and image archives:

```bash
uv run radarena prepare \
  --reports data/raw/iu/reports \
  --images data/raw/iu/images
```

This searches recursively, preserves all referenced views, excludes records with missing
text or images, and writes `data/processed/studies.jsonl` plus a summary of exclusions. To
inspect XML without images, omit `--images`; the resulting unpaired manifest cannot run
the image demo. Sentence segmentation is deliberately simple and needs review for
abbreviations. Split assignment hashes the source study ID into approximately 50/20/30
train/dev/test groups. It does not independently verify patient identities or duplicates.
All variants must retain their original study's split.

## Run one live episode

### Observe runs in the arena

```bash
uv run radarena viewer
```

Open **http://127.0.0.1:8765**. The **Historical runs** tab is a read-only observer of demo and evaluation
traces under `runs/`. Select a run and study/condition to see real study images,
Red's source report and attack, Blue's candidate report and observations, and the exact
recorded request/response for each model call. The action tape supports replay, stepping,
and 1×/2×/4× playback; Space toggles replay and arrow keys step through requests.
Image controls offer zoom, brightness, contrast, inversion, and view selection.

Use **Judge review** to view a saved independent assessment next to the study image.
It separates attack validity, Blue performance, Red outcome, and confidence, and lets
you compare each judge explanation with Blue's actual flag and cited image observation.
Explicit tensions between those recorded statements are highlighted without rewriting
either output. The episode summary keeps code-based edit matching separate from model
opinions. Earlier judge responses stay on the action tape; the review panel shows the
accepted saved assessment. Failed and unfinished reviews have explicit empty states.

The usual demo sidecar is `runs/<name>.judge.json`; evaluation reviews live under
`runs/<evaluation>/judge/<case_id>.<variant>.json`. Additional independently saved reviews
can be placed in `runs/<name>.judges/*.json` or the evaluation's
`judge/<case_id>.<variant>.judges/*.json`, each with its own sibling `.audit` directory.
The reviewer selector appears when multiple reviews are available. Judge costs are
counted once in the run total and displayed separately from contestant costs.

The observer also discovers the open-ended online format (`stages/`, `episodes/`, and
per-stage `audit/` directories) and role-private learning pilots. Online attacks,
unchanged controls, final initial-memory probes, and memory updates are separate views.
Round, checkpoint, supplied indication, and the exact recorded role-private strategy
inputs appear under **Context & private memories**. Online reviewer explanations are
rendered in their recorded format; an overall review is not presented as a per-sentence
judgment. Open rewrites and omissions show report-level outcomes, without the older
injected-sentence localization score. Every audited request contributes once to run cost.

The experiment library refreshes automatically. **Refresh** reloads the current run;
**Watch new calls** also follows updates to the selected view while a runner is writing.

The header shows the entire run's accounted cost; team totals follow the selected
episode's replay position. Each request exposes tokens, duration, and recorded cost.
An asterisk marks unknown charges retained as conservative audit reserves. The tool
registry summarizes harness capabilities and their observed spend, including retries.
Replay makes no paid calls. **Watch new calls** polls traces every four seconds while
a separate CLI demo/evaluation writes them; this is file observation, not agent control.

This researcher view includes private source/attack information; highlighting never
changes agent inputs. Traces show explicit outputs, not hidden reasoning. Images for
standalone demos are resolved through the prepared IU manifest. Use `--runs`, `--manifest`,
or `--port` to override the defaults. The server binds only to `127.0.0.1`.

### Launch a demo in Live Arena

Open **Live Arena**, the separate tab beside Historical runs, or visit
**http://127.0.0.1:8765/#page=live**. Choose 1–10 studies, a $0.50–$3 spending cap,
and whether to include unchanged controls. You can supply role-private starting
memory rules and enable updates when controls are included. **Start live run** uses
the project's `OPENROUTER_API_KEY` and spends real provider credits.

Every launch creates a new `runs/live-<timestamp>-<id>/` directory and randomly samples
original training studies. Red generates candidate reports during the run; no prepared
attacks are loaded, no saved stages are resumed, and DSPy/LiteLLM response caching is
disabled. A model may still abstain; unchanged output is explicitly labelled no attack.
Source images/reports remain unchanged. Gemini 2.5 Flash runs the contestants. New live
runs use three separate judge calls: Gemma 3 27B, Gemini 2.5 Flash, and
`qwen/qwen3-vl-30b-a3b-instruct`. Gemma can use Qwen3-VL 8B as an availability backup.
One reviewer shares the contestant model family. Qwen 30B bounds were checked against
OpenRouter's model endpoints: up to 262,144 context tokens and routing caps of
$0.30/M input, $1/M output, with no additional image/request fees allowed by the filter.

The stage console updates every 1.5 seconds at request start/finish, with elapsed time,
accounted spend, actual report differences, tool inputs/outputs and current memories.
It does not stream hidden reasoning or individual response tokens. Disable **Follow
live** to inspect older actions while inference continues. **Stop after current request**
preserves the current request's final audit/cost and prevents the next request. Only one
live demo runs at a time. Reloading or changing tabs does not restart it.

Transport/rate-limit failures retry once with all attempts audited. If Gemma remains
unavailable, Live Arena automatically substitutes `qwen/qwen3-vl-8b-instruct`, also
with at most one retry. The first retry waits five seconds; a backup retry waits ten,
with a visible countdown and stop checks. The backup occupies Gemma's one judge slot;
Gemini remains the other reviewer. Backup model identity is shown in judge selection,
match votes and recorded metadata. Failed primary requests/reserves remain in the
same audited stage and count toward the unchanged spending cap. Disagreement, schema
errors and rejected reviews never trigger model substitution. If both primary and
backup are unavailable, that judge is recorded as failed and the other reviewer can
continue. This applies to newly launched live runs, not to historical failures.
Matching accepted reviews from the full configured crew
and a recorded control are required for memory feedback. Proposed lessons pass mechanical
checks and model rule review; this demo does **not** apply the research runner's measured
performance promotion gate. Memories may stay unchanged when evidence is insufficient.
Unknown/in-flight charges retain conservative reserves; spending guards can stop before
the cap to reserve a whole request. Completed, stopped and failed sessions remain inspectable.
Live-control POSTs accept only same-origin local JSON and bounded options; no client-supplied
commands, paths, credentials or model names are accepted.

The **Final match result** displays Red/Blue study wins, undecided studies, each judge's
votes and a plain-language reason. Red wins a validated attack that Blue misses; Blue
wins a validated attack it detects (partial correctness is labelled). Both accepted
judges must agree on validity and performance for older two-judge runs. New three-judge
runs use the versioned `majority_distinct_families_v1` rule: at least two reviewers must
agree on the same validity/performance pair, and the agreeing reviewers must include
two model families. Qwen 8B and Qwen 30B cannot form a majority alone. Initial votes
remain independent and all dissent is shown. This is a panel aggregation update, not
activation of the proposed clinical-scoring v2 protocol or judge debate.
Invalid/unchanged attacks, missing reviews without a quorum,
disagreements and uncertain outcomes earn no competitive win. Multi-study runs with
unresolved studies show confirmed tallies without declaring an overall winner. Unchanged
control verdicts are displayed separately. These are model-judged demo outcomes.

With paired data and a configured key:

```bash
uv run radarena demo --error-type laterality --output runs/laterality-demo.json
uv run radarena demo --control --output runs/control-demo.json
```

By default these select the first paired training study. Pass `--study-id ID` to select
one explicitly. A study may not support a requested error family; Red can return no
edits, in which case the run stops instead of inventing an eligible case. Try an
appropriate reviewed study or a different category (`presence_absence`, `severity`).

The attack run consists of one Red call, one Blue planning call, up to three vision
calls, and one Blue verdict call. Framework parsing fallback and transport retries can
add requests. DSPy caches responses locally in `.cache/dspy`; identical requests may be
replayed. Ordered traces retain explicit prompts, responses, usage, and failures.
The approved-model CLI pilot has a pre-request cost reserve and persistent per-run
ledger. It is not a global account-wide $10 spending control. See the validation guide.

Red receives original sentences and images. Blue receives only candidate sentences,
strategy inputs (currently empty), and images through focused tool calls. The grader
receives the private edits. A trace contains source and private attack information for
the researcher, but those fields are not passed to Blue. The image tool receives only
the images and question, not the original report or edit record.

Reported scores compare Blue's flagged sentence IDs with the injected edit IDs. This
does not prove an attack is image-inconsistent or the original report is error-free.
Attack validity, category correctness, and evidence quality need independent review.

## Reproduce the baseline evaluation

Start with [the validation checklist and trace guide](VALIDATION.md).
The [first live pilot findings](PILOT_FINDINGS.md) report 18 completed
development episodes, a model-generated Red/Blue demo, costs, and observed failures.
The [November 4 RadGraph comparison](RADGRAPH_ABLATION_2026-11-04.md) adds a fresh
matched baseline: Blue flagged more edited sentences with graphs but also more
unchanged sentences, reducing localization F1 from 0.50 to 0.46 on the six reports.
Paid CLI runs now use an audited pilot with a default $0.50 per-run guard;
`--max-cost` and `--max-calls` set the allowance. The supported pilot model is
`qwen/qwen3-vl-8b-instruct`; the verified fallback is `google/gemma-3-27b-it`,
both with at most 2,048 output tokens. Ordered prompts and
explicit responses are saved locally; these are observable explanations and actions,
not access to hidden internal reasoning. No learning loop is required for the first
baseline comparison.

A role-routed, on-demand radiology handbook is available. See
[docs/HANDBOOK.md](HANDBOOK.md) and the entrypoint
[handbooks/radiology-handbook/SKILL.md](../handbooks/radiology-handbook/SKILL.md).
It contains project-authored workflows and short cited public-source summaries.
Clinical review remains pending.

```bash
uv run radarena show-knowledge --file handbooks/radiology-handbook --role verifier
uv run radarena demo --handbook handbooks/radiology-handbook
uv run radarena evaluate --split dev --limit-studies 1 --variants blue_tools \
  --handbook handbooks/radiology-handbook --handbook-condition full --output runs/hb-dev-full
```

The handbook loads its index and active role first, then uses one extra model call to
select up to three chapters. Conditions `full`, `no_domain`, `no_medical`, and `none`
change reader access without changing the cases or image tools. Both Red and Blue can
use their own role books. Chapter reads and content hashes are logged. RadGraph now has
an [optional local extraction path](RADGRAPH.md), tested on the six development
candidates. It supplies report entities/relations, not image truth; a separate
[small development ablation](RADGRAPH_ABLATION_2026-11-04.md) measured its effect.
The handbook reader has no
write interface, while OS-level read-only container mounting is not implemented.

Optional shared radiology/reporting context is supported for both Red and Blue.
See [docs/KNOWLEDGE.md](KNOWLEDGE.md) for sources, review status, and the distinction
between reference knowledge, training demonstrations, and learned memory. The starter
pack contains nine reporting/task cards; clinical image-feature cards and retrieval
are not implemented. Enable it explicitly with:

```bash
uv run radarena show-knowledge
uv run radarena demo --error-type laterality --knowledge-file knowledge/reporting_v1.json
uv run radarena evaluate --split dev --limit-studies 1 \
  --knowledge-file knowledge/reporting_v1.json --output runs/dev-smoke-knowledge
```

All three evaluation conditions receive the same verifier reference pack. Run metadata
records its hash. Without the flag, evaluation uses no added reference context. Choose
the condition on development data before reporting test comparisons.

The concrete protocol, success criteria, sampling limitations, and human-review process
are in [the evaluation protocol](EVALUATION.md). The baseline commands below
describe the constrained synthetic benchmark. The main online experiment uses
separate report-level metrics.

1. Run the CSV preparation command above.
2. Use the included frozen `data/processed/synthetic_benchmark_v2.jsonl`. To
   deliberately generate a separate local benchmark without model calls:

```bash
uv run radarena make-benchmark --output data/processed/synthetic_benchmark_local.jsonl
```

The included v2 benchmark contains 50 training, 20 development, and 30 test studies, each paired
with an unchanged control and one lexical corruption (200 candidates total). Test has
10 attacks per error family. The generator refuses to overwrite a frozen benchmark;
use a new `--output` filename for a deliberate new version. midpoint-v1 was an unused
sampling draft; use the included v2 file for the recorded comparisons. A newly
generated local benchmark has its own metadata and checksum and is not a replacement
for the archived file.

The seed attacker is deterministic, not learned Red. Exact selected-report and image-byte
duplicates are excluded. Image-supported validity is pending; automated scores measure
synthetic-edit detection. Patient linkage and near-duplicate detection remain limitations.

3. After configuring a key, run a **paid** development smoke test on one study (both
   its control and attack) across text_only, direct_vlm, and blue_tools:

```bash
uv run radarena evaluate --split dev --limit-studies 1 --output runs/dev-smoke
```

4. Select settings on development data, then run fixed full comparisons:

```bash
uv run radarena evaluate --split dev --output runs/dev-baselines
uv run radarena evaluate --split test --output runs/test-baselines
uv run radarena summarize --run runs/test-baselines
```

The full test run contains 60 candidates x 3 variants = 180 verifier episodes, with
up to about 420 model calls before retries/parsing fallbacks. Configure provider spend
controls before scaling; CLI audit guards do not enforce an account-wide budget. Repeating the
same command resumes completed records. A changed configuration requires a new directory.
Fresh cache misses incur model charges. Do not tune the system using test feedback.

Each run produces `metadata.json`, `predictions.jsonl`, `summary.json`, `results.md`,
and `failure_cases.jsonl`. Summaries include expected/completed counts, detection and
localization F1, control false alarms, per-category localized recall, coverage, costs
when available, and exploratory paired intervals. Execution failures stop the run;
summaries retain missing denominators and mark partial runs incomplete.

5. Export a blinded human-review subset without model calls:

```bash
uv run radarena export-review
```

This selects 12 category-stratified test studies (24 reports). Give a qualified reviewer
`data/processed/human_review/blinded_cases.jsonl` and its referenced images first; keep
`organizer_key.jsonl` separate until initial judgments are recorded. Review values start
empty and are not clinical labels. Review import/scoring remains future work.

Historical image paths are translated into `data/raw/iu_xray/` at load time without
changing archived bytes. For other dataset locations, create a new manifest and a
new benchmark output rather than manually editing frozen records.

Small live development pilots began November 3, 2026, followed by completed learned-memory
experiments. Clinical review and held-out final-test evaluation remain pending. Unit-test success is not
a model-performance result; the initial smoke test is too small for accuracy claims.

## Documentation

- DSPy image type: https://dspy.ai/current/api/primitives/Image/
- DSPy model interface: https://dspy.ai/current/api/models/LM/
- OpenRouter transport: https://docs.litellm.ai/docs/providers/openrouter
- OpenRouter image inputs: https://openrouter.ai/docs/guides/overview/multimodal/image-understanding
- Default model: https://openrouter.ai/qwen/qwen3-vl-8b-instruct
- Project architecture: [code walkthrough](architecture.md)
- Evaluation design: [protocol](EVALUATION.md)

Optional clinical indication ablation: pass
`--indications-csv 'data/raw/iu_xray/indiana_reports.csv'` to `evaluate` or `demo`;
omit it for no context. Only indication is supplied, equally across methods.
See [configuration, privacy boundaries and paired pilot](INDICATION_ABLATION.md).

Real-data strategy learning: `radarena learn --output runs/my-learning-pilot --max-cost .50`.
Red and Blue update separate bounded memories on training cases, then freeze them
for a before/after development comparison. See [the learning protocol and logs](LEARNING_PILOT.md).

Ten-study Red → Blue → Judge batch: `.venv/bin/python scripts/run_ten_study_batch.py`.
Uses frozen learned memories, ten edited reports plus ten controls, independent
image judges, and a $1 global audit cap. [Protocol and completed results](TEN_STUDY_BATCH.md).

Stronger-model/evidence-ledger pilot: [configuration and comparison protocol](STRONGER_BLUE_PILOT.md).
Use `--structured-blue` for explicit evidence assessments and `--strict-attacks` for
conservative controlled Red validation. Models remain selectable through the existing
`RADARENA_TEXT_MODEL` and `RADARENA_VISION_MODEL` settings.

Open-ended online experiment: [20-study protocol](OPEN_ONLINE_20.md).
Red chooses and logs clinical report changes; Blue and two reviewers evaluate them,
role-private memories update over 15 studies, and five later studies compare frozen
starting versus learned Blue memories on identical reports. New-run audit cap: $3.

Memory updates now use explicit role rewards, conflict review, and paired measured
promotion gates. [Policy, calibration and validation](MEMORY_PROMOTION.md).
The default online output is a new `open-online-gated-20-2026-11-04` directory;
old results are preserved. No measured improvement is implied until the new policy
is evaluated in a live run.
