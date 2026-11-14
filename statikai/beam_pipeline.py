"""Image -> detection/OCR -> measured geometry -> guarded statics -> equilibrium.

Only extraction.extracted_inputs can enter physics. Partial OCR fields are
diagnostic only. Equilibrium verifies arithmetic for read inputs, never truth.
The historical analytic solver is imported without modifying its source.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import time
from PIL import Image, UnidentifiedImageError
from . import physics
from .beam_scope import inspect_scope
from .diagram_reading import dimension_graph,interpret
from .ocr_quantities import parse_quantity

FIELDS=('L_m','P1_kN','x1_m','P2_kN','x2_m')
BALANCE=dict(force_absolute_kN=1e-9,moment_absolute_kNm=1e-8,relative=1e-10)
TRUTH_NOTE=('Denge yalnız okunan girdiler için aritmetik tutarlılığı sınar. '
            'Yanlış okunan kuvvet ve ölçüler de denge sağlayabilir; görüntü yorumu bağımsız doğrulanmış değildir.')


def confidence_at_least(value,minimum):
    """Fail closed: a missing, boolean, non-numeric or non-finite score never passes."""
    return (isinstance(value,(int,float)) and not isinstance(value,bool)
            and math.isfinite(value) and value>=minimum)


def validate_extraction(extraction,scope):
    """Fail closed, revalidate units/provenance/graph; never complete missing data."""
    errors=[]
    def error(code,detail):errors.append(dict(code=code,detail=detail,severity='review_required'))
    if extraction.get('review_required') is not False or extraction.get('issues'):
        error('extraction_requires_review','Partial or warned readings must not enter the solver.')
    if scope.get('passed') is not True or scope.get('issues'):
        error('scope_requires_review','Support/load direction and unexplained-ink checks must pass.')
    inputs=extraction.get('extracted_inputs')
    if not isinstance(inputs,dict) or set(inputs)!=set(FIELDS):
        error('missing_inputs','Exactly five extracted inputs with explicit provenance required.');return None,errors
    try:
        values=physics.validated_inputs(*(inputs[k] for k in FIELDS))
    except (ValueError,TypeError) as exc:
        error('invalid_inputs',str(exc));return None,errors
    # A numeric string/boolean is not an accepted structured OCR quantity.
    if any(isinstance(inputs[k],bool) or not isinstance(inputs[k],(int,float)) for k in FIELDS):
        error('invalid_input_type','Inputs must be finite JSON numbers, not strings or booleans.')
    symbols=extraction.get('symbols',[])
    if Counter(s.get('class_id') for s in symbols)!=Counter({0:1,1:1,2:2}):
        error('invalid_support_or_load_type','One pin, one roller, exactly two point loads required.')
    supports=extraction.get('supports',[])
    if [(s.get('id'),s.get('class_id')) for s in supports]!=[('support_A',0),('support_B',1)]:
        error('invalid_support_type','Left pin and right roller required.')
    readings=extraction.get('ocr_readings',[]);texts={t['id']:t for t in readings}
    if len(texts)!=len(readings):error('duplicate_source_ids','OCR source identifiers must be unique.')
    def check_quantity(ids,kind,value):
        if not isinstance(ids,list) or len(ids)!=1 or ids[0] not in texts:
            error('missing_quantity_source','A quantity must refer to one unambiguous OCR label.');return
        t=texts[ids[0]];q=parse_quantity(t.get('raw_text',''))
        if (not t.get('accepted') or q.get('status')!='ok' or q.get('kind')!=kind
                or not math.isclose(q.get('value_si',float('nan')),value,rel_tol=1e-10,abs_tol=1e-9)
                or not t.get('bbox') or not confidence_at_least(t.get('confidence'),.8)):
            error('unit_or_provenance_mismatch','Read text, unit, confidence and numerical input disagree.')
    forces=extraction.get('forces',[])
    if len(forces)!=2 or [f.get('id') for f in forces]!=['load_1','load_2']:
        error('missing_forces','Two force associations are required.')
    else:
        for i,force in enumerate(forces,1):
            q=force.get('magnitude_kN') or {};value=q.get('value')
            if not isinstance(value,(int,float)) or isinstance(value,bool) or value!=inputs[f'P{i}_kN']:
                error('force_value_mismatch','Force association disagrees with complete inputs.')
            else:check_quantity(q.get('source_text_ids'),'force',value)
    dimensions=extraction.get('geometry',{}).get('dimensions',[])
    for dimension in dimensions:
        value=dimension.get('value_m')
        if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or value<=0:
            error('invalid_dimension','Dimension must be a positive finite length.');continue
        check_quantity(dimension.get('text_source_ids'),'length',value)
        if len(dimension.get('nodes',[]))!=2 or any(n not in ('support_A','support_B','load_1','load_2') for n in dimension['nodes']):
            error('invalid_dimension_nodes','Unknown dimension endpoint.')
    if len({tuple(d.get('nodes',[])) for d in dimensions})!=len(dimensions):
        error('duplicate_dimensions','Ambiguous repeated measurement interval.')
    if errors:return None,errors
    positions,_,conflicts=dimension_graph({},dimensions)
    if conflicts or any(not math.isclose(positions.get(name,float('nan')),inputs[key],rel_tol=1e-10,abs_tol=1e-9)
                        for name,key in [('support_B','L_m'),('load_1','x1_m'),('load_2','x2_m')]):
        error('dimension_graph_mismatch','Contradictory, missing or mismatched measured positions.')
    return (dict(zip(FIELDS,values)) if not errors else None),errors


def solve_extraction(extraction,scope):
    """Pure guarded integration entry for testing, not an untrusted JSON service."""
    result=dict(schema_version='statikai.end_to_end.v1',status='review_required',review_required=True,
                extraction=extraction,scope_check=scope,validated_inputs=None,issues=[],
                stages={},static_solution=dict(status='not_run',RA_kN=None,RB_kN=None),
                equilibrium=dict(status='not_run',passed=None),
                interpretation_truth_status='not_independently_verified',interpretation_warning=TRUTH_NOTE)
    result['stages']=dict(image='passed',detection='passed' if Counter(s.get('class_id') for s in extraction.get('symbols',[]))==Counter({0:1,1:1,2:2}) else 'review_required',
        ocr='passed' if extraction.get('extracted_inputs') is not None else 'review_required',
        geometry='passed' if extraction.get('extracted_inputs') is not None else 'review_required',
        scope=scope.get('status','review_required'),validation='not_run',statics='not_run',equilibrium='not_run')
    inputs,issues=validate_extraction(extraction,scope);result['issues']=issues
    if issues:
        result['stages']['validation']='review_required';return result
    result['validated_inputs']=inputs;result['stages']['validation']='passed'
    try:
        values=[inputs[k] for k in FIELDS];ra,rb=physics.reactions(*values)
        force,moment=physics.residuals(*values,ra,rb)
        L,p1,x1,p2,x2=values
        force_scale=max(1,abs(ra)+abs(rb)+abs(p1)+abs(p2))
        moment_scale=max(1,abs(rb*L)+abs(p1*x1)+abs(p2*x2))
        ftol=BALANCE['force_absolute_kN']+BALANCE['relative']*force_scale
        mtol=BALANCE['moment_absolute_kNm']+BALANCE['relative']*moment_scale
        passed=abs(force)<=ftol and abs(moment)<=mtol
        result['equilibrium']=dict(status='passed' if passed else 'failed',passed=passed,
             force_residual_kN=force,moment_residual_kNm=moment,
             force_tolerance_kN=ftol,moment_tolerance_kNm=mtol,
             normalized_force_residual=force/force_scale,normalized_moment_residual=moment/moment_scale,
             equations=['RA + RB = P1 + P2','RB * L = P1 * x1 + P2 * x2'],
             interpretation_verified=False)
        result['stages']['equilibrium']='passed' if passed else 'failed'
        if not passed:
            result['issues'].append(dict(code='equilibrium_failure',detail='Computed reactions fail force/moment balance.',severity='review_required'))
            result['static_solution']['status']='withheld_equilibrium_failure'
            result['stages']['statics']='failed';return result
        result['static_solution']=dict(status='computed_from_read_inputs',RA_kN=ra,RB_kN=rb,
             sign_convention='upward positive; loads downward',force_unit='kN',length_unit='m',
             input_source='validated_inputs only; no partial-field fallback')
        result['stages']['statics']='passed';result.update(status='computed',review_required=False)
    except (ValueError,OverflowError,ArithmeticError) as exc:
        result['issues'].append(dict(code='numerical_failure',detail=str(exc),severity='review_required'))
        result['stages']['statics']='failed'
    return result


def analyze_image(image_path,detector,ocr):
    started=time.perf_counter()
    path=Path(image_path);timings={};completed=[]
    try:
        t=time.perf_counter()
        with Image.open(path) as image:image=image.convert('RGB')
        timings['image']=time.perf_counter()-t;completed.append('image')
        t=time.perf_counter();symbols=detector.read(image)
        timings['detection']=time.perf_counter()-t;completed.append('detection')
        t=time.perf_counter();texts=ocr.read(image)
        timings['ocr']=time.perf_counter()-t;completed.append('ocr')
        t=time.perf_counter();extraction=interpret(image,symbols,texts)
        timings['geometry']=time.perf_counter()-t;completed.append('geometry')
        extraction['image']=dict(path=str(path.resolve()),width=image.width,height=image.height,
                                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        extraction['detector']=detector.metadata;extraction['ocr_engine']=ocr.metadata()
        t=time.perf_counter();scope=inspect_scope(image,extraction)
        timings['scope']=time.perf_counter()-t;completed.append('scope')
        t=time.perf_counter()
        result=solve_extraction(extraction,scope)
        timings['validation_statics_equilibrium']=time.perf_counter()-t
    except (OSError,UnidentifiedImageError,ValueError,RuntimeError) as exc:
        result=dict(schema_version='statikai.end_to_end.v1',status='review_required',review_required=True,
             image_path=str(path.resolve()),extraction=None,scope_check=None,validated_inputs=None,
             issues=[dict(code='image_or_inference_failure',detail=str(exc),severity='review_required')],
             stages=dict(image='failed',detection='not_completed',ocr='not_completed',geometry='not_completed',
                         validation='not_run',statics='not_run',equilibrium='not_run'),
             static_solution=dict(status='not_run',RA_kN=None,RB_kN=None),equilibrium=dict(status='not_run',passed=None),
             interpretation_truth_status='not_independently_verified',interpretation_warning=TRUTH_NOTE)
        result['completed_stages_before_error']=completed
    result['elapsed_seconds']=time.perf_counter()-started
    result['stage_timings_seconds']=timings
    result['physics_source_sha256']=hashlib.sha256(Path(physics.__file__).read_bytes()).hexdigest()
    return result
