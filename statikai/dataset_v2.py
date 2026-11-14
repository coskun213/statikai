"""Versioned engineering-style redraws, not external engineering drawings.

The original family IDs, split and physical interventions are inherited verbatim.
Only dimension lines carry distances; no L/x1/x2 summary or reactions are drawn.
"""
import csv
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import platform
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFont, __version__ as pillow_version
from statikai.physics import reactions

SCHEMA='statikai.dimensions.v2'
LAYOUTS=('chain_total','datum','chain_only','mixed')
CLASSES=['pin_support','roller_support','point_load']
PHYSICAL=('L_m','P1_kN','x1_m','P2_kN','x2_m')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def available_fonts():
    folders=[Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts',
             Path('/usr/share/fonts/truetype/dejavu'),Path('/usr/share/fonts/truetype/liberation2'),
             Path('/System/Library/Fonts/Supplemental'),Path('/Library/Fonts')]
    names=['arial.ttf','times.ttf','cour.ttf','calibri.ttf','DejaVuSans.ttf',
           'DejaVuSerif.ttf','DejaVuSansMono.ttf','LiberationSans-Regular.ttf']
    fonts=[];seen=set()
    for name in names:
        for candidate in [Path(name),*(p/name for p in folders)]:
            try:
                font=ImageFont.truetype(str(candidate),20)
                path=Path(font.path).resolve();digest=sha256(path)
                if digest not in seen:
                    fonts.append(dict(name=path.name,path=str(path),sha256=digest));seen.add(digest)
                break
            except OSError:pass
    if len(fonts)<2:
        raise RuntimeError('At least two scalable fonts are required; no false font diversity is reported.')
    return fonts


@lru_cache(maxsize=128)
def font_at(path,size):return ImageFont.truetype(path,size)


def number_label(value,unit,comma):
    factors={'m':1,'cm':100,'mm':1000,'kN':1,'N':1000}
    number=format((Decimal(str(value))*factors[unit]).normalize(),'f')
    if comma:number=number.replace('.',',')
    return number+' '+unit


def parameters(seed,pid,variant,attempt=0):
    # A stable digest, not Python's randomized hash. v4 deliberately reuses v0's drawing.
    key=f'{seed}:{pid}:{0 if variant==4 else variant}:{attempt}'
    rng=random.Random(int(hashlib.sha256(key.encode()).hexdigest(),16))
    width,height=rng.choice([(900,660),(1200,880),(1500,1100)])
    s=width/900
    return dict(width=width,height=height,scale=s,a=rng.uniform(90,125)*s,
        b=width-rng.uniform(90,125)*s,y=rng.uniform(.38,.44)*height,
        ink=rng.randint(15,65),stroke=rng.randint(1,3),beam_stroke=rng.randint(2,5),
        radius=rng.uniform(13,21)*s,triangle_height=rng.uniform(20,32)*s,
        hatch=rng.uniform(5,9)*s,roller_radius=rng.uniform(3,5)*s,
        arrow_height=rng.uniform(75,110)*s,head_width=rng.uniform(7,13)*s,
        head_height=rng.uniform(12,20)*s,symbol_style=rng.randrange(4),
        font_index=rng.randrange(len(available_fonts())),font_size=round(rng.uniform(18,23)*s),
        length_unit=rng.choice(['m','cm','mm']),force_unit=rng.choice(['kN','N']),
        decimal_comma=rng.choice([False,True]),layout=LAYOUTS[0 if variant==4 else variant])


