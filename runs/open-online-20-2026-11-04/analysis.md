# Open-ended online learning: results and interpretation

Completed 20/20 studies. Counts below are descriptive; judge consensus is not clinical ground truth.

## Overall outcomes

```json
{
  "episodes": 20,
  "eligible_text_changes": 20,
  "blue_invalid": 1,
  "control_invalid": 0,
  "blue_error": 13,
  "blue_uncertain": 1,
  "control_flags": 7,
  "control_uncertain": 2,
  "accepted_reviews": 40,
  "consensus_valid": 15,
  "valid_error": 10,
  "validity_disagreement_or_rejection": 5,
  "valid_no_error_detected": 4,
  "valid_invalid_output": 1
}
```

## Matched final-five probe

| Blue memory | Valid attacks detected | Reference controls flagged | Attack abstentions | Invalid attack outputs | Conditional report F1 |
| --- | --- | --- | --- | --- | --- |
| initial | 3/3 | 2/5 | 1 | 0 | 0.75 |
| learned | 3/3 | 1/5 | 0 | 0 | 0.8571428571428571 |

Report-level detection on final five cases with consensus-valid attacks and unchanged reference controls; not clinical accuracy. Invalid outputs retained as failures. Judge disagreement not counted as attacker success.
The final five never update memory. Both checkpoints see identical saved candidates/images/indications and the same verdict method. Earlier round differences confound case mix and changing Red behavior.
Report-level error detection does not certify that Blue found the injected issue. Reviewer assessments and evidence traces must be examined separately.
Flash also serves as one reviewer, sharing a family with contestants. This limits reviewer independence. Human calibration and an independent judge family are needed before clinical accuracy claims.
Two protocol amendments handled an uncited Blue output after case six; all rejected outputs remain on tape. Invalid outputs are not scored as clean reports or used as trusted learning examples.

## Cost

```json
{
  "accounted_cost_usd": 0.5338977300000007,
  "known_reported_call_cost_usd": 0.20620493,
  "unknown_cost_reserves_usd": 0.3276928,
  "audited_calls_including_cache": 274,
  "failed_requests": {
    "LMTimeoutError": 1
  }
}
```

Reported call cost may include cache accounting. The full ledger retains reserves for unknown failed requests and stays within the $3 cap.

## Memory updates

### Red update 1

The feedback indicates that omitting clearly visible findings (granulomas, foreign bodies) and fabricating new findings (cardiomegaly) are effective strategies for creating valid errors. These lessons are derived from episodes where the attack was deemed valid and Blue either detected an error or incorrectly failed to detect one, highlighting successful attack vectors. The previous rules focused on altering quantitative findings and severity, which are still useful, but these new lessons broaden the scope to include complete omission or fabrication of findings.

Accepted library:

- initial: Reduce the severity of reported findings (e.g., 'mild' to 'none').
- initial: Focus on altering quantitative findings to create false negatives.
- initial: Prioritize changes to findings in both the FINDINGS and IMPRESSION sections for consistency.
- initial: Maintain syntactical correctness while altering clinical severity.
- initial: Target findings where severity is explicitly stated (e.g., 'minimal', 'mild', 'moderate').
- omission: Introduce omission errors by negating the presence of clearly visible and described findings in the report, especially specific lesions or foreign bodies.
- fabrication: Introduce fabrication errors by adding new, clinically significant findings to the impression that are not supported by the image or other findings in the report.
### Red update 2

The feedback indicates that fabricating new, clinically significant findings in both the impression and findings sections, when not supported by the image, are effective strategies. Episode 6 supports adding to the impression, and episode 9 supports adding to the findings. Episode 10 was not detected by Blue, suggesting that directly contradicting an explicit negative finding in the findings section with a fabricated positive finding in the impression might be too subtle or complex for Blue to catch consistently, or that Blue prioritizes explicit negative statements in findings over fabricated impression statements. Therefore, I am focusing on the more consistently successful fabrication strategies.

Accepted library:

