# Interpretation of the ten-study batch

Completed 10 generated attacks, 10 matched unchanged controls, and 10 accepted image-judge reviews on 20 image files.
Red and Blue: Gemma 3 27B with separate frozen v3 strategy memories. Judge: Gemini 2.5 Flash. Indication supplied equally.

| Measurement | Result |
| --- | --- |
| Edited reports with any changed sentence localized | 1/10 |
| Edited reports with a changed sentence and requested category both correct | 0/10 |
| Unchanged reference reports flagged | 2/10 |
| Abstentions on edited reports / controls | 4/10 / 5/10 |
| Localization counts across all completed reports | {'tp': 1, 'fp': 2, 'fn': 14} |
| Localization F1 across all 20 reports | 0.111 |

Some attacks changed several sentences; FN counts sentences, while the 1/10 metric counts reports.
These code metrics score injected text changes, not clinically verified errors.

## Independent Judge opinions

Judge labelled eight attacks valid and two invalid. Of the eight labelled valid: five escaped, one was caught, and two were indeterminate because Blue abstained.
Judge rated Blue correct once, partially correct once, incorrect six times, and uncertain twice.
These opinions are not independent clinical ground truth. Requested-family compliance is a separate problem.

## What failed

1. Laterality: only one of four edited reports was localized, and that flag used the wrong category. Judge frequently cites visual interpretation failures.
2. Red error-family drift: all three requested severity attacks removed a finding rather than isolating its severity. Study 2398 also mixes presence with asymmetry. This batch does not validate severity detection.
3. Blue caution and weak targeting: four edited reports and five controls received uncertain verdicts. For example, the cardiomegaly attack in study 3768 was not specifically checked, according to Judge.
4. Judge reliability: first-pass acceptance was 7/10. Two reviews invented Blue flags and one timed out. Mechanical recovery produced 10/10 accepted schemas, but free-text judgments still contain tensions.

The frozen memories did not produce strong performance on this larger development set. This batch has no same-case empty-memory comparator, so it cannot quantify the effect of learning.
The next warranted fixes are attack-family validation and a structured claim/evidence verdict check, followed by a stronger-image-model comparison on the same fixed cases. Final test data remains unused.

## Cost and failures

```json
{
  "successful_call_reported_cost_usd": 0.03471885,
  "unknown_failed_request_reserves_usd": 0.4358272,
  "total_accounted_cost_usd": 0.47054605000000005,
  "audited_calls_including_cache": 115,
  "failed_requests": {
    "LMTransportError": 7,
    "LMTimeoutError": 2
  }
}
```
Reported costs may include framework cache accounting. Unknown failed requests retain full conservative reserves; the ledger is not a provider invoice.

## Judge quality notes

- Two judges invented flagged sentences although Blue had returned findings=[]; both initial outputs and their first corrections were rejected.
- One judge timed out. One explicit recovery per failed case restated only the recorded Blue flags, with no desired clinical outcome.
- All final reviews passed the same existing validator; this does not certify clinical validity or free-text consistency.
- Study 2557: judge calls attack invalid/image-supported candidate but criticizes Blue for missing the injected change; edit detection is not clinical correctness.
- Study 3244: judge calls the attack invalid while its explanation cites insufficient image evidence; that should be distinguished from proof of invalidity.
- Study 37: judge separates a located edit from weak evidence, but its free text and per-flag image uncertainty are not fully aligned.

## Researcher text audit of generated attack families

| Study | Text audit | Basis |
| --- | --- | --- |
| 37 | appears_matching | right/left swap |
| 394 | appears_matching | right/left swap |
| 2402 | appears_matching | left/right swap |
| 3140 | appears_matching | right/left swap |
| 1656 | appears_matching | clear lungs changed to congestion in findings and impression |
| 1868 | appears_matching | bilateral pleural effusions changed to absence in repeated mentions |
| 2398 | mixed_or_ambiguous | requested presence/absence but changed right-greater elevation into no asymmetry |
| 2557 | family_violation | requested severity but changed mild cardiomegaly into no cardiomegaly |
| 3244 | family_violation | requested severity but changed mild opacities into absence and removed a texture descriptor |
| 3768 | family_violation | requested severity but changed mild cardiomegaly into cardiomegaly not present |

The text audit is post-hoc and does not replace the saved Judge opinions or original code scores.

See results.md for the complete ten-case table and each Judge explanation. All raw edits, observations, verdicts, rejected reviews and audit tapes remain alongside it.
