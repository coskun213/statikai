"""Phase 1: 500 families, 2500 diagrams; geometry varies, style B is held out.

Both renderers are authored synthetic drawings, NOT independent real sources.
Variants 0,1,2,3 preserve physics; variant 4 moves only the first load.
"""
import argparse
import csv
import json
from pathlib import Path
import random
from PIL import Image, ImageDraw
from statikai.compat import load_font
from statikai.physics import reactions

CLASS_NAMES=['pin_support','roller_support','point_load']


def _filled_symbols(draw, a, b, y, loads, radius, color, force, height):
    r=radius
    draw.polygon([(a,y+3),(a-r,y+2*r),(a+r,y+2*r)], fill=color)
    pin=(a-r-1,y+2,a+r+1,y+2*r+1)
    draw.line((a-r-7,y+2*r+5,a+r+7,y+2*r+5),fill=color,width=2)
    draw.ellipse((b-r,y+5,b+r,y+2*r+5),fill=color)
    roller=(b-r-1,y+4,b+r+1,y+2*r+6)
    draw.line((b-r-7,y+2*r+10,b+r+7,y+2*r+10),fill=color,width=2)
    boxes=[(0,pin),(1,roller)]
    for x,_ in loads:
        top=y-height
        draw.line((x,top,x,y-14),fill=force,width=3)
        draw.polygon([(x,y-3),(x-r*.65,y-19),(x+r*.65,y-19)],fill=force)
        boxes.append((2,(x-r*.65-2,top-2,x+r*.65+2,y-2)))
    return boxes


def _outline_symbols(draw, a, b, y, loads, radius, color, force, height):
    # Independent engineering conventions: outline triangles, hatch, two rollers,
    # open arrowheads. These symbols are intentionally not pixel-equivalent to A.
    r=radius
    draw.line([(a,y+3),(a-r,y+2*r),(a+r,y+2*r),(a,y+3)],fill=color,width=2)
    for x in range(int(a-r),int(a+r+1),6):
        draw.line((x,y+2*r+4,x-4,y+2*r+10),fill=color,width=1)
    pin=(a-r-1,y+2,a+r+1,y+2*r+1)
    draw.line([(b,y+3),(b-r,y+2*r),(b+r,y+2*r),(b,y+3)],fill=color,width=2)
    for x in (b-r*.55,b+r*.55):
        draw.ellipse((x-4,y+2*r+2,x+4,y+2*r+10),outline=color,width=2)
    draw.line((b-r-5,y+2*r+13,b+r+5,y+2*r+13),fill=color,width=2)
    roller=(b-r-1,y+2,b+r+1,y+2*r+11)
    boxes=[(0,pin),(1,roller)]
    for x,_ in loads:
        top=y-height
        draw.line((x,top,x,y-3),fill=color,width=2)
        draw.line([(x-r*.65,y-19),(x,y-3),(x+r*.65,y-19)],fill=color,width=2)
        boxes.append((2,(x-r*.65-2,top-2,x+r*.65+2,y-2)))
    return boxes


def render(path, label_path, physics, layout, style):
    L,p1,x1,p2,x2=physics
    width,height,a,b,y,r,h,offset=layout
    im=Image.new('RGB',(width,height),'white' if style=='B' else '#f7fafc')
    draw=ImageDraw.Draw(im)
    color='#202020' if style=='B' else '#254a64'
    force='#202020' if style=='B' else '#a73532'
    draw.line((a,y,b,y),fill=color,width=3 if style=='B' else 5)
    x=lambda value: round(a+(b-a)*value/L)
    loads=[(x(x1),p1),(x(x2),p2)]
    renderer=_outline_symbols if style=='B' else _filled_symbols
    boxes=renderer(draw,a,b,y,loads,r,color,force,h)
    font=load_font(16 if style=='A' else 17,serif=style=='B')
    for xp,p in loads:
        label=f'{p:g} kN'
        draw.text((xp,y-h-25+offset),label,font=font,anchor='mt',fill=force)
    draw.text((a,y+2*r+25),'A',font=font,anchor='mt',fill=color)
    draw.text((b,y+2*r+25),'B',font=font,anchor='mt',fill=color)
    text=f'L={L:g} m | x1={x1:g} m | x2={x2:g} m'
    draw.text((width/2,height-36),text,font=load_font(14),anchor='mt',fill=color)
    draw.text((width/2,height-19),'Distances from A',font=load_font(11),anchor='mt',fill=color)
    path.parent.mkdir(parents=True,exist_ok=True)
    label_path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path)
    lines=[]
    for cls,(x0,y0,xend,yend) in boxes:
        coords=((x0+xend)/(2*width),(y0+yend)/(2*height),(xend-x0)/width,(yend-y0)/height)
        lines.append(str(cls)+' '+' '.join(f'{v:.8f}' for v in coords))
    label_path.write_text('\n'.join(lines)+'\n',encoding='utf8')


