"""Fixed end-to-end experiment: references used for scoring AFTER inference."""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
from read_beam_diagram import DEFAULT_DETECTOR,DEFAULT_OCR_MODELS
from statikai.beam_pipeline import analyze_image,FIELDS,BALANCE
from statikai.beam_scope import CONFIG
from statikai.symbol_reader import SymbolReader
from statikai.ocr_engine import LocalOCR
from statikai.detector_metrics import aggregate
from evaluate_ocr_pipeline import score as score_ocr,ratios,visualize

ROOT=Path(__file__).resolve().parent;RUN=ROOT/'experiments/end_to_end_v1_20261108_01'
DATA=ROOT/'dataset_dimensions_v2';BENCH=RUN/'benchmark'
CODE=['statikai/beam_pipeline.py','statikai/beam_scope.py','solve_beam_image.py','statikai_beam_app.py',
      'evaluate_beam_pipeline.py','statikai/physics.py','statikai/diagram_reading.py','statikai/ocr_engine.py',
      'statikai/ocr_quantities.py','statikai/symbol_reader.py','evaluate_ocr_pipeline.py']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,data):
    with Path(p).open('x',encoding='utf8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
def rows(data):
    with (data/'ground_truth.csv').open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))
def near(a,b):return a is not None and abs(float(a)-float(b))<=1e-6


def prepare():
    old=rows(DATA);val_ids=sorted({int(r['problem_id']) for r in old if r['split']=='val'})[:10]
    save(RUN/'plan.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),seed=22091115,
        development_train_ids=list(range(5)),validation_ids=val_ids,
        test_ids=list(range(20000,20030)),test_physical_problems=30,test_images=120,
        primary_problem_view='variant 0, one predefined drawing per each of 30 unique physical problems',
        secondary_view='all four layouts, 120 drawings; siblings are not independent problems',
        benchmark_manifest_sha256=sha(BENCH/'manifest.json'),v2_manifest_sha256=sha(DATA/'manifest.json'),
        benchmark_csv_sha256=sha(BENCH/'ground_truth.csv'),
        classification=dict(correct='computed AND five inputs AND both reactions correct within 1e-6 AND balance passed',
            review='no published reactions; validation/inference/geometry/scope failure',
            wrong='computed but inputs or reactions incorrect, even if balance passed'),
        safety_challenges='14 edited training copies; controlled diagnostics, not external open-set performance',
        no_test_parameter_selection=True,no_real_external_drawings=True))


def freeze():
    if not (RUN/'validation/metrics.json').exists() or not (RUN/'safety/metrics.json').exists():raise ValueError('Run validation and safety first')
    save(RUN/'frozen_protocol.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(RUN/'plan.json'),code_sha256={p:sha(ROOT/p) for p in CODE},
        scope_config=CONFIG,balance_tolerances=BALANCE,detector=SymbolReader(DEFAULT_DETECTOR).metadata,
        ocr_models={p.name:sha(p) for p in DEFAULT_OCR_MODELS.glob('*.onnx')},
        validation_metrics_sha256=sha(RUN/'validation/metrics.json'),
        decisions='Keep train-developed scope checks; no changes based on validation or test accuracy.'))


def verify():
    frozen=read(RUN/'frozen_protocol.json');plan=read(RUN/'plan.json')
    if sha(RUN/'plan.json')!=frozen['plan_sha256']:raise ValueError('Plan changed')
    for p,digest in frozen['code_sha256'].items():
        if sha(ROOT/p)!=digest:raise ValueError('Frozen code changed: '+p)
    if sha(BENCH/'manifest.json')!=plan['benchmark_manifest_sha256']:raise ValueError('Test manifest changed')
    for p,digest in read(BENCH/'manifest.json')['files'].items():
        if sha(BENCH/p)!=digest:raise ValueError('Test input/reference changed: '+p)
    for p,digest in frozen['ocr_models'].items():
        if sha(DEFAULT_OCR_MODELS/p)!=digest:raise ValueError('OCR weights changed')
    if SymbolReader(DEFAULT_DETECTOR).metadata!=frozen['detector']:raise ValueError('Detector changed')