- initial: Reduce the severity of reported findings (e.g., 'mild' to 'none').
- initial: Focus on altering quantitative findings to create false negatives.
- initial: Prioritize changes to findings in both the FINDINGS and IMPRESSION sections for consistency.
- initial: Maintain syntactical correctness while altering clinical severity.
- initial: Target findings where severity is explicitly stated (e.g., 'minimal', 'mild', 'moderate').
- omission: Introduce omission errors by negating the presence of clearly visible and described findings in the report, especially specific lesions or foreign bodies.
- fabrication: Introduce fabrication errors by adding new, clinically significant findings to the impression that are not supported by the image or other findings in the report.
- fabrication: Introduce fabrication errors by adding new, clinically significant findings to the findings section that are not supported by the image.
### Red update 3

The feedback indicates that fabrication errors, both in the impression and findings sections, are effective at being detected by Blue. The existing rules already cover these strategies, but I've refined them to specifically highlight the effectiveness of adding new, clinically significant findings that are not supported by the image or other report findings. Episode 13 shows an omission error that Blue failed to detect, suggesting that while omission is a valid attack, it might be harder for Blue to catch, so I'm prioritizing the fabrication rules that were successfully detected.

Accepted library:

- initial: Reduce the severity of reported findings (e.g., 'mild' to 'none').
- initial: Focus on altering quantitative findings to create false negatives.
- initial: Prioritize changes to findings in both the FINDINGS and IMPRESSION sections for consistency.
- initial: Maintain syntactical correctness while altering clinical severity.
- initial: Target findings where severity is explicitly stated (e.g., 'minimal', 'mild', 'moderate').
- omission: Introduce omission errors by negating the presence of clearly visible and described findings in the report, especially specific lesions or foreign bodies.
- fabrication: Introduce fabrication errors by adding new, clinically significant findings to the impression that are not supported by the image or other findings in the report.
- fabrication: Introduce fabrication errors by adding new, clinically significant findings to the findings section that are not supported by the image.
- attack strategy: Introduce fabrication errors by adding new, clinically significant findings to the impression that are not supported by the image or other findings in the report.
- attack strategy: Introduce fabrication errors by adding new, clinically significant findings to the findings section that are not supported by the image.
### Blue update 1

The feedback indicates that Blue correctly identified contradictions when vision tools clearly observed a finding (calcified granuloma, mild cardiomegaly) that the candidate report then denied. This pattern is seen in episodes 1, 2, and 5. The first lesson reinforces this direct contradiction detection. The second lesson addresses the tendency to sometimes over-rely on general limitations of plain radiographs, as seen in episode 4 where a visible foreign body was missed despite the limitations section acknowledging the possibility of missing small lesions. The feedback for episodes 1, 2, and 5 praises Blue for correctly identifying errors despite acknowledging limitations, suggesting that clear findings should override general limitations as a reason to abstain from flagging. Therefore, the second lesson encourages flagging clear contradictions even when general limitations are present, preventing a repeat of the issue in episode 4 where a visible finding was overlooked.

Accepted library:

- initial: Avoid flagging the absence of a finding when subtle image features suggest its possible presence.
- initial: When image quality or views are limited, prioritize uncertainty and avoid confident error flags.
- initial: Do not confidently flag a claim as incorrect if the image findings are open to multiple interpretations.
- initial: Acknowledge limitations of single-view radiographs when assessing findings.
- initial: Be cautious when assessing subtle differences in image density, especially when characterizing opacities.
- error detection: When an observation from a vision tool explicitly identifies a finding (e.g., a calcified nodule or cardiomegaly), and the candidate report explicitly denies or contradicts this finding, confidently flag it as a contradiction.
- limitations handling: Do not allow general limitations of plain radiographs (e.g., difficulty with precise localization or subtle findings) to prevent flagging clear contradictions when a specific finding is visible and explicitly denied by the candidate.
### Blue update 2

