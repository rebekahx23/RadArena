# Optional indication context

`demo` and `evaluate` accept `--indications-csv 'data/raw/iu_xray/indiana_reports.csv'`.
Omit the flag for the no-context condition. The CSV is joined by exact study UID;
only `indication` enters model inputs. MeSH, Problems, comparison, findings and
impression columns never enter through this context loader. Findings and impression
continue to come from the frozen candidate report, not a fresh CSV lookup.

The indication is separate from report sentences: it supplies the reason for the
examination, is not an editable/gradable sentence, and is not proof of a visible
finding. Missing indications stay empty; an absent study UID fails before paid calls.
The source CSV SHA-256 and condition are recorded in run metadata; exact supplied
context is retained in every prediction and the audited requests. Existing benchmark
and experiment files are not changed. Do not resume a run with a different CSV.

In generated-attack demos, both Red and Blue receive the same unmodified indication.
In evaluation, text-only, direct vision and Blue planner/final assessor get the same
indication for both the control and corrupted version. Blue's independent image
inspection call still receives just images and a neutral question. A post-hoc judge
reads the context actually recorded for Blue, never an additional fresh history.

## Paired pilot

Run `.venv/bin/python scripts/run_indication_pilot.py` from the project root.
This fixes Gemma 3 27B for both roles and compares indication off/on on dev studies
1094, 1106 and 2036: three controls plus three seed attacks per condition, across
text-only, direct vision and Blue with tools (36 verdicts total).
RadGraph is off and the reporting reference pack is held fixed. Each condition has
an audited $0.05 cap and 80-call ceiling, no automatic retries; failures stay on tape.
Use a new output directory if implementation/configuration changes.

Inspect `runs/indication-ablation-2026-11-04/{none,indication}/audit/trace.md`
for requests, outputs and cost, and `summary.json`/`failure_cases.jsonl` for grading.
Explanations and observations are inspectable outputs, not access to hidden model
reasoning. This small development subset tests behavior, not statistical efficacy.
Compare localization F1, control false alarms, abstention, category errors, completion
and cost. Study-level paired evaluation is needed before a larger performance claim;
unchanged reports and synthetic edits remain unadjudicated clinical references.

## Completed pilot: November 4, 2026

All 36 verdicts completed after one explicit resume for a temporary upstream Gemma
429. The failed attempt is retained. Run metadata differs only in clinical context.
Both conditions used the same code, Gemma 3 27B, reporting pack and six candidates.

| Method | Localization F1, no indication | With indication | Control false alarms, no indication → with |
| --- | --- | --- | --- |
| Text-only | 0.500 | 0.333 | 1/3 → 1/3 |
| Direct vision | 0.667 | 0.333 | 1/3 → 1/3 |
| Blue with tools | 0.571 | 0.571 | 0/3 → 1/3 |

There is no improvement demonstrated in this pilot. Blue's unchanged F1 hides a
change in errors: one extra flag disappeared from a corrupted report, while a new
false alarm appeared on its unchanged control. In study 1094's unchanged report,
context changed the planner from broad checks (including bones and soft tissue) to
focused lower-lobe density/consolidation checks. The final assessor then incorrectly
flagged s4 as a presence/absence error while citing an observation describing that
same lower-lobe density with uncertainty. This is an evidence-to-verdict consistency
failure; supplying more context did not fix it. We cannot infer that the history
alone caused worse clinical interpretation from this tiny sample.

For study 1106's injected pneumothorax candidate, direct vision changed from flagging
the injected s7 to flagging unchanged s5 ("Left lung clear"). That reduced localization
performance. Text-only also shifted its flags away from the edited location in
study 1094. These comparisons use injected edit locations, not adjudicated clinical
truth. The next useful investigation is a supported/contradicted/uncertain check
before turning an observation into an error accusation, followed by a larger paired
sample; do not tune against the held-out test set.

Successful audited calls have combined reported cost $0.0109408 (cache accounting
may be included). Total audit accounting is $0.0244576, including a $0.0135168
conservative reserve for the failed request whose actual billed cost is unknown.
Each condition stayed below its $0.05 cap. Detailed results and trace links are in
`runs/indication-ablation-2026-11-04/comparison.md` and the condition subdirectories.
