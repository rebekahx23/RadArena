# Real-data learning walkthrough

These are saved model outputs from actual IU images/reports, not fabricated examples.
Source reports and attacks have not been independently clinically adjudicated.
The researcher can read all sections; each agent received only its role-specific inputs.

## Round 1: study 113

Requested error family: laterality. Status: syntactically_valid_clinically_unreviewed.

### Red generated edit

```json
[
  {
    "sentence_id": "s2",
    "replacement": "There are two subcentimeter hyperdense nodular opacities are noted within the left lung."
  }
]
```

Red explanation: Changed the laterality of the lung nodules from right to left to introduce a laterality error as requested.

### Blue on the attack

Indication: Chest pain.

```json
{
  "verdict": {
    "decision": "error",
    "findings": [
      {
        "sentence_id": "s4",
        "error_type": "presence_absence",
        "evidence": "The provided images show a region of increased density in the left lung, potentially representing a nodule approximately 1-2 cm in diameter. This contradicts the claim that the lungs are clear without infiltrate.",
        "tool_call_ids": [
          "vision_1"
        ]
      }
    ],
    "limitations": "The assessment of nodule size is approximate due to the lack of a scale or reference point in the images. The density could be due to various factors other than a nodule, such as consolidation, scarring, or overlying structures. A definitive diagnosis requires further investigation with additional imaging modalities like a CT scan."
  },
  "score": {
    "localization_tp": 0,
    "localization_fp": 1,
    "localization_fn": 1,
    "uncertain": false,
    "injected_edit_detected": false,
    "unchanged_control_flagged": null,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Is there a hyperdense nodular opacity in the left lung, and if so, what is its approximate size?",
      "observation": "The provided images are chest X-rays, including anterior-posterior (AP) and lateral views. In the AP view, there appears to be a region of increased density in the left lung, potentially representing a nodule. It is located approximately in the left upper lobe. The lateral view does not clearly delineate this opacity, but it appears to be present. Estimating the size is difficult without scale or comparison to other structures, but it appears to be approximately 1-2 cm in diameter. There is also some opacity in the right lung, but it is less distinct. The images are labeled 'BLM LT' and 'LT', suggesting a left-sided view.",
      "limitations": "The assessment of nodule size is approximate due to the lack of a scale or reference point in the images. The density could be due to various factors other than a nodule, such as consolidation, scarring, or overlying structures. A definitive diagnosis requires further investigation with additional imaging modalities like a CT scan. The image quality is moderate, and subtle findings may be missed. Without prior imaging for comparison, it is difficult to determine if this is a new finding or a chronic one."
    },
    {
      "tool_call_id": "vision_2",
      "question": "Is the heart and mediastinum unremarkable?",
      "observation": "The provided chest radiographs show the heart size and mediastinal contours. In the PA and lateral views, the cardiac silhouette appears within normal limits, and the mediastinum does not show obvious widening or masses. However, subtle abnormalities can be difficult to assess without comparison to prior imaging. The images are labeled 'BLM LT' and 'LT LAT', suggesting these are views from a single patient. There is no obvious acute cardiopulmonary pathology.",
      "limitations": "Assessment is limited by the lack of prior imaging for comparison. A definitive determination of 'unremarkable' requires excluding chronic conditions or subtle changes that would be best identified with serial imaging. Image quality is adequate but not optimal for detailed assessment. The question is subjective and relies on interpretation."
    }
  ]
}
```

### Blue on the unchanged control

Indication: Chest pain.

