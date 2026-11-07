# Proposed RadArena judging protocol v2

Status: design specification; not activated. Existing judgments, winner rules and
run artifacts retain their original version. No model calls are required to write
this proposal. Prompt, schemas, rewards, UI and aggregation must migrate together.

## Objective

Blue checks the candidate report against the supplied study images, available
patient history, and the report's internal consistency. Finding genuine issues is
the primary task, including issues in sentences Red did not change. Localizing
Red's actual modifications is a separate bonus. Supplying a corrected diagnosis or
report is an optional third task, not a condition for detection credit.

Red's original report is a privileged experimental reference, not clinical truth.
History is contextual evidence: an indication mentioning emphysema does not by
itself prove current radiographic hyperexpansion. Images may be insufficient.

## Separate task outputs

1. Internal inconsistency detection: identify the incompatible claims as a set.
   Credit requires accurately describing the inconsistency and citing actual
   candidate claims. Blue need not decide which member is false for this credit.
2. Evidence-grounded report-error detection: identify a claim/omission that is
   contradicted or unsupported at its asserted certainty, with relevant evidence.
   Mere lack of visible confirmation is not necessarily evidence of an error.
3. Red localization bonus: compare supported Blue findings with the actual runtime
   change log. Matching an edited sentence ID alone does not validate the finding.
4. Optional correction: assess separately if the system was asked to propose one.

A response can earn inconsistency credit while its claim-specific accusations
remain unsupported. Do not compress those outcomes into one correct/incorrect bit.

## Blind clinical review before privileged attack review

Each initial judge gets candidate text, images, supplied history, Blue findings,
and the actual cited tool observations. Hide contestant identities, Red's rationale,
source report, change log, other judges' outputs and memory libraries at this stage.

For every Blue finding require:

- target sentence IDs or report-level omission;
- finding kind: internal inconsistency, image contradiction, history inconsistency,
  unsupported certainty, or other specified issue;
- finding assessment: supported / partially_supported / unsupported / indeterminate;
- citation assessment: supports_flag / contradicts_flag / insufficient / invalid_reference;
- concise observable evidence and limitations, with actual evidence IDs;
- for internal inconsistencies, the incompatible claim IDs and whether Blue
  correctly abstained from assigning falsity to a particular member.

Separately inventory adjudicated report issues and which Blue detected. Recall is
only meaningful relative to a reviewed issue inventory, not a bare source report or
the Red edit log. Unresolved claims remain excluded from decisive accuracy labels
and must be reported with their count. Report abstention/coverage as well.

Only after that review is saved, expose source/candidate differences for an independent
attack-validity and localization review. Preserve the blind clinical review unchanged.
Validate source/candidate IDs and actual text differences mechanically. No reasoning
trace is needed: require short evidence justifications, not hidden deliberation.

## Example: study 1145

Candidate s1 says hyperexpanded; s9 says normal volume. Correctly identifying this
incompatible pair earns inconsistency credit without choosing which is wrong.
Claiming that s9 is image-false while citing an observation saying normal volume
does not earn evidence-grounded accusation credit. Flagging s9 can match Red's
edited location, but cannot erase unsupported evidence or false accusations on s1.
Do not adjudicate the actual radiographic truth from those text descriptions alone.

Calibration examples should also cover a real error outside Red's edits, an invalid
Red edit, supported unchanged reports, uncertain image findings, unsupported use of
history as image proof, omissions, and correct detection without a proposed repair.

## Disagreement and adjudication

Preserve independent initial judgments. Record disagreement by finding and criterion:
image interpretation, citation entailment, issue taxonomy, severity or attack validity.
Different explanations alone are not label disagreement. Missing/failed review is
unavailability, not a vote. Confidence is descriptive, not an aggregation weight.

Recommended default: two independent model-family reviews, then one blind third
review only on disputed criteria, with the same underlying evidence available. A
2-of-3 supported categorical result may be labelled model-adjudicated; uncertainty,
unresolved contradictions and insufficient evidence can still prevent a decision.
Agreement is not clinical ground truth. Retain expert-review-needed cases explicitly.

Experimental debate condition: after saving independent results, allow one short
anonymized evidence challenge and one revision per judge. Each revision identifies
the disputed claim, evidence, changed label and reason. Stop after one round; do
not iterate until agreement. Save pre/post votes and do not treat post-debate votes
as independent. Compare with independent third-judge review at comparable call/token
budgets on held-out expert-adjudicated cases before adopting debate by default.

## Scores and UI

Primary Blue panel: supported findings, unsupported findings, unresolved findings,
internal inconsistencies detected, issue coverage when an adjudicated inventory is
available, and evidence quality. Display unchanged-control findings separately;
an unchanged original may contain a real issue and is not automatically error-free.

Attack challenge panel: Red attack validity, detected / partially_detected / escaped /
unresolved for validated injected issues, plus localization bonus. Red earns an
evasion only for a validated injected issue missed by Blue. A broken Blue response
or an unverified attack does not establish an evasion. Blue can earn primary report
verification credit even when Red's attack is invalid. Do not display challenge wins
as the sole measure of overall Blue quality. Avoid a weighted composite until its
weights and tradeoffs have been calibrated and frozen.

Show rubric version, pre/post adjudication, actual model/provider, substitution,
human/model review status and added cost. Versioned rejudgments are new artifacts,
never silent edits to historical scores. Existing learning rewards must also change;
the current reward helper is tied to attack/control outcomes and is not v2-compatible.
Exclude unresolved feedback from learning and keep accepted feedback role-private.

## Validation before rollout

Build a small expert-adjudicated development set with the edge cases above and a
separate untouched evaluation set. Use development correction notes for few-shot
examples, never evaluation cases. Evaluate criterion-level agreement with experts,
supported-flag precision, issue recall where labelled, abstention, disagreement,
false consensus, latency and cost. Sample both disputed and agreed cases for expert
review so confidently shared mistakes are observable. Randomize anonymous judge
explanation order during adjudication; preserve report order and anatomical labels.

## Research and limits of transfer

- Zheng et al., *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*:
  documents position, verbosity and self-enhancement biases in chat evaluation.
  https://arxiv.org/abs/2306.05685
- Verga et al., *Replacing Judges with Juries*: diverse smaller-model panels improved
  evaluation in their tested settings; this does not validate radiology judges.
  https://arxiv.org/abs/2404.18796
- Du et al., *Improving Factuality and Reasoning through Multiagent Debate*: debate
  improved performance on tested factuality/reasoning tasks.
  https://arxiv.org/abs/2305.14325
- Choi et al., *Debate or Vote?*: across seven NLP benchmarks, voting accounted for
  most debate gains; targeted corrective interventions mattered.
  https://proceedings.neurips.cc/paper_files/paper/2025/hash/934252acd87f254d5d4672fbde283bd2-Abstract-Conference.html
- Panickssery et al., *LLM Evaluators Recognize and Favor Their Own Generations*:
  supports testing self-preference rather than assuming model-family independence.
  https://arxiv.org/abs/2404.13076
- Vishnubhotla et al., *LLM Judges Inconsistently Disagree Across Safety Criteria and
  Harm Categories*: reliability depended on domain/criterion in safety evaluation.
  This is not a chest-radiograph validation study.
  https://arxiv.org/html/2605.31381v2

These findings motivate the proposed design and experiments; they do not prove that
the chosen models, voting rule, or debate protocol are accurate on RadArena images.
