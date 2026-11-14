"""Reproducible synthetic statics image dataset and exact analytical ground truth.

Produces rendered simply supported beams (pin at A, roller at B) with two
vertical point loads, 4 equivalent renderings and 1 physically altered case.
All split assignments happen at the underlying problem level to avoid leakage.
This is NOT a trained AI model. It is the scientifically verifiable dataset
and baseline with which a trained diagram parser can be evaluated.
"""
from pathlib import Path
import argparse, csv, random, math
from PIL import Image, ImageDraw, ImageFont
from statikai.compat import load_font
from statikai.physics import reactions

W, H, LEFT, RIGHT, BEAM_Y = 720, 400, 80, 640, 190
CLASSES = {"pin_support": 0, "roller_support": 1, "point_load": 2}


def fonts(size=19, serif=False):
    return load_font(size, serif)


def normalized_bbox(box):
    x0,y0,x1,y1=box
    return ((x0+x1)/(2*W), (y0+y1)/(2*H), (x1-x0)/W, (y1-y0)/H)


def draw_case(path, yolo_path, L,P1,x1,P2,x2,style):
    # Styles 0-3 preserve engineering values, style 4 is a physical intervention.
    bg = '#ffffff' if style != 1 else '#edf4fc'
    beam_color = ['#253e57', '#286398', '#252525', '#444d6c', '#253e57'][style]
    force_color = ['#a63628', '#ad2f7c', '#a32e1e', '#dc502a', '#a63628'][style]
    thick = 6 if style != 3 else 10
    f=fonts(18 if style != 2 else 21, serif=style == 2)
    sm=fonts(16 if style != 2 else 18, serif=style == 2)
    im=Image.new('RGB',(W,H), bg); d=ImageDraw.Draw(im)
    xA,xB=LEFT,RIGHT
    def xpos(v): return int(round(xA+(xB-xA)*v/L))
    p1,p2=xpos(x1),xpos(x2)
    d.line([(xA,BEAM_Y),(xB,BEAM_Y)], fill=beam_color,width=thick)
    d.polygon([(xA, BEAM_Y+5),(xA-18,BEAM_Y+35),(xA+18,BEAM_Y+35)],fill='#8196a7',outline=beam_color)
    d.line([(xA-30,BEAM_Y+36),(xA+30,BEAM_Y+36)], fill=beam_color,width=2)
    d.ellipse((xB-10,BEAM_Y+10,xB+10,BEAM_Y+30),fill='#8196a7',outline=beam_color,width=2)
    d.line([(xB-30,BEAM_Y+35),(xB+30,BEAM_Y+35)],fill=beam_color,width=2)
    for xp,load in ((p1,P1),(p2,P2)):
        d.line((xp,80,xp,BEAM_Y-10),fill=force_color,width=4)
        d.polygon([(xp,BEAM_Y-1),(xp-11,BEAM_Y-23),(xp+11,BEAM_Y-23)],fill=force_color)
        t=f'{load:g} kN'
        b=d.textbbox((0,0),t,font=f)
        d.text((xp-(b[2]-b[0])/2,45), t,font=f,fill=force_color)
    d.text((xA-7,BEAM_Y+60),'A',font=f,fill=beam_color)
    d.text((xB-8,BEAM_Y+60),'B',font=f,fill=beam_color)
    # Coordinates are text, NOT inferred from graphical distance alone.
    dimension=f'L={L:g} m  |  x1={x1:g} m  |  x2={x2:g} m (A noktasindan)'
    d.text((82,310),dimension,font=sm,fill=beam_color)
    # Annotations identify symbols only, not numerical text (OCR task).
    boxes=[(0,(xA-19,BEAM_Y,xA+19,BEAM_Y+36)),
           (1,(xB-15,BEAM_Y+6,xB+15,BEAM_Y+37)),
           (2,(p1-14,76,p1+14,BEAM_Y)),
           (2,(p2-14,76,p2+14,BEAM_Y))]
    path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path)
    yolo_path.write_text('\n'.join(f'{c} '+ ' '.join(f'{z:.6f}' for z in normalized_bbox(b)) for c,b in boxes)+'\n',encoding='utf8')


def generate(out, n, seed):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError('n must be a positive integer')
    out=Path(out); rng=random.Random(seed)
    (out/'images').mkdir(parents=True,exist_ok=True)
    (out/'labels').mkdir(parents=True,exist_ok=True)
    rows=[]
    # Distinct physical configurations across ALL base families, including
    # the physically changed variant. This prevents near-exact repeats from
    # leaking across train/validation/test at the physical parameter level.
    seen_physical=set()
    for idx in range(n):
        for attempt in range(10000):
            L=rng.choice([8,9,10,12,14])
            x1=rng.randint(2,L-5); x2=rng.randint(x1+2,L-2)
            P1=rng.choice([4,6,8,10,12,14,16]); P2=rng.choice([4,6,8,10,12,14])
            candidates=[v for v in range(1,x2) if v != x1]
            x1_changed=rng.choice(candidates)
            original=(L,P1,x1,P2,x2)
            intervention=(L,P1,x1_changed,P2,x2)
            if original not in seen_physical and intervention not in seen_physical:
                seen_physical.update((original,intervention))
                break
        else:
            raise RuntimeError('Could not generate distinct physical beam configurations')
        train_split='train' if idx%10<7 else ('val' if idx%10<9 else 'test')
        for variant in range(5):
            x1_case=x1_changed if variant==4 else x1
            ra,rb=reactions(L,P1,x1_case,P2,x2)
            fn=f'beam_{idx:04d}_v{variant}'
            draw_case(out/'images'/f'{fn}.png',out/'labels'/f'{fn}.txt',L,P1,x1_case,P2,x2,variant)
            rows.append(dict(problem_id=idx,variant=variant,split=train_split,
                             physical_change=(variant==4),L_m=L,P1_kN=P1,x1_m=x1_case,
                             P2_kN=P2,x2_m=x2,RA_kN=round(ra,6),RB_kN=round(rb,6),
                             image=f'images/{fn}.png',symbol_labels=f'labels/{fn}.txt'))
    with (out/'ground_truth.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0].keys()))
        writer.writeheader();writer.writerows(rows)
    (out/'classes.txt').write_text('\n'.join(CLASSES)+'\n',encoding='utf8')
    print(f'Created {n} base problems, {len(rows)} images in {out}.')
    print('Reminder: this is a synthetic annotated dataset, NOT a trained neural network.')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default='dataset');ap.add_argument('--n',type=int,default=40)
    ap.add_argument('--seed',type=int,default=2209)
    a=ap.parse_args();generate(a.out,a.n,a.seed)