```json
{
  "verdict": {
    "decision": "error",
    "findings": [
      {
        "sentence_id": "s2",
        "error_type": "presence_absence",
        "evidence": "The provided images show a subtle area of increased density in the right lung field on the PA and AP views, appearing as a somewhat rounded opacity approximately 1-2 cm in diameter.",
        "tool_call_ids": [
          "vision_1"
        ]
      },
      {
        "sentence_id": "s4",
        "error_type": "presence_absence",
        "evidence": "The images show some increased opacity in the lower lung fields bilaterally, which could potentially represent infiltrates. However, it is difficult to definitively characterize these findings as infiltrates.",
        "tool_call_ids": [
          "vision_2"
        ]
      }
    ],
    "limitations": "The size estimate of the opacity in the right lung is approximate and subject to interpretation. The potential infiltrates are difficult to definitively characterize based on the image quality and without prior imaging for comparison."
  },
  "score": {
    "localization_tp": 0,
    "localization_fp": 2,
    "localization_fn": 0,
    "uncertain": false,
    "injected_edit_detected": null,
    "unchanged_control_flagged": true,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Is there a hyperdense nodular opacity in the right lung, and if so, what is its approximate size?",
      "observation": "The provided images are chest radiographs, including a PA view, an AP view, and a lateral view. There is a subtle area of increased density in the right lung field on the PA and AP views. It appears as a somewhat rounded opacity. On the lateral view, this area is less clearly defined. Estimating size is difficult without scale or comparison to known structures, but it appears to be approximately 1-2 cm in diameter. It is difficult to definitively characterize this finding as a 'nodule' without further information.",
      "limitations": "The images are in grayscale and of moderate resolution. The density could be due to a variety of factors, including a nodule, a mass, atelectasis, or overlying structures. Without prior imaging for comparison, it is impossible to determine if this is a new finding. The size estimate is approximate and subject to interpretation. A definitive diagnosis requires further investigation, such as a CT scan."
    },
    {
      "tool_call_id": "vision_2",
      "question": "Are there any infiltrates visible in the lungs?",
      "observation": "The images show chest radiographs in multiple views (AP, PA, and lateral). There appears to be some increased opacity in the lower lung fields bilaterally, which could potentially represent infiltrates. However, it is difficult to definitively characterize these findings as infiltrates without further information. The heart size appears normal. The bony structures of the chest wall are intact. There is some artifact present in the images which may obscure subtle findings.",
      "limitations": "The quality of the images is moderate, and subtle infiltrates could be missed. It is impossible to determine the etiology of any potential infiltrates (e.g., pneumonia, edema, malignancy) based on these images alone. A comparison to prior imaging studies would be helpful. Clinical correlation is necessary to interpret these findings."
    }
  ]
}
```

### Red memory after this round

- Introduce errors by swapping left and right laterality.
- Modify anatomical locations to create inconsistencies.
- Focus on findings related to paired organs (lungs, kidneys, etc.).
- Prioritize edits that are syntactically correct but clinically implausible.
- Ensure edits are localized to specific sentences.

The feedback indicates a successful laterality error injection. To reinforce this attack strategy, I will add a rule specifically targeting laterality swaps. Since this is the first rule set, I will also include a general rule about introducing errors in anatomical descriptions.

Memory SHA-256: `2535bf8ae7c3ab60c32f540f9e7e65218dfbdbe590f7392f16904bd34941f41f`.

### Blue memory after this round

- Do not flag 'clear lungs' as incorrect based on subtle opacities without strong image evidence.
- Avoid confident error flags when image findings are ambiguous or could have multiple explanations.
- Do not flag sentences that are identical to the control report.
- If image evidence supports a claim, avoid flagging the claim as incorrect.
- Prioritize uncertainty when image findings are not definitive.

The feedback indicates a tendency to flag sentences as incorrect when image evidence supports a finding (e.g., a nodule) that contradicts a 'clear lungs' statement. The system also incorrectly flagged an unchanged control sentence.  The rules should focus on avoiding confident error flags when evidence is ambiguous or doesn't definitively disprove a statement, and avoiding flagging unchanged sentences. Prioritize uncertainty when image findings are not conclusive.

Memory SHA-256: `23e5d6fa1a4f5e43e58d8059c640b89840739c6bd768dac96448fcfd9735cf0d`.

## Round 2: study 102

