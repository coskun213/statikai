"""Research abstention policy. Scores are NOT calibrated probabilities.

Three automatic decisions; human approval is a separate immutable event.
Old analytic/OCR/geometry/scope code and old frozen thresholds stay unchanged.
"""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re
import time
from uuid import uuid4
from PIL import Image
from .beam_pipeline import FIELDS,TRUTH_NOTE,validate_extraction,solve_extraction
from .beam_scope import inspect_scope
from .ocr_quantities import parse_quantity
from . import physics

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_RUN=ROOT/'experiments/reliability_v1_20261108_01'
LABELS=dict(automatic_solution='Otomatik çözüm üretildi',review_required='İnsan incelemesi gerekli',
            unsupported='Problem desteklenmiyor')

def valid_score(value):
    return (isinstance(value,(int,float)) and not isinstance(value,bool)
            and math.isfinite(value) and 0<=value<=1)


def json_digest(data):
    return hashlib.sha256(json.dumps(data,ensure_ascii=False,sort_keys=True,allow_nan=False).encode('utf8')).hexdigest()


def load_policy(run=DEFAULT_RUN):
    run=Path(run);path=run/'policy.json'
    frozen=json.loads((run/'frozen_protocol.json').read_text(encoding='utf8'))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=frozen['policy_sha256']:
        raise ValueError('Reliability policy checksum mismatch')
    for relative,digest in frozen['runtime_code_sha256'].items():
        if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:
            raise ValueError('Reliability runtime changed: '+relative)
    return json.loads(path.read_text(encoding='utf8'))


def collect_evidence(image_path,detector,ocr):
    """Only pixels and models; no solver, references or saved previous results."""
    from read_beam_diagram import extract
    started=time.perf_counter()
    try:
        extraction=extract(image_path,detector,ocr)
        with Image.open(image_path) as im:scope=inspect_scope(im.convert('RGB'),extraction)
        result=dict(extraction=extraction,scope_check=scope,error=None)
    except (OSError,ValueError,RuntimeError) as exc:
        result=dict(extraction=None,scope_check=None,error=dict(code='image_or_inference_failure',detail=str(exc)))
    result['elapsed_seconds']=time.perf_counter()-started
    return result


