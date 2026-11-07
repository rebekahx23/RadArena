"""Paired 2x2 model/architecture pilot on saved attacks; $1.50 global cap."""
import hashlib
import json
import os
from pathlib import Path
import dspy
from radarena.agents import BlueVerifier
from radarena.structured_blue import StructuredBlueVerifier
from radarena.data import Sentence
from radarena.evaluate import metrics
from radarena.knowledge import load_pack
from radarena.memory import load_memory
from radarena.runtime import make_models
from radarena.tracing import AuditSession,audit_context

root=Path('runs/stronger-blue-2026-11-04')
root.mkdir(parents=True,exist_ok=True)
source=Path('runs/red-blue-judge-10-2026-11-04')
uids=['37','1656','3768']
inputs=[]
for uid in uids:
    for condition in ['attack','control']:
        p=source/f'study-{uid}.{condition}.json'
        record=json.loads(p.read_text());inputs.append((f'{uid}.{condition}',record))
        for image in record['image_paths']:
            expected=json.loads((source/'organizer/selected_cases.json').read_text())
            case=next(c for c in expected if c['study_id']==uid)
            assert hashlib.sha256(Path(image).read_bytes()).hexdigest()==case['image_sha256'][case['image_paths'].index(image)]
rules,memory=load_memory(Path('runs/learning-pilot-2026-11-04/memories/blue/v3.json'),'blue')
pack=load_pack(Path('knowledge/reporting_v1.json'))
meta={'study_ids':uids,'source':str(source),'source_files_sha256':{key:hashlib.sha256((source/f'study-{key}.json').read_bytes()).hexdigest() for key,_ in inputs},
      'total_cap_usd':1.5,'max_checks':2,'memory':memory,'knowledge':pack.metadata(),
      'implementation':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/radarena').glob('*.py')},
      'limitation':'Three dev studies. Saved Red severity edit 3768 violates requested family; this tests detection of the fixed edit, not clean severity accuracy. Prior Judge shares Flash family and is not an independent grader here.'}
mp=root/'metadata.json'
if mp.exists():assert json.loads(mp.read_text())==meta,'Use a new output directory after code/config changes'
else:mp.write_text(json.dumps(meta,indent=2)+'\n')
(root/'cases.json').write_text(json.dumps(dict(inputs),indent=2)+'\n')

def costs():return sum(json.loads(p.read_text())['accounted_cost_usd'] for p in root.glob('*/audit/budget.json'))

def grade(key,original,record):
    edits=original['private_attack']['edits']
    return dict(record,case_id=key,study_id=original['study_id'],variant='blue_tools',status='ok',
                private_label={'has_error':bool(edits),'changed_sentence_ids':[e['sentence_id'] for e in edits],
                    'error_type':original['private_attack']['requested_error_type']})

base=root/'gemma_legacy';base.mkdir(exist_ok=True)
(base/'predictions.jsonl').write_text(''.join(json.dumps(grade(key,r,{'verdict':r['blue'],'observations':r['observations'],'provenance':'reused saved baseline; no new model call'}))+'\n' for key,r in inputs))
for arm,model,structured in [('flash_legacy','google/gemini-2.5-flash',False),('gemma_structured','google/gemma-3-27b-it',True),('flash_structured','google/gemini-2.5-flash',True)]:
    directory=root/arm;directory.mkdir(exist_ok=True)
    audit_dir=directory/'audit'
    own=json.loads((audit_dir/'budget.json').read_text())['accounted_cost_usd'] if (audit_dir/'budget.json').exists() else 0
    cap=min(1,1.5-costs()+own)
    os.environ['RADARENA_TEXT_MODEL']=model;os.environ['RADARENA_VISION_MODEL']=model
    with audit_context(AuditSession(audit_dir,cap,60)) as _:
        from radarena.tracing import ACTIVE_AUDIT
        audit=ACTIVE_AUDIT.get()
        text,vision=make_models()
        for key,original in inputs:
            path=directory/(key+'.json')
            if path.exists():continue
            audit.set_context(case_id=key,study_id=original['study_id'],variant=arm,role='verifier')
            try:
                verifier=(StructuredBlueVerifier if structured else BlueVerifier)(text_lm=text,vision_lm=vision,max_checks=2)
                out=verifier(candidate=[Sentence.model_validate(s) for s in original['candidate']],
                    images=[dspy.Image.from_path(p) for p in original['image_paths']],
                    clinical_context=original['clinical_context'],strategies=rules,report_claims=[],reference_notes=pack.render('verifier'))
                row=grade(key,original,{'verdict':out.verdict.model_dump(),'observations':out.observations,
                                      'claim_assessments':getattr(out,'assessments',[])})
                path.write_text(json.dumps(row,indent=2)+'\n')
                print(arm,key,'complete',flush=True)
            except Exception as exc:
                with (root/'failures.jsonl').open('a') as f:f.write(json.dumps({'arm':arm,'case':key,'exception_type':type(exc).__name__})+'\n')
                raise RuntimeError(f'{arm} {key} failed ({type(exc).__name__}); explicit resume supported') from exc
    (directory/'predictions.jsonl').write_text(''.join(json.dumps(json.loads((directory/(key+'.json')).read_text()))+'\n' for key,_ in inputs))
result={'arms':{},'new_audited_cost_usd':costs(),'limitations':meta['limitation']}
lines=['# Stronger-model and evidence-ledger pilot','','| Arm | Completed | Localization F1 | Edit recall | Control FPR | Abstention |','| --- | --- | --- | --- | --- | --- |']
for arm in ['gemma_legacy','flash_legacy','gemma_structured','flash_structured']:
    rows=[json.loads(x) for x in (root/arm/'predictions.jsonl').read_text().splitlines()]
    m=metrics(rows,6);result['arms'][arm]=m
    lines.append(f"| {arm} | {m['completed']}/6 | {m['localization_f1_completed']:.3f} | {m['detection_recall']:.3f} | {m['false_positive_rate_completed_controls']:.3f} | {m['abstention_rate_completed']:.3f} |")
lines+=['',meta['limitation'],'',f'New audit accounting: ${costs():.6f}, including unknown-cost reserves.']
(root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
(root/'results.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