Requested error family: presence_absence. Status: syntactically_valid_clinically_unreviewed.

### Red generated edit

```json
[
  {
    "sentence_id": "s3",
    "replacement": "Pneumothorax is present."
  }
]
```

Red explanation: The error type is presence_absence, and the task is to introduce an error. The original sentence states 'No pneumothorax.' I have changed it to 'Pneumothorax is present.' to introduce a false positive finding. This change is unambiguous and consistent with the instructions.

### Blue on the attack

Indication: Syncope. XXXX attack.

```json
{
  "verdict": {
    "decision": "error",
    "findings": [
      {
        "sentence_id": "s3",
        "error_type": "presence_absence",
        "evidence": "The frontal chest x-ray shows a radiopaque linear object traversing the right hemithorax. This could be a chest tube. The lateral view does not clearly demonstrate a pneumothorax, but the presence of a chest tube makes assessment difficult. There is some subtle lucency in the right apex, but this is not definitive for pneumothorax and could be normal lung anatomy or artifact.",
        "tool_call_ids": [
          "vision_1"
        ]
      },
      {
        "sentence_id": "s5",
        "error_type": "presence_absence",
        "evidence": "The frontal chest radiograph shows a radiopaque linear structure projecting over the anterior mediastinum. This appears to be a central venous catheter with the tip terminating in the superior vena cava. There is no obvious substernal density or mass identified on either the frontal or lateral chest radiograph.",
        "tool_call_ids": [
          "vision_2"
        ]
      }
    ],
    "limitations": "The assessment of pneumothorax is complicated by the presence of a chest tube and the limited image quality. The assessment of substernal density is limited by the 2D nature of the radiographs and potential obscuration by overlapping structures."
  },
  "score": {
    "localization_tp": 1,
    "localization_fp": 1,
    "localization_fn": 0,
    "uncertain": false,
    "injected_edit_detected": true,
    "unchanged_control_flagged": null,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Is pneumothorax visible on the image?",
      "observation": "The frontal chest x-ray shows a radiopaque linear object traversing the right hemithorax. This could be a chest tube. The lateral view does not clearly demonstrate a pneumothorax, but the presence of a chest tube makes assessment difficult. There is some subtle lucency in the right apex, but this is not definitive for pneumothorax and could be normal lung anatomy or artifact. ",
      "limitations": "The images are limited to these two views. A full series of chest x-rays or a CT scan would be needed to definitively rule out or confirm pneumothorax. The presence of a chest tube complicates the assessment of pneumothorax. The quality of the images is moderate, and subtle findings may be difficult to interpret."
    },
    {
      "tool_call_id": "vision_2",
      "question": "Is there any substernal density, and if so, where is it located?",
      "observation": "The frontal chest radiograph shows a radiopaque linear structure projecting over the anterior mediastinum. This appears to be a central venous catheter with the tip terminating in the superior vena cava. There is no obvious substernal density or mass identified on either the frontal or lateral chest radiograph. However, the lateral view is limited in its ability to fully assess the retrosternal space. The heart border and mediastinal contours appear within normal limits for the views provided.",
      "limitations": "The assessment of substernal density is limited by the 2D nature of the radiographs. Subtle densities could be obscured by overlapping structures. A CT scan would be more sensitive for detecting and characterizing any subtle substernal abnormalities. The lateral view is not fully representative of the entire retrosternal space."
    }
  ]
}
```

### Blue on the unchanged control

Indication: Syncope. XXXX attack.