def render_case(physics,p):
    L,P1,x1,P2,x2=map(float,physics)
    w,h,s=p['width'],p['height'],p['scale'];a,b,y=p['a'],p['b'],p['y']
    ink=(p['ink'],)*3;stroke=max(1,round(p['stroke']*s))
    image=Image.new('RGB',(w,h),'white');draw=ImageDraw.Draw(image)
    draw.line((a,y,b,y),fill=ink,width=max(1,round(p['beam_stroke']*s)))
    xpos=lambda x:a+(b-a)*x/L
    mask=np.zeros((h,w),np.uint8);symbols=[]
    roles=[('support_A',0,0.),('support_B',1,L),('load_1',2,x1),('load_2',2,x2)]
    for instance,(role,cls,position) in enumerate(roles,1):
        layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer);color=(*ink,255)
        x=xpos(position);r=p['radius'];th=p['triangle_height'];style=p['symbol_style']
        if cls in (0,1):
            top=y+4*s;bottom=top+th
            points=[(x,top),(x-r,bottom),(x+r,bottom),(x,top)]
            if style in (0,2):d.polygon(points,fill=color)
            else:d.line(points,fill=color,width=stroke)
            if style==3:d.ellipse((x-2*s,y+2*s,x+2*s,y+6*s),outline=color,width=stroke)
            if cls==1:
                rr=p['roller_radius'];cy=bottom+rr+3*s
                for cx in (x-r*.55,x+r*.55):
                    d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=color,width=stroke)
                base=cy+rr+3*s
            else:base=bottom+4*s
            d.line((x-r-5*s,base,x+r+5*s,base),fill=color,width=stroke)
            hatch=p['hatch']
            for j in range(int((2*r+10*s)/hatch)+1):
                xx=x-r-5*s+j*hatch
                d.line((xx,base+2*s,xx-4*s,base+8*s),fill=color,width=max(1,round(s)))
        else:
            top=y-p['arrow_height'];tip=y-3*s;hh=p['head_height'];hw=p['head_width']
            d.line((x,top,x,tip-hh/2 if style in (0,2) else tip),fill=color,width=stroke)
            head=[(x-hw,tip-hh),(x,tip),(x+hw,tip-hh)]
            if style in (0,2):d.polygon(head,fill=color)
            else:d.line(head,fill=color,width=stroke)
        active=np.asarray(layer.getchannel('A'))>0
        if np.any((mask>0)&active):raise ValueError('Symbol instances overlap')
        mask[active]=instance;image.paste(layer,(0,0),layer)
        ys,xs=np.where(active);bbox=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1]
        symbols.append(dict(instance_id=instance,role=role,class_id=cls,bbox=bbox,
                            position_m=position,anchor_px=[x,y]))
    draw=ImageDraw.Draw(image);texts=[];dimensions=[]
    font=font_at(available_fonts()[p['font_index']]['path'],p['font_size'])
    def text(value,cx,top,kind,association,**extra):
        bounds=draw.textbbox((0,0),value,font=font,anchor='lt')
        origin=[round(cx-(bounds[2]-bounds[0])/2),round(top)]
        bbox=list(draw.textbbox(origin,value,font=font,anchor='lt'))
        texts.append(dict(text=value,bbox=bbox,origin_px=origin,kind=kind,association=association,
                          font_size=p['font_size'],ink_rgb=list(ink),**extra))
        return len(texts)-1
    for role,pos,load in [('load_1',x1,P1),('load_2',x2,P2)]:
        text(number_label(load,p['force_unit'],p['decimal_comma']),xpos(pos),
             y-p['arrow_height']-p['font_size']-13*s,'force',role,value_si=load,unit=p['force_unit'])
    text('A',a-45*s,y+12*s,'support_id','support_A')
    text('B',b+45*s,y+12*s,'support_id','support_B')
    definitions={
        'chain_total':[(0,x1,0),(x1,x2,0),(x2,L,0),(0,L,2)],
        'chain_only':[(0,x1,0),(x1,x2,0),(x2,L,0)],
        'datum':[(0,x1,0),(0,x2,1),(0,L,2)],
        'mixed':[(0,x1,0),(x1,x2,1),(0,L,2)]}[p['layout']]
    for index,(start,end,level) in enumerate(definitions):
        xa,xb=xpos(start),xpos(end);dy=y+(115+56*level)*s
        for xx in (xa,xb):draw.line((xx,y+70*s,xx,dy+8*s),fill=ink,width=max(1,round(s)))
        draw.line((xa,dy,xb,dy),fill=ink,width=max(1,round(s)))
        if p['symbol_style'] in (0,1):
            for xx,sign in [(xa,1),(xb,-1)]:
                draw.polygon([(xx,dy),(xx+sign*8*s,dy-3*s),(xx+sign*8*s,dy+3*s)],fill=ink)
        else:
            for xx in (xa,xb):draw.line((xx-4*s,dy+5*s,xx+4*s,dy-5*s),fill=ink,width=stroke)
        length=Decimal(str(end))-Decimal(str(start))
        tid=text(number_label(length,p['length_unit'],p['decimal_comma']),(xa+xb)/2,
                 dy-p['font_size']-8*s,'dimension',f'dim_{index}',value_si=float(length),unit=p['length_unit'])
        dimensions.append(dict(id=f'dim_{index}',from_m=start,to_m=end,text_index=tid,
                               endpoints_px=[[xa,dy],[xb,dy]],level=level))
    for i,t in enumerate(texts):
        x0,y0,x1p,y1p=t['bbox']
        if x0<4 or y0<4 or x1p>w-4 or y1p>h-4:raise ValueError('Text outside page')
        for previous in texts[:i]:
            u=previous['bbox']
            if min(x1p+3,u[2]+3)>max(x0-3,u[0]-3) and min(y1p+3,u[3]+3)>max(y0-3,u[1]-3):
                raise ValueError('Text labels overlap')
    # Draw ALL graphics before ALL text, so witness lines never cover labels.
    for t in texts:
        x0,y0,x1p,y1p=t['bbox'];draw.rectangle((x0-3,y0-3,x1p+3,y1p+3),fill='white')
    for t in texts:draw.text(t['origin_px'],t['text'],font=font,anchor='lt',fill=ink)
    return image,Image.fromarray(mask),dict(beam=dict(left_px=a,right_px=b,y_px=y),
        symbols=symbols,texts=texts,dimensions=dimensions,render=p)


