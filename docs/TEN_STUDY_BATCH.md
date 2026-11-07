# Ten-study Red → Blue → Judge batch

Run `.venv/bin/python scripts/run_ten_study_batch.py` from the project root.
Output: `runs/red-blue-judge-10-2026-11-04/`.

This is a frozen-memory evaluation, not another training run or a before/after
learning comparison. Gemma 3 27B runs Red and Blue using their separate final v3
memories from the learning pilot. Gemini 2.5 Flash independently reviews each
edited-report episode with images and privileged source/edit information. The
judge is a fallible analyzer, not clinical ground truth. No judge feedback or
original/edit information is given to Blue. Both roles receive the same indication.

Ten deterministic development studies, not used in the preceding small pilots,
are selected before model calls: four laterality, three presence/absence and three
severity targets. All views for each study stay together. This selection contains
20 image files. The ten patient-study IDs and source/image hashes are frozen in
metadata and organizer files. Patient independence beyond study grouping is not
verified. The final test split is unused.

For each study:

1. Red gets source report, images, indication, reporting references, its own frozen
   strategy rules, and a requested error family. Save its generated edits before
   checking them with Blue, so a failed verification never forces regenerating Red.
2. Blue gets the whole candidate report, images, indication, reporting references
   and only its own rules. At most two neutral image checks inform its final verdict.
3. Judge gets the source, candidate, actual edit, Red explanation, Blue response,
   observations and images. It evaluates attack validity, Blue correctness, evidence
   use and limitations. The structured validator checks IDs/citations and permits
   one bounded mechanical correction. The judge may still be wrong or inconsistent.
4. Blue separately checks the unchanged report as a control, with the same context
   and rules. These controls measure false alarms relative to reference reports;
   they are not certified clinically error-free. The ten attack episodes are judged;
   controls are not independently judged in this batch.

The global $1 audited cap includes every agent/judge audit in this batch. Unknown
failed-request costs retain their conservative reserves. Stages run sequentially,
and each stage's cap is computed from the remaining global budget, including its
existing charges on resume. Agent stages allow at most one explicit retry for a
transient provider timeout/rate limit; no failed outcome is scored as success or
replaced with an easier case. Raw Red checkpoints, failed requests and all outputs
remain inspectable. Red edits are syntax-validated but requested-family compliance
and image validity must be assessed separately from synthetic edit localization.

`results.md` and `summary.json` update as the batch progresses, retaining all ten
studies in their completion counts. Main measurements: edit localization, extra
sentence flags, correct requested category, control false alarms, uncertainty,
judge attack-validity distribution, judge assessment of Blue, conditional Red
outcome, failure modes, completion and cost. Conditional Red outcomes can be
indeterminate or invalid attack; an undetected text edit alone is not proof of a
successful image-valid attack.

Each `study-ID.attack.json`/`.control.json` has its own `.audit/trace.md`. Each
attack's `.judge.json` and `.judge.audit/` hold the independent review and cost.
The existing local viewer discovers these episodes and attaches judge reviews in
its Judge workspace. The exact implementation is archived in `implementation/`
without credentials. `metadata.json` records model, image, source, context and
memory provenance. Saved runs are included with source attribution; raw data is
downloaded separately and API keys remain excluded.

## Completed results and recovery

All ten attack episodes, ten controls and ten accepted Judge reviews completed.
Blue localized one edited report out of ten, with zero correct requested-category
hits, and flagged two unchanged reference reports out of ten. It abstained on four
attacks and five controls. Localization F1 across the twenty completed reports was
0.111 (one true-positive sentence, two extra flags, fourteen missed edited sentences).

Judge labelled eight attacks valid: five escaped, one was caught, two were
indeterminate. Two were labelled invalid. These are fallible model opinions.
Post-hoc text review found that all three requested severity attacks changed a
finding to absence rather than isolating severity, and one presence/absence attack
mixed in asymmetry. This is not a clean severity benchmark or evidence that the
learned memories improve performance.

Initial Judge acceptance was 7/10: one timed out and two hallucinated Blue flags
despite Blue returning an empty findings list, including on their first correction.
`scripts/recover_batch_reviews.py` made one further explicit recovery per failed case,
restating Blue's exact recorded decision and flags, without prescribing any clinical
outcome. All three then passed the original validator. Prior failed records are
preserved in `failed-judge-reviews/`, and every request remains in its original
cumulative audit. Some accepted free-text judgments still have consistency problems,
discussed in `analysis.md`; schema acceptance is not clinical validity.

Seven agent transport failures, one agent timeout and one Judge timeout are retained.
Agent stages were explicitly resumed from the same checkpoints after the network
recovered. Total audit accounting was $0.47054605, including $0.4358272 in conservative
unknown-cost reserves. Successful audited calls reported $0.03471885, possibly
including cache cost accounting. The $1 global cap was preserved throughout.

Regenerate the descriptive analysis with
`.venv/bin/python scripts/analyze_ten_study_batch.py`.
Read `runs/red-blue-judge-10-2026-11-04/results.md` for the full case table and Judge
explanations, and `analysis.md` for metrics, attack-family review and Judge quality.
The local viewer on port 8767 displays each episode and its independent Judge panel.
