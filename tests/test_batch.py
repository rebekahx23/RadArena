import json
from pathlib import Path

import pytest

from radarena.batch import select_cases, stage_cap, summarize_batch, total_cost


def test_batch_selection_has_ten_new_dev_studies_and_no_train():
    cases = []
    groups = {'laterality':['37','394','2402','3140','3873'],
              'presence_absence':['1656','1868','2398','3256'], 'severity':['2557','3244','3768']}
    for kind, ids in groups.items():
        for uid in ids:
            count = 1 if uid == '394' else 3 if uid == '2398' else 2
            cases.append({'split':'dev','study_id':uid,'private_label':{'has_error':True,'error_type':kind},
                          'image_paths':['fixture.png']*count})
    cases.append({'split':'train','study_id':'1','private_label':{'has_error':True,'error_type':'laterality'}})
    selected = select_cases(cases)
    assert len(selected) == len({c['study_id'] for c in selected}) == 10
    assert all(c['split'] == 'dev' for c in selected)
    assert not {c['study_id'] for c in selected} & {'1094','1106','2036','2088','1411','2070'}
    assert sum(len(c['image_paths']) for c in selected) == 20


def test_global_budget_includes_every_existing_audit_and_own_resume(tmp_path):
    own = tmp_path/'one.audit';other = tmp_path/'two.judge.audit'
    for directory, cost in [(own,.08),(other,.40)]:
        directory.mkdir();(directory/'budget.json').write_text(json.dumps({'accounted_cost_usd':cost}))
    assert total_cost(tmp_path) == pytest.approx(.48)
    assert stage_cap(tmp_path, own, .5, .5) == pytest.approx(.10)
    assert stage_cap(tmp_path, tmp_path/'new.audit', .5, .5) == pytest.approx(.02)


def test_summary_does_not_count_invalid_attack_as_judged_red_success(tmp_path):
    (tmp_path/'metadata.json').write_text(json.dumps({'selection':[{'study_id':'1','error_type':'laterality','image_count':2}]}))
    (tmp_path/'study-1.attack.json').write_text(json.dumps({'score':{'injected_edit_detected':False,
        'localization_tp':0,'localization_fp':0,'localization_fn':1},'blue':{'decision':'no_error_detected','findings':[]},
        'private_attack':{'edits':[{'sentence_id':'s1'}]}}))
    (tmp_path/'study-1.attack.judge.json').write_text(json.dumps({'status':'ok','red_outcome':'invalid_attack',
        'analysis':{'attack_validity':'invalid','blue_assessment':'correct','failure_modes':['attack_invalid'],
        'explanation':'Invalid change','attack_explanation':'Original reference not image truth',
        'confidence':'low','limitations':'Unadjudicated'}}))
    summary = summarize_batch(tmp_path)
    assert summary['counts']['judge_red_invalid_attack'] == 1
    assert summary['counts'].get('judge_red_escaped',0) == 0
    assert not summary['complete']
    assert summary['expected_studies'] == 10