def generate_dimensions(out,source='dataset_extended',seed=20261109):
    source=Path(source).resolve();out=Path(out).resolve()
    if out.exists():raise FileExistsError('V2 requires a NEW output directory; nothing is overwritten')
    # Validate lineage before creating the output directory.
    from audit_dataset import audit
    check=audit(source)
    if not check['passed']:raise ValueError('Source dataset audit failed: '+str(check['errors'][:5]))
    with (source/'ground_truth.csv').open(encoding='utf8',newline='') as f:original=list(csv.DictReader(f))
    original.sort(key=lambda r:(int(r['problem_id']),int(r['variant'])))
    siblings={(r['problem_id'],r['variant']):r for r in original}
    fonts=available_fonts();out.mkdir(parents=True)
    for name in ('images','labels','annotations','masks'): (out/name).mkdir()
    rows=[];retries=0;paired_attempt={}
    for row in original:
        variant=int(row['variant']);pid=int(row['problem_id']);physics=[row[k] for k in PHYSICAL]
        # v0/v4 use the same attempt, preserving a controlled visual intervention.
        for attempt in ([paired_attempt[pid]] if variant==4 else range(50)):
            p=parameters(seed,pid,variant,attempt)
            try:
                image,mask,annotation=render_case(physics,p)
                if variant==0:
                    sibling=siblings[(row['problem_id'],'4')]
                    render_case([sibling[k] for k in PHYSICAL],p)
                break
            except ValueError:retries+=1
        else:raise RuntimeError(f'Cannot render readable labels for family {pid}')
        if variant==0:paired_attempt[pid]=attempt
        stem=f'beam_{pid:04d}_v{variant}';image_name=f'images/{stem}.png'
        image.save(out/image_name);mask.save(out/f'masks/{stem}.png')
        lines=[]
        for obj in annotation['symbols']:
            x0,y0,x1p,y1p=obj['bbox'];w,h=image.size
            box=[(x0+x1p)/(2*w),(y0+y1p)/(2*h),(x1p-x0)/w,(y1p-y0)/h]
            lines.append(str(obj['class_id'])+' '+' '.join(f'{v:.10f}' for v in box))
        (out/f'labels/{stem}.txt').write_text('\n'.join(lines)+'\n',encoding='utf8')
        annotation.update(schema=SCHEMA,problem_id=row['problem_id'],variant=row['variant'],
            split=row['split'],image=image_name,font=fonts[p['font_index']],image_sha256=sha256(out/image_name))
        (out/f'annotations/{stem}.json').write_text(json.dumps(annotation,indent=2,ensure_ascii=False),encoding='utf8')
        ra,rb=reactions(*physics)
        rows.append(dict(problem_id=row['problem_id'],variant=row['variant'],split=row['split'],
            physical_change=row['physical_change'],**{k:row[k] for k in PHYSICAL},
            RA_kN=round(ra,10),RB_kN=round(rb,10),image=image_name,
            symbol_labels=f'labels/{stem}.txt',annotation_json=f'annotations/{stem}.json',
            instance_mask=f'masks/{stem}.png',style='D2',dimension_layout=p['layout'],
            symbol_style=p['symbol_style'],font_name=fonts[p['font_index']]['name'],
            length_unit=p['length_unit'],force_unit=p['force_unit'],line_width=p['stroke'],
            width_px=image.width,height_px=image.height,source_image=row['image']))
    with (out/'ground_truth.csv').open('w',newline='',encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
    (out/'source_ground_truth.csv').write_bytes((source/'ground_truth.csv').read_bytes())
    (out/'classes.txt').write_text('\n'.join(CLASSES)+'\n',encoding='utf8')
    # The manifest is written last. A partial run is never declared complete.
    manifest=dict(schema_version=SCHEMA,seed=seed,images=len(rows),families=check['problems'],
        source_dataset_name=source.name,source_csv_sha256=sha256(source/'ground_truth.csv'),
        split_policy='inherit source problem_id groups and splits; no old test ID enters training',
        fonts=fonts,python=platform.python_version(),pillow=pillow_version,rejected_text_layouts=retries,
        annotation_scope='symbols, instance masks, text values/units and dimension endpoint associations',
        limitations=['Synthetic redraws, not independent real-source drawings',
            'Same physical families as the source; not a fresh independent physical test set',
            'No OCR, model training, or image-to-reaction solution is implemented here',
            'Legacy trainer filters style A; D2 needs an explicitly versioned training adapter'],
        files={p.relative_to(out).as_posix():sha256(p) for p in sorted(out.rglob('*')) if p.is_file()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
    return rows


