# Public result summaries

These files summarize experiments. Source data and complete saved records are
available separately in `data/` and `runs/`.

| File | Scope |
| --- | --- |
| `online_experiment_results.json` | Text-free decisions, reviewer validity labels, costs, and source hashes for the main online experiment |
| `benchmark_inventory.json` | Dataset/benchmark counts, CSV hashes, and provenance status |
| `baseline_smoke_results.json` | Earlier small development baseline comparison |
| `radgraph_ablation_2026-11-04.json` | Separate report-graph ablation metrics and completion status |
| `stronger_model_cost_estimates_2026-11-04.json` | Dated measured usage and planning estimates, not current pricing guarantees |

Run `python3 scripts/reproduce_results.py` from the repository root to recalculate
the main table. The other summaries describe separate experiments and should not
be pooled with the online probe. Embedded status/test counts describe when each
summary was generated, rather than the current repository state.

`radgraph_smoke.json` and `memory_policy_audit_2026-11-04.json` contain report
excerpts or case-derived observations and are included as supporting evidence.
These and the complete run records retain dataset-specific attribution and terms;
see `data/LICENSE.md` and `runs/README.md`.
