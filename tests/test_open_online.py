from types import SimpleNamespace
import hashlib
import json

import pytest
from PIL import Image
from dspy.utils.dummies import DummyLM
from radarena.open_online import validate_attack, validate_blue, private_feedback, promote


def test_open_rewrites_omissions_and_additions_have_exact_provenance():
    old=[{'id':'s1','text':'Effusion.'},{'id':'s2','text':'Normal heart.'}]
    new=[{'id':'s2','text':'Normal heart.'},{'id':'a1','text':'Opacity.'}]
    changes=[{'source_ids':['s1'],'candidate_ids':['a1'],'category':'substitution','description':'Finding swap'}]
    assert validate_attack(old,new,changes)
    with pytest.raises(ValueError):validate_attack(old,new,[])
    assert not validate_attack(old,old,[])


def test_open_blue_can_flag_missing_claim_at_report_level_but_needs_real_evidence():
    verdict={'decision':'error','findings':[{'sentence_id':'report_level','error_type':'omission','evidence':'Visible finding absent from report','tool_call_ids':['vision_1']}],'limitations':''}
    assert validate_blue(verdict,[{'id':'s1','text':'Normal.'}],[{'tool_call_id':'vision_1'}]).decision=='error'
    with pytest.raises(ValueError):validate_blue(verdict,[{'id':'s1','text':'Normal.'}],[])


def test_feedback_and_promotion_are_role_scoped_and_evidence_gated():
    r={'changes':[],'rationale':'RED PRIVATE','candidate':[],'blue':{'decision':'uncertain'},'observations':['BLUE OBSERVATION']}
    j={'attack_validity':'valid','blue_assessment':'uncertain','blue_explanation':'Ambiguous'}
    c={'blue':{'decision':'uncertain'},'observations':[]}
    assert 'RED PRIVATE' not in str(private_feedback('blue','1',r,j,c))
    assert 'BLUE OBSERVATION' not in str(private_feedback('red','1',r,j,c))
    old={'laterality':['Check both sides.']}
    lessons=[{'category':'severity','rule':'Inspect degree explicitly.','supporting_episode_ids':['1']},
             {'category':'bad','rule':'Compare against original report','supporting_episode_ids':['1']},
             {'category':'bad','rule':'Ignore the report','supporting_episode_ids':['2']}]
    new,rejected=promote(old,lessons,['1'])
    assert new['laterality']==old['laterality'] and new['severity']==['Inspect degree explicitly.']
    assert len(rejected)==2


