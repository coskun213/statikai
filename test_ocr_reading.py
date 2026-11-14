"""Safety and geometry checks, independent of OCR language-model scores."""
import copy
from pathlib import Path
import pytest
from PIL import Image, ImageDraw
from statikai.ocr_quantities import parse_quantity, parse_readings
from statikai.diagram_reading import interpret, dimension_graph


@pytest.mark.parametrize('text,kind,value', [('8 kN','force',8),('6000 N','force',6),
    ('10 m','length',10),('250 cm','length',2.5),('1,375 mm','length',.001375)])
def test_explicit_unit_conversion(text,kind,value):
    item=parse_quantity(text)
    assert item['status']=='ok' and item['kind']==kind and item['value_si']==value


@pytest.mark.parametrize('text', ['8','O kN','l0 m','5 kg','5 KN','5 mN','4 kNm',
    '2 m²','1,234.5 m','nan m','-5 kN','0 m','L=10m|x1=2m'])
def test_no_digit_repair_missing_units_or_parameter_shortcuts(text):
    assert parse_quantity(text)['value_si'] is None


def reading(text,box,score=.99):
    return dict(raw_text=text,bbox=box,quad=None,confidence=score)


def fixture():
    im=Image.new('RGB',(1000,700),'white');d=ImageDraw.Draw(im)
    d.line((100,270,900,270),fill='black',width=3)
    symbols=[dict(class_id=0,bbox=[75,274,125,310],score=.99),
             dict(class_id=1,bbox=[875,274,925,310],score=.99)]
    for x in (340,660):
        d.line((x,180,x,265),fill='black',width=2)
        symbols.append(dict(class_id=2,bbox=[x-12,180,x+12,265],score=.99))
    for x in (100,340,660,900):d.line((x,335,x,408),fill='black',width=2)
    d.line((100,400,900,400),fill='black',width=2)
    for x in (100,900):d.line((x,335,x,528),fill='black',width=2)
    d.line((100,520,900,520),fill='black',width=2)
    texts=[reading('8 kN',[310,140,370,160]),reading('6000 N',[620,140,700,160]),
           reading('3 m',[195,360,245,380]),reading('4 m',[475,360,525,380]),
           reading('300 cm',[735,360,815,380]),reading('10 m',[470,480,530,500])]
    return im,symbols,texts


def test_unique_split_number_and_unit_are_joined_without_assumption():
    a=reading('150',[10,20,45,40]);b=reading('cm',[50,22,73,40])
    parsed=parse_readings([a,b]);assert len(parsed)==3
    assert parsed[-1]['quantity']['value_si']==1.5
    assert parsed[-1]['component_text_ids']==['text_0','text_1']
    # Two plausible unit boxes: decline to choose one.
    assert len(parse_readings([a,b,reading('m',[50,20,60,40])]))==3


def test_graph_detects_conflicting_redundant_measurement():
    edges=[dict(id='a',nodes=['support_A','load_1'],value_m=3),
           dict(id='b',nodes=['load_1','support_B'],value_m=7),
           dict(id='c',nodes=['support_A','support_B'],value_m=11)]
    _,_,conflicts=dimension_graph({},edges)
    assert conflicts


def test_chain_extraction_and_provenance_without_solver_or_metadata(monkeypatch):
    im,symbols,texts=fixture()
    monkeypatch.setattr(Path,'read_text',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No sidecars')))
    result=interpret(im,symbols,texts)
    assert not result['review_required'],result['issues']
    assert result['extracted_inputs']==dict(L_m=10,P1_kN=8,x1_m=3,P2_kN=6,x2_m=7)
    assert result['forces'][1]['position_m']['dimension_ids']
    assert result['length_m']['source_text_ids'] and result['length_m']['confidence']==.99
    assert result['static_solution']==dict(status='not_run',RA_kN=None,RB_kN=None)


@pytest.mark.parametrize('mutation,code', [('missing','missing_force_text'),('unit','unsupported_unit'),
    ('conflict','contradictory_dimensions'),('confidence','low_confidence'),
    ('ambiguous','ambiguous_force_text'),('symbol','symbol_inventory'),('dimension','incomplete_dimension_chain')])
def test_unsafe_or_unreadable_inputs_require_review(mutation,code):
    im,symbols,texts=fixture()
    if mutation=='missing':texts=texts[1:]
    if mutation=='unit':texts[0]['raw_text']='8 kg'
    if mutation=='conflict':texts[-1]['raw_text']='11 m'
    if mutation=='confidence':texts[0]['confidence']=.4
    if mutation=='symbol':symbols=symbols[:-1]
    if mutation=='dimension':texts=texts[:2]
    if mutation=='ambiguous':
        # A deliberately broad allowed region makes both assignments feasible.
        result=interpret(im,symbols,texts,dict(force_label_dx_width=.5))
    else:result=interpret(im,symbols,texts)
    assert result['review_required'] and result['extracted_inputs'] is None
    assert code in [i['code'] for i in result['issues']]


def test_missing_dimension_never_replaced_by_pixel_scale():
    im,symbols,texts=fixture()
    # Chain-only, one segment unreadable; no total length or scale fallback.
    result=interpret(im,symbols,texts[:4])
    assert result['length_m'] is None and result['forces'][1]['position_m']['value']==7
    assert result['extracted_inputs'] is None


def test_wrong_unit_cannot_be_bypassed_using_redundant_dimensions():
    im,symbols,texts=fixture()
    texts[2]=reading('300 kg',[190,360,250,397])
    result=interpret(im,symbols,texts)
    # The other three edges suffice to derive x1, but explicit kg still blocks.
    assert result['review_required'] and result['extracted_inputs'] is None
    assert 'unsupported_unit' in [i['code'] for i in result['issues']]
