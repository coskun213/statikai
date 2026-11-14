"""Stage and integration tests. Oracle fixtures here are not benchmark scores."""
from copy import deepcopy
from decimal import Decimal
import math
from pathlib import Path
import random
import pytest
from PIL import Image,ImageDraw
from statikai import physics
from statikai.beam_scope import inspect_scope,arrow_evidence,ink_mask
from statikai.beam_pipeline import solve_extraction,analyze_image
from statikai.diagram_reading import interpret
from statikai.dataset_v2 import parameters,render_case


def controlled():
    p=parameters(22091113,0,0)
    p.update(width=1000,height=700,scale=1000/900,a=100,b=900,y=270,
             symbol_style=0,length_unit='m',force_unit='kN',decimal_comma=False,layout='chain_total',
             radius=18,triangle_height=26,roller_radius=4,arrow_height=100,
             head_height=16,head_width=10,stroke=2,beam_stroke=3,font_size=22)
    image,_,ann=render_case([10,8,3,6,7],p)
    symbols=[dict(class_id=s['class_id'],bbox=s['bbox'],score=.99) for s in ann['symbols']]
    text=[dict(raw_text=t['text'],bbox=t['bbox'],quad=None,confidence=.99) for t in ann['texts']]
    extraction=interpret(image,symbols,text)
    return image,extraction


def test_analytic_solver_matches_independent_decimal_reference_and_balance():
    rng=random.Random(22091114)
    for _ in range(100):
        L=Decimal(str(round(rng.uniform(8,20),2)));x1=L*Decimal('.3');x2=L*Decimal('.7')
        p1=Decimal(rng.randint(1,30));p2=Decimal(rng.randint(1,30))
        rb=(p1*x1+p2*x2)/L;ra=p1+p2-rb
        values=(float(L),float(p1),float(x1),float(p2),float(x2))
        actual=physics.reactions(*values)
        assert actual==pytest.approx((float(ra),float(rb)),abs=1e-10)
        assert physics.residuals(*values,*actual)==pytest.approx((0,0),abs=1e-10)


def test_all_stages_known_values_and_source_preservation():
    image,extraction=controlled();before=deepcopy(extraction)
    scope=inspect_scope(image,extraction);assert scope['passed'],scope
    result=solve_extraction(extraction,scope)
    assert result['status']=='computed' and not result['review_required']
    assert result['static_solution']['RA_kN']==pytest.approx(7.4)
    assert result['static_solution']['RB_kN']==pytest.approx(6.6)
    assert result['equilibrium']['passed'] is True
    assert result['equilibrium']['interpretation_verified'] is False
    assert extraction==before and extraction['static_solution']['status']=='not_run'
    assert all(v=='passed' for v in result['stages'].values())


@pytest.mark.parametrize('mutation', ['review','missing','nan','bool','position','string','support',
    'unit','provenance','source_value','dimension','scope','extra_load'])
def test_invalid_extraction_never_calls_solver(monkeypatch,mutation):
    image,x=controlled();s=inspect_scope(image,x)
    if mutation=='review':x['review_required']=True
    if mutation=='missing':x['extracted_inputs'].pop('P1_kN')
    if mutation=='nan':x['extracted_inputs']['P1_kN']=float('nan')
    if mutation=='bool':x['extracted_inputs']['L_m']=True
    if mutation=='position':x['extracted_inputs']['x2_m']=20
    if mutation=='string':x['extracted_inputs']['P1_kN']='8'
    if mutation=='support':x['supports'][0]['class_id']=3
    if mutation=='unit':x['ocr_readings'][0]['raw_text']='8 kg'
    if mutation=='provenance':x['forces'][0]['magnitude_kN']['source_text_ids']=[]
    if mutation=='source_value':x['extracted_inputs']['P1_kN']=18
    if mutation=='dimension':x['geometry']['dimensions'][0]['value_m']=4
    if mutation=='scope':s['passed']=False
    if mutation=='extra_load':x['symbols'].append(dict(class_id=2,bbox=[10,10,20,40]))
    monkeypatch.setattr(physics,'reactions',lambda *args:pytest.fail('Solver must not be called'))
    result=solve_extraction(x,s)
    assert result['review_required'] and result['static_solution']['RA_kN'] is None
    assert result['static_solution']['status']=='not_run'


