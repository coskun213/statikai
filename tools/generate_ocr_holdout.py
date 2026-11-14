"""Predefined fresh physical families for OCR V1.1, no detector/OCR inspection.

Same V2 renderer, not a new external style. No old images or models are changed.
References are calculated directly here; the statics engine is not modified.
"""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from statikai.dataset_v2 import render_case,parameters,available_fonts,PHYSICAL


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(p):return tuple(str(Decimal(str(v)).normalize()) for v in p)


def main():
    out=ROOT/'experiments/ocr_v1_1_20261108_01/fresh_test'
    out.mkdir(exist_ok=False)
    for name in ('images','annotations'):(out/name).mkdir()
    seed=22091110;rng=random.Random(seed)
    old=set()
    sources=[ROOT/'dataset_dimensions_v2/ground_truth.csv',ROOT/'experiments/detector_v3_20261108_01/independent_test/ground_truth.csv']
    for source in sources:
        with source.open(encoding='utf8') as handle:
            for row in csv.DictReader(handle):
                if all(row.get(k) for k in PHYSICAL):old.add(key([row[k] for k in PHYSICAL]))
    source_keys=set(old);rows=[];fonts=available_fonts();attempts=0
    for pid in range(10000,10050):
        L=round(rng.uniform(8,18),2);p1=rng.randint(6,30);p2=rng.randint(6,30)
        x1=round(L*rng.uniform(.22,.38),3);x2=round(L*rng.uniform(.62,.78),3)
        changed=round(L*rng.uniform(.12,.45),3)
        cases=[[L,p1,x1,p2,x2] for _ in range(4)]+[[L,p1,changed,p2,x2]]
        assert all(key(p) not in old for p in (cases[0],cases[4]))
        assert key(cases[0])!=key(cases[4])
        old.update(key(p) for p in cases)
        paired=None
        for variant,physics in enumerate(cases):
            for attempt in ([paired] if variant==4 else range(50)):
                params=parameters(seed,pid,variant,attempt)
                try:
                    image,_,annotation=render_case(physics,params)
                    if variant==0:render_case(cases[4],params)
                    break
                except ValueError:attempts+=1
            else:raise RuntimeError('Unable to render nonoverlapping labels')
            if variant==0:paired=attempt
            stem=f'ocr_fresh_{pid}_v{variant}'
            image_path=out/'images'/(stem+'.png');image.save(image_path)
            annotation.update(problem_id=str(pid),variant=str(variant),split='test',image_sha256=digest(image_path))
            ann='annotations/'+stem+'.json'
            (out/ann).write_text(json.dumps(annotation,ensure_ascii=False,indent=2),encoding='utf8')
            # Independent Decimal moment balance, evaluation references only.
            ell,pa,xa,pb,xb=map(lambda v:Decimal(str(v)),physics)
            rb=(pa*xa+pb*xb)/ell;ra=pa+pb-rb
            assert abs(ra+rb-pa-pb)<Decimal('1e-20') and abs(rb*ell-pa*xa-pb*xb)<Decimal('1e-20')
            rows.append(dict(problem_id=str(pid),variant=variant,split='test',
                **dict(zip(PHYSICAL,physics)),RA_kN=str(ra),RB_kN=str(rb),
                image='images/'+stem+'.png',annotation_json=ann,dimension_layout=params['layout'],
                font_name=fonts[params['font_index']]['name'],length_unit=params['length_unit'],force_unit=params['force_unit']))
    with (out/'ground_truth.csv').open('x',newline='',encoding='utf8') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    manifest=dict(seed=seed,families=50,images=250,unique_physical_configurations=100,
        source='statikai.dataset_v2.parameters/render_case unchanged',overlap_with_existing_physics=0,
        existing_physical_configurations_checked=len(source_keys),font_files=fonts,rejected_layout_attempts=attempts,
        no_model_used_in_generation=True,ground_truth_balance_checks='all 250 passed Decimal force/moment checks',
        limitations='same-author synthetic renderer, not external drawings',
        generation_code_sha256=digest(Path(__file__)),renderer_sha256=digest(ROOT/'statikai/dataset_v2.py'),
        files={p.relative_to(out).as_posix():digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps({k:manifest[k] for k in ('families','images','unique_physical_configurations','overlap_with_existing_physics','rejected_layout_attempts')}))


if __name__=='__main__':main()
