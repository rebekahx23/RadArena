# Radiology references and usage

`Radiology for Medical students.pdf` is a supplied reference kept locally and excluded from Git. Agents
read selected summaries in `handbooks/radiology-handbook/` through the role-scoped reader. They
cannot open arbitrary PDFs or send the full book to a model. The separate
`reporting_v1.json` pack is unchanged.

## Additional supplied reference

J. S. Benseler. *The Radiology Handbook: A Pocket Guide to Medical Imaging*. Ohio
University Press, 2006. Print ISBN 978-0-8214-1708-9; eBook ISBN 978-0-8214-4232-6.
[Publisher record](https://www.ohioswallow.com/9780821417089/the-radiology-handbook/).

- Local file: `knowledge/The Radiology Handbook.pdf`, 203 PDF pages.
- SHA-256: `ced7f3abe2cba61e9312e310b7733853f6be505b4f4ee9f2a6fd7de33d307792`.
- Usage: supplied background reference. The handbook has no recorded Benseler
  page extraction or automated ingestion. Its page-cited book summaries come from Eze.
- The local PDF's page count describes that file, not the publisher's print edition.

Both full books stay local. The agents read authored reference cards or selected
handbook chapters, not the PDFs themselves. The central 20-study experiment used the
reporting pack; the optional handbook selector was disabled.

## Eze source record and implemented summaries

- Author: Kenneth C. Eze.
- Title: *Radiology for Medical Students*.
- Publisher: Mindex Publishing Co. Ltd., Benin City, Nigeria.
- Year: 2012, verified on the copyright page. The PDF creation date was not used.
- ISBN: 978-978-8448-41-9.
- Local file: `knowledge/Radiology for Medical students.pdf`, 230 PDF pages.
- SHA-256: `734d409fe21b4cdf504bfe2ef5b1dd7100764b09a2196200cda7c714bf22c635`.
- Review: inspected November 3, 2026; qualified radiologist review pending.

| Selected source passage | PDF viewer page (1-based) | Printed page | Handbook chapter |
| --- | --- | --- | --- |
| Plain films and projection effects | 15-16 | 1-2 | `references/medical-library/cxr-technique.md` |
| Table 1.2, chest radiograph reading checklist | 19 | 5 | `references/medical-library/systematic-review.md` |
| Heart size and cardiothoracic ratio | 53-55 | 39-41 | `references/medical-library/cardiac-enlargement.md` |

The page map covers selected passages, not a full book review. These general reference
notes are separate from evaluation labels, training demonstrations, and learned memory.
No book images, full-text extraction, or textbook case reports are bundled into the
handbook. The summaries omit numerical and population-specific size cutoffs and
management recommendations pending source reconciliation and clinical review. The book
is copyrighted; its presence here does not establish redistribution rights.

For experiments, freeze the versioned handbook before evaluation. Both roles may read
these medical chapters in `full` and `no_domain`; `no_medical`
and `none` hide them. Do not add held-out study reports or evaluation
answers to this directory.
