"""Descriptive metrics and readable per-case traces; no model calls or output edits."""
import json
from collections import Counter
from pathlib import Path


def main():
    root=Path('runs/open-online-20-2026-11-04')
    records=[json.loads(p.read_text()) for p in sorted((root/'episodes').glob('*.json'))]
    summary=json.loads((root/'summary.json').read_text())
    last=[r for r in records if r['index']>15]

    def agreed_valid(r):
        return len(r['reviews'])==2 and all(j['status']=='ok' and j['review']['attack_validity']=='valid' for j in r['reviews'])

    probe={}
    for name in ['initial','learned']:
        valid=[r for r in last if agreed_valid(r)]
        def verdict(r):return r['initial_probe']['blue'] if name=='initial' else r['blue']
        def control(r):return r['initial_control']['blue'] if name=='initial' else r['control']['blue']
        tp=sum(verdict(r)['decision']=='error' for r in valid)
        fn=len(valid)-tp
        fp=sum(control(r)['decision']=='error' for r in last)
        probe[name]={'paired_studies':len(last),'consensus_valid_attacks':len(valid),'detected_consensus_valid_attacks':tp,
                     'missed_or_abstained_or_invalid_on_valid_attacks':fn,'reference_control_flags':fp,
                     'attack_invalid_outputs':sum(verdict(r)['decision']=='invalid_output' for r in last),
                     'control_invalid_outputs':sum(control(r)['decision']=='invalid_output' for r in last),
                     'attack_abstentions':sum(verdict(r)['decision']=='uncertain' for r in last),
                     'control_abstentions':sum(control(r)['decision']=='uncertain' for r in last),
                     'consensus_conditioned_report_detection_f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    ends=[]
    for p in root.glob('audit/*/calls.jsonl'):
        for line in p.read_text().splitlines():
            r=json.loads(line)
            if r['event']=='end':ends.append(r)
    costs={'accounted_cost_usd':summary['accounted_cost_usd'],'known_reported_call_cost_usd':sum(r['accounted_cost_usd'] for r in ends if r['cost_known']),
           'unknown_cost_reserves_usd':sum(r['accounted_cost_usd'] for r in ends if not r['cost_known']),
           'audited_calls_including_cache':len(ends),'failed_requests':dict(Counter(r['exception_type'] for r in ends if r.get('exception_type')))}
    memories={role:[json.loads(p.read_text()) for p in sorted((root/'memories'/role).glob('*.json'))] for role in ['red','blue']}
    analysis={'summary':summary,'paired_probe':probe,'costs':costs,'memory_updates':{
     role:{'versions':len(values),'proposed_lessons':sum(len(v['lessons']) for v in values),
           'rejected_lessons':sum(len(v['rejected']) for v in values),
           'final_rules':sum(len(v) for v in values[-1]['library'].values()) if values else None} for role,values in memories.items()},
     'metric_scope':'Report-level detection on final five cases with consensus-valid attacks and unchanged reference controls; not clinical accuracy. Invalid outputs retained as failures. Judge disagreement not counted as attacker success.'}
    (root/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    lines=['# Open-ended online learning: results and interpretation','',
           f"Completed {len(records)}/20 studies. Counts below are descriptive; judge consensus is not clinical ground truth.",'',
           '## Overall outcomes','','```json',json.dumps(summary['counts'],indent=2),'```','',
           '## Matched final-five probe','','| Blue memory | Valid attacks detected | Reference controls flagged | Attack abstentions | Invalid attack outputs | Conditional report F1 |',
           '| --- | --- | --- | --- | --- | --- |']
    for label,m in probe.items():
        lines.append(f"| {label} | {m['detected_consensus_valid_attacks']}/{m['consensus_valid_attacks']} | {m['reference_control_flags']}/{m['paired_studies']} | {m['attack_abstentions']} | {m['attack_invalid_outputs']} | {m['consensus_conditioned_report_detection_f1']} |")
    lines+=['',analysis['metric_scope'],
            'The final five never update memory. Both checkpoints see identical saved candidates/images/indications and the same verdict method. Earlier round differences confound case mix and changing Red behavior.',
            'Report-level error detection does not certify that Blue found the injected issue. Reviewer assessments and evidence traces must be examined separately.',
            'Flash also serves as one reviewer, sharing a family with contestants. This limits reviewer independence. Human calibration and an independent judge family are needed before clinical accuracy claims.',
            'Two protocol amendments handled an uncited Blue output after case six; all rejected outputs remain on tape. Invalid outputs are not scored as clean reports or used as trusted learning examples.','','## Cost','','```json',json.dumps(costs,indent=2),'```','',
            'Reported call cost may include cache accounting. The full ledger retains reserves for unknown failed requests and stays within the $3 cap.','','## Memory updates','']
    for role,versions in memories.items():
        for i,m in enumerate(versions,1):
            lines += [f'### {role.title()} update {i}','',m['explanation'],'','Accepted library:','']
            for category,rules in m['library'].items():
                lines += ['- '+category+': '+rule for rule in rules]
            if m['rejected']:lines+=['','Rejected proposals:','```json',json.dumps(m['rejected'],indent=2),'```']
    (root/'analysis.md').write_text('\n'.join(lines)+'\n')
    walk=['# All twenty open-ended episodes','',
          'Researcher trace: the agents did not see each other\'s private notes. Explanations are observable outputs, not hidden model reasoning.','']
    for r in records:
        walk += [f"## {r['index']}. Study {r['study_id']}",'',f"Indication: {r['indication']}",'',
                 '### Source report (hidden from Blue during the attack attempt)','','```text','\n'.join(s['id']+': '+s['text'] for s in r['source']),'```','',
                 '### Red candidate','','```text','\n'.join(s['id']+': '+s['text'] for s in r['candidate']),'```','',
                 'Red explanation: '+r['rationale'],'','Changes:','```json',json.dumps(r['changes'],indent=2),'```','',
                 '### Blue verdict and evidence','','```json',json.dumps({'verdict':r['blue'],'observations':r['observations'],'control':r['control']['blue']},indent=2),'```','']
        for j in r['reviews']:
            walk += ['### Reviewer: '+j['model'],'','```json',json.dumps(j,indent=2),'```','']
    (root/'walkthrough.md').write_text('\n'.join(walk)+'\n')
    print(json.dumps({'counts':summary['counts'],'paired_probe':probe,'cost':costs},indent=2))


if __name__ == "__main__":
    main()
