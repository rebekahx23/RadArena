import json

import dspy
import pytest
from dspy.utils.dummies import DummyLM
from PIL import Image

from radarena.clinical_context import Indications
from radarena.evaluate import verify_case


def test_indication_allowlist_hash_missing_and_duplicates(tmp_path):
    path = tmp_path / 'reports.csv'
    path.write_text('uid,indication,MeSH,Problems,comparison\n1,Cough,SECRET,SECRET,SECRET\n2,,,,\n')
    store = Indications(path)
    assert store.get('1') == 'Cough'
    assert store.get('2') == ''
    assert store.metadata()['reports_with_indication'] == 1
    assert 'SECRET' not in json.dumps(store.metadata()) + str(store.values)
    with pytest.raises(ValueError, match='missing'):
        store.get('3')
    original_hash = store.sha256
    path.write_text(path.read_text().replace('Cough', 'Fever'))
    assert Indications(path).sha256 != original_hash
    path.write_text('uid,indication\n1,Cough\n1,Fever\n')
    with pytest.raises(ValueError, match='duplicate'):
        Indications(path)


@pytest.mark.parametrize('variant', ['text_only', 'direct_vlm', 'blue_tools'])
def test_context_reaches_verifier_without_private_answers(tmp_path, variant):
    image = tmp_path / 'image.png'
    Image.new('RGB', (8, 8)).save(image)
    case = {'candidate': [{'id': 's1', 'text': 'No effusion.'}], 'image_paths': [str(image)],
            'source': 'PRIVATE ORIGINAL', 'private_label': {'secret': 'PRIVATE KEY'}}
    verdict = {'verdict': {'decision': 'uncertain', 'findings': [], 'limitations': 'Fixture'}}
    lm = DummyLM([{'questions': ['Describe the pleura.']},
                  {'observation': 'Unclear.', 'limitations': 'Fixture'}, verdict] if variant == 'blue_tools' else [verdict])
    with dspy.context(lm=lm, adapter=dspy.ChatAdapter()):
        verify_case(case, variant, lm, lm, clinical_context='CONTEXT: cough for two days')
    messages = [str(h['messages']) for h in lm.history]
    assert 'CONTEXT: cough for two days' in messages[0]
    assert 'CONTEXT: cough for two days' in messages[-1]
    assert 'PRIVATE ORIGINAL' not in str(messages)
    assert 'PRIVATE KEY' not in str(messages)
    if variant == 'blue_tools':
        # Independent pixel reader remains blinded; planner and assessor have context.
        assert 'CONTEXT: cough for two days' not in messages[1]


def test_judge_uses_recorded_context_not_fresh_history(tmp_path):
    from radarena.judge import load_episode
    row = {'case_id': 'case', 'variant': 'text_only', 'status': 'ok',
           'verdict': {'decision': 'uncertain', 'findings': []},
           'clinical_context': 'Recorded indication'}
    case = {'case_id': 'case', 'study_id': '1', 'source': [], 'candidate': [],
            'private_label': {'has_error': False}, 'image_paths': []}
    (tmp_path / 'cases.jsonl').write_text(json.dumps(case) + '\n')
    (tmp_path / 'predictions.jsonl').write_text(json.dumps(row) + '\n')
    packet, *_ = load_episode(tmp_path, 'case', 'text_only')
    assert packet['available_to_blue']['clinical_context'] == 'Recorded indication'
    assert packet['recorded_blue_accusations']['flagged_sentence_ids'] == []
    assert packet['recorded_blue_accusations']['flags'] == []
    del row['clinical_context']
    (tmp_path / 'predictions.jsonl').write_text(json.dumps(row) + '\n')
    packet, *_ = load_episode(tmp_path, 'case', 'text_only')
    assert packet['available_to_blue']['clinical_context'] is None
