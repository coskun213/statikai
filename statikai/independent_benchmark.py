"""New physical families and independently coded synthetic drawing renderer.

Not external real-source data. Never imports either legacy dataset renderer.
All profiles are specified before training; no model is used in construction.
"""
import csv
import hashlib
import json
from pathlib import Path
import random
import cv2
import numpy as np
from PIL import Image,ImageDraw

PROFILES=['clean','affine_scan','low_contrast','noisy_low_light','low_resolution','dark_background']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_frame(physics,seed):
    rng=random.Random(seed);L,p1,x1,p2,x2=physics
    w,h=rng.choice([(720,480),(840,560),(960,640)]);s=w/720
    a=rng.uniform(.09,.17)*w;b=rng.uniform(.81,.91)*w;y=rng.uniform(.39,.57)*h
    right_pin=rng.random()<.5
    xp=lambda x:(b-(b-a)*x/L) if right_pin else (a+(b-a)*x/L)
    gray=rng.randint(10,65);rgb=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(rgb)
    d.line((a,y,b,y),fill=(gray,)*3,width=rng.choice([2,3,4]))
    mask=np.zeros((h,w),np.uint8)
    for instance,kind,position in [(1,'pin',0),(2,'roller',L),(3,'load',x1),(4,'load',x2)]:
        layer=Image.new('L',(w,h),0);pen=ImageDraw.Draw(layer);x=xp(position)
        width=max(1,round(rng.uniform(1,2.5)*s));r=rng.uniform(12,18)*s
        if kind!='load':
            top=y+3*s;bottom=top+rng.uniform(20,29)*s
            points=[(x,top),(x-r,bottom),(x+r,bottom),(x,top)]
            if rng.random()<.5:pen.polygon(points,fill=255)
            else:pen.line(points,fill=255,width=width)
            if kind=='roller':
                rr=rng.uniform(3.5,5)*s;cy=bottom+rr+3*s
                for cx in (x-r*.55,x+r*.55):pen.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=255,width=width)
                ground=cy+rr+3*s
            else:ground=bottom+3*s
            pen.line((x-r-5*s,ground,x+r+5*s,ground),fill=255,width=width)
            for j in range(7):
                xx=x-r-4*s+j*(2*r+8*s)/6
                pen.line((xx,ground+2*s,xx-4*s,ground+8*s),fill=255,width=1)
        else:
            top=y-rng.uniform(65,100)*s;tip=y-3*s;hh=rng.uniform(11,18)*s
            pen.line((x,top,x,tip),fill=255,width=width)
            if rng.random()<.5:pen.polygon([(x,tip),(x-r*.6,tip-hh),(x+r*.6,tip-hh)],fill=255)
            else:pen.line([(x-r*.6,tip-hh),(x,tip),(x+r*.6,tip-hh)],fill=255,width=width)
        active=np.asarray(layer)>0
        if np.any(mask[active]):raise ValueError('Overlapping benchmark symbols')
        mask[active]=instance;rgb.paste((gray,)*3,(0,0),layer)
    image=np.array(rgb)
    # OpenCV Hershey lettering differs from the four source dataset fonts.
    for pos,value in [(x1,p1),(x2,p2)]:
        cv2.putText(image,f'{value:g} kN',(round(xp(pos)-24*s),round(y-115*s)),cv2.FONT_HERSHEY_SIMPLEX,.55*s,(gray,)*3,1,cv2.LINE_AA)
    for left,right in [(0,x1),(x1,x2),(x2,L)]:
        xx0,xx1=xp(left),xp(right);dy=y+100*s
        cv2.line(image,(round(xx0),round(y+65*s)),(round(xx0),round(dy+5*s)),(gray,)*3,1)
        cv2.line(image,(round(xx1),round(y+65*s)),(round(xx1),round(dy+5*s)),(gray,)*3,1)
        cv2.line(image,(round(xx0),round(dy)),(round(xx1),round(dy)),(gray,)*3,1)
        for xx in (xx0,xx1):cv2.line(image,(round(xx-4*s),round(dy+4*s)),(round(xx+4*s),round(dy-4*s)),(gray,)*3,1)
        cv2.putText(image,f'{right-left:.3f} m',(round((xx0+xx1)/2-24*s),round(dy-7*s)),cv2.FONT_HERSHEY_SIMPLEX,.47*s,(gray,)*3,1,cv2.LINE_AA)
    return image,mask


