# Role-private learning pilot

| Checkpoint | Blue localization F1 | Control FPR |
| --- | --- | --- |
| Before | 0.333 | 0.333 |
| After | 0.500 | 0.000 |

Red probe against a fixed baseline Blue:
```json
{
  "before": {
    "attack_status": "syntactically_valid_clinically_unreviewed",
    "syntactic_edit_escaped_localization": true,
    "blue_decision": "no_error_detected",
    "score": {
      "localization_tp": 0,
      "localization_fp": 0,
      "localization_fn": 1,
      "uncertain": false,
      "injected_edit_detected": false,
      "unchanged_control_flagged": null,
      "ground_truth_scope": "synthetic edits; image support not adjudicated"
    }
  },
  "after": {
    "attack_status": "syntactically_valid_clinically_unreviewed",
    "syntactic_edit_escaped_localization": true,
    "blue_decision": "no_error_detected",
    "score": {
      "localization_tp": 0,
      "localization_fp": 0,
      "localization_fn": 1,
      "uncertain": false,
      "injected_edit_detected": false,
      "unchanged_control_flagged": null,
      "ground_truth_scope": "synthetic edits; image support not adjudicated"
    }
  }
}
```

Audit accounting: $0.038785; 95 audited calls (includes cache and unknown-cost reserves).

Three dev studies, one Red probe; no statistical improvement claim.
Development studies disjoint from this run training studies, not untouched final test.
Attack image validity and requested semantic-family compliance not independently adjudicated.
Strategy adaptation, no weight updates; models have no filesystem access or shared chat history.