```json
{
  "verdict": {
    "decision": "no_error_detected",
    "findings": [],
    "limitations": "The assessment of heart size is limited by the lack of prior imaging for comparison. The assessment of lung hyperaeration is limited by the lack of prior imaging and the presence of a radiopaque object obscuring some of the lung fields. A possible small pleural effusion was noted, but confirmation requires further imaging."
  },
  "score": {
    "localization_tp": 0,
    "localization_fp": 0,
    "localization_fn": 0,
    "uncertain": false,
    "injected_edit_detected": null,
    "unchanged_control_flagged": false,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Is the heart size normal on the image?",
      "observation": "The frontal chest radiograph shows a central line with the tip appearing to be in the superior vena cava. The cardiac silhouette appears within normal limits for size, but a precise assessment is difficult without prior imaging for comparison. The lateral view does not provide a clear assessment of cardiac size. There are no obvious signs of cardiomegaly on the available images.",
      "limitations": "Assessing heart size accurately requires comparison to previous radiographs of the same patient. The lateral view is not optimally positioned for cardiac size assessment. The quality of the images limits detailed evaluation. Without clinical context, it is difficult to determine if the observed size is appropriate for the patient."
    },
    {
      "tool_call_id": "vision_2",
      "question": "Are the lungs clear and hyperaerated on the image?",
      "observation": "The frontal chest x-ray shows a radiopaque linear object projecting across the right hemithorax. The lungs appear generally clear, without obvious consolidations or large effusions. The lateral view does not show any obvious signs of hyperaeration, but it is difficult to assess lung volumes accurately without a prior image for comparison. There is a possible small pleural effusion on the right side, but this is difficult to confirm without further imaging.",
      "limitations": "Assessment of hyperaeration is limited by the lack of a prior chest x-ray for comparison. The quality of the images is moderate, and subtle findings may be missed. The presence of the radiopaque object obscures some of the underlying lung fields. A definitive assessment of lung clarity and hyperaeration would require additional clinical information and potentially further imaging."
    }
  ]
}
```

### Red memory after this round

- Introduce or remove findings related to common abnormalities.
- Focus on creating false positives or negatives for key findings.
- Prioritize edits that change 'no evidence of' to 'evidence of' or vice versa.
- Maintain syntactical correctness while ensuring clinical implausibility.
- Target findings related to easily confused conditions (e.g., effusion vs. pneumothorax).

The feedback indicates a successful introduction of a presence/absence error. The strategy should be reinforced to continue focusing on introducing or removing findings, particularly those related to common abnormalities. The existing rules are good, but can be sharpened to emphasize clinically implausible, yet syntactically correct, alterations.

Memory SHA-256: `30bad2d33d70a76f7148f6a052332fdbeeec8da6607699696aa01ae31fa218cb`.

### Blue memory after this round

- When image evidence is inconclusive or limited, prioritize uncertainty and avoid confident error flags.
- Do not flag the absence of pneumothorax when a chest tube is present, as assessment is complicated.
- Avoid flagging findings as incorrect based solely on subtle image features without strong supporting evidence.
- If image findings could have multiple explanations, avoid flagging a claim as incorrect.
- Be cautious when assessing substernal densities on standard radiographs due to potential obscuration.

The feedback highlights challenges in pneumothorax and substernal density assessment due to image limitations (chest tube, image quality, 2D views) and the need to avoid confident error flags when findings are ambiguous. The rules should emphasize uncertainty and the importance of image evidence. We need to reinforce avoiding flags based on subtle findings without strong support and the potential for multiple interpretations.

Memory SHA-256: `ec1cc4371a817aef463f97ea740d091ecd683d5914bd74eb950fc22705b4d9cf`.

## Round 3: study 1187

Requested error family: severity. Status: syntactically_valid_clinically_unreviewed.

### Red generated edit

```json
[
  {
    "sentence_id": "s1",
    "replacement": "FINDINGS: No airspace opacities bilaterally, most prominent in the lung bases."
  },
  {
    "sentence_id": "s5",
    "replacement": "IMPRESSION: No air space opacities bilaterally, most prominent in the lung bases."
  }
]
```

Red explanation: Changed the severity of the airspace opacities from 'minimally increased' to 'no' to introduce a false negative finding, as per the error type (severity) and strategies provided. The change was applied consistently in both the Findings and Impression sections.

### Blue on the attack

Indication: XXXX-year-old with shortness of breath