def safety():
    out=RUN/'safety';out.mkdir(exist_ok=False);cases=read(BENCH/'invalid_cases.json')
    det=SymbolReader(DEFAULT_DETECTOR);ocr=LocalOCR(DEFAULT_OCR_MODELS);results=[]
    for case in cases:
        result=analyze_image(BENCH/case['image'],det,ocr)
        save(out/(case['case']+'.json'),result)
        correct_stop=result['review_required'] and result['static_solution']['RA_kN'] is None and result['static_solution']['status']=='not_run'
        codes=[i['code'] for i in result['issues']]
        if result.get('extraction'):codes.extend(i['code'] for i in result['extraction']['issues'])
        if result.get('scope_check'):codes.extend(i['code'] for i in result['scope_check']['issues'])
        results.append(dict(case=case['case'],status='BAŞARILI' if correct_stop else 'BAŞARISIZ',observed=result['status'],issues=codes))
    report=dict(status='BAŞARILI' if all(c['status']=='BAŞARILI' for c in results) else 'BAŞARISIZ',
         correct_stops=sum(c['status']=='BAŞARILI' for c in results),total=len(results),cases=results,
         limitation='edited training copies; not open-set detection completeness')
    save(out/'metrics.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))


def evaluate(phase):
    if phase=='test':verify()
    plan=read(RUN/'plan.json');data=BENCH if phase=='test' else DATA
    selected=[r for r in rows(data) if r['split']==('test' if phase=='test' else 'val')
              and int(r['problem_id']) in plan['test_ids' if phase=='test' else 'validation_ids']]
    out=RUN/phase;out.mkdir(exist_ok=False);(out/'predictions').mkdir();(out/'failures').mkdir()
    det=SymbolReader(DEFAULT_DETECTOR);ocr=LocalOCR(DEFAULT_OCR_MODELS)
    summary=[];counts=Counter();ocr_counts=Counter();truths={};predictions={};issues=Counter();started=time.perf_counter();failed=0
    for index,row in enumerate(selected):
        result=analyze_image(data/row['image'],det,ocr) # image only, NO reference row
        stem=Path(row['image']).stem;save(out/'predictions'/(stem+'.json'),result)
        truth=read(data/row['annotation_json']);truths[row['image']]=truth['symbols']
        extraction=result.get('extraction')
        predictions[row['image']]=extraction['symbols'] if extraction else []
        if extraction:
            diagnostic=score_ocr(extraction,truth,row);ocr_counts.update(diagnostic['counts'])
        else:diagnostic=None
        solved=result['status']=='computed'
        inputs_correct=solved and all(near(result['validated_inputs'].get(k),row[k]) for k in FIELDS)
        reaction_correct=solved and all(near(result['static_solution'].get(k),row[k]) for k in ('RA_kN','RB_kN'))
        correct=bool(inputs_correct and reaction_correct and result['equilibrium']['passed'])
        category='automatic_correct' if correct else 'wrong_result' if solved else 'review_required'
        counts[category]+=1;counts['images']+=1
        if solved and not correct and result['equilibrium']['passed']:counts['balanced_wrong_results']+=1
        row_issues=[i['code'] for i in result['issues']]
        if extraction:row_issues.extend(i['code'] for i in extraction['issues'])
        if result.get('scope_check'):row_issues.extend(i['code'] for i in result['scope_check']['issues'])
        issues.update(row_issues)
        summary.append(dict(problem_id=row['problem_id'],variant=row['variant'],image=row['image'],category=category,
            reference={k:float(row[k]) for k in (*FIELDS,'RA_kN','RB_kN')},
            inputs=result['validated_inputs'],RA_kN=result['static_solution']['RA_kN'],RB_kN=result['static_solution']['RB_kN'],
            stages=result['stages'],balance_passed=result['equilibrium'].get('passed'),issues=row_issues,
            extraction_diagnostic=diagnostic))
        if not correct:
            failed+=1
            if failed<=20 and extraction:visualize(data/row['image'],extraction,row,out/'failures'/(stem+'.png'))
        if (index+1)%10==0:print(f'{phase} {index+1}/{len(selected)}: '+json.dumps(dict(counts)),flush=True)
    det_metrics,_=aggregate(selected,predictions,truths)
    primary=[r for r in summary if str(r['variant'])=='0']
    primary_counts=Counter(r['category'] for r in primary)
    families=defaultdict(list)
    for r in summary:families[r['problem_id']].append(r['category'])
    stage_counts={stage:dict(Counter(r['stages'].get(stage,'not_run') for r in summary))
                  for stage in ('image','detection','ocr','geometry','scope','validation','statics','equilibrium')}
    errors=[abs(r[k]-r['reference'][k]) for r in summary if r['category']!='review_required' for k in ('RA_kN','RB_kN')]
    report=dict(status='BAŞARILI',measurement_completed=True,phase=phase,counts=dict(counts),
        primary_distinct_problems=dict(total=len(primary),**dict(primary_counts)),
        families=dict(total=len(families),all_layouts_correct=sum(all(x=='automatic_correct' for x in v) for v in families.values())),
        automatic_correct_rate=counts['automatic_correct']/len(selected),
        review_rate=counts['review_required']/len(selected),wrong_result_rate=counts['wrong_result']/len(selected),
        reaction_max_abs_error_published_kN=max(errors) if errors else None,
        stage_counts=stage_counts,detector_metrics=det_metrics,
        ocr_and_geometry_metrics=dict(counts=dict(ocr_counts),metrics=ratios(ocr_counts)),issues=dict(issues),
        elapsed_seconds=time.perf_counter()-started,python=sys.version,platform=platform.platform(),
        detector=det.metadata,ocr_engine=ocr.metadata(),
        limitation='same-renderer synthetic narrow domain, not real engineering drawings; no guarantee of all unsupported-load rejection')
    save(out/'case_scores.json',summary);save(out/'metrics.json',report)
    with (out/'case_results.csv').open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['problem_id','variant','image','category','RA_kN','RB_kN','reference_RA_kN','reference_RB_kN','balance_passed','issues'])
        writer.writeheader()
        for r in summary:writer.writerow({k:r[k] for k in ('problem_id','variant','image','category','RA_kN','RB_kN','balance_passed')}|
            dict(reference_RA_kN=r['reference']['RA_kN'],reference_RB_kN=r['reference']['RB_kN'],issues=';'.join(r['issues'])))
    print(json.dumps({k:report[k] for k in ('counts','primary_distinct_problems','families','automatic_correct_rate','elapsed_seconds')},ensure_ascii=False),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('stage',choices=['prepare','validation','safety','freeze','test','verify'])
    stage=parser.parse_args().stage
    if stage=='prepare':prepare()
    elif stage=='freeze':freeze()
    elif stage=='verify':verify();print('Frozen protocol verified')
    elif stage=='safety':safety()
    else:evaluate(stage)
