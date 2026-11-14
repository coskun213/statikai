"""New fixed synthetic physical problems; no inference during data creation."""
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import random
import sys
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from statikai.dataset_v2 import parameters,render_case,available_fonts,PHYSICAL
from statikai.compat import load_font

RUN=ROOT/'experiments/end_to_end_v1_20261108_01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(p):return tuple(str(Decimal(str(v)).normalize()) for v in p)


def main():
    out=RUN/'benchmark';out.mkdir(exist_ok=False)
    for name in ('images','annotations','invalid'):(out/name).mkdir()
    rng=random.Random(22091115);old=set();rows=[]
    sources=[ROOT/'dataset_dimensions_v2/ground_truth.csv',
        ROOT/'experiments/detector_v3_20261108_01/independent_test/ground_truth.csv',
        ROOT/'experiments/ocr_v1_1_20261108_01/fresh_test/ground_truth.csv']
    for source in sources:
        with source.open(encoding='utf8') as f:
            for r in csv.DictReader(f):
                if all(r.get(k) for k in PHYSICAL):old.add(key([r[k] for k in PHYSICAL]))
    for pid in range(20000,20030):
        L=round(rng.uniform(8,18),2);p1=rng.randint(6,30);p2=rng.randint(6,30)
        x1=round(L*rng.uniform(.22,.38),3);x2=round(L*rng.uniform(.62,.78),3)
        physics=[L,p1,x1,p2,x2];assert key(physics) not in old;old.add(key(physics))
        ell,pa,xa,pb,xb=map(lambda v:Decimal(str(v)),physics)
        rb=(pa*xa+pb*xb)/ell;ra=pa+pb-rb
        assert abs(ra+rb-pa-pb)<Decimal('1e-20') and abs(rb*ell-pa*xa-pb*xb)<Decimal('1e-20')
        for variant in range(4):
            for attempt in range(50):
                p=parameters(22091115,pid,variant,attempt)
                try:im,_,ann=render_case(physics,p);break
                except ValueError:continue
            else:raise RuntimeError('Cannot place nonoverlapping labels')
            stem=f'e2e_{pid}_v{variant}';image='images/'+stem+'.png';annotation='annotations/'+stem+'.json'
            im.save(out/image);(out/annotation).write_text(json.dumps(ann,ensure_ascii=False,indent=2),encoding='utf8')
            rows.append(dict(problem_id=str(pid),variant=str(variant),split='test',**dict(zip(PHYSICAL,physics)),
                RA_kN=str(ra),RB_kN=str(rb),image=image,annotation_json=annotation,
                layout=p['layout'],font=available_fonts()[p['font_index']]['name']))
    with (out/'ground_truth.csv').open('x',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    # Predefined safety challenges are edited COPIES of a training image only.
    source=ROOT/'dataset_dimensions_v2/images/beam_0000_v0.png'
    ann=json.loads((ROOT/'dataset_dimensions_v2/annotations/beam_0000_v0.json').read_text(encoding='utf8'))
    force=next(t for t in ann['texts'] if t['kind']=='force')
    total=next(t for t in ann['texts'] if t['kind']=='dimension' and t['value_si']==15.88)
    dimension=next(t for t in ann['texts'] if t['kind']=='dimension')
    first=next(s for s in ann['symbols'] if s['role']=='load_1');support=next(s for s in ann['symbols'] if s['role']=='support_A')
    cases=[]
    for name in ('erased_force','wrong_force_unit','contradictory_total','wrong_length_unit','erased_dimensions',
                 'extra_force_text','upward_force','horizontal_force','fixed_support','moment','distributed','third_arrow','blank','corrupt'):
        dest=out/'invalid'/(name+'.png')
        if name=='corrupt':dest.write_bytes(b'not a readable image')
        else:
            with Image.open(source) as image:im=image.convert('RGB')
            d=ImageDraw.Draw(im);beam=ann['beam'];y=beam['y_px']
            def replace(text,value):
                a,b,c,e=text['bbox'];d.rectangle((a-8,b-8,c+12,e+8),fill='white')
                if value:d.text((a,b-4),value,font=load_font(22),fill='black')
            if name=='erased_force':replace(force,None)
            if name=='wrong_force_unit':replace(force,'17 kg')
            if name=='contradictory_total':replace(total,'20000 mm')
            if name=='wrong_length_unit':replace(dimension,'5242 kg')
            if name=='erased_dimensions':
                for t in ann['texts']:
                    if t['kind']=='dimension':replace(t,None)
            if name=='extra_force_text':d.text((280,90),'23 kN',font=load_font(22),fill='black')
            if name in ('upward_force','horizontal_force'):
                a,b,c,e=first['bbox'];x=(a+c)/2;d.rectangle((a-8,b-8,c+8,e+3),fill='white')
                if name=='upward_force':
                    d.line((x,b,x,e),fill='black',width=2);d.polygon([(x,b),(x-9,b+16),(x+9,b+16)],fill='black')
                else:
                    d.line((x-25,b+30,x+25,b+30),fill='black',width=2)
                    d.polygon([(x+25,b+30),(x+11,b+20),(x+11,b+40)],fill='black')
            if name=='fixed_support':
                a,b,c,e=support['bbox'];x=beam['left_px'];d.rectangle((a-5,y+2,c+5,e+5),fill='white')
                d.line((x,y+3,x,y+56),fill='black',width=4)
                for yy in range(round(y+7),round(y+55),8):d.line((x,yy,x-16,yy+7),fill='black',width=2)
            if name=='moment':d.arc((400,y-55,455,y-5),20,330,fill='black',width=3)
            if name=='distributed':
                d.line((300,180,610,180),fill='black',width=3)
                for xx in range(350,580,40):d.line((xx,180,xx,y-5),fill='black',width=2)
                d.text((420,130),'5 kN/m',font=load_font(22),fill='black')
            if name=='third_arrow':
                d.line((450,179,450,y-5),fill='black',width=2);d.polygon([(450,y-5),(441,y-21),(459,y-21)],fill='black')
            if name=='blank':im=Image.new('RGB',im.size,'white')
            im.save(dest)
        cases.append(dict(case=name,image=dest.relative_to(out).as_posix(),expected='review_required',
                          source_split='train',expected_reactions=None))
    (out/'invalid_cases.json').write_text(json.dumps(cases,indent=2),encoding='utf8')
    manifest=dict(seed=22091115,families=30,distinct_physical_problems=30,positive_images=120,
         layouts_per_problem=4,invalid_cases=len(cases),exact_overlap_with_existing_physics=0,
         generator_sha256=sha(Path(__file__)),renderer_sha256=sha(ROOT/'statikai/dataset_v2.py'),
         limitations='same synthetic V2 renderer; no external real-source engineering drawings',
         files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps({k:manifest[k] for k in ('families','positive_images','invalid_cases','exact_overlap_with_existing_physics')}))


if __name__=='__main__':main()
