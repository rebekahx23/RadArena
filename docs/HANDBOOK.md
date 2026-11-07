# RadArena radiology handbook and reference ablations

The project now has an original, role-routed handbook at `handbooks/radiology-handbook/`.
Agents start with an index, route to their active role, and open relevant chapters on
demand. The handbook combines project-authored workflows with short source-attributed
summaries. Ablations suppress workflow or medical books while holding cases and tools
fixed. Clinical source citations are retained in the chapters.

## Contents

```text
handbooks/radiology-handbook/
  SKILL.md                      short purpose and role routing
  handbook.json                 manifest, roles, chapter groups, version
  SOURCES.md                    provenance and review status
  references/
    red-team/                   role index, workflow, error families
    blue-team/                  role index, workflow, evidence handling
    reporting/                  structure, claim attributes, terminology
    medical-library/            index and five sourced reference chapters
    tools/                      index and actual tool contracts/status
```

There are 19 Markdown files, plus the manifest. The clinical appendix is a starter:
pleural effusion, pneumothorax, cardiac enlargement, X-ray technique, and systematic
review. It contains brief source-attributed summaries, not a clinical textbook,
validated image-sign library, quantitative thresholds,
or comprehensive coverage of IU findings. All chapters require qualified radiologist
review. Sources include RSNA reporting/terminology overviews, limited ACR excerpts,
NCI/NHLBI background, and Mayo Clinic's enlarged-heart diagnostic overview. Exact source
links and limitations are in the chapters and SOURCES.md. Version 0.2.0 adds selected
original summaries from the user-supplied Eze (2012) textbook, with both PDF and printed
page references. `knowledge/README.md` records the local PDF's provenance and hash.
The PDF stays local and is excluded from Git; neither full-book retrieval nor training
on the book is implemented. The existing chapter selector makes the new medical notes
available to both roles and hides them in `no_medical` and `none`.

The source registry distinguishes source-backed background from project-authored workflows.
Clinical review should verify each claim, replace ambiguous statements, add approved
visual criteria and confounders, and record reviewer/date per chapter in a new version.

## Access and lazy context loading

The application initially supplies the root index, the active role index, and a short
tool index. It supplies a catalog of available chapter paths/titles. One additional
DSPy selector call chooses at most three chapters based on the role and current report
text. The controller reads those exact authorized chapters and appends their text to
the `reference_notes` input of the agent. It does not generate a supposed reference
summary from model memory. Each read is limited to 4,000 characters and final context
to 14,000 characters. No full library is injected by default.

This is a bounded, single-step chapter-selection workflow. It is not an unrestricted
filesystem agent or a fully iterative multi-read ReAct session. The `tool_for(role)`
method also exposes a callable reader for a future tool-agent loop; that loop has not
been added. The current implementation logs the index and chapter paths actually used.

Red selection sees only Red's permitted source-report text; Blue selection sees only the
candidate report. Neither the selector nor the reader gets private evaluation labels or
Blue's inaccessible original report. The reader rejects unlisted paths, cross-role reads,
directory traversal, and symlink escapes. It exposes no write operation. This is an
application-level read-only interface, not an OS/container mount; Docker mounts remain
future work. Local developers can edit the source files, creating a different content hash.

The image-inspection call remains separate and receives only images plus its question.
Handbook content cannot establish the current image's findings. The tool reference makes
RadGraph's actual status explicit: optional local report extraction is implemented,
while image verification and graph-based private reference scoring remain separate.
See RADGRAPH.md for setup, scope, and an observed status-label extraction error.

## Four conditions

| Condition | Domain chapters | Medical chapters | Tool/index interface |
| --- | --- | --- | --- |
| full | Active role + shared reporting available | Available | Same |
| no_domain | Unavailable | Available | Same |
| no_medical | Available | Unavailable | Same |
| none | Unavailable | Unavailable | Same |

Domain chapters are the Red/Blue workflows and shared reporting book; medical chapters
are the separate medical-library book. Ablated chapters are hidden from the selector
catalog, and direct reads return an unavailable stub. No files are physically deleted.
Role permissions remain enforced even under ablation. Basic task prompts, pretrained
model knowledge, input reports/images, and tool access remain unchanged. Thus `none`
means no domain/medical handbook access, not a model with no radiology knowledge.

Inspect the interface without making model calls:

```bash
uv run radarena show-knowledge --file handbooks/radiology-handbook --role verifier
uv run radarena show-knowledge --file handbooks/radiology-handbook --role red
uv run radarena show-knowledge --file handbooks/radiology-handbook \
  --condition no_medical --chapter references/medical-library/pleural-effusion.md
```

With paired images and a configured key, run a paid Red/Blue demo:

```bash
uv run radarena demo --error-type laterality --handbook handbooks/radiology-handbook
```

Start ablations on development cases with the same case subset and settings:

```bash
uv run radarena evaluate --split dev --limit-studies 1 --variants blue_tools \
  --handbook handbooks/radiology-handbook --handbook-condition full --output runs/hb-dev-full
uv run radarena evaluate --split dev --limit-studies 1 --variants blue_tools \
  --handbook handbooks/radiology-handbook --handbook-condition no_domain --output runs/hb-dev-no-domain
uv run radarena evaluate --split dev --limit-studies 1 --variants blue_tools \
  --handbook handbooks/radiology-handbook --handbook-condition no_medical --output runs/hb-dev-no-medical
uv run radarena evaluate --split dev --limit-studies 1 --variants blue_tools \
  --handbook handbooks/radiology-handbook --handbook-condition none --output runs/hb-dev-none
```

Each command incurs model calls. The handbook adds one selector call per verifier
episode, including ablations so the nominal selection budget stays fixed. The selected
content and prompt-token count can differ; report those differences and recorded cost.
When multiple verifier variants are requested, they have the same handbook access and
selector settings. Identical DSPy requests may use cached selection results; log/cache
effects matter when comparing wall time and spend.

Run metadata includes handbook content hash, version, condition, and chapter budget.
Per-episode traces include read paths. The reader checks that chapter contents do not
change after loading. A changed book or ablation cannot silently resume the same run.

## Experimental scope

Measure whether these short references improve localization, category handling,
uncertainty, false alarms, and evidence quality on the fixed cases. Make comparisons
paired by study and retain failures/coverage. Bootstrap comparisons currently operate
between verifier variants in one run; statistical comparisons between handbook conditions
in separate runs are not yet automated. Keep clinical review and manual error analysis.

The handbook is frozen external guidance, not learned memory. Its ablation does not
establish that Red or Blue learned. Train-only strategy memory and GEPA remain separate
future interventions. The deterministic benchmark attacker does not read the handbook;
changing Red's handbook affects the model-based demo, not an already frozen benchmark.
To study Red's handbook effect, generate matched attacks separately, review their validity,
and evaluate them against a fixed Blue.

Live handbook smoke attempts failed safely: a selector exceeded the chapter limit and
another invented an unlisted chapter. The completed core pilot used the fixed JSON pack
instead. No handbook benefit has been measured. Software tests establish access
boundaries and context routing, not clinical correctness. See PILOT_FINDINGS.md.
