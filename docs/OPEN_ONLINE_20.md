# Twenty-study open-ended online experiment

Run: `.venv/bin/python scripts/run_open_online.py`.
Output: `runs/open-online-20-2026-11-04/`. New experiment audit cap: $3.

This experiment uses 20 distinct, previously unused IU training studies, including
all 39 associated image files. All 100 studies in the frozen synthetic benchmark
and their exact report/image duplicates are excluded. Selected cases are fixed
before paid calls and never replaced based on results. The project final test
split is untouched. `selection.json` stores report text and image hashes.

## Protocol

- Red and Blue use Gemini 2.5 Flash, starting from their separate v3 memories from
  the earlier learning pilot. Each call gets fresh explicit inputs, not shared chat
  history or tools for reading another role's files. Both receive indication.
- Red chooses clinical error types and can revise, add, or remove sentences across
  the whole report. Retained sentence IDs stay stable; added IDs use a1,a2,... .
  Its explicit provenance log must account for every changed/deleted/added sentence.
  Original images and history cannot be changed. Prompt injection is outside this
  radiology experiment. A no-op is allowed and counted separately.
- Blue receives only candidate text, images, indication, reporting references and
  its own learned rules. Two focused image checks inform a whole-report verdict.
  Error categories are open text; `report_level` supports omissions with no existing
  candidate sentence. Every error flag requires actual image-evidence citations.
- Blue separately checks each unchanged report as a control. There are 20 attack
  attempts and 20 controls, not 40 independent studies.
- Two independent calls review each attack episode: Gemma 3 27B and Gemini 2.5 Flash.
  Reviewers do not see each other's judgments or contestant memory. They see source,
  candidate, images, change log, Red rationale and actual Blue outputs. They explicitly
  inventory Blue's accusations to avoid confusing them with Red's edits. Flash shares
  a family with the contestants; two-model agreement is not clinical ground truth.
- After each of the first three blocks of five studies, Red and Blue separately
  propose bounded lessons. Only episodes with two accepted, agreeing validity and
  Blue-assessment judgments, both calling the attack valid, support updates. Invalid
  Blue outputs are excluded. Every supporting episode ID must be in that trusted set.
- Lessons are stored by category, preserving other categories instead of overwriting
  the entire memory with the latest example. At most two rules per category and
  twenty total rules are allowed. Rules requiring unavailable original/control
  reports or referring to sentence IDs are rejected. No evidence means no update.
- The final five studies never update memory. Blue additionally checks their same
  saved attacks and controls with its starting memory. This is the matched initial
  versus learned comparison; changes between earlier rounds alone confound learning
  with differences in cases and Red attacks.

## Feedback boundaries

Red's updater receives its own edits/rationale and structured validity/Blue outcomes,
not Blue's observations or memory. Blue's updater receives its own candidate,
observations/verdict, control outcomes and post-episode reviewer feedback, not Red's
strategy memory or raw rationale. Reviewer explanations can describe training-case
clinical facts; this is supervised feedback after an attempt, not inference-time
access to the source report. The researcher can inspect all artifacts. The models
have no filesystem tools; role separation is implemented through input whitelists.

This is strategy-memory adaptation, not model-weight training. A lesson supported
by judge consensus is not proven beneficial. The final probe measures whether the
combined updates helped on those particular cases. This does not separate Red and
Blue training effects generally or establish clinical safety.

## Failure handling and amendments

Every stage has its own persistent audit and saved checkpoint. The global cap sums
all ledgers, retaining conservative reserves for unknown failed requests. Transient
provider errors get at most one immediate retry; completed stages are skipped on
explicit resume. Changing code/configuration requires an archived, documented
amendment or a new run directory.

After six completed cases, Blue returned an uncited accusation on case seven. One
bounded mechanical correction with the same candidate and observations was added;
no gold/source data was supplied. It repeated the invalid accusation. The output
was therefore retained as `invalid_output`, not converted into uncertainty or success,
and excluded from learning. The selected case and raw attempts remain included.
Future invalid verdicts after that bounded correction also remain failures rather
than stopping all later cases. Both amendments, original implementations, metadata
versions, and raw failed requests are preserved. These amendments limit comparisons
of early versus late rounds; the final matched probe uses the same amended pipeline
for both starting and learned memories.

