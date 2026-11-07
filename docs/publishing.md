# Publishing and reproducibility

The repository includes code, documentation, dataset download instructions, processed
manifests/benchmarks, aggregate results, and saved experiments in `runs/`.
Original run records and frozen data artifacts retain their recorded bytes.

## Included artifacts

- `src/`, `tests/`, `scripts/`, `configs/`, and `.github/`.
- Package metadata, lockfile, configuration template, and documentation.
- Dataset download/verification scripts and upstream source attribution.
- `data/processed/`: paired-study manifest, frozen benchmarks, and review exports.
- `runs/`: prompts, explicit model outputs, failures, judgments, memories, costs,
  and archived implementation versions.
- `reports/`: aggregate results and text-free metric inputs.
- Authored handbook summaries, source notes, and selected UI screenshots.

Role-private records are withheld from the opposing agent during execution and included
here for readers auditing the experiment.

## Dataset terms and references

[The dataset notice](../data/LICENSE.md) records the upstream CC BY-NC-ND 4.0 license, attribution, and the
sharing restrictions for edited report text. Unmodified dataset sharing and distribution
of adapted text are different cases under those terms. Reorganizing folders does not
change the raw file contents. The original acquisition date and export version remain
unrecorded.

Full reference-book PDFs stay local. The README and `knowledge/README.md` cite the books
and explain their usage. They are not covered by the project's [MIT License](../LICENSE). That
license covers RadArena's original code and documentation; third-party material retains
its respective terms.

## Files that stay out of Git

| Artifact | Reason |
| --- | --- |
| `.env` and credentials | Machine-local secrets |
| `data/raw/`, `data/downloads/` | Upstream data acquired separately |
| `.venv/`, `.cache/`, Python/test caches | Dependencies and regenerable caches |
| `knowledge/*.pdf` | Full copyrighted reference books |
| `tmp/`, `output/` | Disposable build output |
| Original `docs/*preview.png` | Duplicate captures; selected copies are in `docs/images/` |
| `docs/history/` | Local planning documents |

## Large files and pre-upload checks

Download original CSVs and PNGs from the upstream source using `data/README.md`. They
are not staged or pushed. Processed records and run traces remain ordinary Git files.
Text conversion is disabled for frozen records so their historical hashes stay valid.

```bash
git status --short
git check-ignore data/raw/iu_xray/indiana_reports.csv data/downloads/iu_xray.zip
git check-ignore .env knowledge/'The Radiology Handbook.pdf'
```

Before an upload, review the staged files, retain dataset attribution, resolve sharing
rights for adapted report text, and ensure credentials remain excluded. A
credential-pattern scan of the current runs/processed records found no provider API key
or bearer-token patterns; automated scans do not replace content review.

Archived source hashes identify the original implementations. Current code uses path
translation at load time, leaving the historical files unchanged. See [reproducibility](REPRODUCIBILITY.md)
for replay, result recomputation, and the limits of rerunning hosted inference.