```json
{
  "verdict": {
    "decision": "error",
    "findings": [
      {
        "sentence_id": "s1",
        "error_type": "presence_absence",
        "evidence": "The PA view shows some increased opacity in the lower lung fields bilaterally, which could represent airspace opacity. The lateral view shows some increased opacity in the left lower lung field.",
        "tool_call_ids": [
          "vision_1"
        ]
      }
    ],
    "limitations": "The images are limited in that they are single views and do not allow for a comprehensive assessment of the lungs. It is difficult to definitively determine if the increased opacity is airspace opacity versus other causes of increased density."
  },
  "score": {
    "localization_tp": 1,
    "localization_fp": 0,
    "localization_fn": 1,
    "uncertain": false,
    "injected_edit_detected": true,
    "unchanged_control_flagged": null,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Is there any airspace opacity visible bilaterally?",
      "observation": "The PA view shows some increased opacity in the lower lung fields bilaterally, which could represent airspace opacity. The lateral view shows some increased opacity in the left lower lung field. However, it is difficult to definitively determine if this is airspace opacity versus other causes of increased density, such as vascular congestion or pleural effusion. There is also some artifact present in the images that could affect interpretation.",
      "limitations": "The images are limited in that they are single views and do not allow for a comprehensive assessment of the lungs. Without prior imaging for comparison, it is difficult to determine if these findings are new or chronic. The quality of the images is also somewhat limited, making it difficult to definitively characterize the opacities."
    },
    {
      "tool_call_id": "vision_2",
      "question": "Is the heart size within normal limits?",
      "observation": "The frontal chest radiograph shows the cardiac silhouette. Assessing cardiac size on a single PA view can be subjective. The cardiothoracic ratio appears within normal limits, but a precise measurement is difficult without a prior image for comparison. The lateral view does not provide a clear assessment of cardiac size. There are no obvious signs of cardiomegaly, such as significant enlargement of the cardiac silhouette or effacement of the costophrenic angles.",
      "limitations": "Assessment of cardiac size is limited by the lack of prior imaging for comparison. A precise cardiothoracic ratio cannot be determined without a standardized PA view and knowledge of the patient's body habitus. The lateral view is not optimal for assessing cardiac size."
    }
  ]
}
```

### Blue on the unchanged control

Indication: XXXX-year-old with shortness of breath

```json
{
  "verdict": {
    "decision": "no_error_detected",
    "findings": [],
    "limitations": "The image observations indicate the presence of increased opacities in the lung fields, but it is difficult to definitively characterize them as airspace opacities without further information or comparison to prior imaging. The report claims are consistent with these findings, and therefore cannot be confidently contradicted."
  },
  "score": {
    "localization_tp": 0,
    "localization_fp": 0,
    "localization_fn": 0,
    "uncertain": false,
    "injected_edit_detected": null,
    "unchanged_control_flagged": false,
    "ground_truth_scope": "synthetic edits; image support not adjudicated"
  },
  "observations": [
    {
      "tool_call_id": "vision_1",
      "question": "Are there airspace opacities visible bilaterally?",
      "observation": "The frontal chest radiograph shows some areas of increased opacity in both lung fields, particularly in the lower lobes. These could potentially represent airspace opacities, but could also be due to other factors like vascular prominence or overlying soft tissue. The lateral view shows some increased opacity in the left lung, but it is difficult to definitively characterize as airspace opacity without comparison to prior imaging or additional views. There is some haziness in the right lung base on the frontal view as well.",
      "limitations": "It is difficult to definitively determine if these are airspace opacities without further clinical information or comparison to prior imaging. The quality of the images and the lack of additional views limit the ability to fully characterize the findings. The images are grayscale and subtle differences in density can be hard to assess."
    },
    {
      "tool_call_id": "vision_2",
      "question": "If airspace opacities are present, are they most prominent in the lung bases?",
      "observation": "The frontal chest x-ray shows some areas of increased opacity in both lung bases. The lateral view also demonstrates increased opacity in the left lung base. However, it is difficult to definitively characterize these opacities as airspace disease without further information. There is also some opacity in the right mid-lung field on the frontal view. ",
      "limitations": "The images are limited to these two views. A full set of chest x-rays (AP/PA and lateral) or a CT scan would be needed to better characterize the opacities and determine if they are truly airspace disease. It is also difficult to assess the extent and distribution of the opacities without comparison to prior imaging. The question asks specifically about airspace opacities, but the images do not confirm this diagnosis."
    }
  ]
}
```

