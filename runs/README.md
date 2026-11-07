# Saved experiments

Saved experiment evidence includes prompts and explicit responses, source/candidate
reports, changes, verifier outputs, model reviews, memory checkpoints, failures, cost
ledgers, and versioned implementation snapshots. Records retain their original bytes and
names so cross-references and source-file hashes still match.

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

The viewer's Historical runs tab replays saved outputs. Download the images to
`data/raw/iu_xray/images/` first. The loader translates old absolute paths in memory and leaves
the archived JSON and JSONL files unchanged.

Researchers can inspect the full traces, but agents receive only their permitted inputs.
Role-private information is withheld from the opposing agent during execution and is
available here for auditing. Logs record explicit model outputs; they do not expose
hidden internal reasoning. Reviewer consensus does not establish clinical accuracy.

Archived Python snapshots preserve historical implementations. Some retain their
original filesystem paths and need an isolated reconstruction to run. Use the current
CLI for supported commands. Resuming a historical run with changed code does not
constitute an independent replication.

Dataset-derived content retains its source attribution and applicable terms; see
[the dataset notice](../data/LICENSE.md). Modified report text has a distinct sharing question under the
upstream NoDerivatives condition. Credentials are excluded. A pre-release scan found no
provider-key or bearer-token patterns in these records.
