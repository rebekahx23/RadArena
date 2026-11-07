# Whole-report RadGraph comparison: November 4, 2026

The rerun did not establish a benefit from RadGraph for Blue. It increased edited-
sentence recall, but also increased extra flags and control false alarms. This is a
three-study development behavior test, not held-out or clinical validation.

## Fixed comparison

Both conditions used the same six candidate reports from studies 1094, 1106, and 2036,
Gemma 3 27B for text and vision, temperature 0, 2,048 output tokens per call, the same
reporting reference pack, the same images, and identical agent code. The source,
reference, benchmark, and graph hashes were saved before completions. The only input
intervention was optional candidate-text RadGraph context. Reports were supplied whole
in both conditions. No handbook selection or learning loop was used. The proposed
three-way claim assessor remains unimplemented and was not tested here.

This fresh baseline is necessary because the current signatures include a new
`report_claims` input. Comparing directly against the older pilot would confound that
prompt-format change with graph content. No test-split evaluation was performed.

| Method | Localization F1 without / with RadGraph | Control false alarms without / with | Successful episodes without / with |
| --- | --- | --- | --- |
| Text-only | 0.50 / not comparable | 0/3 / not comparable | 6/6 / 5/6 |
| Direct image verification | 0.33 / 0.40 | 1/3 / 1/3 | 6/6 / 6/6 |
| Blue with image tools | 0.50 / 0.46 | 1/3 / 2/3 | 6/6 / 6/6 |

Text-only with RadGraph failed citation validation on the pneumothorax attack: it
returned an error finding with an empty evidence-source list. This failed output is
retained, not repaired or replaced. Its completed-only F1 is not used to claim an
effect. Across conditions, 35/36 episodes completed successfully; every direct-image
and Blue episode completed, permitting their paired descriptive comparisons.

## What changed in Blue

| Synthetic sentence-localization count | Without RadGraph | With RadGraph |
| --- | ---: | ---: |
| Edited sentences flagged | 2/3 | 3/3 |
| Additional sentence flags | 3 | 7 |
| Edited sentences missed | 1 | 0 |
| Category-correct laterality hits | 0/1 | 0/1 |
| Category-correct severity hits | 0/1 | 1/1 |
| Category-correct presence/absence hits | 1/1 | 1/1 |

Finding all three sentence IDs does not establish that the model identified all three
errors correctly. The laterality edit was still classified as presence/absence. The
severity hit cited an image observation that could not confidently grade severity.
The resulting report-level detection F1 increased from 0.67 to 0.75, while sentence-
level localization F1 decreased because of additional flags. Report both rather than
selecting whichever metric looks favorable.

Trace checks show the original reasoning problem persists. On unchanged study 1094,
Blue flagged the left-lower-lobe density sentence while citing an observation of
left-lower-lobe opacity. It also flagged negative consolidation claims using uncertain
or broadly agreeing observations. On unchanged study 1106, it treated inability to
characterize a subtle opacity confidently as a contradiction of a subtle-density claim.
These are reasoning-consistency observations, not radiologist adjudications of the X-rays.

The graph's known pneumothorax extraction error was left unchanged in the experiment;
both text polarities were extracted as absent. Original text remained available. Blue
flagged the edited sentence, but its image observation was itself equivocal. Thus that
localization hit does not establish reliable visual grounding or a clinically valid
contradiction.

## Execution, continuation, and spending

One baseline request encountered an upstream 524 timeout; one graph request encountered
a client timeout. Each condition was explicitly resumed once, preserving request
failures and reusing completed records/cache. Later, the graph text-only validation
failure stopped the original harness before the final two image-based episodes.
`scripts/resume_evaluation.py` ran only those unattempted episodes with the frozen agent
configuration and existing budget. It did not retry the failed text prediction. This
continuation and its script hash are recorded in `continuation_note.json`.

The cap was $0.05 per condition, $0.10 combined. Observed OpenRouter key usage increased
by **$0.01240304** (about 1.24 cents). A key-level delta can include unrelated concurrent
activity and excludes credit-purchase fees. Conservative local accounting totaled
about $0.04125, including retained full reserves for unknown-cost timeout requests;
those reserves are not observed charges. Cached calls can repeat framework cost
metadata and shorten latency, so this run is not a fresh cost/latency comparison.

All 55 software tests passed before paid execution. The same implementation hash was
verified across both conditions. No clinical review or independent replications have
been completed, and these cases have already been inspected during development.

## Inspect and decide the next step

The local artifact root is `runs/radgraph-ablation-2026-11-04/`:

- `comparison.md` and `comparison.json`: matched metrics and case-level changes.
- `no_radgraph/walkthrough.md` and `with_radgraph/walkthrough.md`: reports, graph
  context where enabled, image links, questions, observations, and verdicts.
- Each condition's `audit/trace.md` and `audit/calls.jsonl`: ordered explicit prompts
  and responses, usage, and failures. These do not expose hidden internal reasoning.
- `plan.json`, `preflight.json`, `billing.json`, and `continuation_note.json`: setup,
  bounds, observed provider usage, and preserved protocol amendments.

The next intervention should target the evidence-to-verdict step: explicitly classify
checked claims as supported, contradicted, or insufficient evidence, then derive the
verdict from those judgments. Test that step using reviewed observations before
spending on a larger grid or attributing the failures entirely to the vision model.
Keep clinical attack/evidence review separate from software scoring. Do not expand
to the held-out test set based on this tiny rerun alone.
