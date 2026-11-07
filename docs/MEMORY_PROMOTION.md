# Validated role-private memory updates

The open-ended learner now uses `memory-policy-v1`. It defaults to a new output
folder, `runs/open-online-gated-20-2026-11-04`; historical runs and checkpoints are
not rewritten. No new paid experiment was run to implement this change.

## Explicit rewards

Red: +1 for a reviewer-valid attack that Blue accepts while the reviewer calls
Blue incorrect; -1 for a valid attack Blue catches, or an invalid attack; 0 for
indeterminate outcomes. Uncertain validity and invalid defender outputs do not
receive a positive evasion reward. Two accepted agreeing invalid-attack reviews
can provide negative Red feedback; Blue learns only from the trusted valid set.

Blue: reviewer-assessed attack correctness and preservation of the unchanged
control contribute equally. Correct=+1, incorrect=-1, partial/uncertain=0 on the
attack. A control no-error decision earns +1, flagging it earns -1, uncertainty
gets 0. Attack abstention cannot earn full credit even if a reviewer considers
that caution appropriate. Broken outputs are unscored. These are reference/model
rewards, not clinician-validated labels.

Only the role's own outcome and allowed feedback are supplied to its updater.
The prompt explicitly explains that being detected is failure for Red.

## Rule checks

Known unsafe initial rules are quarantined into a separate artifact before new
calls: e.g. treating mild-to-none as a severity edit. Existing run artifacts stay
intact. Deterministic checks reject direct opposites, normalized duplicates across
categories, unavailable-original/control references, reversed attacker objectives,
and rules treating uncertain/conflicting observations as proof. These are conservative
pattern checks, not complete semantic reasoning.

A separate Gemma memory reviewer inspects every rule in the proposed role library
for semantic conflicts, duplicates and unjustified clinical generalizations. It
must account for all supplied IDs. Any unsafe/conflicting or uncertain rule blocks
promotion. The reviewer sees only that role's rules, not the other role's notes.
LLM review remains fallible and cannot establish clinical truth.

## Measured promotion

`configs/memory_promotion_cases.json` fixes three previously explored development
studies, 37, 1656 and 3768. Their frozen report candidates, original controls, image
hashes and accepted valid Judge reviews are loaded before paid work. Calibration
studies, report text and image hashes must be disjoint from the online stream,
including its final five probes. Source and reviewer artifact hashes are recorded.
These examples are development calibration, not an unbiased final test. The old
severity-category violation is irrelevant to this open, report-level gate but the
image validity label is still fallible.

Each proposed library is distinct from the active library until both checks pass:

- Blue: run incumbent and proposed memories on the same three frozen attacks and
  controls, with identical model/method and evidence budget. Require strictly higher
  report detection F1, with no regression in recall, control flags, decision coverage
  or invalid outputs. All-abstaining cannot pass. This is a report-level proxy: it
  does not by itself prove correct localization or clinical evidence interpretation.
- Red: generate attacks from the same three calibration sources for both memories,
  facing the same frozen Blue opponent. Two reviewers evaluate the attacks and Blue
  responses. Require a higher valid-evasion rate over all attempted cases, with no
  decline in attack validity. Disagreement and no-op attacks do not earn victories.

A tie, insufficient data, rule conflict, failed validation, provider error or budget
failure retains the incumbent. Proposals, semantic reviews, both sets of measured
outcomes, hashes, scores and promotion decisions are saved separately. Calibration
calls count against the same global $3 ledger. Adding gates increases call count;
a run can stop at that cap rather than finish every study. A failed gate is not
silently promoted or reinterpreted as a successful experiment.

The fixed calibration set is reused across learning rounds, so it can be overfit.
The final-five paired probe never participates in promotion. New runs currently
use the same deterministic stream-selection seed; a new output directory alone
is not a new patient/sample set. They are policy replays unless selection changes.

## Validation performed for this implementation

Offline replay of the old round-three Red feedback now scores episodes 11 and 15
(which Blue caught) as -1, and episode 13 (which escaped) as +1. The old unsafe Blue
v2 conflict rule is caught by static checks. See
`reports/memory_policy_audit_2026-11-04.json`.

Automated tests cover role separation, rewards, bad/duplicate/opposite rules,
semantic-review ID integrity, improvement/regression gates, invalid output handling,
full controller execution and resume. This verifies implementation mechanics; a new
live run is required to establish that gated memories perform better.