### Red memory after this round

- Reduce the severity of reported findings (e.g., 'mild' to 'none').
- Focus on altering quantitative findings to create false negatives.
- Prioritize changes to findings in both the FINDINGS and IMPRESSION sections for consistency.
- Maintain syntactical correctness while altering clinical severity.
- Target findings where severity is explicitly stated (e.g., 'minimal', 'mild', 'moderate').

The feedback indicates a successful severity reduction, creating a false negative. The strategy should be reinforced to focus on similar severity alterations. Additionally, expanding to other findings where severity is reported is beneficial. The existing rules are generally sound and will be refined to emphasize this successful tactic.

Memory SHA-256: `bc894c3e0978a30976d23121c6ce1b977fa2ac13aec9df2d6f09bcc990593c3a`.

### Blue memory after this round

- Avoid flagging the absence of a finding when subtle image features suggest its possible presence.
- When image quality or views are limited, prioritize uncertainty and avoid confident error flags.
- Do not confidently flag a claim as incorrect if the image findings are open to multiple interpretations.
- Acknowledge limitations of single-view radiographs when assessing findings.
- Be cautious when assessing subtle differences in image density, especially when characterizing opacities.

The feedback highlights a case where a subtle difference in opacity description (increased vs. minimally increased) led to a disagreement between the model and the synthetic edit. The model initially flagged the absence of airspace opacity, but the vision tool identified some increased opacity. This reinforces the need to avoid strong negative claims when image evidence is subtle or open to interpretation. The feedback also shows the importance of acknowledging limitations in single-view radiographs. We should prioritize uncertainty when the image quality or view limits definitive characterization of findings.

Memory SHA-256: `b5d2f2ab202f72dcab49e1e0a8c4f38ee01088d9d87a667b2822fcb0e891deb1`.

## Frozen development evaluation

# Role-private learning pilot

| Checkpoint | Blue localization F1 | Control FPR |
| --- | --- | --- |
| Before | 0.333 | 0.333 |
| After | 0.500 | 0.000 |

Red probe against a fixed baseline Blue:
```json
{
  "before": {
    "attack_status": "syntactically_valid_clinically_unreviewed",
    "syntactic_edit_escaped_localization": true,
    "blue_decision": "no_error_detected",
    "score": {
      "localization_tp": 0,
      "localization_fp": 0,
      "localization_fn": 1,
      "uncertain": false,
      "injected_edit_detected": false,
      "unchanged_control_flagged": null,
      "ground_truth_scope": "synthetic edits; image support not adjudicated"
    }
  },
  "after": {
    "attack_status": "syntactically_valid_clinically_unreviewed",
    "syntactic_edit_escaped_localization": true,
    "blue_decision": "no_error_detected",
    "score": {
      "localization_tp": 0,
      "localization_fp": 0,
      "localization_fn": 1,
      "uncertain": false,
      "injected_edit_detected": false,
      "unchanged_control_flagged": null,
      "ground_truth_scope": "synthetic edits; image support not adjudicated"
    }
  }
}
```

Audit accounting: $0.038785; 95 audited calls (includes cache and unknown-cost reserves).

Three dev studies, one Red probe; no statistical improvement claim.
Development studies disjoint from this run training studies, not untouched final test.
Attack image validity and requested semantic-family compliance not independently adjudicated.
Strategy adaptation, no weight updates; models have no filesystem access or shared chat history.

