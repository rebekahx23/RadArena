# Architecture and code walkthrough

RadArena is a Python research harness with a local web interface. DSPy calls hosted
models through OpenRouter, and Pydantic validates their structured outputs. The harness
manages the dataset, private annotations, experiment state, and audit records.

## Follow a verification episode

1. [`data.py`](../src/radarena/data.py) loads IU XML or CSV
   reports, matches views, and assigns deterministic study splits.
   [`clinical_context.py`](../src/radarena/clinical_context.py) supplies optional
   indication without leaking MeSH/Problems labels.
2. [`agents.py`](../src/radarena/agents.py) creates candidates through
   controlled sentence edits. [`open_online.py`](../src/radarena/open_online.py)
   also supports open report rewrites, additions, and omissions, with a
   private change-provenance log. Images stay fixed.
3. Blue verifies the candidate by planning focused questions, running bounded image
   inspections, and returning a structured verdict. Validation checks decision
   consistency, real sentence identifiers, and evidence references. These checks
   establish output provenance, not the correctness of an image observation.
4. [`judge.py`](../src/radarena/judge.py) and the
   open-ended review signatures assess source/candidate differences, attack
   validity, and Blue's actual behavior. Reviewers have privileged information
   withheld from Blue. [`outcomes.py`](../src/radarena/outcomes.py) keeps invalid,
   uncertain, and disputed results separate from competitive wins.
5. [`tracing.py`](../src/radarena/tracing.py) saves explicit
   inputs/outputs, usage, failures, and cost reserves.
   [`viewer.py`](../src/radarena/viewer.py) serves the local researcher UI.

## What each role can see

| Role | Supplied case information |
| --- | --- |
| Red | Source report, images, its own strategy memory, enabled reference context |
| Blue | Candidate report, its own strategy memory, enabled indication/reference context, image-tool observations |
| Image tool | Images and a focused question |
| Reviewers | Source, candidate, images, change provenance, and Blue's actual outputs |
| Researcher/controller | Full records, private labels, checkpoints, and audit logs |

The controller builds each model's arguments and withholds the full private episode
record from Blue. Models have no general shell or arbitrary filesystem tools.
Application code separates the roles within one trusted process; there are no isolated
operating-system identities.

## Three execution paths

### Frozen synthetic benchmark

[`benchmark.py`](../src/radarena/benchmark.py) generates deterministic presence/absence, laterality, and severity
edits paired with unchanged controls. [`evaluate.py`](../src/radarena/evaluate.py) compares `text_only`,
`direct_vlm`, and `blue_tools`. It computes report detection, sentence
localization, control flags, coverage, category recall, and paired study-bootstrap
comparisons.

Known textual edits are not medically validated contradictions. Selected exact
report/image duplicates are excluded; study splits do not establish patient-level
independence or eliminate near duplicates.

### Strategy-memory research

[`learning.py`](../src/radarena/learning.py) implements the earlier pilot; [`memory.py`](../src/radarena/memory.py) manages role-bound
checkpoints. [`open_online.py`](../src/radarena/open_online.py) orchestrates open attacks, controls, reviews, blockwise
adaptation, and frozen-checkpoint probes.

The main historical experiment used an earlier policy. The current [`memory_policy.py`](../src/radarena/memory_policy.py)
adds explicit rewards, conflict review, quarantine, and paired performance gates. Its
live benefit has not been established. The current research runner also requires the
included starting memories and calibration records; it differs from the interactive
quickstart.

### Interactive Live Arena

[`live.py`](../src/radarena/live.py) validates bounded launch options and manages sessions.
[`live_runner.py`](../src/radarena/live_runner.py) runs new paid experiments, retries, reviewer panels, and optional
memory updates. [`viewer_experiments.py`](../src/radarena/viewer_experiments.py) adapts saved experiment layouts for the UI. The
browser code lives in [`viewer_static/`](../src/radarena/viewer_static/).

Historical replay reads saved records; starting a live session makes new provider
requests. The server binds to localhost and exposes researcher information. It has no
deployed multi-user clinical interface. Its panel aggregation and memory updates use
different rules from the historical experiment and research gates.

## Optional context and evidence components

- [`knowledge.py`](../src/radarena/knowledge.py): shared reporting reference cards.
- [`handbook.py`](../src/radarena/handbook.py): role-routed, bounded chapter retrieval.
- [`report_graph.py`](../src/radarena/report_graph.py): local RadGraph text extraction.
- [`structured_blue.py`](../src/radarena/structured_blue.py): explicit evidence-ledger
  verification for the controlled pipeline.
- [`attack_validation.py`](../src/radarena/attack_validation.py): stricter checks on
  controlled semantic edits.

Reference notes and text-extracted claims are not image evidence. The central historical
online experiment used the reporting pack, not RadGraph or the handbook selector. Those
components have separate pilot protocols.

## Configuration, evidence, and tests

[`runtime.py`](../src/radarena/runtime.py) reads local configuration and builds model adapters.
[`cli.py`](../src/radarena/cli.py) exposes the supported commands. The lockfile captures dependencies;
provider model behavior can still vary.

Public `reports/` summaries let readers inspect results without dataset text.
`scripts/reproduce_results.py` recalculates the main table from saved decisions. It makes no new
predictions and does not establish clinical validity. Readers can also inspect the
included historical records and check their hashes.

Offline tests exercise input boundaries, checkpoint ownership, verdict validation,
budget accounting, outcomes, and UI/server behavior using fixtures and scripted model
responses. They establish software behavior, not clinical performance.
