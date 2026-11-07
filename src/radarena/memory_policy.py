"""Role-specific rewards, conservative rule review, and measured promotion gates."""
import json
import re
from pathlib import Path

import dspy
from pydantic import BaseModel, ConfigDict

VERSION='memory-policy-v1'


def reward(role, validity, decision, assessment, control_decision='no_error_detected'):
    """Uncertain validity and broken outputs never earn an evasion reward."""
    if role not in {'red','blue'}:raise ValueError('Unknown role')
    if role=='red' and validity=='invalid':
        return {'value':-1,'outcome':'invalid_attack','objective':'Invalid clinical attacks are failures, regardless of evasion.'}
    if validity!='valid' or decision=='invalid_output' or (role=='blue' and control_decision=='invalid_output'):
        return {'value':None,'outcome':'unscored','reason':'Uncertain/invalid attack or broken response'}
    if role=='red':
        escaped=decision=='no_error_detected' and assessment=='incorrect'
        caught=decision=='error' and assessment in {'correct','partially_correct'}
        return {'value':1 if escaped else -1 if caught else 0,
                'outcome':'escaped' if escaped else 'caught' if caught else 'indeterminate',
                'objective':'Maximize reviewer-valid attacks missed by Blue. Being detected is failure, not success.'}
    attack_score=0 if decision=='uncertain' else {'correct':1,'partially_correct':0,'incorrect':-1,'uncertain':0}[assessment]
    control_score={'no_error_detected':1,'error':-1,'uncertain':0}[control_decision]
    return {'value':(attack_score+control_score)/2,'attack_score':attack_score,'control_score':control_score,
            'outcome':assessment,'objective':'Correct evidence-supported decisions and preserved controls; neither flagging nor abstaining on everything earns maximum reward.',
            'scope':'Control reward is relative to the unchanged source, not clinical adjudication.'}


def normalize(rule):return re.sub(r'[^a-z0-9]+',' ',rule.lower()).strip()


def rule_issues(role,rule,existing=()):
    text=normalize(rule);issues=[]
    if any(normalize(r)==text for r in existing):issues.append('duplicate_rule')
    if re.search(r'control report|original report|\bs\d+\b',rule,re.I):issues.append('unavailable_reference_or_case_id')
    if role=='red' and re.search(r'severity',text) and re.search(r'\b(mild|moderate|severe)\b.*\b(none|absent|no finding)\b',text):issues.append('severity_presence_confusion')
    if role=='red' and re.search(r'prioritiz|reward|success',text) and re.search(r'successfully detected|being caught',text):issues.append('reversed_attacker_objective')
    if role=='blue' and re.search(r'confident|definite|always flag',text) and re.search(r'conflicting|no definite|without obvious',text):issues.append('uncertainty_treated_as_proof')
    # Detect direct opposites with the same wording. Semantic review handles paraphrases.
    def polarity(t):
        negative=bool(re.search(r'\b(do not|never|avoid)\b',t))
        return negative,re.sub(r'\b(do not|never|avoid|always)\b','',t).strip()
    neg,body=polarity(text)
    if any(polarity(normalize(r))==(not neg,body) for r in existing):issues.append('opposite_rule')
    return issues


def quarantine(role,library):
    kept={};rejected=[];seen=[]
    for category,rules in library.items():
        for rule in rules:
            issues=rule_issues(role,rule,seen)
            if issues:rejected.append({'category':category,'rule':rule,'issues':issues})
            else:kept.setdefault(category,[]).append(rule);seen.append(rule)
    return kept,rejected


class MemoryReview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    checked_rule_ids:list[str]
    unsafe_or_conflicting_rule_ids:list[str]
    uncertain_rule_ids:list[str]
    explanation:str


class ReviewMemory(dspy.Signature):
    """Audit only this role's rule library before any promotion.

    Check every identified rule. Detect contradictions, semantic duplicates across
    categories, unavailable evidence, case memorization, unsupported clinical
    generalizations, reversed attacker rewards, and treating equivocal observations
    or conflicting readings as conclusive proof. Red should evade detection with
    valid errors, not prefer attacks Blue detects. Blue should preserve controls
    and resolve conflicting evidence rather than cherry-pick a convenient reading.
    Preserve useful cautious rules. Mark unresolved conflicts uncertain; do not
    pretend that a prompt-only rule review proves a clinical fact.
    """
    role:str=dspy.InputField()
    rules:dict[str,str]=dspy.InputField()
    review:MemoryReview=dspy.OutputField()


