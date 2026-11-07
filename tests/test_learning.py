import json
from types import SimpleNamespace

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from radarena.learning import choose_cases, role_feedback, validate_rules


def episode():
    return {'study_id': 'private-study', 'source': 'SECRET SOURCE', 'candidate': 'PUBLIC CANDIDATE',
            'red_rationale': 'SECRET RED RATIONALE', 'red_rules': 'SECRET RED MEMORY',
            'blue_rules': 'SECRET BLUE MEMORY', 'clinical_context': 'PUBLIC INDICATION',
            'error_type': 'laterality', 'changed_sentence_ids': ['s1'], 'edits': [],
            'blue': {'decision': 'uncertain'}, 'observations': ['BLUE PRIVATE OBSERVATIONS'],
            'attack_status': 'syntax_only', 'score': {'injected_edit_detected': False}}


def test_feedback_separates_role_private_notes():
    red = json.dumps(role_feedback('red', episode()))
    blue = json.dumps(role_feedback('blue', episode(), episode()))
    assert 'SECRET SOURCE' in red
    assert 'BLUE PRIVATE OBSERVATIONS' not in red
    assert 'SECRET BLUE MEMORY' not in red
    assert 'SECRET SOURCE' not in blue
    assert 'SECRET RED RATIONALE' not in blue
    assert 'SECRET RED MEMORY' not in blue
    assert 'PUBLIC CANDIDATE' in blue
    assert 'changed_sentence_ids' in blue  # training-only supervised feedback, explicitly labelled
    with pytest.raises(ValueError):
        role_feedback('judge', episode())


def test_strategy_memory_is_bounded():
    assert validate_rules({'rules': ['Check evidence before flagging.'], 'explanation': 'General lesson'}).rules
    with pytest.raises(ValueError):
        validate_rules({'rules': ['x']*6, 'explanation': ''})
    with pytest.raises(ValueError):
        validate_rules({'rules': ['x'*401], 'explanation': ''})


def test_learning_selection_is_split_disjoint_and_not_outcome_selected():
    cases = [{'split': split, 'study_id': f'{split}-{kind}', 'private_label': {
        'has_error': True, 'error_type': kind}} for split in ['train', 'dev']
        for kind in ['laterality', 'presence_absence', 'severity']]
    a = choose_cases(cases); b = choose_cases(list(reversed(cases)))
    assert a == b
    assert {c['study_id'] for c in a['train']}.isdisjoint(c['study_id'] for c in a['dev'])


def test_complete_learning_controller_and_resume(tmp_path, monkeypatch):
    import radarena.learning as learning
    from radarena.agents import Verdict
    from test_evaluation import benchmark_fixture
    _, benchmark = benchmark_fixture(tmp_path)
    csv = tmp_path / 'context.csv'
    csv.write_text('uid,indication\n' + ''.join(f'{split}-{kind},Fixture history\n'
                    for split in ['train', 'dev', 'test'] for kind in ['laterality', 'presence_absence', 'severity']))
    lm = DummyLM([])
    monkeypatch.setattr(learning, 'make_models', lambda: (lm, lm))
    seen = []
    class FakeBlue:
        def __init__(self, **kwargs): pass
        def __call__(self, **kwargs):
            assert 'source' not in kwargs and 'edits' not in kwargs
            seen.append(('blue', list(kwargs['strategies'])))
            return SimpleNamespace(verdict=Verdict(decision='uncertain', findings=[], limitations='Fixture'), observations=[])
    class FakePredict:
        def __init__(self, signature): self.signature = signature
        def set_lm(self, lm): pass
        def __call__(self, **kwargs):
            if self.signature is learning.MakeAttack:
                seen.append(('red', list(kwargs['strategies'])))
                return SimpleNamespace(edits=[{'sentence_id': 's1', 'replacement': 'Fixture changed report.'}], private_rationale='Private Red explanation')
            role = 'red' if self.signature is learning.ReflectRed else 'blue'
            text = json.dumps(kwargs['feedback'])
            if role == 'blue':assert 'Private Red explanation' not in text
            return SimpleNamespace(strategy={'rules': [role + ' general strategy'], 'explanation': 'Fixture lesson'})
    monkeypatch.setattr(learning, 'BlueVerifier', FakeBlue)
    monkeypatch.setattr(learning.dspy, 'Predict', FakePredict)
    output = tmp_path / 'run'
    result = learning.run_learning(output, benchmark, csv)
    assert result['complete']
    assert result['blue_fixed_seed_evaluation']['before']['completed'] == 6
    assert ('red', ['red general strategy']) in seen
    assert ('blue', ['blue general strategy']) in seen
    assert all('red general strategy' not in rules for role, rules in seen if role == 'blue')
    assert all('blue general strategy' not in rules for role, rules in seen if role == 'red')
    count = len(seen)
    assert learning.run_learning(output, benchmark, csv)['complete']
    assert len(seen) == count  # completed inference stages are never rerun on resume
    assert len(list((output/'memories/red').glob('*.json'))) == 3
    assert len(list((output/'memories/blue').glob('*.json'))) == 3


def test_replay_loads_only_matching_role_rules_and_checks_integrity(tmp_path):
    from radarena.learning import digest
    from radarena.memory import load_memory
    p = tmp_path / 'blue.json'
    rules = ['Use uncertainty for inconclusive images.']
    p.write_text(json.dumps({'role': 'blue', 'rules': rules, 'memory_sha256': digest(rules),
                             'explanation': 'PRIVATE EXPLANATION', 'training_study_id': 'PRIVATE ID', 'round': 3}))
    loaded, metadata = load_memory(p, 'blue')
    assert loaded == rules
    assert 'PRIVATE' not in json.dumps([loaded, metadata])
    with pytest.raises(ValueError, match='another role'):
        load_memory(p, 'red')
    record = json.loads(p.read_text());record['rules'] = ['Tampered rule']
    p.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='hash mismatch'):
        load_memory(p, 'blue')
    assert load_memory(None, 'red')[0] == []