def assess(evidence,policy):
    """Apply a validation-selected policy; never replace missing quantities."""
    result=dict(schema_version='statikai.reliability.v1',decision='review_required',
        status_label=LABELS['review_required'],review_required=True,supported=None,
        automatic=False,policy_id=policy['policy_id'],policy=deepcopy(policy),reasons=[],
        extraction=deepcopy(evidence.get('extraction')),scope_check=deepcopy(evidence.get('scope_check')),
        checks={},validated_inputs=None,static_solution=dict(status='not_run',RA_kN=None,RB_kN=None),
        equilibrium=dict(status='not_run',passed=None),interpretation_warning=TRUTH_NOTE,
        interpretation_truth_status='not_independently_verified',human_review_required_for_approval=False)
    reasons=result['reasons'];hard=[]
    def warn(code,detail,sources=None,kind='review'):
        item=dict(code=code,detail=detail,source_ids=sources or [],classification=kind)
        reasons.append(item)
        if kind=='unsupported':hard.append(item)
    extraction=result['extraction'];scope=result['scope_check']
    if evidence.get('error') or not extraction or not scope:
        warn('unreadable_or_failed_inference','Image or inference could not be read; no unsupported-type guess.')
        result['checks']['image']='review_required';return result
    symbols=extraction.get('symbols',[]);count=Counter(s.get('class_id') for s in symbols)
    invalid_scores=[i for i,s in enumerate(symbols) if isinstance(s.get('score'),bool)
                    or not isinstance(s.get('score'),(int,float)) or not math.isfinite(s['score']) or not 0<=s['score']<=1]
    low=[i for i,s in enumerate(symbols) if i not in invalid_scores and s['score']<policy['minimum_symbol_score']]
    if invalid_scores:warn('invalid_symbol_score','Missing or nonfinite symbol confidence.',invalid_scores)
    if low:warn('low_symbol_confidence','Detected symbol score below validation-selected threshold.',low)
    result['checks']['symbols']=dict(counts=dict(count),minimum_score=min((s['score'] for i,s in enumerate(symbols) if i not in invalid_scores),default=None),
        low_score_indices=low,invalid_score_indices=invalid_scores,threshold=policy['minimum_symbol_score'],
        note='uncalibrated detector scores; candidates below original detector floor 0.35 are not present')
    strong=not invalid_scores and not low and bool(symbols)
    if count!=Counter({0:1,1:1,2:2}):
        if strong and (count.get(2,0)>2 or any(c not in (0,1,2) for c in count)):
            warn('unsupported_loading_inventory','Confident extra point loads or an unsupported class.',kind='unsupported')
        else:warn('uncertain_symbol_inventory','Missing/ambiguous support or load inventory.')
    if strong and any(i['code']=='unsupported_orientation' for i in extraction.get('issues',[])):
        warn('unsupported_support_orientation','Current solver requires left pin and right roller.',kind='unsupported')
    # Explicit distributed-load/moment units are positive evidence of a different
    # load domain. A misspelling or unknown kg is an OCR/unit review, not proof.
    unsupported_labels=[]
    for text in extraction.get('ocr_readings',[]):
        compact=re.sub(r'\s+','',text.get('raw_text',''))
        if (valid_score(text.get('confidence')) and text['confidence']>=policy['minimum_ocr_score'] and
            re.fullmatch(r'(?:[A-Za-z]=)?[+-]?\d+(?:[.,]\d+)?(?:kN/m|N/m|kNm|Nmm|kN·m)',compact)):
            unsupported_labels.append(text['id'])
    if unsupported_labels:warn('unsupported_loading_unit','Distributed-load or applied-moment label read.',unsupported_labels,'unsupported')
    for arrow in scope.get('arrows',[]):
        if (strong and arrow.get('upper_width_px',0)>policy['upward_head_ratio']*max(1,arrow.get('lower_width_px',0))):
            warn('unsupported_upward_load','Pixel evidence indicates an upward arrow.',kind='unsupported')
    used=set()
    for force in extraction.get('forces',[]):
        for name in ('magnitude_kN','position_m'):
            if force.get(name):used.update(force[name].get('source_text_ids',[]))
    if extraction.get('length_m'):used.update(extraction['length_m'].get('source_text_ids',[]))
    for dimension in extraction.get('geometry',{}).get('dimensions',[]):used.update(dimension.get('text_source_ids',[]))
    readings={t['id']:t for t in extraction.get('ocr_readings',[])}
    low_text=[];bad_units=[]
    for identity in sorted(used):
        text=readings.get(identity)
        if not text:warn('missing_ocr_source','Used quantity has no OCR source.',[identity]);continue
        score=text.get('confidence');quantity=parse_quantity(text.get('raw_text',''))
        if not valid_score(score) or score<policy['minimum_ocr_score']:
            low_text.append(identity)
        if quantity.get('status')!='ok':bad_units.append(identity)
    if low_text:warn('low_ocr_confidence','Used text score below validation-selected threshold.',low_text)
    if bad_units:warn('unit_mismatch','Used label has missing, invalid or incompatible units.',bad_units)
    result['checks']['ocr']=dict(critical_source_ids=sorted(used),low_confidence_ids=low_text,unit_error_ids=bad_units,
                                 threshold=policy['minimum_ocr_score'],confidence_is_probability=False)
    inputs,old_errors=validate_extraction(extraction,scope)
    for issue in old_errors:warn(issue['code'],issue['detail'])
    for issue in extraction.get('issues',[]):warn('reading_'+issue['code'],issue['detail'],issue.get('source_ids'))
    for issue in scope.get('issues',[]):warn('scope_'+issue['code'],issue['detail'])
    candidate=extraction.get('extracted_inputs')
    if isinstance(candidate,dict):
        try:
            positions_ok=(0<float(candidate['x1_m'])<float(candidate['x2_m'])<float(candidate['L_m']))
        except (KeyError,TypeError,ValueError,OverflowError):positions_ok=False
        result['checks']['positions']=dict(passed=positions_ok,condition='0 < x1 < x2 < L')
        if not positions_ok:warn('positions_outside_span','Load positions must lie strictly within the span and be ordered.')
    else:result['checks']['positions']=dict(passed=None,reason='complete inputs unavailable')
    if hard:
        result.update(decision='unsupported',status_label=LABELS['unsupported'],supported=False,review_required=False)
    elif reasons:
        result['human_review_required_for_approval']=True
    else:
        solved=solve_extraction(extraction,scope)
        if solved['status']=='computed':
            result.update(decision='automatic_solution',status_label=LABELS['automatic_solution'],automatic=True,
                review_required=False,supported=True,validated_inputs=solved['validated_inputs'],
                static_solution=solved['static_solution'],equilibrium=solved['equilibrium'])
        else:
            for issue in solved['issues']:warn(issue['code'],issue['detail'])
            result['equilibrium']=solved['equilibrium'];result['human_review_required_for_approval']=True
    return result


