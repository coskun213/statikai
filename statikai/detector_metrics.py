"""Score-ranked one-to-one matching; IoU denominators are explicit."""
from collections import defaultdict
import math
import numpy as np
from statikai.detection import iou,NAMES,summarize


def score_detailed(predictions,truth,threshold=.5):
    count=np.zeros((3,3),int);used=set();matched=[];false_positive=[]
    for p in sorted(predictions,key=lambda p:p['score'],reverse=True):
        if p['class_id'] not in (0,1,2) or not math.isfinite(p['score']):raise ValueError('Invalid prediction')
        if len(p['bbox'])!=4 or not all(math.isfinite(v) for v in p['bbox']):raise ValueError('Nonfinite box')
        if p['bbox'][2]<=p['bbox'][0] or p['bbox'][3]<=p['bbox'][1]:raise ValueError('Degenerate box')
        choices=[(iou(p['bbox'],g['bbox']),i) for i,g in enumerate(truth) if i not in used and p['class_id']==g['class_id']]
        overlap,index=max(choices,default=(0.,-1))
        if overlap>=threshold:
            used.add(index);count[p['class_id'],0]+=1;matched.append(overlap)
        else:count[p['class_id'],1]+=1;false_positive.append(p)
    missed=[]
    for index,g in enumerate(truth):
        if index not in used:count[g['class_id'],2]+=1;missed.append(g)
    best_iou=sum(max((iou(g['bbox'],p['bbox']) for p in predictions if p['class_id']==g['class_id']),default=0.) for g in truth)
    return dict(count=count,matched_ious=matched,best_iou_sum=best_iou,missed=missed,false_positive=false_positive)


def aggregate(rows,predictions,truths,threshold=.5):
    total=np.zeros((3,3),int);details=[];overlaps=[];best=0.;gt=0;positive_exact=0;positive_n=0;negative_alarm=0;negative_n=0
    for row in rows:
        image=row['image'];truth=truths[image];pred=predictions[image];r=score_detailed(pred,truth,threshold)
        total+=r['count'];overlaps+=r['matched_ious'];best+=r['best_iou_sum'];gt+=len(truth)
        exact=int(not r['count'][:,1:].any())
        if truth:positive_n+=1;positive_exact+=exact
        else:negative_n+=1;negative_alarm+=bool(pred)
        details.append(dict(image=image,problem_id=str(row['problem_id']),condition=row.get('condition','validation'),
                            **summarize(r['count']),exact=exact,ground_truth_objects=len(truth)))
    report=dict(**summarize(total),images=len(rows),ground_truth_objects=gt,
        per_class={name:summarize(total[i:i+1]) for i,name in enumerate(NAMES)},
        mean_iou_matched_tp=float(np.mean(overlaps)) if overlaps else None,
        mean_best_class_iou_all_gt=best/gt if gt else None,
        exact_positive_image_rate=positive_exact/positive_n if positive_n else None,
        negative_images=negative_n,negative_false_alarm_rate=negative_alarm/negative_n if negative_n else None)
    return report,details


def roller_failures(rows,predictions,raw_predictions,truths,score_threshold):
    result=[]
    for row in rows:
        image=row['image'];pred=predictions[image]
        for g in score_detailed(pred,truths[image])['missed']:
            if g['class_id']!=1:continue
            same=max((iou(g['bbox'],p['bbox']) for p in pred if p['class_id']==1),default=0.)
            other=max((iou(g['bbox'],p['bbox']) for p in pred if p['class_id']!=1),default=0.)
            low=[p['score'] for p in raw_predictions[image] if p['class_id']==1 and iou(p['bbox'],g['bbox'])>=.5 and p['score']<score_threshold]
            reason='below_score_threshold' if low else 'class_confusion' if other>=.5 else 'localization' if same>=.1 else 'missed'
            result.append(dict(image=image,problem_id=row['problem_id'],condition=row['condition'],
                reason=reason,best_same_class_iou=same,best_other_class_iou=other,gt_bbox=g['bbox']))
    return result


def paired_family_bootstrap(a,b,repeats=1000,seed=22091108):
    groups=defaultdict(lambda:np.zeros((2,3)))
    for method,rows in enumerate((a,b)):
        for r in rows:groups[r['problem_id']][method]+=np.array([r['tp'],r['fp'],r['fn']])
    data=np.stack(list(groups.values()));rng=np.random.default_rng(seed)
    sums=data[rng.integers(0,len(data),(repeats,len(data)))].sum(1)
    values=2*sums[:,:,0]/np.maximum(1,2*sums[:,:,0]+sums[:,:,1]+sums[:,:,2])
    return dict(clusters=len(data),repeats=repeats,new_model_f1_ci=np.quantile(values[:,0],[.025,.975]).tolist(),
        matched_tiny_f1_ci=np.quantile(values[:,1],[.025,.975]).tolist(),
        paired_f1_difference_ci=np.quantile(values[:,0]-values[:,1],[.025,.975]).tolist())
