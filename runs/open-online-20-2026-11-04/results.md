# Open-ended 20-study online experiment

Completed episodes: 20/20. Audit accounting: $0.533898.

| Study | Attack types | Blue | Control | Judge 1 validity | Judge 2 validity |
| --- | --- | --- | --- | --- | --- |
| 1849 | omission | error | error | valid | valid |
| 2470 | fabrication | error | error | valid | valid |
| 2539 | fabrication, fabrication | no_error_detected | no_error_detected | uncertain | invalid |
| 1223 | omission | no_error_detected | no_error_detected | valid | valid |
| 2488 | omission | error | no_error_detected | valid | valid |
| 2941 | fabrication | error | no_error_detected | valid | valid |
| 2766 | fabrication | invalid_output | uncertain | valid | valid |
| 294 | omission | uncertain | error | valid | invalid |
| 886 | fabrication | error | error | valid | valid |
| 3848 | fabrication | no_error_detected | no_error_detected | valid | valid |
| 2643 | fabrication | error | no_error_detected | valid | valid |
| 120 | fabrication, fabrication | error | error | valid | invalid |
| 1556 | omission | no_error_detected | no_error_detected | valid | valid |
| 74 | fabrication | no_error_detected | error | valid | valid |
| 3830 | fabrication | error | no_error_detected | valid | valid |
| 3865 | fabrication | error | error | valid | valid |
| 1284 | omission | error | uncertain | valid | invalid |
| 1818 | fabrication | error | no_error_detected | valid | invalid |
| 22 | fabrication | error | no_error_detected | valid | valid |
| 1946 | fabrication, unlogged_text_change | error | no_error_detected | valid | valid |

```json
{
  "complete": true,
  "counts": {
    "episodes": 20,
    "eligible_text_changes": 20,
    "blue_invalid": 1,
    "control_invalid": 0,
    "blue_error": 13,
    "blue_uncertain": 1,
    "control_flags": 7,
    "control_uncertain": 2,
    "accepted_reviews": 40,
    "consensus_valid": 15,
    "valid_error": 10,
    "validity_disagreement_or_rejection": 5,
    "valid_no_error_detected": 4,
    "valid_invalid_output": 1
  },
  "categories": {
    "omission": 6,
    "fabrication": 16,
    "unlogged_text_change": 1
  },
  "rounds": {
    "1": {
      "episodes": 5,
      "attack_flags": 3,
      "control_flags": 2
    },
    "2": {
      "episodes": 5,
      "attack_flags": 2,
      "control_flags": 2
    },
    "3": {
      "episodes": 5,
      "attack_flags": 3,
      "control_flags": 2
    },
    "4": {
      "episodes": 5,
      "attack_flags": 5,
      "control_flags": 1
    }
  },
  "final_five_paired_probe": {
    "initial": {
      "reports": 5,
      "attack_flags": 4,
      "invalid_outputs": 0,
      "attack_abstentions": 1,
      "control_flags": 2,
      "control_invalid_outputs": 0
    },
    "learned": {
      "reports": 5,
      "attack_flags": 5,
      "invalid_outputs": 0,
      "attack_abstentions": 0,
      "control_flags": 1,
      "control_invalid_outputs": 0
    }
  },
  "accounted_cost_usd": 0.5338977300000007,
  "limitations": [
    "Online round changes are confounded by case mix. Only final five have paired initial-memory comparisons.",
    "Two reviewers are fallible; Flash family is shared with contestants. Consensus is not clinical truth.",
    "Open rewrites/omissions do not support the earlier injected-sentence localization F1; report-level outcomes are primary.",
    "All studies are unused training studies, not the project final test split."
  ]
}
```
