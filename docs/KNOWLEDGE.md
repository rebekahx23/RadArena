# Supplying radiology knowledge to Red and Blue

There are now two supported interfaces: the original small JSON reference pack described
below, and a role-routed handbook with bounded chapter selection described in
[HANDBOOK.md](HANDBOOK.md). The handbook uses a directory index and read-only reader; the JSON
pack continues to be included in full when selected.

The implemented starting point is a small versioned reference pack supplied as explicit
DSPy input context. Both roles receive the same nine reporting cards and different role
instructions. The draft awaits radiologist review. It is separate from diagnostic
textbooks, model fine-tuning, and learned strategy memory.

## Content and sources

- ACR's Communication of Diagnostic Imaging Findings parameter: limited paraphrases
  about report components, terminology, and limitations. Official search excerpts were
  checked, but full-document retrieval returned 403; confirm the version/full text during
  review. This is not a complete review of the current parameter.
- RSNA RadReport overview: templates support consistent organization. No individual
  chest template is imported. Establish the applicable terms before copying templates
  or third-party teaching material.
- RSNA RadLex overview: common terminology. No ontology export or synonym mapping is
  bundled; those require obtaining the actual licensed resource.
- Project-authored task rules: explicit claim attributes, negation versus uncertainty,
  checking side/severity, repeated-finding consistency, and reference versus image evidence.

The pack identifies source URLs, access notes, scope, and review status. The source
links do not establish clinical approval. Clinical image-feature cards are not present
yet. Add those later with specific sources and qualified review, especially for severity
criteria.

## How agents receive the context

`KnowledgePack` loads `knowledge/reporting_v1.json`. `render("red")` and `render("verifier")`
supply the shared cards plus the relevant role instructions through a separate
`reference_notes` field in DSPy signatures. The pack is under 8,000 characters per
role, so it can be sent in full without embeddings or a vector database.

Red receives the pack alongside source report sentences, images, and a permitted error
family. It uses the conventions to preserve report style and consistency during a
synthetic edit. Blue receives the pack when planning and assessing candidate claims. The
image-inspection call sees only images and a focused question. Findings must cite actual
tool calls. General reference principles cannot establish what a particular image shows.

When knowledge is enabled, direct VLM and text-only baselines receive the same verifier
pack. The reference hash is included in experiment metadata, preventing an existing run
from silently resuming with changed reference content. No live effect has been measured.

```bash
uv run radarena show-knowledge
uv run radarena demo --error-type laterality \
  --knowledge-file knowledge/reporting_v1.json
uv run radarena evaluate --split dev --limit-studies 1 \
  --knowledge-file knowledge/reporting_v1.json --output runs/dev-smoke-knowledge
```

Without `--knowledge-file`, prior no-reference conditions remain available. In both
conditions, the image tool receives neither the report nor the reference pack.

## Growing the library

Add a few reviewed training demonstrations: authentic report wording for Red, and
image/question/observation/verdict examples for Blue. Use training studies only. DSPy
demonstrations have not been connected in this version; do not put test reports or gold
edits into reference context, demos, or a retrieval index.

As the library grows, add bounded retrieval returning a few source-labeled cards from a
public candidate query or explicit question. Log query, retrieved card IDs, index
version, and source. General text-search/vector retrieval is not implemented; the new
handbook already supports bounded selection of chapters from its directory catalog. The
user-supplied Eze (2012) textbook now contributes selected page-cited summaries to the
handbook's medical chapters: technique, systematic review, and cardiac-size limitations.
See [the source record](../knowledge/README.md). The original JSON pack is unchanged; select `--handbook handbooks/radiology-handbook`
to use those chapters. The PDF is kept local and is not ingested wholesale or used to
update model weights.

| Store | Purpose | Update policy |
| --- | --- | --- |
| Curated reference pack | General reporting and clinical principles | Version and freeze before evaluation |
| Training demonstrations | Examples of desired behavior/output | Training studies only |
| Strategy memory | Rules learned from failures | Training feedback only; freeze for evaluation |
| Private grader data | Original report, edits, expected answers | Never supplied to Blue or indexed as knowledge |

Compare the same verifier conditions without and with this fixed pack on development
data, keeping cases and settings unchanged. Track prompt-token/cost increases. Separate
this knowledge intervention from learned-memory and GEPA experiments; freeze the chosen
condition before test evaluation. More consistent reporting does not establish better
visual recognition: image-supported performance still needs reviewed cases.