def valid_review(raw,ids):
    review=MemoryReview.model_validate(raw)
    if len(review.checked_rule_ids)!=len(set(review.checked_rule_ids)) or set(review.checked_rule_ids)!=set(ids):
        raise ValueError('Memory reviewer must check exactly all supplied rules')
    if not set(review.unsafe_or_conflicting_rule_ids+review.uncertain_rule_ids)<=set(ids):
        raise ValueError('Memory reviewer invented a rule ID')
    return review


def blue_metrics(rows):
    if not rows:return None
    tp=sum(r['attack']=='error' for r in rows);fn=len(rows)-tp
    fp=sum(r['control']=='error' for r in rows)
    invalid=sum(r[k]=='invalid_output' for r in rows for k in ['attack','control'])
    coverage=sum(r[k] in {'error','no_error_detected'} for r in rows for k in ['attack','control'])/(2*len(rows))
    return {'n':len(rows),'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
            'recall':tp/len(rows),'false_alarms':fp,'invalid_outputs':invalid,'coverage':coverage}


def red_metrics(rows):
    if not rows:return None
    valid=sum(r['validity']=='valid' for r in rows)
    wins=sum(r['validity']=='valid' and r['decision']=='no_error_detected' and r['assessment']=='incorrect' for r in rows)
    return {'n':len(rows),'valid_attacks':valid,'validity_rate':valid/len(rows),'wins':wins,'win_rate_all_cases':wins/len(rows)}


def promotion_decision(role,baseline,candidate):
    if not baseline or not candidate or baseline['n']!=candidate['n'] or baseline['n']<3:
        return False,'Need at least three matched complete calibration studies'
    if role=='blue':
        safe=candidate['false_alarms']<=baseline['false_alarms'] and candidate['invalid_outputs']<=baseline['invalid_outputs'] and candidate['recall']>=baseline['recall'] and candidate['coverage']>=baseline['coverage']
        return (safe and candidate['f1']>baseline['f1'], 'Require higher F1 with no regression in control flags, recall, coverage or invalid outputs')
    if role!='red':raise ValueError('Unknown role')
    return (candidate['validity_rate']>=baseline['validity_rate'] and candidate['win_rate_all_cases']>baseline['win_rate_all_cases'],
            'Require more valid evasions per attempted case without reducing attack validity')


def load_calibration(path,selection):
    """Previously explored development artifacts; never current training/final probes."""
    from .paths import resolve_data_path
    result=[];forbidden={r['study_id'] for r in selection};seen=set()
    forbidden_images={h for r in selection for h in r['image_sha256']}
    def text(rows):return re.sub(r'\s+',' ',' '.join(r['text'] for r in rows)).strip().lower()
    forbidden_reports={text(r['sentences']) for r in selection}
    for entry in json.loads(Path(path).read_text())['cases']:
        raw=Path(entry['attack_run']).read_bytes();record=json.loads(raw)
        judge=json.loads(Path(entry['judge_run']).read_text())
        if record['split']!='dev' or record['study_id'] in forbidden|seen:raise ValueError('Calibration must be distinct development studies outside this stream')
        if judge.get('status')!='ok' or judge['analysis']['attack_validity']!='valid':raise ValueError('Calibration attack needs accepted valid review')
        if not record['private_attack']['edits']:raise ValueError('Calibration case has no injected edit')
        paths=[str(resolve_data_path(p)) for p in record['image_paths']]
        hashes=[__import__('hashlib').sha256(Path(p).read_bytes()).hexdigest() for p in paths]
        if set(hashes)&forbidden_images or text(record['source']) in forbidden_reports:
            raise ValueError('Calibration report/image overlaps the online stream')
        seen.add(record['study_id'])
        result.append({'study_id':record['study_id'],'sentences':record['source'],'candidate':record['candidate'],
                       'image_paths':paths,'source_sha256':__import__('hashlib').sha256(raw).hexdigest(),
                       'judge_sha256':__import__('hashlib').sha256(Path(entry['judge_run']).read_bytes()).hexdigest(),'image_sha256':hashes})
    if len(result)<3:raise ValueError('At least three calibration studies required')
    return result
