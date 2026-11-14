"""Freeze on val, then evaluate both methods on the SAME grouped test once."""
import argparse
from collections import defaultdict
import csv
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import torch
from statikai.compat import load_font
from statikai.detection import NAMES,records,annotations,classical_detect,evaluate_rows,summarize
from statikai.detector_model import TinyDetector,learned_detect
from train_detector import predict_rows


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def family_bootstrap(details,seed=2209,repeats=1000):
    families=defaultdict(lambda:np.zeros(3))
    for row in details: families[row['problem_id']]+=np.array([row['tp'],row['fp'],row['fn']])
    data=np.stack(list(families.values()));rng=np.random.default_rng(seed)
    draws=data[rng.integers(0,len(data),size=(repeats,len(data)))].sum(1)
    tp,fp,fn=draws.T
    values=dict(precision=tp/np.maximum(1,tp+fp),recall=tp/np.maximum(1,tp+fn),f1=2*tp/np.maximum(1,2*tp+fp+fn))
    return {key:np.quantile(value,[.025,.975]).tolist() for key,value in values.items()}


def overlay(image,predictions,truth,path):
    im=image.convert('RGB').copy();draw=ImageDraw.Draw(im);font=load_font(12)
    for gt in truth: draw.rectangle(gt['bbox'],outline='#008b45',width=2)
    for pred in predictions:
        draw.rectangle(pred['bbox'],outline='#c52222',width=2)
        x,y=pred['bbox'][:2]
        draw.text((x,max(15,y-15)),f"{NAMES[pred['class_id']]} {pred['score']:.2f}",fill='#c52222',font=font)
    draw.text((8,3),'green=reference; red=prediction; NO OCR / NO REACTIONS',fill='#000000',font=font)
    im.save(path)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',default='dataset_extended')
    parser.add_argument('--checkpoint',default='detector_results/best_full_image_detector.pt')
    parser.add_argument('--out',default='detector_results/evaluation')
    args=parser.parse_args();torch.set_num_threads(2)
    out=Path(args.out)
    if (out/'frozen_protocol.json').exists(): raise FileExistsError('Use a new evaluation directory; frozen tests are preserved')
    out.mkdir(parents=True,exist_ok=True)
    root=Path(args.dataset)
    val=records(root,'val','A')
    checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
    if checkpoint.get('architecture')!='TinyDetector-v1': raise ValueError('Wrong checkpoint architecture')
    model=TinyDetector();model.load_state_dict(checkpoint['model_state']);model.eval()
    calibration=[]
    for cutoff in (.55,.65,.75):
        prediction={}
        for row in val:
            with Image.open(root/row['image']) as image:
                prediction[row['image']]=classical_detect(image,cutoff)
        report,_=evaluate_rows(val,prediction,root)
        calibration.append(dict(method='classical',fill_cutoff=cutoff,val_f1=report['f1']))
        print(json.dumps(calibration[-1]),flush=True)
    best_classic=max(calibration,key=lambda x:x['val_f1'])
    raw=predict_rows(model,root,val,.05)
    learned=[]
    for threshold in (.1,.2,.35,.5,.65):
        prediction={key:[p for p in value if p['score']>=threshold] for key,value in raw.items()}
        report,_=evaluate_rows(val,prediction,root)
        learned.append(dict(method='learned',score_threshold=threshold,val_f1=report['f1']))
        print(json.dumps(learned[-1]),flush=True)
    best_learned=max(learned,key=lambda x:x['val_f1'])
    protocol=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),iou_threshold=.5,
        checkpoint_sha256=digest(args.checkpoint),data_csv_sha256=digest(root/'ground_truth.csv'),
        selected_epoch=checkpoint['epoch'],classical=best_classic,learned=best_learned,
        calibration=calibration+learned,selection_split='val',selection_style='A',
        test_accessed_during_selection=False)
    # This artifact is committed to disk BEFORE any test predictions or scoring.
    (out/'frozen_protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf8')
    print('Validation selection frozen; starting fixed test evaluation.',flush=True)
    test=records(root,'test')
    predictions=dict(learned=predict_rows(model,root,test,best_learned['score_threshold']),classical={})
    for row in test:
        with Image.open(root/row['image']) as image:
            predictions['classical'][row['image']]=classical_detect(image,best_classic['fill_cutoff'])
    summaries={};all_details=[]
    for method,prediction in predictions.items():
        report,details=evaluate_rows(test,prediction,root)
        report['family_bootstrap_95_ci']=family_bootstrap(details)
        report['by_style']={style:evaluate_rows([r for r in test if r['style']==style],prediction,root)[0] for style in ('A','B')}
        summaries[method]=report
        all_details += [dict(method=method,**d) for d in details]
    (out/'predictions.json').write_text(json.dumps(predictions,indent=2),encoding='utf8')
    with (out/'per_image_metrics.csv').open('w',newline='',encoding='utf8') as handle:
        writer=csv.DictWriter(handle,fieldnames=all_details[0].keys());writer.writeheader();writer.writerows(all_details)
    test_ids=sorted({int(r['problem_id']) for r in test})[:10]
    diagnostic=[]
    for row in test:
        if int(row['problem_id']) not in test_ids: continue
        diagnostic.append(dict(image=row['image'],problem_id=row['problem_id'],variant=row['variant'],style=row['style'],
            symbol_predictions={m:p[row['image']] for m,p in predictions.items()},
            ocr_status='not_implemented',extracted_physical_inputs=None,
            reaction_solver_status='not_connected_to_images',RA_kN=None,RB_kN=None,
            end_to_end_solution_status='not_implemented',review_required=True))
    (out/'diagnostic_10_families.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf8')
    errors=sorted(all_details,key=lambda d:(d['f1'],d['image'],d['method']))[:10]
    examples=out/'examples';examples.mkdir(exist_ok=True)
    by_image={r['image']:r for r in test}
    selected=errors+[dict(image=r['image'],method='learned') for r in test if int(r['problem_id']) in test_ids and r['variant']=='0']
    for i,item in enumerate(selected):
        row=by_image[item['image']]
        with Image.open(root/row['image']) as image:
            overlay(image,predictions[item['method']][row['image']],annotations(root,row),
                    examples/f"{i:02d}_{item['method']}_{Path(row['image']).stem}.png")
    negative=[]
    for label in ('blank','beam_only','text_only'):
        im=Image.new('RGB',(720,400),'white');draw=ImageDraw.Draw(im)
        if label=='beam_only': draw.line((90,210,630,210),fill='black',width=4)
        if label=='text_only': draw.text((90,100),'A 10 kN 12 m  B',font=load_font(20),fill='black')
        p=dict(classical=classical_detect(im,best_classic['fill_cutoff']),
               learned=learned_detect(model,im,best_learned['score_threshold']))
        negative.append(dict(condition=label,predictions=p,false_positive_counts={m:len(v) for m,v in p.items()}))
    (out/'negative_diagnostics.json').write_text(json.dumps(negative,indent=2),encoding='utf8')
    result=dict(scope='Full-image symbol detection only; no OCR or automatic reaction solution',
        test_families=len({r['problem_id'] for r in test}),test_images=len(test),
        diagnostic_families=test_ids,methods=summaries,
        limitations=['Both styles are synthetic and authored in this repository',
            'Style B is held out from training/threshold selection but is not an external source',
            'Bootstrap clusters by base problem; one training seed only',
            'Negative diagnostic has only three simple cases',
            'Physical dimensions must not be inferred from image scale'],
        protocol_sha256=digest(out/'frozen_protocol.json'))
    (out/'metrics.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
