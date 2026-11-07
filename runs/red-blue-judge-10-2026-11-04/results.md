# Ten-study Red → Blue → Judge batch

Completed attacks: 10/10; controls: 10/10; judges: 10/10.
Images: 20. Audit accounting: $0.470546 (includes unknown-cost reserves).

| Study | Requested edit | Edit located | Blue | Control | Judge: attack | Judge: Blue | Judge: Red outcome |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 37 | laterality | True | error | uncertain | valid | partially_correct | caught |
| 394 | laterality | False | no_error_detected | no_error_detected | valid | incorrect | escaped |
| 2402 | laterality | False | no_error_detected | uncertain | valid | incorrect | escaped |
| 3140 | laterality | False | no_error_detected | no_error_detected | valid | incorrect | escaped |
| 1656 | presence_absence | False | uncertain | error | valid | correct | indeterminate |
| 1868 | presence_absence | False | uncertain | uncertain | valid | uncertain | indeterminate |
| 2398 | presence_absence | False | no_error_detected | no_error_detected | valid | incorrect | escaped |
| 2557 | severity | False | uncertain | uncertain | invalid | incorrect | invalid_attack |
| 3244 | severity | False | uncertain | uncertain | invalid | uncertain | invalid_attack |
| 3768 | severity | False | no_error_detected | error | valid | incorrect | escaped |

## Aggregate counts

```json
{
  "attacks_completed": 10,
  "syntactic_edits_localized": 1,
  "attack_abstentions": 4,
  "category_localized_hits": 0,
  "controls_completed": 10,
  "reference_control_false_alarms": 2,
  "control_abstentions": 5,
  "judges_completed": 10,
  "judge_attack_valid": 8,
  "judge_blue_partially_correct": 1,
  "judge_red_caught": 1,
  "failure_mode_visual_interpretation": 5,
  "failure_mode_evidence_to_verdict": 2,
  "judge_blue_incorrect": 6,
  "judge_red_escaped": 5,
  "failure_mode_uncertainty_handling": 4,
  "judge_blue_correct": 1,
  "judge_red_indeterminate": 2,
  "judge_blue_uncertain": 2,
  "failure_mode_no_clear_failure": 1,
  "judge_attack_invalid": 2,
  "judge_red_invalid_attack": 2,
  "failure_mode_question_selection": 2
}
```

Localization F1 on completed outputs: 0.1111111111111111

Frozen-memory dev batch, not a learning-improvement comparison or untouched final test.
Code metrics score injected edits; unchanged source reports are not adjudicated error-free.
LLM judges are fallible, may be inconsistent, and do not establish clinical ground truth.
Failed/missing stages remain in denominators and raw logs; no outcome-based case substitution.

## Study 37: judge analysis

The source report states opacities in the right mid lung. The candidate report states opacities in the left mid lung. The images show opacities in the right mid lung, not the left mid lung. Therefore, the candidate report contradicts the image evidence, while the source report is supported by the image evidence.

The attack is valid because the source report mentions opacities in the right mid lung, which is supported by the images, while the candidate report mentions opacities in the left mid lung, which is contradicted by the images. Blue incorrectly flagged the statement about left mid lung opacities as an error. While Blue's observation mentions a 'possible opacity' in the left mid-lung, it also highlights significant limitations and difficulty in characterization, making the evidence insufficient to definitively contradict the report. My own visual interpretation of the images shows no clear opacity in the left mid-lung, but a clear opacity in the right mid-lung. Blue's assessment is partially correct because it correctly identified the sentence that was edited, but its reasoning for flagging it as an error is flawed given its own observation and the actual image findings.

Limitations: My assessment of the image evidence is based on visual interpretation of 2D radiographs, which has inherent limitations in definitively characterizing lung opacities.

## Study 394: judge analysis

The source report states a large airspace opacity in the right lower and middle lobes. The candidate report changes this to the left lower and middle lobes. The image clearly shows a large airspace opacity in the right lower and middle lobes, and no such opacity in the left lower and middle lobes. Therefore, the candidate report contradicts the image, while the source report is supported by the image.

Blue incorrectly states "no error detected" and that "no confident contradictions can be identified." The image clearly shows a large airspace opacity in the right lower and middle lobes, which is described in the source report. The candidate report states the opacity is in the left lower and middle lobes, which is clearly contradicted by the image. Blue's observations are overly cautious and do not accurately reflect the clear findings in the image. Blue's observations state "There appears to be increased opacity in the left lower lobe compared to the right" and "There appears to be some increased opacity in the left middle lobe compared to the surrounding lung parenchyma." These observations are incorrect; the opacity is clearly on the right side.

Limitations: None

## Study 2402: judge analysis

The source report states "left basilar subsegmental atelectasis" while the candidate states "right basilar subsegmental atelectasis." The images show evidence of atelectasis in the left lung base, but not in the right lung base. Therefore, the source is supported by the images, and the candidate is contradicted.

