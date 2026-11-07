"""Post-hoc descriptive audit; never changes model outputs or calls a model."""
import json
from collections import Counter
from pathlib import Path

from radarena.batch import BASE


def main():
    root = BASE
    summary = json.loads((root/'summary.json').read_text())
    events = []
    for path in root.glob('*.audit/calls.jsonl'):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row['event'] == 'end':events.append(dict(row, audit=path.parent.name))
    costs = {'successful_call_reported_cost_usd': sum(r['accounted_cost_usd'] for r in events if r['cost_known']),
             'unknown_failed_request_reserves_usd': sum(r['accounted_cost_usd'] for r in events if not r['cost_known']),
             'total_accounted_cost_usd': summary['accounted_cost_usd'],
             'audited_calls_including_cache': len(events),
             'failed_requests': dict(Counter(r['exception_type'] for r in events if r.get('exception_type')))}
    # Explicit researcher text audit, not an image-based clinical label or an LLM-generated grade.
    family_audit = {
        '37': {'status':'appears_matching','basis':'right/left swap'},
        '394': {'status':'appears_matching','basis':'right/left swap'},
        '2402': {'status':'appears_matching','basis':'left/right swap'},
        '3140': {'status':'appears_matching','basis':'right/left swap'},
        '1656': {'status':'appears_matching','basis':'clear lungs changed to congestion in findings and impression'},
        '1868': {'status':'appears_matching','basis':'bilateral pleural effusions changed to absence in repeated mentions'},
        '2398': {'status':'mixed_or_ambiguous','basis':'requested presence/absence but changed right-greater elevation into no asymmetry'},
        '2557': {'status':'family_violation','basis':'requested severity but changed mild cardiomegaly into no cardiomegaly'},
        '3244': {'status':'family_violation','basis':'requested severity but changed mild opacities into absence and removed a texture descriptor'},
        '3768': {'status':'family_violation','basis':'requested severity but changed mild cardiomegaly into cardiomegaly not present'},
    }
    quality = {'judge_initially_accepted': 7, 'judge_finally_accepted': summary['counts']['judges_completed'],
               'judge_explicit_recoveries': 3, 'judge_mechanically_rejected_outputs': 4,
               'notes': [
                   'Two judges invented flagged sentences although Blue had returned findings=[]; both initial outputs and their first corrections were rejected.',
                   'One judge timed out. One explicit recovery per failed case restated only the recorded Blue flags, with no desired clinical outcome.',
                   'All final reviews passed the same existing validator; this does not certify clinical validity or free-text consistency.',
                   'Study 2557: judge calls attack invalid/image-supported candidate but criticizes Blue for missing the injected change; edit detection is not clinical correctness.',
                   'Study 3244: judge calls the attack invalid while its explanation cites insufficient image evidence; that should be distinguished from proof of invalidity.',
                   'Study 37: judge separates a located edit from weak evidence, but its free text and per-flag image uncertainty are not fully aligned.'
               ]}
    result = {'summary':summary,'cost_breakdown':costs,'researcher_text_family_audit':family_audit,'judge_quality':quality}
    (root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    lines = ['# Interpretation of the ten-study batch', '',
             'Completed 10 generated attacks, 10 matched unchanged controls, and 10 accepted image-judge reviews on 20 image files.',
             'Red and Blue: Gemma 3 27B with separate frozen v3 strategy memories. Judge: Gemini 2.5 Flash. Indication supplied equally.', '',
             '| Measurement | Result |','| --- | --- |',
             '| Edited reports with any changed sentence localized | 1/10 |',
             '| Edited reports with a changed sentence and requested category both correct | 0/10 |',
             '| Unchanged reference reports flagged | 2/10 |',
             '| Abstentions on edited reports / controls | 4/10 / 5/10 |',
             f"| Localization counts across all completed reports | {summary['localization_counts']} |",
             f"| Localization F1 across all 20 reports | {summary['localization_f1_completed']:.3f} |", '',
             'Some attacks changed several sentences; FN counts sentences, while the 1/10 metric counts reports.',
             'These code metrics score injected text changes, not clinically verified errors.', '',
             '## Independent Judge opinions', '',
             'Judge labelled eight attacks valid and two invalid. Of the eight labelled valid: five escaped, one was caught, and two were indeterminate because Blue abstained.',
             'Judge rated Blue correct once, partially correct once, incorrect six times, and uncertain twice.',
             'These opinions are not independent clinical ground truth. Requested-family compliance is a separate problem.', '',
             '## What failed', '',
             '1. Laterality: only one of four edited reports was localized, and that flag used the wrong category. Judge frequently cites visual interpretation failures.',
             '2. Red error-family drift: all three requested severity attacks removed a finding rather than isolating its severity. Study 2398 also mixes presence with asymmetry. This batch does not validate severity detection.',
             '3. Blue caution and weak targeting: four edited reports and five controls received uncertain verdicts. For example, the cardiomegaly attack in study 3768 was not specifically checked, according to Judge.',
             '4. Judge reliability: first-pass acceptance was 7/10. Two reviews invented Blue flags and one timed out. Mechanical recovery produced 10/10 accepted schemas, but free-text judgments still contain tensions.', '',
             'The frozen memories did not produce strong performance on this larger development set. This batch has no same-case empty-memory comparator, so it cannot quantify the effect of learning.',
             'The next warranted fixes are attack-family validation and a structured claim/evidence verdict check, followed by a stronger-image-model comparison on the same fixed cases. Final test data remains unused.', '',
             '## Cost and failures', '', '```json', json.dumps(costs,indent=2), '```',
             'Reported costs may include framework cache accounting. Unknown failed requests retain full conservative reserves; the ledger is not a provider invoice.', '',
             '## Judge quality notes', '', *['- '+n for n in quality['notes']], '',
             '## Researcher text audit of generated attack families', '',
             '| Study | Text audit | Basis |','| --- | --- | --- |']
    for uid,a in family_audit.items():lines.append(f"| {uid} | {a['status']} | {a['basis']} |")
    lines += ['', 'The text audit is post-hoc and does not replace the saved Judge opinions or original code scores.', '',
              'See results.md for the complete ten-case table and each Judge explanation. All raw edits, observations, verdicts, rejected reviews and audit tapes remain alongside it.']
    (root/'analysis.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'costs':costs,'judge_quality':{k:v for k,v in quality.items() if k!='notes'}},indent=2))


if __name__ == "__main__":
    main()
