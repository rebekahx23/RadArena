# Independent post-hoc judge

`radarena judge --run runs/midpoint-red-blue-demo.json --max-cost .50` uses a fresh Gemini 2.5 Flash client to review Red's edit, Blue's
verdict, observations and images. Evaluation directories also require `--case-id`
and `--variant`. The judge gets privileged source/edit information; neither
contestant receives the judge packet or its review. Existing output is preserved.
`--evidence-only` omits images and cannot certify an attack as image-valid.

The local viewer's Judge review workspace displays independent assessments, per-flag
citation checks, concise explanations, limitations and call cost. Code grading remains
separate. Model judgments can be wrong and need clinical validation. Review
disagreements and consistency warnings. The judge can contradict itself in free text even
when schema and mechanical checks pass.

Reviews include attack validity, image support, Blue correctness, error categories and
localization, citation fidelity, uncertainty and failure modes. The validator checks
referenced sentence/tool IDs and some structured consistency requirements; one
correction request is allowed for mechanical violations. All attempts, usage and failed
requests remain in the audit tape. The logs do not expose hidden model reasoning.
Reviews use the clinical indication recorded as available to Blue. The judge fetches no
new history.

The original demonstration's current judge-v2 result assessed Blue as partially correct,
with one supported report statement incorrectly flagged. A prior, inconsistent judge-v1
response is archived separately and is not the accepted current assessment. Two real
judge requests across those versions have combined reported/accounted cost $0.0044966.
These are model judgments of one case, not a validated evaluation of clinical
correctness or judge reliability.