def analyze_reliably(image_path,detector,ocr,policy):
    evidence=collect_evidence(image_path,detector,ocr);result=assess(evidence,policy)
    result['elapsed_seconds']=evidence['elapsed_seconds'];return result


def confirm_reading(original,values,reviewer,acknowledged_fields,scope_confirmed,notes='',test_only=False):
    """Separate human event; cannot convert unsupported or replace original JSON.

    Reviewer is a supplied label, not authenticated identity. No field defaults.
    The caller/UI must collect explicit acknowledgements and all five SI values.
    """
    if original['decision']=='unsupported':raise ValueError('Unsupported problems cannot be approved through this form.')
    if not (original.get('extraction') or {}).get('image',{}).get('sha256'):
        raise ValueError('A readable source image with a recorded checksum is required for confirmation.')
    if not isinstance(reviewer,str) or not reviewer.strip():raise ValueError('Reviewer name/code required.')
    if set(acknowledged_fields)!=set(FIELDS) or scope_confirmed is not True:
        raise ValueError('All five fields and the supported load/support scope must be acknowledged.')
    if not isinstance(values,dict) or set(values)!=set(FIELDS):raise ValueError('All five SI values required; no defaults.')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) for v in values.values()):raise ValueError('Explicit numerical SI values required.')
    validated=dict(zip(FIELDS,physics.validated_inputs(*(values[k] for k in FIELDS))))
    extraction=original.get('extraction') or {};candidate=extraction.get('extracted_inputs') or {}
    changes={k:dict(before=candidate.get(k),after=validated[k]) for k in FIELDS if candidate.get(k)!=validated[k]}
    if changes and not notes.strip():raise ValueError('Explain corrected or supplied values; they are human inputs, not OCR results.')
    ra,rb=physics.reactions(*(validated[k] for k in FIELDS));force,moment=physics.residuals(*(validated[k] for k in FIELDS),ra,rb)
    L,p1,x1,p2,x2=[validated[k] for k in FIELDS]
    from .beam_pipeline import BALANCE
    ftol=BALANCE['force_absolute_kN']+BALANCE['relative']*max(1,abs(ra)+abs(rb)+p1+p2)
    mtol=BALANCE['moment_absolute_kNm']+BALANCE['relative']*max(1,abs(rb*L)+p1*x1+p2*x2)
    if not (abs(force)<=ftol and abs(moment)<=mtol):raise ValueError('Human-confirmed inputs failed numerical equilibrium check.')
    return dict(schema_version='statikai.human_review.v1',event_id=uuid4().hex,
        created_utc=datetime.now(timezone.utc).isoformat(),status='human_confirmed_solution',automatic=False,test_only=bool(test_only),
        reviewer_label=reviewer.strip(),identity_authenticated=False,original_result_sha256=json_digest(original),
        original_decision=original['decision'],image=(extraction.get('image') or {}),
        acknowledged_fields=sorted(acknowledged_fields),scope_confirmed=True,
        scope='left pin/right roller, horizontal beam, exactly two downward point loads',
        confirmed_inputs=validated,changes=changes,notes=notes.strip(),
        static_solution=dict(status='computed_from_human_confirmed_inputs',RA_kN=ra,RB_kN=rb,force_unit='kN'),
        equilibrium=dict(passed=True,force_residual_kN=force,moment_residual_kNm=moment,interpretation_verified=False),
        interpretation_warning=TRUTH_NOTE,counts_as_automatic_success=False)
