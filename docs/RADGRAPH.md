# Structured report claims with RadGraph

RadGraph is now an optional local preprocessing step. It operates on the text in
Findings and Impression; it does not replace those sections or read the X-ray.
Keep the original sentences and IDs, and attach the extracted graph to each sentence.
The first completed verifier pilot did not use RadGraph and its scores are unchanged.

## Installed and tested

The official `radgraph==0.1.18` package and its `radgraph-xl` checkpoint run on CPU in
the project environment. Installation is optional to keep the base application small:

```bash
uv sync --extra radgraph
```

The first model initialization downloads the checkpoint/tokenizer; the configured
cache is under `.cache/`, excluded from Git. Cached inference makes no OpenRouter calls.
The checkpoint and archive occupy about 857 MB locally. This is a local pretrained
extractor, not fine-tuning. Transformers is constrained below version 5 for this setup.

Official source and annotation format:
[Stanford-AIMI RadGraph](https://github.com/Stanford-AIMI/radgraph).
The original method is Jain et al. (2021), *RadGraph: Extracting Clinical Entities
and Relations from Radiology Reports*. The XL model is Delbrouck et al. (2024),
[*RadGraph-XL*](https://aclanthology.org/2024.findings-acl.765/).

## Representation and boundaries

Each extracted sentence retains its exact original text, section prefix, sentence ID,
the prefix-stripped extraction input, and raw RadGraph output. Compact claims expose
the observation, present/absent/uncertain label, anatomy, modifying terms, and relations.
Unknown labels stay unknown. Anatomy modifiers such as side are reconstructed from
actual graph edges; the adapter does not invent missing edges or normalize synonyms.
Raw token spans and entity IDs remain available for auditing.

Extraction now processes the complete report in one RadGraph call, preserving Findings
and Impression headings. Global token spans are mapped back to sentence IDs afterward;
predicted cross-sentence relations retain both endpoints. Sentence IDs are citation and
scoring addresses, not independent verification tasks. The LLMs already received the
whole ordered report together before this change. Fragments, de-identification
placeholders, abbreviations, and model errors can still lose meaning. No empty graph
is treated as a normal image/report. Alignment failures stop rather than silently
assigning an entity to the wrong sentence; raw graphs and mapping warnings are retained.
Results are cached by model fingerprint and exact extraction input. Provenance records
the package version and SHA-256 of model/config/vocabulary files. Raw model status labels
are preserved even when they appear wrong; the adapter does not silently correct them.

For evaluation, a graph store looks up only the exact candidate's text hash. Blue sees
that candidate's compact claims, never the source graph, edit metadata, other stored
reports, or a source/candidate graph difference. The image inspector still receives
only the image and a question. Direct and text-only baselines receive the same optional
claim representation. A text-derived graph cannot count as independent image evidence.

For `demo --radgraph`, Red receives extraction from its permitted source sentences;
Blue receives a fresh extraction from the edited candidate. The researcher trace saves
both separately. This is controller-supplied context, not an unrestricted graph-database
or filesystem tool exposed to the agents.

## Extract and inspect the six development candidates

```bash
HF_HOME=.cache/huggingface XDG_CACHE_HOME=.cache \
uv run --extra radgraph radarena extract-graphs --split dev \
  --study-ids 1094 1106 2036 --output data/processed/radgraph-dev-smoke-v2-full-report.json
```

The output is immutable by default: use a new filename for another extraction version.
This actual command has completed for all six candidates. The artifact contains no
benchmark private labels. The extraction audit in `runs/radgraph-extraction-smoke.md`
compares known edited sentences for the researcher; that comparison is not sent to Blue.
The original v1 artifact used sentence-level extraction and remains preserved. The v2
artifact was regenerated with whole-report input; all six report-to-sentence mappings
were verified and the three spot-check outcomes below remained the same. This change
does not alter the previously reported verifier scores.

Observed checks on the three edited claims:

| Edit | Actual extracted distinction |
| --- | --- |
| Study 1094, s4: left to right | Density location changed from `Left lower lobe` to `Right lower lobe` |
| Study 2036, s1: mild to severe | Cardiac observation retained the `mild` / `severe` modifier |
| Study 1106, s7: remove “No” | Failed: both `No pneumothorax.` and the fragment `pneumothorax.` were labeled absent |

These are extraction spot checks, not an estimate of general extraction accuracy.
The last result is an actual tool error and a reason to preserve the original text.
Additional local checks also labeled `There is a pneumothorax.` absent, and full-report
context did not recover the status change for study 1106. Therefore this failure cannot
be attributed only to our sentence-level split or the fragment. Raw diagnostic outputs
are in `runs/radgraph-toy-extractions.json` and `runs/radgraph-full-report-check.json`.
The numeric/period-only fragments in IU also generated an upstream single-token warning.
No clinical validity or improved verification performance is established by extraction.

## Evaluate its effect separately

Run paired development comparisons with and without `--report-graphs` using identical
code, model, reports, image tools, and references. The current signatures include a
`report_claims` input (empty when disabled), so rerun the no-graph baseline rather than
attributing a difference against the older pilot entirely to RadGraph.

```bash
RADARENA_TEXT_MODEL=google/gemma-3-27b-it \
RADARENA_VISION_MODEL=google/gemma-3-27b-it \
uv run radarena evaluate --split dev --study-ids 1094 1106 2036 \
  --variants text_only direct_vlm blue_tools \
  --knowledge-file knowledge/reporting_v1.json \
  --report-graphs data/processed/radgraph-dev-smoke-v2-full-report.json \
  --max-cost 0.10 --output runs/dev-with-radgraph
```

This evaluation command incurs paid model calls. A paired six-report comparison has
now run; see [the November 4 results](RADGRAPH_ABLATION_2026-11-04.md). Blue's localization
F1 fell from 0.50 to 0.46 as extra flags increased; this does not establish a benefit.
Use a second new output directory without `--report-graphs` for a paired baseline. Both conditions
record implementation and extraction artifact hashes. Missing/mismatched candidate
graphs fail before any model calls. Predictions and ordered prompts log the supplied
claims. Measure false alarms and evidence quality as well as sentence F1.

An optional generative demo is `radarena demo --radgraph --study-id 113 --error-type
laterality --knowledge-file knowledge/reporting_v1.json --max-cost 0.02 --output
runs/demo-radgraph.json` with the same model/cache environment. This modified demo path
is covered by input-routing logic; no new paid RadGraph-conditioned demo has been run.

Graph-based source/reference scoring, vocabulary normalization, full-report graph
alignment, automatic contradiction classification, and corrections are not implemented.
F1-RadGraph is a report-to-report similarity measure, not proof that an image supports
a report. Keep private reference scoring separate from Blue's available evidence.
