import pytest
from radarena.memory_policy import reward,rule_issues,quarantine,blue_metrics,red_metrics,promotion_decision,valid_review


def test_rewards_do_not_reverse_attacker_goal():
    assert reward('red','valid','no_error_detected','incorrect')['value']==1
    assert reward('red','valid','error','correct')['value']==-1
    assert reward('red','valid','error','partially_correct')['value']==-1
    assert reward('red','valid','uncertain','uncertain')['value']==0
    assert reward('red','invalid','no_error_detected','incorrect')['value']==-1
    assert reward('blue','valid','uncertain','correct','no_error_detected')['value']==0.5
    assert reward('red','uncertain','no_error_detected','incorrect')['value'] is None
    assert reward('red','valid','invalid_output','incorrect')['value'] is None
    assert reward('blue','valid','error','correct','error')['value']==0
    assert reward('blue','valid','error','correct','no_error_detected')['value']==1


def test_rule_conflicts_duplicates_and_known_unsafe_lessons():
    assert 'opposite_rule' in rule_issues('blue','Never flag definite contradictions.',['Always flag definite contradictions.'])
    assert 'duplicate_rule' in rule_issues('red','Change the side!',['Change the side.'])
    assert rule_issues('red','Reduce severity from mild to none.')
    assert rule_issues('blue','Confidently flag absence even if other readings are conflicting.')
    kept,bad=quarantine('red',{'initial':['Reduce severity from mild to none.','Preserve unrelated claims.']})
    assert kept=={'initial':['Preserve unrelated claims.']} and len(bad)==1


def test_blue_promotion_requires_measured_gain_and_no_regression():
    base=blue_metrics([{'attack':'error','control':'error'},{'attack':'error','control':'no_error_detected'},{'attack':'no_error_detected','control':'no_error_detected'}])
    improved=blue_metrics([{'attack':'error','control':'no_error_detected'},{'attack':'error','control':'no_error_detected'},{'attack':'error','control':'no_error_detected'}])
    assert promotion_decision('blue',base,improved)[0]
    assert not promotion_decision('blue',base,base)[0]
    # Abstaining on everything is never a quality improvement.
    abstain=blue_metrics([{'attack':'uncertain','control':'uncertain'}]*3)
    assert not promotion_decision('blue',base,abstain)[0]
    broken=dict(improved,invalid_outputs=1)
    assert not promotion_decision('blue',base,broken)[0]


def test_red_cannot_improve_by_being_caught_or_making_invalid_attacks():
    caught={'validity':'valid','decision':'error','assessment':'correct'}
    escaped={'validity':'valid','decision':'no_error_detected','assessment':'incorrect'}
    base=red_metrics([caught]*3);better=red_metrics([escaped,caught,caught])
    assert promotion_decision('red',base,better)[0]
    invalid=red_metrics([escaped,dict(escaped,validity='invalid'),caught])
    assert not promotion_decision('red',base,invalid)[0]
    assert not promotion_decision('red',None,better)[0]


def test_semantic_review_cannot_skip_or_invent_rules():
    r={'checked_rule_ids':['0'],'unsafe_or_conflicting_rule_ids':[], 'uncertain_rule_ids':[],'explanation':''}
    assert valid_review(r,{'0'}).checked_rule_ids==['0']
    with pytest.raises(ValueError):valid_review(r,{'0','1'})
    with pytest.raises(ValueError):valid_review(dict(r,unsafe_or_conflicting_rule_ids=['9']),{'0'})
