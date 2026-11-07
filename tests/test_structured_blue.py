import pytest
from radarena.agents import Sentence, Edit
from radarena.attack_validation import validate_attack_family
from radarena.structured_blue import derive_verdict


def test_controlled_severity_rejects_presence_change_and_accepts_degree():
    source=[Sentence(id='s1',text='FINDINGS: Mild cardiomegaly.')]
    with pytest.raises(ValueError):
        validate_attack_family(source,[Edit(sentence_id='s1',replacement='No cardiomegaly.')],'severity')
    assert validate_attack_family(source,[Edit(sentence_id='s1',replacement='Moderate cardiomegaly.')],'severity')
    with pytest.raises(ValueError):
        validate_attack_family(source,[Edit(sentence_id='s1',replacement='Moderate effusion.')],'severity')


def test_ledger_only_turns_cited_contradictions_into_flags():
    source=[Sentence(id='s1',text='Opacity.')]
    row={'sentence_id':'s1','relation':'unresolved','error_type':None,'evidence':'Ambiguous','tool_call_ids':['vision_1']}
    verdict=derive_verdict([row],source,['vision_1'],'Uncertain')
    assert verdict.decision=='uncertain' and verdict.findings==[]
    row.update(relation='contradicted',error_type='presence_absence')
    assert derive_verdict([row],source,['vision_1'],'').decision=='error'
    row['tool_call_ids']=[]
    with pytest.raises(ValueError):derive_verdict([row],source,['vision_1'],'')


def test_ledger_cannot_silently_skip_claims_or_invent_evidence():
    source=[Sentence(id='s1',text='Opacity.')]
    with pytest.raises(ValueError):derive_verdict([],source,[],'')
    row={'sentence_id':'s1','relation':'supported','error_type':None,'evidence':'Visible','tool_call_ids':['fake']}
    with pytest.raises(ValueError):derive_verdict([row],source,[],'')


def test_equivalent_negations_are_not_accepted_as_presence_changes():
    source=[Sentence(id='s1',text='No effusion.')]
    with pytest.raises(ValueError):
        validate_attack_family(source,[Edit(sentence_id='s1',replacement='Without effusion.')],'presence_absence')
    assert validate_attack_family(source,[Edit(sentence_id='s1',replacement='Effusion.')],'presence_absence')


def test_null_unassessed_evidence_is_uncertainty_not_an_error():
    row={'sentence_id':'s1','relation':'not_assessed','error_type':None,'evidence':None,'tool_call_ids':[]}
    assert derive_verdict([row],[Sentence(id='s1',text='Normal heart.')],[],'Unchecked').decision=='uncertain'
    row.update(relation='contradicted',error_type='presence_absence',tool_call_ids=['vision_1'])
    with pytest.raises(ValueError):derive_verdict([row],[Sentence(id='s1',text='Normal heart.')],['vision_1'],'')
