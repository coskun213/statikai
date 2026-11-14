"""Independent dimension/units/raster/lineage checks. Does not import the renderer."""
from collections import Counter,defaultdict
import csv
from decimal import Decimal
from functools import lru_cache
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=256)
def audit_font(path,size):return ImageFont.truetype(path,size)


def parse_quantity(text):
    match=re.fullmatch(r'([0-9]+(?:[.,][0-9]+)?)\s+(mm|cm|m|kN|N)',text)
    if not match:raise ValueError('Invalid numeric unit label')
    value=Decimal(match[1].replace(',','.'));unit=match[2]
    factor={'m':Decimal(1),'cm':Decimal('.01'),'mm':Decimal('.001'),
            'kN':Decimal(1),'N':Decimal('.001')}[unit]
    return value*factor,unit


def audit_dimensions(root,rows,manifest):
    root=Path(root);errors=[];warnings=[];families=defaultdict(list)
    crop_hashes=defaultdict(set);input_hashes=defaultdict(set);crop_examples=defaultdict(list)
    fonts=Counter();resolutions=Counter();layouts=Counter();units=Counter();styles=Counter();strokes=Counter()
    text_count=0;dimension_count=0;text_raster_checks=0;max_reaction_error=0.;font_availability={}
    for name,expected in manifest['files'].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()):errors.append('unsafe manifest path');continue
        if not path.is_file() or digest(path)!=expected:errors.append(f'artifact checksum mismatch: {name}')
    files={p.relative_to(root).as_posix() for directory in ('images','labels','masks','annotations')
           for p in (root/directory).rglob('*') if p.is_file()}
    if files!={p for p in manifest['files'] if p.split('/')[0] in ('images','labels','masks','annotations')}:
        errors.append('untracked or missing dataset files')
    snapshot=root/'source_ground_truth.csv'
    if digest(snapshot)!=manifest['source_csv_sha256']:errors.append('source snapshot checksum mismatch')
    external=root.parent/manifest['source_dataset_name']/'ground_truth.csv'
    if external.exists() and digest(external)!=manifest['source_csv_sha256']:
        errors.append('external source dataset CSV changed')
    with snapshot.open(encoding='utf8',newline='') as f:source=list(csv.DictReader(f))
    source_by_key={(r['problem_id'],r['variant']):r for r in source}
    if len(source_by_key)!=len(source):errors.append('duplicate source family/variant')
    if len(rows)!=len(source) or manifest['images']!=len(rows):errors.append('incomplete source redraw')
    for row in rows:
        image=row['image'];key=(row['problem_id'],row['variant']);families[row['problem_id']].append(row)
        original=source_by_key.get(key)
        if original is None:errors.append(f'unknown source identity: {image}');continue
        keys=('split','physical_change','L_m','P1_kN','x1_m','P2_kN','x2_m')
        if any(row[k]!=original[k] for k in keys) or row['source_image']!=original['image']:
            errors.append(f'source physics/split changed: {image}')
        L,p1,x1,p2,x2=(Decimal(row[k]) for k in ('L_m','P1_kN','x1_m','P2_kN','x2_m'))
        rb=(p1*x1+p2*x2)/L;ra=p1+p2-rb
        err=max(abs(Decimal(row['RA_kN'])-ra),abs(Decimal(row['RB_kN'])-rb))
        max_reaction_error=max(max_reaction_error,float(err))
        if err>Decimal('0.00000001'):errors.append(f'independent Decimal reaction mismatch: {image}')
        annotation=json.loads((root/row['annotation_json']).read_text(encoding='utf8'))
        if any(str(annotation[k])!=row[k] for k in ('problem_id','variant','split','image')):
            errors.append(f'annotation identity mismatch: {image}')
        if annotation['image_sha256']!=digest(root/image):errors.append(f'annotation image checksum mismatch: {image}')
        p=annotation['render'];beam=annotation['beam'];a,b,y=beam['left_px'],beam['right_px'],beam['y_px']
        if p['layout']!=row['dimension_layout'] or p['symbol_style']!=int(row['symbol_style']):
            errors.append(f'render metadata mismatch: {image}')
        with Image.open(root/image) as im:
            rgb=im.convert('RGB');width,height=im.size;pixels=np.asarray(rgb)
            resized=rgb.convert('L').resize((256,160),Image.Resampling.BILINEAR)
            input_hashes[hashlib.sha256(resized.tobytes()).hexdigest()].add(row['split'])
            with Image.open(root/row['instance_mask']) as m:mask=np.asarray(m)
            if mask.shape!=(height,width) or set(np.unique(mask))!={0,1,2,3,4}:
                errors.append(f'invalid instance mask: {image}');continue
            if (width,height)!=(int(row['width_px']),int(row['height_px'])):
                errors.append(f'image resolution mismatch: {image}')
            label_boxes=[]
            for line in (root/row['symbol_labels']).read_text().splitlines():
                cls,cx,cy,bw,bh=map(float,line.split())
                label_boxes.append((int(cls),[(cx-bw/2)*width,(cy-bh/2)*height,(cx+bw/2)*width,(cy+bh/2)*height]))
            objects=annotation['symbols']
            expected={'support_A':(1,0,0.),'support_B':(2,1,float(L)),
                      'load_1':(3,2,float(x1)),'load_2':(4,2,float(x2))}
            if len(objects)!=4 or {o['role'] for o in objects}!=set(expected):
                errors.append(f'wrong semantic inventory: {image}');continue
            used=set()
            for obj in objects:
                instance,cls,position=expected[obj['role']]
                if (obj['instance_id'],obj['class_id'])!=(instance,cls):errors.append(f'wrong semantic class: {image}')
                yy,xx=np.where(mask==instance)
                bbox=[int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
                if bbox!=obj['bbox']:errors.append(f'mask/semantic bbox mismatch: {image}')
                matches=[i for i,(c,bb) in enumerate(label_boxes) if i not in used and c==cls and max(abs(v-u) for v,u in zip(bb,bbox))<.001]
                if not matches:errors.append(f'YOLO class/bbox does not match raster mask: {image}')
                else:used.add(matches[0])
                anchor=a+(b-a)*position/float(L)
                if abs(obj['anchor_px'][0]-anchor)>1e-6 or abs(obj['position_m']-position)>1e-8:
                    errors.append(f'wrong physical symbol position: {image}')
                if not bbox[0]-1<=anchor<=bbox[2]+1 or (cls==2 and yy.max()>=y) or (cls!=2 and yy.min()<=y):
                    errors.append(f'symbol pixel position disagrees with beam: {image}')
                if np.mean(np.min(pixels[mask==instance],axis=1)<150)<.95:
                    errors.append(f'symbol mask covers missing/overwritten ink: {image}')
                x0,y0,xend,yend=bbox;dx=(xend-x0)*.22;dy=(yend-y0)*.22
                patch=rgb.crop((int(x0-dx),int(y0-dy),int(xend+dx),int(yend+dy))).resize((48,48),Image.Resampling.BICUBIC)
                digest_patch=hashlib.sha256(patch.tobytes()).hexdigest()
                crop_hashes[digest_patch].add(row['split']);crop_examples[digest_patch].append((image,obj['role']))
        texts=annotation['texts'];dimensions=annotation['dimensions'];layout=row['dimension_layout']
        inventory=Counter((t['kind'],t['association']) for t in texts)
        required=Counter([('force','load_1'),('force','load_2'),('support_id','support_A'),('support_id','support_B')]
                         +[('dimension',d['id']) for d in dimensions])
        if inventory!=required:errors.append(f'incomplete text association inventory: {image}')
        expected_pairs={
            'chain_total':[(0,float(x1)),(float(x1),float(x2)),(float(x2),float(L)),(0,float(L))],
            'chain_only':[(0,float(x1)),(float(x1),float(x2)),(float(x2),float(L))],
            'datum':[(0,float(x1)),(0,float(x2)),(0,float(L))],
            'mixed':[(0,float(x1)),(float(x1),float(x2)),(0,float(L))]}.get(layout,[])
        if [(d['from_m'],d['to_m']) for d in dimensions]!=expected_pairs:
            errors.append(f'wrong dimension endpoint associations: {image}')
        for d in dimensions:
            dimension_count+=1
            t=texts[d['text_index']]
            expected_value=Decimal(str(d['to_m']))-Decimal(str(d['from_m']))
            try:value,unit=parse_quantity(t['text'])
            except ValueError:errors.append(f'invalid dimension text: {image}');continue
            if (unit not in ('m','cm','mm') or unit!=t['unit'] or unit!=row['length_unit']
                or abs(value-expected_value)>Decimal('0.00000001')
                or abs(Decimal(str(t['value_si']))-value)>Decimal('0.00000001')
                or t['kind']!='dimension' or t['association']!=d['id']):
                errors.append(f'wrong dimension text/unit/value: {image}')
            for point,metres in zip(d['endpoints_px'],(d['from_m'],d['to_m'])):
                if abs(point[0]-(a+(b-a)*metres/float(L)))>1e-6:
                    errors.append(f'dimension witness point is misplaced: {image}')
        font_info=annotation['font'];font_path=Path(font_info['path'])
        font_key=(str(font_path),font_info['sha256'])
        if font_key not in font_availability:
            font_availability[font_key]=font_path.is_file() and digest(font_path)==font_info['sha256']
        font_available=font_availability[font_key]
        for index,t in enumerate(texts):
            text_count+=1
            if re.search(r'\b(?:L|x1|x2|RA|RB)\s*=',t['text']):errors.append(f'parameter summary shortcut present: {image}')
            x0,y0,xend,yend=t['bbox']
            if not (0<=x0<xend<=width and 0<=y0<yend<=height):errors.append(f'text outside image: {image}');continue
            if t['kind']=='force':
                force={'load_1':p1,'load_2':p2}.get(t['association'])
                try:value,unit=parse_quantity(t['text'])
                except ValueError:errors.append(f'invalid force text: {image}');continue
                if (force is None or unit not in ('N','kN') or unit!=t['unit'] or unit!=row['force_unit']
                    or abs(value-force)>Decimal('0.00000001')
                    or abs(Decimal(str(t['value_si']))-value)>Decimal('0.00000001')):
                    errors.append(f'wrong force text/unit/value: {image}')
            if t['kind']=='support_id' and (t['text'],t['association']) not in [('A','support_A'),('B','support_B')]:
                errors.append(f'wrong support identifier: {image}')
            for other in texts[:index]:
                q=other['bbox']
                if min(xend,q[2])>max(x0,q[0]) and min(yend,q[3])>max(y0,q[1]):errors.append(f'overlapping text boxes: {image}')
            if font_available:
                # Independently rasterize the claimed transcription, not OCR and not a renderer import.
                reference=Image.new('RGB',(xend-x0,yend-y0),'white')
                ImageDraw.Draw(reference).text((t['origin_px'][0]-x0,t['origin_px'][1]-y0),t['text'],
                    font=audit_font(str(font_path),t['font_size']),anchor='lt',fill=tuple(t['ink_rgb']))
                if not np.array_equal(np.asarray(reference),pixels[y0:yend,x0:xend]):
                    errors.append(f'text transcription/raster mismatch: {image}')
                text_raster_checks+=1
        fonts[font_info['name']]+=1;resolutions[f'{width}x{height}']+=1;layouts[layout]+=1
        units[row['length_unit']]+=1;units[row['force_unit']]+=1;styles[row['symbol_style']]+=1;strokes[row['line_width']]+=1
    for pid,family in families.items():
        by_variant={r['variant']:r for r in family}
        if len({r['split'] for r in family})!=1:errors.append(f'family split leak: {pid}')
        if set(by_variant)!={'0','1','2','3','4'}:errors.append(f'incomplete family: {pid}');continue
        first=json.loads((root/by_variant['0']['annotation_json']).read_text(encoding='utf8'))['render']
        changed=json.loads((root/by_variant['4']['annotation_json']).read_text(encoding='utf8'))['render']
        if first!=changed:errors.append(f'intervention changed drawing parameters: {pid}')
    crop_leaks=[h for h,s in crop_hashes.items() if len(s)>1]
    full_leaks=sum(len(s)>1 for s in input_hashes.values())
    if full_leaks:errors.append('resized full-image inputs repeat across splits')
    if crop_leaks:warnings.append('Exact symbol crops repeat across splits; unsuitable as independent patch-classifier evaluation')
    if text_raster_checks!=text_count:warnings.append('Some fonts unavailable: not all text transcriptions could be raster-verified')
    return dict(passed=not errors,errors=errors,warnings=warnings,source_external_csv_checked=external.exists(),
        dimension_annotations=dimension_count,text_annotations=text_count,text_raster_checks=text_raster_checks,
        max_independent_reaction_error_kN=max_reaction_error,
        cross_split_preprocessed_image_hash_leaks=full_leaks,cross_split_symbol_crop_hashes=len(crop_leaks),
        symbol_crop_leak_examples=[crop_examples[h][:3] for h in crop_leaks[:10]],
        fonts=dict(fonts),resolutions=dict(resolutions),dimension_layouts=dict(layouts),
        units=dict(units),symbol_styles=dict(styles),stroke_widths=dict(strokes),
        limitations=['Synthetic drawing conventions, not external real-world validation',
            'Text raster verification uses available recorded fonts, not an OCR experiment',
            'Exact hash checks do not rule out perceptual/template-level similarity',
            'Source families are reused; this is not a new independent physical benchmark'])
