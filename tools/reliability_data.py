"""Predefined validation/test images and labels; never invokes OCR or detector.

All siblings in one family/split. Clean drawings use the unchanged V2 renderer.
Perturbations are fixed before score selection. Ground truth only for scoring.
"""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from statikai.dataset_v2 import parameters,render_case,PHYSICAL
from statikai.compat import load_font
RUN=ROOT/'experiments/reliability_v1_20261108_01'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(p):return tuple(str(Decimal(str(v)).normalize()) for v in p)


def perturb(im,ann,profile,seed):
    im=im.copy().convert('RGB');d=ImageDraw.Draw(im);s=im.width/900
    first=next(t for t in ann['texts'] if t['kind']=='force')
    def replace(text,value):
        a,b,c,e=text['bbox'];d.rectangle((a-8*s,b-8*s,c+12*s,e+8*s),fill='white')
        if value:d.text((a,b-4*s),value,font=load_font(round(22*s)),fill='black')
    if profile=='blur_scan':
        # Preserves the physical problem; readability is measured, not assumed bad.
        rng=np.random.default_rng(seed);w,h=im.size
        small=im.resize((round(w*.38),round(h*.38)),Image.Resampling.BILINEAR)
        im=small.resize((w,h),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(.8*s))
        arr=np.asarray(im).astype(float);arr+=rng.normal(0,5,arr.shape[:2])[:,:,None]
        im=Image.fromarray(np.clip(arr,0,255).astype('uint8'))
    elif profile=='erased_force':replace(first,None)
    elif profile=='wrong_force_unit':replace(first,str(first['value_si'])+' kg')
    elif profile=='distributed':
        y=ann['beam']['y_px'];a=im.width*.31;b=im.width*.68;top=y-55*s
        d.line((a,top,b,top),fill='black',width=max(2,round(2*s)))
        for xx in np.linspace(a,b,8):
            d.line((xx,top,xx,y-4*s),fill='black',width=max(1,round(s)))
            d.polygon([(xx,y-4*s),(xx-4*s,y-11*s),(xx+4*s,y-11*s)],fill='black')
        d.text((im.width*.44,top-28*s),'5 kN/m',font=load_font(round(20*s)),fill='black')
    else:raise ValueError(profile)
    return im


def generate():
    data=RUN/'data';data.mkdir(exist_ok=False)
    for folder in ('images','annotations'):(data/folder).mkdir()
    with (ROOT/'dataset_dimensions_v2/ground_truth.csv').open(encoding='utf8') as f:old_rows=list(csv.DictReader(f))
    val_ids=sorted({int(r['problem_id']) for r in old_rows if r['split']=='val'})[:20]
    used=set(key([r[k] for k in PHYSICAL]) for r in old_rows)
    for relative in ('experiments/detector_v3_20261108_01/independent_test/ground_truth.csv',
                     'experiments/ocr_v1_1_20261108_01/fresh_test/ground_truth.csv',
                     'experiments/end_to_end_v1_20261108_01/benchmark/ground_truth.csv'):
        with (ROOT/relative).open(encoding='utf8') as f:
            for row in csv.DictReader(f):
                if all(row.get(k) for k in PHYSICAL):used.add(key([row[k] for k in PHYSICAL]))
    families=[]
    for pid in val_ids:
        base=next(r for r in old_rows if int(r['problem_id'])==pid and r['variant']=='0')
        families.append(('validation',pid,[float(base[k]) for k in PHYSICAL]))
    rng=random.Random(22091116)
    for pid in range(30000,30030):
        L=round(rng.uniform(8,18),2);values=[L,rng.randint(6,30),round(L*rng.uniform(.22,.38),3),rng.randint(6,30),round(L*rng.uniform(.62,.78),3)]
        assert key(values) not in used;used.add(key(values));families.append(('test',pid,values))
    records=[]
    for split,pid,values in families:
        ell,p1,x1,p2,x2=map(lambda v:Decimal(str(v)),values);rb=(p1*x1+p2*x2)/ell;ra=p1+p2-rb
        assert abs(ra+rb-p1-p2)<Decimal('1e-20') and abs(rb*ell-p1*x1-p2*x2)<Decimal('1e-20')
        base_im=base_ann=None
        for variant in range(4):
            for attempt in range(50):
                # Validation rendering seed distinct from old test settings.
                p=parameters(22091116,pid,variant,attempt)
                try:im,_,ann=render_case(values,p);break
                except ValueError:continue
            else:raise RuntimeError('Cannot render nonoverlapping labels')
            if variant==0:base_im,base_ann=im.copy(),ann
            stem=f'{split}_{pid}_clean_v{variant}';image='images/'+stem+'.png';annotation='annotations/'+stem+'.json'
            im.save(data/image);(data/annotation).write_text(json.dumps(ann,ensure_ascii=False,indent=2),encoding='utf8')
            records.append(dict(split=split,problem_id=pid,profile='clean',variant=variant,
                problem_supported=True,required_text_complete=True,**dict(zip(PHYSICAL,values)),
                RA_kN=str(ra),RB_kN=str(rb),image=image,annotation_json=annotation))
        for j,profile in enumerate(('blur_scan','erased_force','wrong_force_unit','distributed')):
            im=perturb(base_im,base_ann,profile,pid*31+j)
            stem=f'{split}_{pid}_{profile}';image='images/'+stem+'.png';annotation='annotations/'+stem+'.json'
            im.save(data/image);(data/annotation).write_text(json.dumps(base_ann,ensure_ascii=False,indent=2),encoding='utf8')
            records.append(dict(split=split,problem_id=pid,profile=profile,variant=0,
                problem_supported=profile!='distributed',required_text_complete=profile not in ('erased_force','wrong_force_unit'),
                **dict(zip(PHYSICAL,values)),RA_kN=str(ra),RB_kN=str(rb),image=image,annotation_json=annotation))
    with (data/'cases.csv').open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=records[0]);writer.writeheader();writer.writerows(records)
    manifest=dict(seed=22091116,validation_ids=val_ids,test_ids=list(range(30000,30030)),
        validation_images=160,test_images=240,grouping='8 sibling images per family, no train/validation/test family crossover',
        test_exact_physical_overlap=0,profiles=['clean x4','blur_scan','erased_force','wrong_force_unit','distributed'],
        references='Decimal reactions independently verified; damaged-image annotations are original layout references, not OCR truth for erased text',
        limitations='synthetic V2 renderer; no external real drawings',generator_sha256=sha(Path(__file__)),
        files={p.relative_to(data).as_posix():sha(p) for p in sorted(data.rglob('*')) if p.is_file()})
    (data/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps({k:manifest[k] for k in ('validation_images','test_images','validation_ids','test_ids')}))


if __name__=='__main__':generate()
