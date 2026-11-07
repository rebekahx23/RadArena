# Evaluation results

Split: dev. Complete: False.
Scope: source-report-relative synthetic edits; clinical validity unreviewed.

| Variant | Completed / expected | Detection F1 | Localization F1 | Control FPR | Abstention |
| --- | --- | --- | --- | --- | --- |
| text_only | 5 / 6 | 0.000 | 0.000 | 0.000 | 0.000 |
| direct_vlm | 6 / 6 | 0.400 | 0.400 | 0.333 | 0.000 |
| blue_tools | 6 / 6 | 0.750 | 0.462 | 0.667 | 0.000 |

F1 and FPR use completed verdicts; strict accuracy and completion rate in summary.json also account for missing/failed cases.
Controls are unchanged source reports, not adjudicated error-free clinical reports.
No clinical or co-evolution conclusion follows from this synthetic benchmark alone.