def corrupt(image,mask,profile,seed):
    rng=np.random.default_rng(seed);h,w=image.shape[:2]
    if profile=='affine_scan':
        matrix=cv2.getRotationMatrix2D((w/2,h/2),3.5 if seed%2 else -3.5,.94)
        image=cv2.warpAffine(image,matrix,(w,h),borderValue=(255,255,255))
        mask=cv2.warpAffine(mask,matrix,(w,h),flags=cv2.INTER_NEAREST,borderValue=0)
        ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,55]);assert ok
        image=cv2.imdecode(encoded,cv2.IMREAD_COLOR)
    elif profile=='low_contrast':image=np.clip(150+image.astype(float)*.32,0,255).astype(np.uint8)
    elif profile=='noisy_low_light':
        image=np.clip(image.astype(float)*.35+rng.normal(0,10,image.shape),0,255).astype(np.uint8)
        image=cv2.GaussianBlur(image,(5,5),1.1)
    elif profile=='low_resolution':image=cv2.resize(cv2.resize(image,(128,88),interpolation=cv2.INTER_AREA),(w,h),interpolation=cv2.INTER_LINEAR)
    elif profile=='dark_background':image=255-image
    return image,mask


def create_benchmark(out,training_root,families=80,seed=911082026,negative_count=40):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'images').mkdir();(out/'labels').mkdir()
    with (Path(training_root)/'ground_truth.csv').open(encoding='utf8') as f:old=list(csv.DictReader(f))
    keys=('L_m','P1_kN','x1_m','P2_kN','x2_m');used={tuple(float(r[k]) for k in keys) for r in old}
    rng=random.Random(seed);rows=[];physical=[]
    for i in range(families):
        while True:
            L=round(rng.uniform(6,20),3);p1=rng.randint(2,40);p2=rng.randint(2,40)
            x1=round(L*rng.uniform(.12,.43),3);x2=round(L*rng.uniform(.59,.89),3)
            values=(L,p1,x1,p2,x2)
            if values not in used:used.add(values);break
        physical.append(values);base,mask=independent_frame(values,seed+i*37)
        for j,profile in enumerate(PROFILES):
            im,m=corrupt(base.copy(),mask.copy(),profile,seed+i*10+j)
            h,w=im.shape[:2];stem=f'new_{10000+i}_{profile}';Image.fromarray(im).save(out/f'images/{stem}.png')
            boxes=[]
            for instance,cls in [(1,0),(2,1),(3,2),(4,2)]:
                yy,xx=np.where(m==instance)
                if not len(xx):raise ValueError('A benchmark object was lost from view')
                x0,y0,xend,yend=int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1
                boxes.append(f'{cls} {(x0+xend)/(2*w):.10f} {(y0+yend)/(2*h):.10f} {(xend-x0)/w:.10f} {(yend-y0)/h:.10f}')
            (out/f'labels/{stem}.txt').write_text('\n'.join(boxes)+'\n',encoding='utf8')
            rb=(p1*x1+p2*x2)/L
            rows.append(dict(problem_id=10000+i,condition=profile,image=f'images/{stem}.png',symbol_labels=f'labels/{stem}.txt',
                **dict(zip(keys,values)),RA_kN=p1+p2-rb,RB_kN=rb,negative=False))
    for index in range(negative_count):
        nr=np.random.default_rng(seed+90000+index);h,w=480,720
        im=np.clip(nr.normal(nr.uniform(235,253),1.5,(h,w,3)),0,255).astype(np.uint8)
        kind=['blank_paper','beam_only','text_dimensions','drafting_grid'][index%4]
        if kind=='beam_only':cv2.line(im,(85,240),(635,240),(30,30,30),3)
        elif kind=='text_dimensions':
            cv2.putText(im,f'{index+10} kN    4.50 m',(95,200),cv2.FONT_HERSHEY_SIMPLEX,1,(35,35,35),1)
            cv2.line(im,(80,300),(630,300),(60,60,60),1)
        elif kind=='drafting_grid':
            for x in range(40,700,40):cv2.line(im,(x,30),(x,450),(180,180,180),1)
            for y in range(40,460,40):cv2.line(im,(30,y),(690,y),(180,180,180),1)
        stem=f'negative_{index:03d}';Image.fromarray(im).save(out/f'images/{stem}.png')
        (out/f'labels/{stem}.txt').write_text('',encoding='utf8')
        rows.append(dict(problem_id=18000+index,condition=kind,image=f'images/{stem}.png',symbol_labels=f'labels/{stem}.txt',
            **{k:'' for k in keys},RA_kN='',RB_kN='',negative=True))
    with (out/'ground_truth.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.DictWriter(f,fieldnames=rows[0]);wr.writeheader();wr.writerows(rows)
    manifest=dict(seed=seed,positive_families=families,positive_images=families*len(PROFILES),negative_images=negative_count,
        profiles=PROFILES,source='independently implemented synthetic renderer, same project author; not external real drawings',
        exact_physical_overlap_with_all_old_families=0,renderer_sha256=sha(__file__),
        labels='whole glyph including ground line/hatch, consistent with V2; pre-degradation intended extent for photometric/low-resolution profiles',
        files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    return manifest