Episode 9 highlights the importance of prioritizing explicit denials from a vision tool when conflicting observations exist, leading to a clear contradiction flag. Episode 10 demonstrates a failure to detect a clear fabrication (pneumothorax) because the vision tool observations did not directly address it, indicating a need to ensure all significant claims are checked, not just those directly prompted by the vision tool's primary questions.

Accepted library:

- initial: Avoid flagging the absence of a finding when subtle image features suggest its possible presence.
- initial: When image quality or views are limited, prioritize uncertainty and avoid confident error flags.
- initial: Do not confidently flag a claim as incorrect if the image findings are open to multiple interpretations.
- initial: Acknowledge limitations of single-view radiographs when assessing findings.
- initial: Be cautious when assessing subtle differences in image density, especially when characterizing opacities.
- error detection: When an observation from a vision tool explicitly identifies a finding (e.g., a calcified nodule or cardiomegaly), and the candidate report explicitly denies or contradicts this finding, confidently flag it as a contradiction.
- error detection: Do not overlook significant discrepancies or fabricated findings in the candidate report, such as the addition of a pneumothorax, even if the primary focus of the vision tool observations was on other findings like cardiomegaly or pulmonary artery hypertension.
- limitations handling: Do not allow general limitations of plain radiographs (e.g., difficulty with precise localization or subtle findings) to prevent flagging clear contradictions when a specific finding is visible and explicitly denied by the candidate.
- contradiction detection: When a vision tool explicitly states the absence of a finding (e.g., 'No definite focal consolidation, pleural effusion, or pneumothorax is identified'), and the candidate report explicitly claims the presence of that finding, confidently flag it as a contradiction, even if other vision tool observations are less definitive or conflicting.
### Blue update 3

The feedback from episodes 11 and 15 reinforces the existing rule about flagging contradictions when the vision tool explicitly denies a finding that the candidate report explicitly claims. Episode 11 specifically addresses cardiomegaly, and episode 15 addresses scoliosis. These are specific instances that align with the general principle of identifying clear contradictions based on explicit vision tool observations. Episode 13's feedback was about an omission, which is not directly related to the existing rules or the new lessons derived from the other episodes, which focus on contradictions of explicit claims.

Accepted library:

- initial: Avoid flagging the absence of a finding when subtle image features suggest its possible presence.
- initial: When image quality or views are limited, prioritize uncertainty and avoid confident error flags.
- initial: Do not confidently flag a claim as incorrect if the image findings are open to multiple interpretations.
- initial: Acknowledge limitations of single-view radiographs when assessing findings.
- initial: Be cautious when assessing subtle differences in image density, especially when characterizing opacities.
- error detection: When an observation from a vision tool explicitly identifies a finding (e.g., a calcified nodule or cardiomegaly), and the candidate report explicitly denies or contradicts this finding, confidently flag it as a contradiction.
- error detection: Do not overlook significant discrepancies or fabricated findings in the candidate report, such as the addition of a pneumothorax, even if the primary focus of the vision tool observations was on other findings like cardiomegaly or pulmonary artery hypertension.
- limitations handling: Do not allow general limitations of plain radiographs (e.g., difficulty with precise localization or subtle findings) to prevent flagging clear contradictions when a specific finding is visible and explicitly denied by the candidate.
- contradiction detection: When a vision tool explicitly states the absence of a finding (e.g., 'No definite focal consolidation, pleural effusion, or pneumothorax is identified'), and the candidate report explicitly claims the presence of that finding, confidently flag it as a contradiction, even if other vision tool observations are less definitive or conflicting.
- accuracy: When a vision tool explicitly states the absence of a finding (e.g., 'The cardiothoracic ratio appears to be within normal limits') and the candidate report explicitly claims the presence of that finding (e.g., 'Mild cardiomegaly'), confidently flag it as a contradiction.
- accuracy: When a vision tool explicitly states the absence of a finding (e.g., 'The thoracic spine to be relatively straight without obvious lateral curvature') and the candidate report explicitly claims the presence of that finding (e.g., 'There is evidence of mild scoliosis'), confidently flag it as a contradiction.
