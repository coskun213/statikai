"""Full-image classical baseline and class-aware one-to-one bbox scoring."""
from collections import Counter
import csv
import json
import math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

NAMES=['pin_support','roller_support','point_load']


def records(root, split, style=None):
    with (Path(root)/'ground_truth.csv').open(encoding='utf8',newline='') as handle:
        return [r for r in csv.DictReader(handle)
                if r['split']==split and (style is None or r['style']==style)]


def annotations(root,row):
    with Image.open(Path(root)/row['image']) as im: w,h=im.size
    result=[]
    for line in (Path(root)/row['symbol_labels']).read_text(encoding='utf8').splitlines():
        c,cx,cy,bw,bh=map(float,line.split())
        result.append(dict(class_id=int(c),bbox=[(cx-bw/2)*w,(cy-bh/2)*h,
                                               (cx+bw/2)*w,(cy+bh/2)*h]))
    return result


def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=lambda x:max(0,x[2]-x[0])*max(0,x[3]-x[1])
    union=area(a)+area(b)-intersection
    return intersection/union if union>0 else 0.


def classical_detect(image, fill_cutoff=.65, min_support_ratio=.035):
    """Only pixels enter this function; positions and labels are never supplied.

    Scores are heuristic rankings, not calibrated probabilities. The domain is
    horizontal, high-contrast beam diagrams. No OCR is performed.
    """
    gray=np.asarray(image.convert('L'))
    h,w=gray.shape
    _,mask=cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
    horizontal=cv2.morphologyEx(mask,cv2.MORPH_OPEN,
                                np.ones((1,max(20,w//3)),np.uint8))
    contours,_=cv2.findContours(horizontal,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    beams=[cv2.boundingRect(c) for c in contours]
    beams=[b for b in beams if b[2]>.4*w and .15*h<b[1]<.8*h and b[3]<.04*h]
    if not beams: return []
    bx,by,bw,bh=max(beams,key=lambda b:b[2])
    y=by+(bh-1)/2
    output=[]
    for above in (True,False):
        start,end=(0,max(0,int(y)-2)) if above else (min(h,int(y)+3),min(h,int(y+.23*bw)))
        crop=mask[start:end].copy()
        count,_,stats,_=cv2.connectedComponentsWithStats(crop,8)
        for x,cy,cw,ch,area in stats[1:]:
            x,cy,cw,ch,area=map(int,(x,cy,cw,ch,area))
            cy+=start
            center=x+cw/2
            if above:
                if not (bx<center<bx+bw and .09*bw<ch<.4*bw and cw<.09*bw and ch>1.5*cw):
                    continue
                cls=2
            else:
                if not (abs(center-bx)<.09*bw or abs(center-(bx+bw))<.09*bw): continue
                if not (min_support_ratio*bw<ch<.15*bw and .025*bw<cw<.15*bw and .5<cw/ch<1.8):
                    continue
                cls=1 if area/(cw*ch)>fill_cutoff else 0
            output.append(dict(class_id=cls,score=.9,bbox=[max(0,x-1),max(0,cy-1),min(w,x+cw+1),min(h,cy+ch+1)]))
    return output


def score_image(predictions,truth,threshold=.5):
    counts=np.zeros((3,3),dtype=int)  # TP,FP,FN
    used=set()
    for p in sorted(predictions,key=lambda x:x['score'],reverse=True):
        if p['class_id'] not in range(3) or not math.isfinite(p['score']):
            raise ValueError('Invalid detector class or score')
        if len(p['bbox'])!=4 or not all(math.isfinite(v) for v in p['bbox']):
            raise ValueError('Invalid detector box')
        choices=[(iou(p['bbox'],g['bbox']),index) for index,g in enumerate(truth)
                 if index not in used and g['class_id']==p['class_id']]
        best=max(choices,default=(0,-1))
        if best[0]>=threshold:
            counts[p['class_id'],0]+=1;used.add(best[1])
        else: counts[p['class_id'],1]+=1
    for index,g in enumerate(truth):
        if index not in used: counts[g['class_id'],2]+=1
    return counts


def summarize(counts):
    tp,fp,fn=map(int,np.asarray(counts).sum(axis=0))
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else 0.,
                recall=tp/(tp+fn) if tp+fn else 0.,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)


def evaluate_rows(rows,predictions,root):
    details=[];total=np.zeros((3,3),dtype=int)
    for row in rows:
        count=score_image(predictions[row['image']],annotations(root,row))
        total+=count
        details.append(dict(image=row['image'],problem_id=row['problem_id'],style=row['style'],
                            variant=row['variant'],**summarize(count),
                            exact_image=int(count[:,1:].sum()==0 and count[:,0].sum()==4)))
    report=summarize(total)
    report.update(images=len(rows),exact_image_rate=sum(r['exact_image'] for r in details)/len(rows),
                  per_class={name:summarize(total[i:i+1]) for i,name in enumerate(NAMES)})
    return report,details
