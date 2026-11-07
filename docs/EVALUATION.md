# Frozen benchmark evaluation protocol

Protocol version: midpoint-v2, November 3, 2026. Written before any live evaluation.
Benchmark generation and code tests have run. Small live development smoke tests
subsequently began; see [VALIDATION.md](VALIDATION.md). No held-out
accuracy, human-review result, memory-learning result, or GEPA result is being claimed.

## Task and hypotheses

For each IU chest X-ray study, a verifier receives a candidate Findings/Impression
report and the available images (except for the text-only baseline). It predicts
error / no error detected / uncertain, identifies suspect sentence IDs and error
families, and supplies concise evidence. Intended users are medical-AI researchers
investigating report-verification methods.

H1, baseline: focused image-tool verification improves sentence localization over
direct image-and-report verification on fixed, unseen synthetic edits. Evaluate
the paired difference, its uncertainty, false alarms, and cost; do not promise improvement.

H2, later investigation: training-derived strategy memory improves the identical
Blue agent on a fixed held-out attacker set. Keep GEPA as a separate intervention.
Neither memory learning nor GEPA is implemented yet. Joint co-evolution requires
an additional fixed-opponent evaluation of learned Red against frozen Blue.

## Data source, processing, and selection

User-supplied download page:
https://www.kaggle.com/datasets/raddar/chest-xrays-indiana-university

Upstream collection publication: https://doi.org/10.1093/jamia/ocv080
The source contains clinical reports and chest radiographs; this local copy is a
processed CSV/normalized-PNG export. Do not imply we collected or independently
annotated the underlying clinical examinations. Record the Kaggle version/download
date and applicable terms before redistributing any data; those details are not
established by a readable page in this session.

Locally measured inventory: 3,851 report rows, 7,466 projection rows, 7,470 image
files; 3,826 studies retained and 25 excluded for absent report text or image
references. All referenced files exist for retained studies. Findings and Impression
are extracted; MeSH/Problems labels, indication, and comparison fields are excluded
from verifier inputs. Five studies' images were opened/verified during initial QA;
file existence is not a complete image-quality or medical-content audit.

Study IDs are deterministically assigned to train/dev/test using the ingestion
hash seed. All views and report variants stay with the source study. Selected
studies exclude exact normalized report duplicates and byte-identical image
duplicates across the benchmark. No separate patient linkage is available in
this export; do not claim verified patient-independent or external generalization.
Near-duplicate images/reports and pretraining contamination are not ruled out.

The executable seed attacker makes minimal, deterministic edits to explicit
negation, side, or severity terms. It excludes negated side/severity claims,
findings repeated in other sentences, and explicit temporal descriptions in the
target sentence. These are lexical eligibility rules, not clinical validation.
Selection uses scarce categories first so abundant negation cases cannot dominate.

| Split | Studies | Unchanged controls | Corrupted reports | Presence/absence | Laterality | Severity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 50 | 50 | 50 | 17 | 16 | 17 |
| Development | 20 | 20 | 20 | 8 | 7 | 5 |
| Test | 30 | 30 | 30 | 10 | 10 | 10 |

Each study contributes one control and one corruption. Thus there are 200 candidate
reports overall and 60 test candidates. The effective independent sample size for
test comparisons is at most 30 studies, not 60 independent examples. Controls are
unchanged source reports; they are not adjudicated clinically error-free reports.

midpoint-v1 was an unused sampling draft that overrepresented presence/absence
edits. midpoint-v2 is the designated benchmark; no prediction results were used
to revise sampling. The seed attacker is a frozen reference attacker, not evidence
that Red has learned to generate difficult or realistic attacks.

## Fixed comparisons and information boundaries

| Variant | Inputs | Workflow | Learned strategies |
| --- | --- | --- | --- |
| text_only | Candidate report | One typed verification call | None |
| direct_vlm | Candidate and same study images | One typed verification call | None |
| blue_tools | Candidate plus images through tool | Plan, up to three image checks, assess | None |

Use identical frozen candidate reports for all variants. Red is not re-run during
evaluation. Blue, the direct baseline, and the image tool never receive the original
report, edit metadata, correct category, or expected verdict. The text-only arm
never receives an image. Private labels are used only by the scorer and researcher.

Default model for text and vision is `qwen/qwen3-vl-8b-instruct` via OpenRouter;
each call has the same token cap and temperature settings. Direct and tool-based
systems have different total call budgets; report those costs alongside quality.
The comparison measures the entire verification workflow, not pure tool-use benefit
at equal compute. A future equal-call-budget baseline can isolate that question.
Record actual model identifiers, provider information if available, settings, DSPy
version, code revision, and run date. OpenRouter routing can change upstream providers;
the current runner does not pin a provider or guarantee an immutable model revision.

An optional fixed reporting reference pack is now available through `--knowledge-file`.
All three variants receive the same verifier context, and the pack hash is saved in run
metadata. Compare with/without references on development data as a distinct intervention;
do not confound knowledge with memory learning or GEPA. The default remains no added
reference context. Sources, limitations, and pending review are in docs/KNOWLEDGE.md.

