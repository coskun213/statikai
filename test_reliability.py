"""Policy and approval safety checks; controlled fixtures, not OCR accuracy."""
from copy import deepcopy
from pathlib import Path
import pytest
from test_beam_pipeline import controlled
from statikai.beam_scope import inspect_scope
from statikai.reliability import assess,confirm_reading,json_digest
from statikai.beam_pipeline import FIELDS
from statikai import physics

POLICY=dict(policy_id='unit_test_not_deployed',minimum_symbol_score=.65,minimum_ocr_score=.9,upward_head_ratio=1.8)


def evidence():
    image,x=controlled();x['image']=dict(sha256='test-image-checksum',path='controlled_fixture',width=image.width,height=image.height)
    return dict(extraction=x,scope_check=inspect_scope(image,x),error=None)


def test_automatic_state_is_explicit_and_does_not_claim_visual_truth():
    ev=evidence();before=deepcopy(ev);result=assess(ev,POLICY)
    assert result['decision']=='automatic_solution' and result['automatic']
    assert result['static_solution']['RA_kN']==pytest.approx(7.4)
    assert result['equilibrium']['passed'] and result['equilibrium']['interpretation_verified'] is False
    assert ev==before


@pytest.mark.parametrize('confidence',[None,'0.99',True,float('nan'),float('inf')])
def test_invalid_ocr_confidence_fails_closed_in_validation(confidence):
    """Direct guarded entry: an unusable score yields review_required, never a TypeError."""
    from statikai.beam_pipeline import solve_extraction
    ev=evidence();x=ev['extraction'];x['ocr_readings'][0]['confidence']=confidence
    result=solve_extraction(x,ev['scope_check'])
    assert result['review_required'] and result['static_solution']['RA_kN'] is None


@pytest.mark.parametrize('kind',['symbol','missing_symbol_score','ocr','missing_ocr_score','unit','outside','scope','missing_value'])
def test_suspicion_stops_before_solver(monkeypatch,kind):
    ev=evidence();x=ev['extraction']
    if kind=='symbol':x['symbols'][0]['score']=.4
    if kind=='missing_symbol_score':x['symbols'][0].pop('score')
    if kind=='ocr':x['ocr_readings'][0]['confidence']=.83
    if kind=='missing_ocr_score':x['ocr_readings'][0]['confidence']=None
    if kind=='unit':x['ocr_readings'][0]['raw_text']='8 kg'
    if kind=='outside':x['extracted_inputs']['x1_m']=11
    if kind=='scope':ev['scope_check']['passed']=False
    if kind=='missing_value':x['extracted_inputs'].pop('P1_kN')
    monkeypatch.setattr(physics,'reactions',lambda *a:pytest.fail('No solver before reliability acceptance'))
    result=assess(ev,POLICY)
    assert result['decision']=='review_required' and result['review_required']
    assert result['static_solution']['RA_kN'] is None and not result['automatic']


@pytest.mark.parametrize('kind',['explicit_distributed','extra_strong_load','unknown_support_class','reversed_support','upward'])
def test_unsupported_is_separate_and_not_manual_bypass(kind):
    ev=evidence();x=ev['extraction']
    if kind=='explicit_distributed':x['ocr_readings'].append(dict(id='udl',raw_text='5 kN/m',confidence=.99,bbox=[10,10,60,30],accepted=False))
    if kind=='extra_strong_load':x['symbols'].append(dict(class_id=2,score=.99,bbox=[10,10,20,80]))
    if kind=='unknown_support_class':x['symbols'][0]['class_id']=3
    if kind=='reversed_support':x['issues'].append(dict(code='unsupported_orientation',detail='pin right'))
    if kind=='upward':ev['scope_check']['arrows'][0].update(upper_width_px=20,lower_width_px=2)
    result=assess(ev,POLICY)
    assert result['decision']=='unsupported' and result['supported'] is False
    assert result['static_solution']['RA_kN'] is None
    with pytest.raises(ValueError,match='Unsupported'):
        confirm_reading(result,dict(L_m=10,P1_kN=8,x1_m=3,P2_kN=6,x2_m=7),'test',FIELDS,True,test_only=True)


def test_uncertain_shape_or_unreadable_is_review_not_invented_unsupported():
    ev=evidence();ev['scope_check'].update(passed=False,issues=[dict(code='unsupported_support_shape',detail='unverified shape')])
    assert assess(ev,POLICY)['decision']=='review_required'
    assert assess(dict(extraction=None,scope_check=None,error={'code':'unreadable'}),POLICY)['decision']=='review_required'


def test_approval_is_separate_record_and_original_stays_unchanged():
    ev=evidence();ev['extraction']['symbols'][0]['score']=.4
    original=assess(ev,POLICY);before=deepcopy(original)
    values=dict(L_m=10,P1_kN=8,x1_m=3,P2_kN=6,x2_m=7)
    event=confirm_reading(original,values,'unit_test_reviewer',FIELDS,True,test_only=True)
    assert event['status']=='human_confirmed_solution' and event['automatic'] is False
    assert event['counts_as_automatic_success'] is False and event['test_only']
    assert event['original_result_sha256']==json_digest(original)
    assert event['static_solution']['RA_kN']==pytest.approx(7.4)
    assert original==before and original['decision']=='review_required'


@pytest.mark.parametrize('kind',['name','checkbox','scope','missing','nan','boolean','unexplained_change','unreadable'])
def test_approval_requires_explicit_values_scope_and_acknowledgements(kind):
    original=assess(evidence(),POLICY);values=dict(L_m=10,P1_kN=8,x1_m=3,P2_kN=6,x2_m=7)
    reviewer='test';ack=list(FIELDS);scope=True
    if kind=='name':reviewer=''
    if kind=='checkbox':ack=ack[:-1]
    if kind=='scope':scope=False
    if kind=='missing':values.pop('P1_kN')
    if kind=='nan':values['L_m']=float('nan')
    if kind=='boolean':values['L_m']=True
    if kind=='unexplained_change':values['P1_kN']=18
    if kind=='unreadable':original['extraction']=None
    with pytest.raises(ValueError):confirm_reading(original,values,reviewer,ack,scope,test_only=True)


def test_corrected_human_value_has_audit_trail_but_is_not_ocr_truth():
    original=assess(evidence(),POLICY)
    event=confirm_reading(original,dict(L_m=10,P1_kN=18,x1_m=3,P2_kN=6,x2_m=7),
                          'unit_test',FIELDS,True,notes='Controlled changed input, not real approval',test_only=True)
    assert event['changes']['P1_kN']==dict(before=8,after=18)
    assert event['equilibrium']['passed'] and event['equilibrium']['interpretation_verified'] is False
    assert not event['identity_authenticated']


def test_confident_consistent_wrong_reading_can_escape_policy():
    ev=evidence();x=ev['extraction']
    x['ocr_readings'][0]['raw_text']='18 kN';x['forces'][0]['magnitude_kN']['value']=18;x['extracted_inputs']['P1_kN']=18
    result=assess(ev,POLICY)
    assert result['decision']=='automatic_solution'
    assert result['static_solution']['RA_kN']!=pytest.approx(7.4)
    assert result['equilibrium']['passed']  # Deliberately demonstrate a real policy limitation.