def test_failed_equilibrium_withholds_reactions(monkeypatch):
    image,x=controlled();s=inspect_scope(image,x)
    monkeypatch.setattr(physics,'reactions',lambda *args:(1.,1.))
    r=solve_extraction(x,s)
    assert r['review_required'] and not r['equilibrium']['passed']
    assert r['static_solution']['RA_kN'] is None and r['stages']['statics']=='failed'


def test_self_consistent_wrong_ocr_is_not_ground_truth_verification():
    im,x=controlled();s=inspect_scope(im,x)
    # Coherent erroneous reading: no method can infer the true 8 from these data.
    x['ocr_readings'][0]['raw_text']='18 kN';x['forces'][0]['magnitude_kN']['value']=18
    x['extracted_inputs']['P1_kN']=18
    r=solve_extraction(x,s)
    assert r['status']=='computed' and r['equilibrium']['passed']
    assert r['static_solution']['RA_kN']!=pytest.approx(7.4)
    assert r['interpretation_truth_status']=='not_independently_verified'


@pytest.mark.parametrize('mutation',['upward','horizontal','fixed','moment','distributed','third_arrow'])
def test_pixel_scope_rejects_unsupported_loading_or_support(mutation):
    im,x=controlled();d=ImageDraw.Draw(im)
    first=x['forces'][0]['symbol_bbox'];cx=(first[0]+first[2])/2
    if mutation in ('upward','horizontal'):
        a,b,c,e=first;d.rectangle((a-8,b-8,c+8,e+3),fill='white')
        if mutation=='upward':
            d.line((cx,b,cx,e),fill='black',width=2);d.polygon([(cx,b),(cx-10,b+16),(cx+10,b+16)],fill='black')
        else:
            d.line((cx-30,220,cx+30,220),fill='black',width=2);d.polygon([(cx+30,220),(cx+15,210),(cx+15,230)],fill='black')
    if mutation=='fixed':
        box=x['supports'][0]['bbox'];d.rectangle((box[0]-3,270,box[2]+3,box[3]+3),fill='white')
        d.line((100,273,100,320),fill='black',width=4)
        for y in range(278,321,8):d.line((100,y,82,y+7),fill='black',width=2)
    if mutation=='moment':d.arc((470,215,530,265),20,330,fill='black',width=3)
    if mutation=='distributed':d.line((300,140,750,140),fill='black',width=3)
    if mutation=='third_arrow':
        d.line((490,180,490,265),fill='black',width=2);d.polygon([(490,265),(480,249),(500,249)],fill='black')
    s=inspect_scope(im,x);assert not s['passed'],s


def test_image_only_orchestration_and_unreadable_file(tmp_path,monkeypatch):
    im,x=controlled();path=tmp_path/'image.png';im.save(path)
    class Detector:
        metadata={'test':'oracle boxes for stage isolation only'}
        def read(self,image):assert image.size==im.size;return deepcopy(x['symbols'])
    class OCR:
        def read(self,image):return deepcopy(x['ocr_readings'])
        def metadata(self):return {'test':'oracle text for stage isolation only'}
    # Forbid sidecar reads. Model initialization is outside the guarded call.
    monkeypatch.setattr(Path,'read_text',lambda *a,**k:pytest.fail('No ground truth/sidecars in inference'))
    r=analyze_image(path,Detector(),OCR());assert r['status']=='computed'
    bad=tmp_path/'bad.png';bad.write_bytes(b'not an image')
    r=analyze_image(bad,Detector(),OCR());assert r['review_required'] and r['static_solution']['RA_kN'] is None