Use development cases for debugging and configuration choices. Freeze model settings
and any future memory/prompt checkpoints before evaluating test cases. Do not put test
feedback into Red/Blue memories or GEPA training. If the test set is used to redesign
the system, report that use and create a new holdout rather than presenting it as untouched.

The optional role-routed handbook adds a second, separately specified reference study:
`full`, `no_domain`, `no_medical`, and `none`, with the same frozen cases and tools.
See docs/HANDBOOK.md for chapter access, bounded selection, content hashes, read logs,
clinical-review limitations, and exact development commands. These conditions isolate
handbook access; they do not remove base-model knowledge or establish agent learning.
Between-condition statistical comparisons are not yet automated. Do not pool handbook
and original baseline results without labeling the reference condition and added call cost.

## Scoring and success criteria

Primary baseline outcome: sentence-localization micro F1 against mechanically known
changed sentence IDs, comparing blue_tools with direct_vlm on the same test cases.
Report the paired difference and an exploratory 95% percentile bootstrap interval,
resampling whole studies so each control/corruption pair stays together. Report both
positive and negative differences. Thirty studies support only a preliminary pilot.

Secondary outcomes:

- Report error-detection precision/recall/F1, relative to the synthetic labels.
- False-positive rate on unchanged controls.
- Correctly localized and correctly categorized recall, with hit counts and denominators
  for each of the three error families.
- Abstention rate and decision coverage. Uncertain verdicts on corruptions are misses;
  strict decision accuracy counts uncertainty as incorrect on controls too.
- Completion rate and strict accuracy over every expected case, so parse/API failures
  and missing predictions cannot silently improve the score.
- Mean recorded wall time, recorded call count, reported call cost and missing-cost
  counts. Cached replays are not fresh latency or cost measurements. Provider billing
  is authoritative; framework logs may not cover every retry or parsing fallback.

F1/FPR computed on completed verdicts must always be presented beside completion and
coverage. The runner stops on an execution error, records the failure, and can resume.
An incomplete run is labeled incomplete, with its original expected denominator retained.
Synthetic metric improvements are not equivalent to clinical accuracy improvements.

No absolute target such as "80% accuracy" is assumed in advance. The research test is
whether the focused workflow improves localization on fixed unseen cases, at what
false-alarm/uncertainty/cost tradeoff, and with what statistical uncertainty. A null
result with a supported failure analysis is a valid outcome.

## Human review and model-judge roles

The review export selects 12 test studies across error categories (24 reports) and
creates a blinded reader file plus a separate organizer key. First, a qualified reviewer
sees only images and candidate sentences and records a verdict, suspect sentences,
categories, evidence, and uncertainty. Then use the organizer key to inspect whether
the intended edit changed a clinically meaningful attribute and is contradicted by
the supplied images. Record reviewer qualifications, review date, accepted/rejected
attacks, ambiguous cases, and reasons. Do not label pending templates as reviews.

The implemented scorer currently reports the full synthetic benchmark; importing
clinical review decisions and calculating a reviewed-subset score is future work.
Keep that reviewed score separate. For a future validity-filtered benchmark, apply
acceptance decisions uniformly before comparing model variants, freeze a new version,
and disclose exclusions. Do not reject attacks based on whether the preferred model
succeeded on them. If available, have a second reviewer assess an overlapping subset
and report agreement and disagreement resolution; this has not occurred yet.

Optional model reviewers assess explanation relevance, attack validity, and Blue's
actual behavior against supplied evidence. See [the judge interface](JUDGE.md) and
[the online experiment](OPEN_ONLINE_20.md) for implemented protocols and information
boundaries. These model judgments cannot establish that an X-ray interpretation
is correct and are separate from the synthetic-edit scorer described here.

## Failure analysis and reproducibility

The summary emits a results table and `failure_cases.jsonl`, tagging uncertainty,
missed edits, false alarms on controls, incorrect locations/additional flags,
incorrect categories, and runtime failures. Manually inspect representative cases
across systems and categories, including both a success and a failure. Look for
visual misinterpretation, report-language artifacts, conflicting/insufficient views,
unavailable prior context, tool-question anchoring, and unsupported evidence claims.

Benchmark bytes and image contents have checksums. The benchmark cannot be overwritten
by the builder, and the runner checks for edits before model calls. Processed cases, review labels, and run traces are included for
reproducibility; source CSVs and radiographs are downloaded separately. Credentials and response caches stay local.
Frozen files retain their original absolute paths and checksums. The loader resolves
known IU image paths into the current checkout after checksum verification. New
imports prefer relative paths. Do not rewrite frozen records simply to relocate data.
See `data/LICENSE.md` for source attribution and sharing terms.

See [the experiment guide](EXPERIMENT_GUIDE.md) for the exact build/evaluate/summarize/review commands. A recorded demo
is one illustration; the fixed evaluation table and failure cases supply the evidence
for performance claims.
