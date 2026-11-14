"""Separate staged experiment: prepare -> CPU pilot -> full models -> locked test.

Old source code, checkpoints and test outcomes are never modified or selected on.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
from PIL import Image,ImageDraw
import torch
from torch.utils.data import DataLoader
from statikai import lite_detector as lite
from statikai import detector_model as tiny
from statikai.detector_data import CachedSymbols,load_rows
from statikai.detection import annotations,classical_detect,NAMES
from statikai.detector_metrics import aggregate,roller_failures,paired_family_bootstrap
from statikai.independent_benchmark import create_benchmark
from statikai.compat import load_font

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'dataset_dimensions_v2'
DEFAULT_RUN=ROOT/'experiments/detector_v3_20261108_01'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def read(path):return json.loads(Path(path).read_text(encoding='utf8'))


def specification(name):
    return (lite.LiteFPNCenter,lite.WIDTH,lite.HEIGHT,lite.targets,lite.loss,lite.decode,lite.image_tensor,lite.ARCHITECTURE) if name=='lite' else (
        tiny.TinyDetector,tiny.WIDTH,tiny.HEIGHT,tiny.make_target,tiny.detection_loss,tiny.decode_batch,tiny.image_tensor,'TinyDetector-v1')


def predict(model,rows,root,name,threshold=.05,batch_size=12):
    tensor=specification(name)[6];decode=specification(name)[5];model.eval();result={}
    with torch.inference_mode():
        for start in range(0,len(rows),batch_size):
            chunk=rows[start:start+batch_size];images=[];sizes=[]
            for row in chunk:
                with Image.open(Path(root)/row['image']) as im:images.append(tensor(im));sizes.append(im.size)
            result.update({r['image']:p for r,p in zip(chunk,decode(model(torch.stack(images)),sizes,threshold))})
    return result


def truths_for(rows,root):return {r['image']:annotations(root,r) for r in rows}
def filtered(predictions,threshold):return {k:[p for p in v if p['score']>=threshold] for k,v in predictions.items()}


def prepare(run):
    plan=read(run/'preregistered_plan.json')
    if (run/'data_protocol.json').exists():raise FileExistsError('Prepared protocol is immutable')
    manifest=read(SOURCE/'manifest.json')
    for relative,digest in manifest['files'].items():
        if sha(SOURCE/relative)!=digest:raise ValueError('Training data checksum mismatch: '+relative)
    train=load_rows(SOURCE,'train');val=load_rows(SOURCE,'val')
    if {r['problem_id'] for r in train}&{r['problem_id'] for r in val}:raise ValueError('Leaking IDs')
    benchmark=create_benchmark(run/'independent_test',SOURCE,plan['fresh_test']['families'],plan['fresh_test']['seed'],plan['fresh_test']['negative_images'])
    # Geometry/labels and physical references only; no detector is evaluated here.
    with (run/'independent_test/ground_truth.csv').open(encoding='utf8') as f:test=list(csv.DictReader(f))
    for row in test:
        boxes=annotations(run/'independent_test',row)
        if row['negative']=='False':
            if Counter(p['class_id'] for p in boxes)!=Counter({0:1,1:1,2:2}):raise ValueError('Invalid test inventory')
            L,p1,x1,p2,x2=[float(row[k]) for k in ('L_m','P1_kN','x1_m','P2_kN','x2_m')]
            if abs(float(row['RB_kN'])*L-p1*x1-p2*x2)>1e-8:raise ValueError('Wrong fresh reference')
        for p in boxes:
            if p['bbox'][2]<=p['bbox'][0] or p['bbox'][3]<=p['bbox'][1]:raise ValueError('Bad test box')
    old_inputs=set()
    for row in train+val:
        with Image.open(SOURCE/row['image']) as im:
            old_inputs.add(hashlib.sha256(im.convert('L').resize((384,256),Image.Resampling.BILINEAR).tobytes()).hexdigest())
    shared=0
    for row in test:
        with Image.open(run/'independent_test'/row['image']) as im:
            shared+=hashlib.sha256(im.convert('L').resize((384,256),Image.Resampling.BILINEAR).tobytes()).hexdigest() in old_inputs
    if shared:raise ValueError('New test input repeats old training/validation pixels')
    save(run/'independence_audit.json',dict(passed=True,old_train_val_images=len(train)+len(val),new_test_images=len(test),
        cross_dataset_actual_input_hash_matches=shared,exact_physical_overlap=0,
        old_test_images_scored=False,limitation='new physical instances and separate renderer, still same-author synthetic data'))
    code_paths=[ROOT/'train_detector_v3.py',ROOT/'detect_symbols_v3.py',*(ROOT/'statikai').glob('*detector*.py'),ROOT/'statikai/independent_benchmark.py']
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),plan_sha256=sha(run/'preregistered_plan.json'),
        train_csv_sha256=sha(SOURCE/'ground_truth.csv'),training_data_manifest_sha256=sha(SOURCE/'manifest.json'),
        fresh_test_manifest_sha256=sha(run/'independent_test/manifest.json'),
        train_ids=sorted({r['problem_id'] for r in train},key=int),val_ids=sorted({r['problem_id'] for r in val},key=int),
        test_ids=sorted({r['problem_id'] for r in test},key=int),training_images=len(train),validation_images=len(val),
        fresh_test=benchmark,code_sha256={str(p.relative_to(ROOT)):sha(p) for p in code_paths},
        test_predictions_used=False)
    save(run/'data_protocol.json',protocol);print(json.dumps({k:protocol[k] for k in ('frozen_utc','training_images','validation_images','test_predictions_used')}),flush=True)


def verify_protocol(run):
    protocol=read(run/'data_protocol.json')
    if sha(run/'preregistered_plan.json')!=protocol['plan_sha256']:raise ValueError('Plan changed')
    if sha(SOURCE/'ground_truth.csv')!=protocol['train_csv_sha256']:raise ValueError('Data changed')
    for name,h in protocol['code_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen experiment code changed: '+name)
    return protocol


def train(run,name,pilot=False):
    verify_protocol(run);plan=read(run/'preregistered_plan.json');seed=plan['seed']
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.set_num_threads(plan['cpu_threads']);torch.use_deterministic_algorithms(True)
    output=run/('cpu_pilot' if pilot else name);output.mkdir(exist_ok=False)
    train_rows=load_rows(SOURCE,'train');val_rows=load_rows(SOURCE,'val')
    if pilot:train_rows=train_rows[:plan['pilot']['train_images']];val_rows=val_rows[:plan['pilot']['val_images']]
    model_type,width,height,target,loss_func,_,_,architecture=specification(name)
    start=time.perf_counter();dataset=CachedSymbols(SOURCE,train_rows,width,height,target,training=True,seed=seed)
    loader=DataLoader(dataset,batch_size=plan['batch_size'],shuffle=True,num_workers=0,generator=torch.Generator().manual_seed(seed))
    truth=truths_for(val_rows,SOURCE);model=model_type()
    optimizer=torch.optim.AdamW(model.parameters(),lr=plan['learning_rate'],weight_decay=plan['weight_decay'])
    epochs=plan['pilot']['epochs'] if pilot else plan['full_epochs'];scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,epochs,eta_min=.0001)
    history=[];best=(-1.,-1.);training_start=time.perf_counter()
    for epoch in range(1,epochs+1):
        epoch_start=time.perf_counter();dataset.epoch=epoch;model.train();total=0.;n=0
        for images,heat,geo,mask in loader:
            optimizer.zero_grad();value=loss_func(model(images),heat,geo,mask)
            if not torch.isfinite(value):raise ValueError('Nonfinite training loss')
            value.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);optimizer.step();total+=value.item()*len(images);n+=len(images)
        raw=predict(model,val_rows,SOURCE,name,.2);report,_=aggregate(val_rows,raw,truth)
        quality=(report['f1'],report['mean_best_class_iou_all_gt'] or 0)
        item=dict(epoch=epoch,loss=total/n,val_f1=report['f1'],val_precision=report['precision'],val_recall=report['recall'],
                  val_iou=report['mean_best_class_iou_all_gt'],seconds=time.perf_counter()-epoch_start)
        history.append(item)
        if quality>best:
            best=quality;torch.save(dict(model_state=model.state_dict(),architecture=architecture,epoch=epoch,seed=seed,
                input_size=[width,height],pretrained_weights=False,data_protocol_sha256=sha(run/'data_protocol.json')),
                output/'best.pt')
        scheduler.step();save(output/'history.json',history);print(json.dumps(dict(model=name,pilot=pilot,**item)),flush=True)
    metadata=dict(architecture=architecture,pretrained_weights=False,parameters=sum(p.numel() for p in model.parameters()),
        device='cpu',threads=plan['cpu_threads'],seed=seed,epochs=epochs,training_images=len(train_rows),negative_training_images=96,
        validation_images=len(val_rows),cache_dtype='uint8',training_seconds=time.perf_counter()-training_start,
        total_seconds=time.perf_counter()-start,best_epoch=read_checkpoint(output/'best.pt')['epoch'],checkpoint_sha256=sha(output/'best.pt'),
        torch=str(torch.__version__),test_predictions_used=False)
    save(output/'metadata.json',metadata);print(json.dumps(metadata),flush=True)


def read_checkpoint(path):return torch.load(path,map_location='cpu',weights_only=True)


def evaluate(run):
    verify_protocol(run);plan=read(run/'preregistered_plan.json');torch.set_num_threads(plan['cpu_threads'])
    output=run/'evaluation';output.mkdir(exist_ok=False)
    val=load_rows(SOURCE,'val');truth_val=truths_for(val,SOURCE);models={};calibration={};thresholds={}
    for name in ('lite','tiny'):
        checkpoint=read_checkpoint(run/name/'best.pt');model=specification(name)[0]();model.load_state_dict(checkpoint['model_state']);models[name]=model
        raw=predict(model,val,SOURCE,name,.05)
        candidates=[]
        for score in plan['selection']['threshold_candidates']:
            report,_=aggregate(val,filtered(raw,score),truth_val);candidates.append(dict(score=score,f1=report['f1']))
        thresholds[name]=max(candidates,key=lambda r:r['f1'])['score'];calibration[name]=candidates
    classical=[]
    for cutoff in plan['selection']['classical_fill_cutoffs']:
        pred={}
        for row in val:
            with Image.open(SOURCE/row['image']) as im:pred[row['image']]=classical_detect(im,cutoff)
        report,_=aggregate(val,pred,truth_val);classical.append(dict(cutoff=cutoff,f1=report['f1']))
    cutoff=max(classical,key=lambda r:r['f1'])['cutoff']
    frozen=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),thresholds=thresholds,classical_cutoff=cutoff,
        calibration=calibration,classical_calibration=classical,
        checkpoints={name:sha(run/name/'best.pt') for name in ('lite','tiny')},
        data_protocol_sha256=sha(run/'data_protocol.json'),selection_split='validation only',test_predictions_started=False)
    save(output/'frozen_thresholds.json',frozen)
    print('Validation choices frozen. Starting NEW independent test once.',flush=True)
    test_root=run/'independent_test'
    for name,h in read(test_root/'manifest.json')['files'].items():
        if sha(test_root/name)!=h:raise ValueError('Fresh test changed')
    with (test_root/'ground_truth.csv').open(encoding='utf8') as f:rows=list(csv.DictReader(f))
    truths=truths_for(rows,test_root);predictions={};raws={};timing={}
    for name in ('lite','tiny'):
        start=time.perf_counter();raws[name]=predict(models[name],rows,test_root,name,.05)
        predictions[name]=filtered(raws[name],thresholds[name]);timing[name]=time.perf_counter()-start
    model=tiny.TinyDetector();model.load_state_dict(read_checkpoint(ROOT/'detector_results/best_full_image_detector.pt')['model_state'])
    legacy_score=read(ROOT/'detector_results/evaluation/frozen_protocol.json')['learned']['score_threshold']
    start=time.perf_counter();predictions['original_tiny']=predict(model,rows,test_root,'tiny',legacy_score);timing['original_tiny']=time.perf_counter()-start
    start=time.perf_counter();predictions['opencv']={}
    for row in rows:
        with Image.open(test_root/row['image']) as im:predictions['opencv'][row['image']]=classical_detect(im,cutoff)
    timing['opencv']=time.perf_counter()-start
    reports={};details={}
    for name,pred in predictions.items():
        report,detail=aggregate(rows,pred,truths);report['iou_075']=aggregate(rows,pred,truths,.75)[0]
        report['by_condition']={c:aggregate([r for r in rows if r['condition']==c],pred,truths)[0] for c in sorted({r['condition'] for r in rows})}
        report['inference_seconds_including_io']=timing[name];reports[name]=report;details[name]=detail
    fn=roller_failures(rows,predictions['lite'],raws['lite'],truths,thresholds['lite'])
    save(output/'metrics.json',reports);save(output/'predictions_original_pixels.json',predictions)
    save(output/'raw_predictions.json',raws);save(output/'per_image_metrics.json',details);save(output/'roller_false_negatives.json',fn)
    save(output/'paired_bootstrap.json',paired_family_bootstrap(details['lite'],details['tiny']))
    failure_images(run,rows,predictions['lite'],truths,details['lite'])
    print(json.dumps({name:{k:r[k] for k in ('precision','recall','f1','mean_iou_matched_tp','mean_best_class_iou_all_gt')} for name,r in reports.items()}),flush=True)


def failure_images(run,rows,predictions,truths,details):
    out=run/'evaluation/failures';out.mkdir();by_image={r['image']:r for r in rows}
    failures=[d for d in details if d['ground_truth_objects']>0 and not d['exact']]
    chosen=failures[:20];thumbnails=[]
    for index,item in enumerate(chosen):
        row=by_image[item['image']]
        with Image.open(run/'independent_test'/row['image']) as source:
            im=Image.new('RGB',(source.width,source.height+65),'white');im.paste(source,(0,65))
        draw=ImageDraw.Draw(im)
        draw.text((10,7),f"{row['problem_id']} / {row['condition']}  TP={item['tp']} FP={item['fp']} FN={item['fn']}",font=load_font(17),fill='black')
        draw.text((10,31),'GREEN: ground truth   RED: prediction   NO OCR / NO REACTION SOLUTION',font=load_font(14),fill='black')
        for p in truths[item['image']]:
            x0,y0,x1,y1=p['bbox'];draw.rectangle((x0,y0+65,x1,y1+65),outline='#00a647',width=3)
        for p in predictions[item['image']]:
            x0,y0,x1,y1=p['bbox'];draw.rectangle((x0,y0+65,x1,y1+65),outline='#eb2c34',width=2)
            draw.text((max(0,x0),max(65,y0+45)),f"{NAMES[p['class_id']]} {p['score']:.2f}",font=load_font(12),fill='#eb2c34')
        im.save(out/f'{index:02d}_{Path(item["image"]).stem}.png');im.thumbnail((400,300));thumbnails.append(im.copy())
    if thumbnails:
        sheet=Image.new('RGB',(1600,300*math_ceil(len(thumbnails)/4)),'#e8edf2')
        for i,im in enumerate(thumbnails):sheet.paste(im,((i%4)*400,(i//4)*300))
        sheet.save(run/'evaluation/failure_contact_sheet.png')
    save(run/'evaluation/failure_selection.json',dict(total_erroneous_positive_images=len(failures),visualized=len(chosen),rule='first 20 in fixed benchmark row order',selected=chosen))


def math_ceil(value):return int(np.ceil(value))


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','pilot','train-lite','train-tiny','evaluate']);p.add_argument('--run',type=Path,default=DEFAULT_RUN)
    args=p.parse_args();run=args.run.resolve()
    if args.stage=='prepare':prepare(run)
    elif args.stage=='pilot':train(run,'lite',True)
    elif args.stage=='evaluate':evaluate(run)
    else:train(run,args.stage.split('-')[1])


if __name__=='__main__':main()
