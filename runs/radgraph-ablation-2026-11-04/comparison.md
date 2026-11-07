# Whole-report RadGraph development comparison

Both conditions complete: **False**. Same six reports, model, code, references, and image tools.
Only the candidate-text graph context changes. All reports are supplied whole; sentence IDs locate outputs.

| Method | Localization F1, without → with | Control FPR, without → with | Abstention, without → with | Completed, without / with |
| --- | --- | --- | --- | --- |
| text_only | 0.500 → incomplete | 0.000 → incomplete | 0.000 → incomplete | 6/6 / 5/6 |
| direct_vlm | 0.333 → 0.400 | 0.333 → 0.333 | 0.500 → 0.000 | 6/6 / 6/6 |
| blue_tools | 0.500 → 0.462 | 0.333 → 0.667 | 0.167 → 0.000 | 6/6 / 6/6 |

Counts and category metrics are in comparison.json. Only variants with all six verdicts in both conditions can support a paired descriptive comparison. No effect is claimed for an incomplete variant.
This is an exploratory development sample of three studies, with one attack per category. Graph extraction can be wrong.
No clinical accuracy or generalization claim follows from these scores. The proposed three-way claim assessor is not implemented.

[Without RadGraph walkthrough](no_radgraph/walkthrough.md) | [With RadGraph walkthrough](with_radgraph/walkthrough.md)
