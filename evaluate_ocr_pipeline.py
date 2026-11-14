"""OCR evaluation only. Annotations are scoring references, never inference inputs.

prepare records groups before validation; freeze binds code after development;
test verifies the frozen hashes and refuses to overwrite any previous outputs.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from PIL import Image, ImageDraw
from read_beam_diagram import extract, DEFAULT_DETECTOR, DEFAULT_OCR_MODELS
from statikai.diagram_reading import CONFIG
from statikai.ocr_quantities import parse_quantity
from statikai.ocr_engine import LocalOCR
from statikai.symbol_reader import SymbolReader
from statikai.detection import iou
from statikai.compat import load_font

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'experiments/ocr_v1_1_20261108_01'
DATA = ROOT/'dataset_dimensions_v2'
TEST_DATA = RUN/'fresh_test'
FIELDS = ('L_m', 'P1_kN', 'x1_m', 'P2_kN', 'x2_m')
CODE = ['read_beam_diagram.py','evaluate_ocr_pipeline.py','statikai/diagram_reading.py',
        'statikai/ocr_engine.py','statikai/ocr_quantities.py','statikai/symbol_reader.py']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def save(path, data):
    with Path(path).open('x', encoding='utf8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)


def rows(data=DATA):
    with (data/'ground_truth.csv').open(encoding='utf8', newline='') as handle:
        return list(csv.DictReader(handle))


def prepare():
    all_rows = rows()
    ids = {s: sorted({int(r['problem_id']) for r in all_rows if r['split']==s}) for s in ('train','val','test')}
    assert not (set(ids['train'])&set(ids['val']) or set(ids['train'])&set(ids['test']) or set(ids['val'])&set(ids['test']))
    fresh=rows(TEST_DATA)
    fresh_ids=sorted({int(r['problem_id']) for r in fresh})
    assert not set(fresh_ids)&set(ids['train']+ids['val']+ids['test'])
    save(RUN/'evaluation_plan.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        development_train_ids=ids['train'][:5], validation_ids=ids['val'][:10], test_ids=fresh_ids,
        test_image_count=len(fresh), test_data=str(TEST_DATA.relative_to(ROOT)),
        fresh_test_csv_sha256=sha(TEST_DATA/'ground_truth.csv'),fresh_test_manifest_sha256=sha(TEST_DATA/'manifest.json'),
        data_csv_sha256=sha(DATA/'ground_truth.csv'), data_manifest_sha256=sha(DATA/'manifest.json'),
        ocr='RapidOCR 3.10.0 PP-OCRv6 small det+rec, no task training',
        detector='V3 retrained Tiny; frozen validation threshold 0.35',
        metrics=dict(ocr_box_iou=.3, ocr_strict_box_iou=.5, symbol_iou=.5,
                     numeric_tolerance=1e-6, whitespace_ignored=True,
                     full_correct='all five values correct, review_required false; denominator all test images'),
        scope='synthetic V2 horizontal diagrams, four layouts; no ready L/x1/x2 parameter text',
        independence='new physical families, existing V2 renderer; not real-world external drawings',
        prohibited='no OCR/model/geometric threshold selection on test; static motor unchanged'))


def freeze():
    plan = read(RUN/'evaluation_plan.json')
    if not (RUN/'validation/metrics.json').exists():
        raise ValueError('Run separate validation before freeze')
    models = {p.name: sha(p) for p in sorted(DEFAULT_OCR_MODELS.glob('*.onnx'))}
    save(RUN/'frozen_ocr_protocol.json', dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
         plan_sha256=sha(RUN/'evaluation_plan.json'), code_sha256={p:sha(ROOT/p) for p in CODE},
         config=CONFIG, ocr_models=models, detector=SymbolReader(DEFAULT_DETECTOR).metadata,
         validation_metrics_sha256=sha(RUN/'validation/metrics.json'),
         validation_used_for_test_tuning=False, decisions='keep v1 thresholds; no changes after validation'))


def verify():
    p = read(RUN/'frozen_ocr_protocol.json')
    if sha(RUN/'evaluation_plan.json')!=p['plan_sha256']:
        raise ValueError('Plan checksum mismatch')
    for relative, digest in p['code_sha256'].items():
        if sha(ROOT/relative)!=digest:
            raise ValueError('Frozen OCR code changed: '+relative)
    for name, digest in p['ocr_models'].items():
        if sha(DEFAULT_OCR_MODELS/name)!=digest:
            raise ValueError('Frozen OCR weights changed')
    if SymbolReader(DEFAULT_DETECTOR).metadata!=p['detector']:
        raise ValueError('Frozen detector changed')


def match_texts(pred, gt, cutoff):
    candidates = sorted([(iou(p['bbox'], t['bbox']), pi, ti) for pi, p in enumerate(pred)
                         for ti, t in enumerate(gt) if iou(p['bbox'], t['bbox'])>=cutoff], reverse=True)
    used_p, used_t, matches = set(), set(), {}
    for overlap, pi, ti in candidates:
        if pi not in used_p and ti not in used_t:
            matches[ti] = pi
            used_p.add(pi); used_t.add(ti)
    return matches


def near(a, b):
    return a is not None and abs(float(a)-float(b)) <= 1e-6


def score(result, gt, reference):
    pred = [p for p in result['ocr_readings'] if not p.get('grouped_into')]
    matched = match_texts(pred, gt['texts'], .3)
    matched_strict = match_texts(pred, gt['texts'], .5)
    counts = Counter(ocr_gt=len(gt['texts']), ocr_predictions=len(pred), ocr_matched=len(matched),
                     ocr_matched_iou50=len(matched_strict))
    norm = lambda x: ''.join(x.split())
    for ti, target in enumerate(gt['texts']):
        p = pred[matched[ti]] if ti in matched else None
        counts['ocr_exact'] += p is not None and norm(p['raw_text'])==norm(target['text'])
        if target['kind'] in ('force','dimension'):
            counts['quantity_gt'] += 1
            counts['quantity_matched'] += p is not None
            q = p['quantity'] if p is not None else {}
            good = q.get('status')=='ok' and near(q.get('value_si'),target['value_si'])
            counts['quantity_correct_si'] += good
            counts['quantity_usable_correct_si'] += good and p['accepted']
            counts['unit_correct'] += q.get('unit')==target['unit']
    associated = result['forces']
    for target in [s for s in gt['symbols'] if s['class_id']==2]:
        counts['force_gt'] += 1
        text_gt = next(t for t in gt['texts'] if t.get('association')==target['role'] and t['kind']=='force')
        symbol_detected = any(s['class_id']==2 and iou(s['bbox'],target['bbox'])>=.5 for s in result['symbols'])
        text_readable = any(p['accepted'] and p['quantity'].get('kind')=='force'
                            and iou(p['bbox'],text_gt['bbox'])>=.3 for p in pred)
        counts['force_eligible'] += symbol_detected and text_readable
        assigned = [f for f in associated if f['magnitude_kN'] is not None and iou(f['symbol_bbox'],target['bbox'])>=.5]
        correct_link = any(iou(f['magnitude_kN']['bbox'],text_gt['bbox'])>=.3 for f in assigned)
        correct_value_link = any(iou(f['magnitude_kN']['bbox'],text_gt['bbox'])>=.3
                                 and near(f['magnitude_kN']['value'],text_gt['value_si']) for f in assigned)
        counts['force_assignments'] += len(assigned)>0
        counts['force_link_correct'] += correct_link
        counts['force_eligible_link_correct'] += correct_link and symbol_detected and text_readable
        counts['force_value_and_link_correct'] += correct_value_link
    partial = {}
    if result['length_m']:
        partial['L_m'] = result['length_m']['value']
    for i, force in enumerate(associated, 1):
        if force['magnitude_kN']:
            partial[f'P{i}_kN'] = force['magnitude_kN']['value']
        if force['position_m']:
            partial[f'x{i}_m'] = force['position_m']['value']
    counts['images'] = 1
    counts['accepted_images'] = result['extracted_inputs'] is not None and not result['review_required']
    correct = all(near(partial.get(k), reference[k]) for k in FIELDS)
    counts['full_correct'] = correct and counts['accepted_images']
    counts['accepted_wrong'] = counts['accepted_images'] and not correct
    counts['reviewed_images'] = result['review_required']
    for k in FIELDS:
        counts[k+'_available'] = k in partial
        counts[k+'_correct'] = near(partial.get(k), reference[k])
    return dict(counts=dict(counts), partial=partial, full_correct=bool(counts['full_correct']),
                issues=[i['code'] for i in result['issues']])


def ratios(counts):
    def ratio(a,b):return counts.get(a,0)/counts[b] if counts.get(b,0) else None
    return dict(ocr_text_detection_precision_iou30=ratio('ocr_matched','ocr_predictions'),
        ocr_text_detection_recall_iou30=ratio('ocr_matched','ocr_gt'),
        ocr_text_detection_recall_iou50=ratio('ocr_matched_iou50','ocr_gt'),
        ocr_exact_text_recall=ratio('ocr_exact','ocr_gt'),
        ocr_quantity_correct_si_all_gt=ratio('quantity_correct_si','quantity_gt'),
        ocr_quantity_usable_correct_si_all_gt=ratio('quantity_usable_correct_si','quantity_gt'),
        ocr_quantity_correct_si_when_localized=ratio('quantity_correct_si','quantity_matched'),
        ocr_unit_correct_all_gt=ratio('unit_correct','quantity_gt'),
        force_text_link_correct_all_forces=ratio('force_link_correct','force_gt'),
        force_text_link_correct_eligible=ratio('force_eligible_link_correct','force_eligible'),
        force_text_value_and_link_correct_all_forces=ratio('force_value_and_link_correct','force_gt'),
        full_correct_problem_rate=ratio('full_correct','images'),
        complete_extraction_coverage=ratio('accepted_images','images'),
        accepted_but_wrong_rate=ratio('accepted_wrong','images'),
        accepted_precision=ratio('full_correct','accepted_images'),
        review_rate=ratio('reviewed_images','images'),
        fields={k:dict(coverage=ratio(k+'_available','images'),correct_all=ratio(k+'_correct','images')) for k in FIELDS})


def visualize(source, result, reference, output):
    with Image.open(source) as im:im=im.convert('RGB')
    d=ImageDraw.Draw(im)
    for s in result['symbols']:d.rectangle(s['bbox'],outline='blue',width=3)
    for t in result['ocr_readings']:
        if t.get('grouped_into'):continue
        d.rectangle(t['bbox'],outline='green' if t['accepted'] else 'orange',width=2)
    for dimension in result['geometry'].get('dimensions',[]):
        a,b=dimension['endpoints_px'];d.line((*a,*b),fill='purple',width=3)
    im.thumbnail((1000,750))
    canvas=Image.new('RGB',(1000,im.height+150),'white');canvas.paste(im,(0,0))
    d=ImageDraw.Draw(canvas);font=load_font(17)
    lines=[Path(source).name,'GT: '+str({k:reference[k] for k in FIELDS}),
           'Read: '+str(result['extracted_inputs']),
           'Review: '+', '.join(i['code'] for i in result['issues'])]
    for j,line in enumerate(lines):d.text((8,im.height+6+j*32),line[:125],font=font,fill='black')
    canvas.save(output)


def evaluate(phase):
    if phase=='test':verify()
    plan=read(RUN/'evaluation_plan.json')
    if sha(DATA/'ground_truth.csv')!=plan['data_csv_sha256'] or sha(DATA/'manifest.json')!=plan['data_manifest_sha256']:
        raise ValueError('Dataset metadata changed')
    ids=plan['validation_ids' if phase=='validation' else 'test_ids']
    split='val' if phase=='validation' else 'test'
    data=DATA if phase=='validation' else TEST_DATA
    if phase=='test' and (sha(data/'ground_truth.csv')!=plan['fresh_test_csv_sha256'] or sha(data/'manifest.json')!=plan['fresh_test_manifest_sha256']):
        raise ValueError('Fresh test dataset changed')
    selected=[r for r in rows(data) if r['split']==split and int(r['problem_id']) in ids]
    out=RUN/phase;out.mkdir(exist_ok=False)
    (out/'predictions').mkdir();(out/'failures').mkdir()
    detector=SymbolReader(DEFAULT_DETECTOR);ocr=LocalOCR(DEFAULT_OCR_MODELS)
    totals=Counter();by_layout={};by_font={};issue_counts=Counter();summaries=[];failures=0
    start=time.perf_counter()
    for n,row in enumerate(selected):
        source=data/row['image']
        result=extract(source,detector,ocr)  # no row/annotation/physical values passed
        save(out/'predictions'/(source.stem+'.json'),result)
        truth=read(data/row['annotation_json'])  # scoring happens after inference
        case=score(result,truth,row);case.update(image=row['image'],problem_id=row['problem_id'],layout=row['dimension_layout'],font=row['font_name'])
        summaries.append(case);totals.update(case['counts']);issue_counts.update(case['issues'])
        by_layout.setdefault(row['dimension_layout'],Counter()).update(case['counts'])
        by_font.setdefault(row['font_name'],Counter()).update(case['counts'])
        if not case['full_correct']:
            failures+=1
            if failures<=20:visualize(source,result,row,out/'failures'/(source.stem+'.png'))
        if (n+1)%10==0:print(f'{phase}: {n+1}/{len(selected)} images, correct {totals["full_correct"]}, review {totals["reviewed_images"]}',flush=True)
    report=dict(phase=phase,status='BAŞARILI',measurement_completed=True,
         counts=dict(totals),metrics=ratios(totals),issues=dict(issue_counts),
         by_layout={k:dict(counts=dict(v),metrics=ratios(v)) for k,v in by_layout.items()},
         by_font={k:dict(counts=dict(v),metrics=ratios(v)) for k,v in by_font.items()},
         elapsed_seconds=time.perf_counter()-start,python=sys.version,platform=platform.platform(),
         detector=detector.metadata,ocr_engine=ocr.metadata(),
         scientific_limitations=['synthetic same-author data; no real drawings tested',
            'recognition confidence is uncalibrated; consistent high-confidence OCR errors may pass',
            'axis-aligned horizontal beam with one pin/roller and two point loads only',
            'no statics or reaction calculation; no desktop UI integration',
            'new physical families but same V2 renderer; old V1 test and training safety failure disclosed in amendment.json'],
         failed_image_count=failures,saved_failure_visualizations=min(failures,20))
    save(out/'case_scores.json',summaries);save(out/'metrics.json',report)
    print(json.dumps(dict(counts=dict(totals),metrics=report['metrics'],elapsed_seconds=report['elapsed_seconds']),ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['prepare','validation','freeze','test'])
    stage=parser.parse_args().stage
    if stage=='prepare':prepare()
    elif stage=='freeze':freeze()
    else:evaluate(stage)
