# Proposed image-viewing tools and evaluation

Status: researched November 4, 2026; not implemented or evaluated. No images were
modified and no inference calls were made for this proposal.

## Why test it

Contrast/brightness adjustment, grayscale inversion, and region inspection can change
the visibility of existing detail. They do not add new image information or establish
that a reported finding exists. These are candidate perceptual tools for Blue, separate
from report parsing and evidence-to-verdict reasoning.

Human-reader evidence does not establish VLM benefit. Ledda et al. (2022) compared
standard and inverted chest radiographs for 507 patients, using CT as reference, and
found no significant overall advantage of inversion across eight abnormalities.
[Primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8960630/).
Yoon et al. (2023) found that contrast settings and image format affected a ResNet-50
pneumothorax detector. That establishes sensitivity to processing in that experiment,
not an optimal transform for our hosted VLMs.
[Primary study](https://pubmed.ncbi.nlm.nih.gov/36698035/).

## What we actually have

The supplied dataset is normalized PNGs. An inspected pilot image is an 8-bit grayscale
PNG, 2048 by 2529 pixels, with values 0-255, despite `.dcm.png` in its filename.
It is not a DICOM object. Do not call an 8-bit PNG adjustment calibrated DICOM windowing
or infer original detector bit depth/processing. Raw information lost in export cannot
be recovered by changing the PNG display.

DICOM window/level uses defined VOI transformations and available image attributes;
it requires a separate correctly implemented DICOM ingestion path.
[DICOM VOI LUT standard](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.11.2.html).

## Bounded prototype

Expose a controller-validated `get_image_view(image_id, preset, region)` interface.
Suggested initial actions are original, a small number of mild brightness/contrast
presets, grayscale inversion, and crop/zoom. Preset values would be chosen on development
data and frozen before scoring, not described as clinically validated settings.
Avoid arbitrary scripts and an unlimited adjustment/retry loop.

- Keep the source image immutable; always generate a separate deterministic view.
- Keep the original available alongside derived views for comparison.
- Label derived views explicitly and retain image/view IDs, pixel dimensions, original
  and output checksums, preset parameters, clipping statistics, and crop coordinates.
- Grayscale inversion means `255 - pixel` for these 8-bit images; it is not a left/right
  geometric flip. Do not mirror or rotate the image in this laterality experiment.
- Crops retain orientation and map back to source coordinates; the full image remains
  accessible. Upsampling a crop does not recover missing detail.
- Brightness/contrast changes can clip values, and aggressive local enhancement may
  emphasize noise. Start with mild fixed presets. No generative image enhancement.
- A transformed view is another presentation of the same observation source, not an
  independent corroborating examination. The final assessor must not count two views
  of the same pixels as two independent confirmations.
- Apply the same viewing capability to eligible compared methods, or explicitly label
  it as the intervention. It must not reveal source reports, edit locations, or labels.

## Isolate its contribution

After selecting a reliable model/configuration, compare paired development cases:

1. Original-image workflow.
2. Original-image workflow with a matched extra look at the original image.
3. Original-image workflow with a bounded model-selected derived view.

Conditions 2 and 3 should share the image-call budget and resolution policy. This
separates a transform's value from simply spending more inference calls. A fixed-preset
condition can later distinguish access to enhancement from agent selection quality.
Do not combine a new model, RadGraph, new prompts, and image transforms in one causal
comparison. Use unchanged controls and clinically reviewed edits where possible.

Report localization, category correctness, control false alarms, uncertainty, image
tool calls, tokens, cost, and whether contradictions have actual supporting evidence.
Analyze cases where an enhancement adds a false flag or changes an observation's
polarity. Freeze presets/selection policy before held-out scoring.

Pixel operations are inexpensive local CPU work. Additional model image inputs/calls
can increase API tokens or GPU runtime substantially. No cost reduction or performance
benefit should be assumed before a small measured pilot. Viewing tools will not by
themselves repair the observed supported-versus-contradicted judgment failures.
