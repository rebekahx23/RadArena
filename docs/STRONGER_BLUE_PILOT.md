# Stronger-model and structured-evidence updates

New Blue option: `demo --structured-blue` or `evaluate --structured-blue`.
The complete report is passed in one assessment call; it is not split into separate
per-sentence model requests. Every sentence receives a supported, contradicted,
unresolved or not-assessed entry. The controller derives the verdict; only a cited
contradiction with an error category becomes a flag. Unresolved/unassessed entries
produce uncertainty when there are no contradictions. The planner prioritizes
important positive claims and asks about location without assuming the report's side.
These mechanical checks do not establish that model-provided evidence is correct.

New controlled Red option: `demo --strict-attacks`. Laterality/severity edits must
preserve all other normalized wording; removing cardiomegaly is rejected as a severity
change. The validator is conservative, and does not cover open-ended novel attacks
or certify image validity. Red instructions include category examples and abstention
when the requested attribute is unavailable. A rejected edit stops before Blue calls.

Judge rubric v3 repeats the actual Blue decision, flagged sentence IDs and citations
in an explicit accusation inventory, including the rule that no flags means no flag
reviews. The same inventory is supplied during bounded mechanical correction.
Previous reviews and rubric versions remain unchanged. Judge opinions are fallible.

## Model configuration

Use the existing OpenRouter model settings for both text and vision:

```bash
RADARENA_TEXT_MODEL=google/gemini-2.5-flash \
RADARENA_VISION_MODEL=google/gemini-2.5-flash \
.venv/bin/radarena demo --study-id 1187 --error-type severity \
  --strict-attacks --structured-blue \
  --indications-csv 'data/raw/iu_xray/indiana_reports.csv' \
  --knowledge-file knowledge/reporting_v1.json \
  --output runs/flash-structured-demo.json --max-cost .75
```

The example is a new paid run, not a saved result. Omit memory flags for empty-memory
agents; explicit `--red-memory` and `--blue-memory` still accept role-private frozen
checkpoints. Gemini Flash can be used for Red too; the paired comparison below only
changes Blue, to isolate its effect. Actual `.env` credentials are never rewritten.
Runtime sets Flash reasoning budget to zero to preserve the 2,048 output-token cap,
retains provider price filters, and allows 90 seconds per Flash call. The verified
OpenRouter listing gives input/output prices $0.30/$2.50 per million tokens:
https://openrouter.ai/google/gemini-2.5-flash

## Paired pilot

`.venv/bin/python scripts/compare_stronger_blue.py` runs three paid arms with a
$1.50 combined audit cap: Flash legacy, Gemma structured, Flash structured.
The Gemma legacy baseline reuses its exact six saved outputs from the ten-study
batch. Selected studies are 37, 1656 and 3768, each with the same saved attack and
unchanged control, all image views, indication, reporting pack, frozen Blue v3 memory,
and two-image-check budget. Red is not regenerated. Text and vision models change
together, so the comparison does not isolate which model stage drives an improvement.

Study 3768's requested severity attack removed a finding. It remains deliberately
fixed and labelled in this comparison; results are detection of those specific
saved edits, not clean severity accuracy or clinically validated sensitivity.
The earlier Flash Judge is not an independent grader for Flash Blue; primary
comparisons use code-based injected-edit localization and control flags. A future
independent review should use a different judge family and expert calibration.

The first Gemma structured request returned null evidence for unassessed rows and
failed parsing. We allowed null evidence for non-contradicted rows, retaining strict
nonempty evidence for contradictions. No structured prediction completed before
this change. The original implementation/metadata, failed call, and explicit
protocol amendment are preserved. Completed legacy outputs were unaffected.

Read `runs/stronger-blue-2026-11-04/results.md`, `summary.json`, and each arm's
`audit/trace.md` for actual results. This is an exploratory development comparison,
not a test of learned-memory benefit or an untouched final-test evaluation.

## Completed result

All 24 outputs (including six reused baseline outputs) are available. New paid audit
accounting was $0.03617854. On three studies/six reports:

| Model and method | Localization F1 | Report detection recall | Unchanged controls flagged | Abstentions |
| --- | --- | --- | --- | --- |
| Gemma, legacy | 0.286 | 1/3 | 2/3 | 2/6 |
| Flash, legacy | 0.667 | 2/3 | 1/3 | 0/6 |
| Gemma, ledger | 0.250 | 1/3 | 2/3 | 3/6 |
| Flash, ledger | 0.545 | 2/3 | 1/3 | 3/6 |

The model-only replacement helped on this fixed small sample. The ledger did not
improve localization F1 for either model, and increased abstention. It remains
experimental and opt-in. Neither result establishes clinical accuracy or a general
model ranking. This is not evidence that learning helped: all arms used the same
frozen memory. Future independent judging should avoid using Flash as its own judge.

The batch runner now accepts `--model flash --output runs/NEW-DIRECTORY`, enforces
controlled Red-family validation by default, and leaves the experimental ledger
optional with `--structured-blue`. Rejected Red edits remain in private checkpoints
and are not counted as verified attacks or silently replaced. This can produce
ineligible/failed attack stages; it is not an open-ended attack generator. New
stricter code cannot resume the historical batch directory; its source snapshot is
preserved there. The default model is not silently changed in the user's `.env`.

A fresh comparison can be run with
`python scripts/compare_stronger_blue.py --output runs/NEW-COMPARISON` using the
project `.venv` interpreter. The completed pilot's metadata and exact source snapshots
remain preserved. Selective memory promotion, per-family learned memory, additional
independent judge families and broader clinically reviewed attack generation remain
future work; they are not implied by these changes.