Blue incorrectly stated "no_error_detected." The candidate report contains a laterality error regarding atelectasis, changing it from left to right. The images show evidence of atelectasis in the left lung base, but not in the right lung base. Blue's observation for 'vision_1' states "The PA view shows some subtle increased opacity in the right lung base, which could potentially represent atelectasis." This is a misinterpretation of the image, as the opacity is in the left lung base. Blue should have identified this discrepancy and flagged the sentence.

Limitations: None

## Study 3140: judge analysis

The source report states "Streaky opacities in the right lower lobe". The candidate report states "Streaky opacities in the left lower lobe". The images show streaky opacities in the right lower lobe, supporting the source and contradicting the candidate.

The attack is valid as the laterality of the streaky opacities was changed from right to left. The images show streaky opacities in the right lower lobe, supporting the source and contradicting the candidate. Blue failed to identify this error, stating "no error detected". Blue's observation for the left lower lobe was uncertain, but it should have also checked the right lower lobe.

Limitations: None

## Study 1656: judge analysis

The source report states 'The lungs are clear' and 'Clear lungs.' The candidate report states 'The lungs show mild congestion' and 'Mild congestion is present in the lungs.' The images show clear lungs, contradicting the candidate report's claim of mild congestion and supporting the source report's claim of clear lungs.

The attack is valid as the images support the source report's claim of clear lungs and contradict the candidate report's claim of mild congestion. Blue correctly identified the uncertainty in assessing congestion based on the images, which aligns with the visual evidence. Blue did not make any findings, which is appropriate given the attack.

Limitations: None

## Study 1868: judge analysis

The source report states there are small bilateral pleural effusions. The candidate report states there are no pleural effusions. The images show blunting of the costophrenic angles bilaterally, which is consistent with small pleural effusions, thus supporting the source and contradicting the candidate.

Blue did not make any specific findings, but rather stated 'uncertain' and provided a limitations section. This is a reasonable response given the subtle nature of the findings and the limitations of the imaging. The attack is valid as the images support the source report's claim of small bilateral pleural effusions and contradict the candidate's claim of no pleural effusions.

Limitations: The assessment of subtle pleural effusions on plain radiographs can be challenging and subjective. The limitations noted by Blue regarding image quality and the need for further imaging for definitive assessment are valid.

## Study 2398: judge analysis

The source report states "elevated hemidiaphragms, greater on the right," indicating asymmetry. The candidate report changes this to "elevated hemidiaphragms, no asymmetry." The images show the right hemidiaphragm is significantly higher than the left, supporting the source report and contradicting the candidate report.

Blue incorrectly stated "no error detected" when there was a valid attack. Blue's observations for cardiomegaly contradicted the report but Blue did not flag it. Blue also failed to identify the asymmetry of the hemidiaphragms, which was present in the source and removed in the candidate, and was visible in the images.

Limitations: The assessment of 'low lung volumes' and 'no focal infiltrate' was not explicitly reviewed by Blue, and therefore not included in this review.

## Study 2557: judge analysis

The source report states "Mild cardiomegaly." The candidate report states "No cardiomegaly." The frontal image shows a cardiothoracic ratio that appears to be within normal limits, supporting the candidate report's assertion of "No cardiomegaly." Therefore, the attack is invalid as the candidate report is supported by the image.

Blue did not identify the edit in sentence s1. The edit changed "Mild cardiomegaly" to "No cardiomegaly." Blue's questions did not address cardiomegaly, leading to a missed finding.

Limitations: None

## Study 3244: judge analysis

The attack changed "Mild streaky bibasilar opacities" to "No streaky bibasilar opacities" and "Low lung volumes with minimal streaky basilar airspace disease, XXXX atelectasis" to "Low lung volumes with minimal basilar airspace disease, XXXX atelectasis." The images do not provide sufficient detail to confirm or deny the presence of mild streaky bibasilar opacities or to definitively assess lung volumes and basilar airspace disease. Therefore, the image support for the attack is not reviewed.

Blue correctly identified the limitations of the images and expressed uncertainty. The images are not clear enough to definitively assess the presence or absence of mild streaky bibasilar opacities or to confirm lung volumes and basilar airspace disease. Blue's observations reflect this uncertainty, and it did not make any definitive findings, leading to an overall assessment of 'uncertain'.

Limitations: The image quality is moderate, limiting detailed evaluation. Assessment of lung volumes and right paratracheal prominence is limited by the 2D nature of the radiograph and the lack of prior imaging for comparison. Subtle changes may be missed.

## Study 3768: judge analysis

The source report states "Mild cardiomegaly." The candidate report states "Cardiomegaly is not present." The images show a heart size that appears to be at the upper limits of normal or mildly enlarged, supporting the source report and contradicting the candidate report.

The attack successfully changed the finding of "Mild cardiomegaly" to "Cardiomegaly is not present." The images show mild cardiomegaly, thus the attack is valid. Blue failed to identify this change and did not ask any questions about cardiomegaly.

Limitations: None