@pytest.mark.parametrize('bad_first_assessment',[False,True])
def test_full_twenty_episode_protocol_and_resume_offline(tmp_path,monkeypatch,bad_first_assessment):
    import radarena.open_online as m
    root=tmp_path/'run';root.mkdir()
    image=tmp_path/'fixture.png';Image.new('RGB',(8,8)).save(image)
    rows=[{'study_id':str(i),'sentences':[{'id':'s1','text':'No effusion.'}],'image_paths':[str(image)],
           'image_sha256':[hashlib.sha256(image.read_bytes()).hexdigest()]} for i in range(20)]
    (root/'selection.json').write_text(json.dumps(rows))
    monkeypatch.setattr(m,'Indications',lambda _:SimpleNamespace(get=lambda uid:'Fixture indication',metadata=lambda:{}))
    monkeypatch.setattr(m,'load_pack',lambda _:SimpleNamespace(render=lambda role:'Reference',metadata=lambda:{}))
    monkeypatch.setattr(m,'load_memory',lambda path,role:([role.upper()+' PRIVATE RULE'],{}))
    import radarena.memory_policy as policy
    calibration=[dict(rows[0],study_id='cal-'+str(i),candidate=[{'id':'s1','text':'Effusion.'}]) for i in range(3)]
    monkeypatch.setattr(policy,'load_calibration',lambda path,selection:calibration)
    lm=DummyLM([]);monkeypatch.setattr(m,'make_judge_model',lambda model:lm)
    calls=[]
    assess_count=[0]
    class FakePredict:
        def __init__(self,signature):self.signature=signature
        def set_lm(self,lm):pass
        def __call__(self,**kw):
            calls.append(self.signature.__name__)
            if self.signature is m.OpenAttack:
                assert 'BLUE PRIVATE RULE' not in str(kw)
                return SimpleNamespace(candidate=[{'id':'s1','text':'Effusion.'}],changes=[{'source_ids':[],'candidate_ids':['s1'],'category':'presence','description':'Remove negation'}],rationale='RED PRIVATE RATIONALE')
            if self.signature is m.PlanChecks:return SimpleNamespace(questions=['Describe the pleura.'])
            if self.signature is m.InspectImage:return SimpleNamespace(observation='Fixture pixels.',limitations='Synthetic')
            if self.signature is m.OpenAssess:
                assess_count[0]+=1
                if bad_first_assessment and assess_count[0]<=2:
                    return SimpleNamespace(verdict={'decision':'error','findings':[{'sentence_id':'s1','error_type':'presence','evidence':'Uncited fixture','tool_call_ids':[]}],'limitations':'Fixture'})
                assert 'RED PRIVATE' not in str(kw)
                if bad_first_assessment and calls.count('OpenAssess')<=2:
                    return SimpleNamespace(verdict={'decision':'error','findings':[{'sentence_id':'s1','error_type':'omission','evidence':'Uncited','tool_call_ids':[]}],'limitations':'Fixture'})
                return SimpleNamespace(verdict={'decision':'uncertain','findings':[],'limitations':'Fixture'})
            if self.signature is m.ReviewOpen:return SimpleNamespace(review={'attack_validity':'valid','attack_explanation':'Fixture','blue_assessment':'uncertain','reviewed_flag_ids':kw['actual_blue_flag_ids'],'blue_explanation':'Unclear','failure_modes':[],'confidence':'low','limitations':'Not real medicine'})
            if self.signature is policy.ReviewMemory:
                return SimpleNamespace(review={'checked_rule_ids':list(kw['rules']),
                    'unsafe_or_conflicting_rule_ids':[],'uncertain_rule_ids':[],'explanation':'Fixture compatible'})
            if self.signature is m.UpdateLessons:
                if kw['role']=='blue':assert 'RED PRIVATE' not in str(kw)
                return SimpleNamespace(lessons=[{'category':'general','rule':'Check uncertain claims carefully.','supporting_episode_ids':[kw['trusted_feedback'][0]['episode_id']]}],explanation='General lesson')
            raise AssertionError(self.signature)
    monkeypatch.setattr(m.dspy,'Predict',FakePredict)
    result=m.run(root)
    assert result['complete'] and result['counts']['episodes']==20
    assert result['counts']['accepted_reviews']==40
    first=json.loads(next((root/'episodes').glob('01-*.json')).read_text())
    assert first['declared_changes'][0]['source_ids']==[]
    assert first['changes'][0]['source_ids']==['s1']
    assert first['provenance_validation_error']
    assert result['counts']['blue_invalid']==int(bad_first_assessment)
    if bad_first_assessment:
        first=json.loads((root/'episodes/01-0.json').read_text())
        assert first['status']=='invalid_output' and len(first['attempts'])==2
        assert not first['blue']['findings']
        assert len(list((root/'audit/01-0-blue').glob('blue-assessment-attempt-*.json')))==2
    assert result['final_five_paired_probe']['initial']['reports']==5
    assert len(list((root/'memories/blue').glob('*.json')))==3
    for role in ['red','blue']:
        checkpoint=json.loads((root/f'memories/{role}/v3.json').read_text())
        assert not checkpoint['promotion']['promoted']  # identical mock performance never earns promotion
        assert checkpoint['library']=={'initial':[role.upper()+' PRIVATE RULE']}
    n=len(calls);assert m.run(root)['complete'];assert len(calls)==n


def test_textual_contradiction_and_image_findings_have_distinct_citation_rules():
    candidate=[{'id':'s5','text':'No pneumothorax.'},{'id':'a1','text':'Small right pneumothorax.'}]
    text={'sentence_id':'s5','error_type':'contradiction','evidence':'These statements disagree.',
          'tool_call_ids':[],'evidence_type':'report_text','report_sentence_ids':['s5','a1']}
    image={'sentence_id':'a1','error_type':'fabrication','evidence':'Image observation contradicts this claim.',
           'tool_call_ids':['vision_2'],'evidence_type':'image'}
    verdict={'decision':'error','findings':[text,image],'limitations':'Image interpretation still fallible.'}
    assert len(validate_blue(verdict,candidate,[{'tool_call_id':'vision_2'}]).findings)==2
    for ids in [['s5'],['s5','missing'],['s5','s5']]:
        broken=dict(verdict,findings=[dict(text,report_sentence_ids=ids)])
        with pytest.raises(ValueError):validate_blue(broken,candidate,[])
    with pytest.raises(ValueError):validate_blue(dict(verdict,findings=[dict(image,tool_call_ids=[])]),candidate,[])


def test_assessment_repairs_once_and_preserves_rejected_response():
    from radarena.open_online import assess_with_correction
    candidate=[{'id':'s1','text':'Opacity.'}]
    bad={'decision':'error','findings':[{'sentence_id':'s1','error_type':'contradiction','evidence':'Claim','tool_call_ids':[]}],'limitations':''}
    feedback=[];retained=[]
    def assess(correction):
        feedback.append(correction)
        return SimpleNamespace(verdict=bad if len(feedback)==1 else {'decision':'uncertain','findings':[],'limitations':'Insufficient evidence'})
    result=assess_with_correction(assess,candidate,[],lambda n,a:retained.append(a))
    assert result['status']=='ok' and len(feedback)==2
    assert retained[0]['verdict']==bad and not retained[0]['accepted']
    assert retained[1]['accepted'] and feedback[1]['available_sentence_ids']==['s1']
