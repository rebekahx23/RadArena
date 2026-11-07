# First live development pilot

November 3, 2026. This is a behavior/debugging report, not held-out evidence of clinical
accuracy or a positive result for tool-based verification. No more model calls are
needed to inspect these artifacts.

## What actually ran

The frozen selection rule took the lexicographically first development study in each
error category: 1094 (laterality), 1106 (presence/absence), and 2036 (severity). Each
contributed an unchanged control and a synthetic corruption. All three verifier
methods completed all six candidates: **18/18 episodes**. The final core run used
`google/gemma-3-27b-it`, temperature 0, 2,048 output tokens per call, JSONAdapter, and
the same nine-card reporting pack. Blue had up to three image checks and no learned
strategies. The test split was not evaluated.

| Method | Localization F1 | Detection F1 | False alarms / 3 controls | LM calls | Recorded cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Text-only | 0.333 | 0.667 | 1/3 | 6 | $0.000807 |
| Direct image verification | 0.571 | 0.571 | 2/3 | 6 | $0.001041 |
| Blue with image tools | 0.444 | 0.571 | 2/3 | 30 | $0.003376 |

Every arm had zero abstentions. Three studies cannot establish a general performance
difference; per-category denominators are only one attack. Blue did not outperform
the direct baseline on this sample and used five times as many model calls. A matched
sentence ID can still earn synthetic localization credit with incorrect reasoning.
No attack validity or image observations have been adjudicated by a radiologist.

A separate training-study demo (113) completed a genuine model-generated Red attack:
Red changed a nodule claim from right to left. Blue flagged the edited sentence but
called it a presence/absence error and also flagged an unchanged sentence. Its cited
evidence needs review. This demonstrates execution, not reliable clinical judgment
or successful adversarial learning.

## Failures worth tracing

- **Supported statement marked as an error.** On unchanged study 1106, direct image
  verification flagged s3 while its evidence repeated the report's density finding.
  On the training demo, Blue flagged s5 while citing the absence of a large effusion
  or pneumothorax, which does not contradict the negative report claim.
- **Uncertainty became a definite accusation.** On the same unchanged study 1106,
  Blue flagged "No effusions" using a tool observation of *possible* small effusion.
  That is insufficient to establish a definite contradiction without image review.
- **A synthetic hit without visual verification.** Text-only flagged the injected
  pneumothorax sentence while acknowledging it could not determine presence without
  images. Localization credit here does not establish understanding or grounding.
- **Reference selection was not reliable.** Earlier handbook attempts returned seven
  chapters or invented an unlisted `pneumonia.md` chapter. The reader rejected them.
  A clarified instruction alone did not solve path selection. The completed core run
  therefore used the fixed pack, not the handbook. No handbook benefit is claimed.
- **Deployment and output failures.** Qwen's shared upstream pool returned rate-limit
  errors. An earlier Gemma run returned "uncertain" with nonempty error findings and
  was rejected. These attempts are preserved separately; no failed verdict is scored
  as a clean report. JSON output and explicit contracts improved execution reliability
  in the final core run, but did not resolve evidence quality.

## The next validation step

Before spending on the full grid, review these six candidates and their image evidence.
Use a qualified reader where possible to establish whether each intended edit is
image-supported, clinically meaningful, and unambiguous. Check de-identification
placeholders and sentence fragments in the input reports; do not silently remove
difficult cases after seeing which system failed.

Add a small image-grounding control: on a predeclared subset, compare matched images
with deliberately mismatched images or an image-withheld condition. Treat mismatched
images as an ablation, not as gold diagnostic cases. Ask whether observations and
verdicts respond to the visual evidence rather than merely repeating candidate claims.
The existing text-only arm is necessary but does not establish image use by itself.

Separately audit whether each flagged sentence is actually contradicted by the cited
observation: unsupported/agrees, ambiguous/partial, or explicit contradiction. This
is a reasoning-consistency rating, not a substitute for clinical image review. Report
evidence quality alongside F1. A model judge may help triage, but should not be the sole
ground truth or judge its own outputs.

Then choose a reliable configuration on the 20-study development set, freeze it, and
run the 30-study test comparison once. If the same failures dominate, calibrate a
stronger image-capable model on development data before adding memory learning.
Prioritize controlled comparisons over a broad model or tool sweep. Null results
and trace-supported failure analysis remain useful research outcomes.

## Artifacts and spending

Included historical outputs:

- `runs/midpoint-dev-smoke-core-v1/walkthrough.md`: reports, image links, all method
  verdicts, and Blue's questions/observations, grouped by case.
- `runs/midpoint-dev-smoke-core-v1/audit/trace.md`: ordered prompts and explicit
  model responses, including model settings and usage. `calls.jsonl` is the data form.
- `runs/midpoint-red-blue-demo.json` and `runs/midpoint-red-blue-demo.audit/trace.md`:
  model-generated training attack, Red's explicit explanation, and Blue's actions.
- `runs/midpoint-dev-smoke-v1`, `-v2`, `-gemma-v1`, and `-gemma-v2`:
  preserved unsuccessful attempts and their audit ledgers.
- `runs/midpoint-pilot-billing.json`: provider key-level usage observation.

OpenRouter key usage increased from $0.68575943 before these runs to $0.69301321
afterwards: **$0.00725378**, about 0.73 cents. This key-level delta could include
concurrent account activity; it is not a credit-purchase receipt. Framework cost
sums may include cached response costs. The local ledgers conservatively retain
about $0.266 in reserves for two unknown-cost rate-limit failures; these are not
observed charges. Total accounted cost across all pilot ledgers remained below $0.50.
No account limits were changed or credits purchased.

All **42 software tests passed**. A local scan of the generated run files found no
copy of the configured key and no inline image payloads. Software tests and audit
checks do not establish medical correctness. Traces are researcher-only and expose
explicit explanations/actions, not hidden model reasoning.

The shareable aggregate is `reports/baseline_smoke_results.json`.

After this pilot, optional local RadGraph-XL extraction was installed and tested on
the six candidates. It preserved the side and severity edits but missed the status
change in the pneumothorax fragment. See RADGRAPH.md. It was not used for the scores
above; a paired extraction ablation has not been run.
