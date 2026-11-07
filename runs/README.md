# Saved experiments

This directory contains the recorded experiment evidence: prompts and explicit
responses, source/candidate reports, changes, verifier outputs, model reviews,
memory checkpoints, failures, cost ledgers, and versioned implementation snapshots.
Original records are retained byte-for-byte. Historical names remain stable so
cross-references and source-file hashes still match.

| Directory or prefix | Experiment |
| --- | --- |
| `open-online-20-2026-11-04/` | Main 20-study online experiment and matched final probe |
| `learning-pilot-2026-11-04/` | Earlier three-round strategy-memory pilot |
| `red-blue-judge-10-2026-11-04/` | Ten-study Red/Blue/reviewer batch |
| `radgraph-ablation-2026-11-04/` | Graph/no-graph comparison |
| `indication-ablation-2026-11-04/` | Optional indication comparison |
| `stronger-blue-2026-11-04/` | Model and evidence-ledger comparison |
| `midpoint-dev-smoke-*` | Earlier baseline development runs |
| `midpoint-red-blue-demo*` | Earlier recorded controlled-attack demo and review |
| `live-*` | Interactive Live Arena sessions |

## Replay and audit without model calls

```bash
uv run radarena viewer
python3 scripts/reproduce_results.py \
  --from-run runs/open-online-20-2026-11-04
```

The viewer's Historical runs tab replays saved outputs. Images require the separately downloaded
dataset under `data/raw/iu_xray/images/`. Old absolute image paths are translated
at load time; the archived JSON and JSONL files are not rewritten.

The traces are privileged researcher views, not shared agent memory. Role-private
means withheld from the opposing agent during execution, not permanently hidden
from readers auditing the experiment. Logs contain explicit model outputs rather
than hidden internal reasoning. Reviewer consensus is not clinical validation.

Archived Python snapshots document historical implementations. Do not execute a
snapshot as if it were the current supported CLI, or resume historical outputs
with changed code and describe that as an independent replication. Some snapshots
retain their original filesystem paths and require an isolated reconstruction.

Dataset-derived content retains its source attribution and applicable terms;
see [the dataset notice](../data/LICENSE.md). Modified report text has a distinct
sharing question under the upstream NoDerivatives condition. Credentials are
excluded; a pre-release credential-pattern scan found no provider key or bearer
token patterns in these records.
