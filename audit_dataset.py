"""Independent CSV/YOLO/image integrity, split and analytical-reference audit."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from PIL import Image
import numpy as np

PHYSICAL = ('L_m','P1_kN','x1_m','P2_kN','x2_m')


def _audit_impl(root):
    root = Path(root)
    with (root/'ground_truth.csv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    errors, groups, physical, hashes = [], defaultdict(list), defaultdict(set), defaultdict(set)
    physical_families=defaultdict(set)
    if not rows: errors.append('dataset has no rows')
    if (root/'classes.txt').read_text(encoding='utf8').splitlines()!=['pin_support','roller_support','point_load']:
        errors.append('class names/order do not match annotation IDs')
    object_counts, seen, box_count = Counter(), set(), 0
    max_f, max_m, minimum_ink = 0., 0., 1.
    for row in rows:
        image = row['image']
        if image in seen:
            errors.append(f'duplicate image key: {image}')
        seen.add(image)
        groups[row['problem_id']].append(row)
        if row['split'] not in ('train','val','test'):
            errors.append(f'unknown split: {image}')
        values = tuple(float(row[k]) for k in PHYSICAL)
        L,p1,x1,p2,x2 = values
        ra,rb = float(row['RA_kN']),float(row['RB_kN'])
        if not all(math.isfinite(v) for v in (*values,ra,rb)) or not (0<x1<x2<L and p1>0 and p2>0):
            errors.append(f'invalid physical input: {image}')
            continue
        # Deliberately independent formulas; do not call generator.reactions().
        expected_b = (p1*x1+p2*x2)/L
        if max(abs(rb-expected_b),abs(ra-(p1+p2-expected_b)))>1e-5:
            errors.append(f'wrong reaction reference: {image}')
        max_f=max(max_f,abs(ra+rb-p1-p2))
        max_m=max(max_m,abs(rb*L-p1*x1-p2*x2))
        physical[values].add(row['split'])
        physical_families[values].add(row['problem_id'])
        path=root/image
        hashes[hashlib.sha256(path.read_bytes()).hexdigest()].add(row['split'])
        with Image.open(path) as source:
            pixels=np.asarray(source.convert('RGB'))
            width,height=source.size
        counts=Counter()
        for line in (root/row['symbol_labels']).read_text(encoding='utf8').splitlines():
            fields=line.split()
            if len(fields)!=5:
                errors.append(f'malformed YOLO annotation: {image}')
                continue
            cls=int(fields[0]); cx,cy,bw,bh=map(float,fields[1:])
            if cls not in (0,1,2) or not all(math.isfinite(z) for z in (cx,cy,bw,bh)):
                errors.append(f'invalid label values: {image}')
                continue
            if not (bw>0 and bh>0 and cx-bw/2>=-1e-5 and cy-bh/2>=-1e-5
                    and cx+bw/2<=1+1e-5 and cy+bh/2<=1+1e-5):
                errors.append(f'out-of-image annotation: {image}')
            x0,x1p=round((cx-bw/2)*width),round((cx+bw/2)*width)
            y0,y1p=round((cy-bh/2)*height),round((cy+bh/2)*height)
            patch=pixels[max(0,y0):min(height,y1p),max(0,x0):min(width,x1p)]
            if patch.size:
                ink=float(np.mean(np.max(np.abs(patch.astype(float)-pixels[0,0]),axis=2)>30))
                minimum_ink=min(minimum_ink,ink)
                if ink<0.01:
                    errors.append(f'nearly blank annotated object: {image}')
            else:
                errors.append(f'empty annotated patch: {image}')
            counts[cls]+=1; object_counts[cls]+=1; box_count+=1
        if counts != Counter({0:1,1:1,2:2}):
            errors.append(f'unexpected symbol inventory: {image}')
    for pid, family in groups.items():
        if len(family)!=5 or {r['variant'] for r in family}!={'0','1','2','3','4'}:
            errors.append(f'incomplete or duplicated variant family: {pid}')
        if len({r['split'] for r in family})!=1:
            errors.append(f'problem crosses splits: {pid}')
        equivalent=[r for r in family if str(r.get('physical_change','False')).lower()=='false']
        if len({tuple(r[k] for k in PHYSICAL) for r in equivalent})!=1:
            errors.append(f'equivalent renderings changed physics: {pid}')
        if equivalent:
            base=equivalent[0]
            for changed in (r for r in family if str(r.get('physical_change','False')).lower()=='true'):
                differences=[k for k in PHYSICAL if base[k]!=changed[k]]
                if differences!=['x1_m']:
                    errors.append(f'intervention changed unintended inputs: {pid}')
    p_leaks=sum(len(v)>1 for v in physical.values())
    repeated_families=sum(len(v)>1 for v in physical_families.values())
    h_leaks=sum(len(v)>1 for v in hashes.values())
    if p_leaks: errors.append('exact physical configurations cross splits')
    if repeated_families: errors.append('exact physical configurations repeat across families')
    if h_leaks: errors.append('exact image hashes cross splits')
    result=dict(passed=not errors, images=len(rows), problems=len(groups), boxes=box_count,
                split_images=dict(Counter(r['split'] for r in rows)),
                split_problems=dict(Counter(v[0]['split'] for v in groups.values())),
                styles=dict(Counter(r.get('style','legacy') for r in rows)),
                class_counts=dict(object_counts), unique_physical_configurations=len(physical),
                cross_split_physical_leaks=p_leaks,cross_split_image_hash_leaks=h_leaks,
                physical_configurations_shared_across_families=repeated_families,
                max_force_residual_kN=max_f,max_moment_residual_kNm=max_m,
                min_annotation_ink_fraction=minimum_ink, errors=errors,
                limitations=['Ink coverage is a sanity check, not proof of semantic annotation correctness',
                             'Exact duplication audit does not establish real-world generalization'])
    manifest_path=root/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf8'))
        if manifest.get('schema_version')=='statikai.dimensions.v2':
            from statikai.dataset_v2_audit import audit_dimensions
            advanced=audit_dimensions(root,rows,manifest)
            result['dimensions_v2']=advanced
            result['errors'].extend(advanced['errors'])
            result['passed']=not result['errors']
    return result


def audit(root):
    try:
        return _audit_impl(root)
    except (OSError,ValueError,KeyError,TypeError,IndexError) as error:
        return dict(passed=False,errors=[f'Malformed or unreadable dataset: {type(error).__name__}: {error}'])


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',default='dataset')
    parser.add_argument('--out',default='audit_results/dataset_audit.json')
    args=parser.parse_args()
    report=audit(args.dataset)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['passed'] else 1)
