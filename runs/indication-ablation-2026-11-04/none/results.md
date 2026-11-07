# Evaluation results

Split: dev. Complete: True.
Scope: source-report-relative synthetic edits; clinical validity unreviewed.

| Variant | Completed / expected | Detection F1 | Localization F1 | Control FPR | Abstention |
| --- | --- | --- | --- | --- | --- |
| text_only | 6 / 6 | 0.667 | 0.500 | 0.333 | 0.000 |
| direct_vlm | 6 / 6 | 0.667 | 0.667 | 0.333 | 0.333 |
| blue_tools | 6 / 6 | 0.800 | 0.571 | 0.000 | 0.333 |

F1 and FPR use completed verdicts; strict accuracy and completion rate in summary.json also account for missing/failed cases.
Controls are unchanged source reports, not adjudicated error-free clinical reports.
No clinical or co-evolution conclusion follows from this synthetic benchmark alone.