def _layout(rng, variant):
    width,height=rng.choice([(640,360),(720,400),(800,440)])
    a=rng.randint(55,120)
    b=width-rng.randint(55,120)
    y=rng.randint(round(height*.47),round(height*.58))
    return width,height,a,b,y,rng.randint(12,18),rng.randint(64,96),rng.randint(-5,3)


def generate_extended(out,n=500,seed=20261108):
    if isinstance(n,bool) or not isinstance(n,int) or n<10:
        raise ValueError('At least ten families are required for all three splits')
    out=Path(out)
    if (out/'ground_truth.csv').exists():
        raise FileExistsError('Use a new output directory; existing datasets are preserved')
    rng=random.Random(seed)
    rows=[];seen=set()
    for pid in range(n):
        while True:
            L=round(rng.uniform(7,16),2)
            p1,p2=rng.randint(3,30),rng.randint(3,30)
            x1,x2=round(L*rng.uniform(.16,.35),3),round(L*rng.uniform(.62,.84),3)
            changed=round(L*rng.uniform(.08,.49),3)
            original=(L,p1,x1,p2,x2)
            intervention=(L,p1,changed,p2,x2)
            if original not in seen and intervention not in seen and abs(changed-x1)>.06*L:
                seen.update((original,intervention));break
        split='train' if pid%10<7 else ('val' if pid%10<9 else 'test')
        base_layout=_layout(rng,0)
        for variant in range(5):
            physics=intervention if variant==4 else original
            layout=base_layout if variant in (0,4) else _layout(rng,variant)
            style='B' if variant==3 else 'A'
            stem=f'beam_{pid:04d}_v{variant}'
            render(out/'images'/f'{stem}.png',out/'labels'/f'{stem}.txt',physics,layout,style)
            ra,rb=reactions(*physics)
            rows.append(dict(problem_id=pid,variant=variant,split=split,physical_change=variant==4,
                L_m=physics[0],P1_kN=physics[1],x1_m=physics[2],P2_kN=physics[3],x2_m=physics[4],
                RA_kN=round(ra,8),RB_kN=round(rb,8),image=f'images/{stem}.png',
                symbol_labels=f'labels/{stem}.txt',style=style,width_px=layout[0],height_px=layout[1],
                beam_left_px=layout[2],beam_right_px=layout[3],beam_y_px=layout[4]))
    with (out/'ground_truth.csv').open('w',newline='',encoding='utf8') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    (out/'classes.txt').write_text('\n'.join(CLASS_NAMES)+'\n',encoding='utf8')
    manifest=dict(seed=seed,families=n,images=len(rows),variants_per_family=5,
        training_style='A',held_out_style='B',held_out_style_variant=3,
        split_rule='problem_id modulo 10: 0-6 train, 7-8 val, 9 test',
        warning='Both drawing implementations are synthetic; neither is an external real-world source',
        fonts={str(s):str(getattr(load_font(16,s),'path','embedded')) for s in (False,True)})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    print(json.dumps(manifest,indent=2))
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='dataset_extended')
    parser.add_argument('--n',type=int,default=500)
    parser.add_argument('--seed',type=int,default=20261108)
    args=parser.parse_args()
    generate_extended(args.out,args.n,args.seed)