## Results and metrics

`results.md`/`summary.json` update after each complete episode. Reports include attack
categories, Blue decisions, control flags, invalid outputs, both reviewers' validity
labels, consensus/disagreement, memory updates and spending. Open-ended omission and
rewriting cannot be graded by the old sentence-match F1 without misleading omissions;
report-level outcomes and reviewer agreement are primary. Source reports and model
reviewers are not clinical gold labels. Controls measure reference-report flagging,
not verified clinical false-positive rates. Invalid/missing outputs remain explicit.

Artifacts:

- `episodes/`: source, candidate, changes, Red rationale, Blue checks/control and reviews.
- `stages/`: resumable model outputs, including final-five starting-memory probes.
- `audit/*/trace.md`: all prompts, concise model outputs, usage, errors and cost.
- `feedback/{red,blue}/`: exact role-specific feedback supplied to updates.
- `memories/{red,blue}/v1..v3.json`: accepted category libraries, proposals and rejections.
- `implementation*`, `metadata*`, `protocol-amendment*`: reproducibility/protocol history.

Inspect model explanations as observable outputs, not access to hidden reasoning.
Do not publish the raw dataset, credentials or patient-level traces with the code.

At the case-12 resume, the archived interface also gained explicit image/text/mixed
evidence types. A report-internal contradiction must cite two distinct candidate
sentences; it does not prove which statement is image-false. Image claims still need
real image-tool citations. This interface change and the provenance bookkeeping
repair are documented in amendment 03. The later bounded-assessment helper stores
all rejected attempts and returns invalid_output with no accepted findings. Earlier
case 7 retains its original raw rejected accusations explicitly as a failed result.
The final-five initial/learned calls use the same typed interface. Early-versus-late
round outcomes cannot isolate learning because of these protocol changes.

## Completed results

All 20 studies (39 image files), 20 matched controls, 40 accepted reviewer responses,
and ten additional starting-memory probe checks completed. Both roles produced
three memory updates. Across all attacks, Blue returned error 13 times, no-error five
times, uncertainty once and invalid_output once. Seven unchanged controls were
flagged. Both reviewers called 15 attacks valid; on those Blue flagged ten, missed
four and produced one invalid output. Five attacks had reviewer validity disagreement;
they are not counted as confirmed Red successes.

On the final five matched studies, both memory versions detected all three attacks
that both reviewers called valid. Learned memory flagged one control versus two
with starting memory. The consensus-conditioned report detection F1 was 0.75 → 0.857.
This differs from the earlier sentence-localization F1 and rests on only three
consensus-valid attacks plus five reference controls. There is no strong generalization
claim. The learned checkpoint flagged all five edited reports versus four initially,
but the additional flag was on a reviewer-disputed attack, not an established gain
in detection of valid attacks.

Red mainly chose omission/fabrication despite freedom to choose other clinical
error types: six omission labels, sixteen fabrication labels, and one controller-
identified unlogged text change. Multiple changes per report are possible, so those
counts do not sum to twenty. Free choice did not automatically produce broad attack
diversity. Memory changed strategies, but neither attack diversity nor Red improvement
against a fixed opponent has been established.

Audit accounting was $0.53389773: $0.20620493 in successful-call reported costs
(including possible framework cache accounting) plus a $0.3276928 conservative
reserve for one timed-out request with unknown actual billing. There were 274
audited calls including cache lookups and explicit resumes; the $3 cap was preserved.
All invalid responses, protocol amendments and exact implementation versions remain.

`analysis.md` gives the matched-probe metrics and learned libraries; `walkthrough.md`
contains all sources, candidates, provenance, Blue evidence and reviewer responses.
The current observer can display this run, learning actions and probes as separate
conditions. These records remain research artifacts, not a clinically validated system.
