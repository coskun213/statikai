"""Conservative pixel checks for the narrow two-downward-load beam domain.

These are rejection heuristics, not an open-set recognition guarantee. Unknown
ink is never reinterpreted as a supported load. No lengths/forces are inferred.
"""
from collections import Counter
import cv2
import numpy as np

CONFIG = dict(arrow_head_width_ratio=1.8, unexplained_area_fraction=.00012,
              triangle_widening_ratio=1.6, symbol_padding_width=.012,
              support_symmetry_width=.004,
              scope='left pin, right roller, horizontal beam, two downward point loads')


def ink_mask(image):
    gray=np.asarray(image.convert('L'))
    if np.median(gray)<127:gray=255-gray
    return cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)[1]


def arrow_evidence(mask, box, beam_y):
    h,w=mask.shape
    x0,y0,x1,y1=box;pad=round(.01*w)
    a=max(0,int(x0)-pad);b=min(w,int(x1)+pad+1)
    top=max(0,int(y0)-round(.02*h));bottom=min(h,int(beam_y)-max(3,round(w/450)))
    crop=mask[top:bottom,a:b]
    if not crop.size:return dict(downward=False,reason='empty arrow region')
    n,labels,stats,_=cv2.connectedComponentsWithStats(crop,8)
    candidates=[i for i in range(1,n) if stats[i,3]>.05*h
                and stats[i,2]<.07*w and abs(a+stats[i,0]+stats[i,2]/2-(x0+x1)/2)<.025*w]
    if len(candidates)!=1:return dict(downward=False,reason='no unique vertical arrow component')
    i=candidates[0];x,y,cw,ch,_=stats[i];component=labels[y:y+ch,x:x+cw]==i
    widths=np.array([np.ptp(np.flatnonzero(row))+1 if row.any() else 0 for row in component])
    q=max(2,int(ch*.30));upper=float(np.quantile(widths[:q],.9));lower=float(np.quantile(widths[-q:],.9))
    ratio=lower/max(upper,1)
    return dict(downward=bool(ratio>=CONFIG['arrow_head_width_ratio'] and ch>2*cw),
                head_width_ratio=ratio,upper_width_px=upper,lower_width_px=lower,
                component_bbox=[int(a+x),int(top+y),int(a+x+cw),int(top+y+ch)],
                method='head widening at bottom of independently located vertical ink component')


def support_evidence(mask,x,beam_y):
    h,w=mask.shape;s=w/900
    left=max(0,round(x-.035*w));right=min(w,round(x+.035*w))
    top=max(0,round(beam_y+max(4,3*s)));bottom=min(h,round(beam_y+.09*h))
    crop=mask[top:bottom,left:right]
    widths=[];centers=[]
    for row in crop:
        xx=np.flatnonzero(row)
        widths.append(float(xx[-1]-xx[0]+1) if len(xx) else 0)
        centers.append(float(left+(xx[-1]+xx[0])/2) if len(xx) else float(x))
    active=np.flatnonzero(np.array(widths)>0)
    if len(active)<8:return dict(triangle=False,roller_pair=False,reason='support ink missing')
    start=int(active[0]);height=max(10,round(.028*h))
    profile=np.array(widths[start:start+height]);cc=np.array(centers[start:start+height])
    upper=float(np.median(profile[:max(2,len(profile)//4)]))
    lower=float(np.median(profile[len(profile)//2:]))
    q=max(2,len(profile)//4);half=len(profile)//2
    left_extent=x-cc+(profile-1)/2;right_extent=cc+(profile-1)/2-x
    left_growth=float(np.median(left_extent[half:])-np.median(left_extent[:q]))
    right_growth=float(np.median(right_extent[half:])-np.median(right_extent[:q]))
    triangle=(lower/max(upper,1)>=CONFIG['triangle_widening_ratio']
              and abs(float(np.median(cc))-x)<=max(3,CONFIG['support_symmetry_width']*w)
              and min(left_growth,right_growth)>2*s)
    circles=[]
    contours,hierarchy=cv2.findContours(crop,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_SIMPLE)
    for i,contour in enumerate(contours):
        if hierarchy[0][i][3]<0:continue  # a roller must enclose a hole; hatching does not
        a,b,c,d=cv2.boundingRect(contour);px=a+(c-1)/2;py=b+(d-1)/2
        area=cv2.contourArea(contour)
        if (.60<=c/max(d,1)<=1.5 and 2*s*s<=area<=180*s*s and 2*s<=c<=14*s
                and top+py>beam_y+.026*h and abs(left+px-x)<.028*w):
            circles.append([float(left+px),float(top+py)])
    pair=any(a[0]<x<b[0] and abs(a[1]-b[1])<.008*h and .006*w<b[0]-a[0]<.035*w
             for a in circles for b in circles)
    return dict(triangle=bool(triangle),triangle_widening_ratio=lower/max(upper,1),
                left_growth_px=left_growth,right_growth_px=right_growth,
                roller_pair=bool(pair),circle_centers_px=circles,
                method='triangle widening and two separate circular ink components')


def inspect_scope(image,extraction):
    mask=ink_mask(image);h,w=mask.shape;issues=[]
    result=dict(status='review_required',passed=False,config=CONFIG,arrows=[],supports=[],issues=issues,
                limitation='pixel rejection checks do not guarantee recognition of every unsupported symbol')
    def issue(code,detail):issues.append(dict(code=code,detail=detail,severity='review_required'))
    symbols=extraction.get('symbols',[])
    if Counter(s.get('class_id') for s in symbols)!=Counter({0:1,1:1,2:2}):
        issue('unsupported_symbol_inventory','Exactly one pin, one roller and two loads required.');return result
    beam=extraction.get('geometry',{}).get('beam')
    if not beam:issue('unverified_beam','No verified horizontal beam.');return result
    known=np.zeros_like(mask);pad=max(3,round(CONFIG['symbol_padding_width']*w))
    def allow(box,padding=pad):
        a,b,c,d=box
        cv2.rectangle(known,(max(0,int(a)-padding),max(0,int(b)-padding)),
                      (min(w-1,int(c)+padding),min(h-1,int(d)+padding)),255,-1)
    allow([beam['left_px'],beam['y_px']-max(4,w/250),beam['right_px'],beam['y_px']+max(4,w/250)],2)
    for symbol in symbols:
        box=symbol['bbox'];x=(box[0]+box[2])/2
        if symbol['class_id']==2:
            evidence=arrow_evidence(mask,box,beam['y_px']);result['arrows'].append(evidence)
            if not evidence['downward']:issue('unsupported_load_direction','Downward vertical point-load head could not be verified.')
            if evidence.get('component_bbox'):allow(evidence['component_bbox'])
        else:
            x=beam['left_px'] if symbol['class_id']==0 else beam['right_px']
            evidence=support_evidence(mask,x,beam['y_px']);evidence['class_id']=symbol['class_id'];result['supports'].append(evidence)
            if not evidence['triangle']:issue('unsupported_support_shape','Triangular pin/roller support could not be verified.')
            if evidence['roller_pair']!=(symbol['class_id']==1):issue('support_type_unverified','Roller evidence disagrees with the detected support class.')
        allow(box)
    for text in extraction.get('ocr_readings',[]):
        if text.get('accepted') or text.get('raw_text','').strip() in ('A','B'):
            allow(text['bbox'],max(2,round(w/300)))
    # Above-beam ink can include unknown arrows, UDL bars, moments or annotations.
    # Keep all such components unless explicitly explained by supported objects.
    residual=mask.copy();residual[known>0]=0
    residual[max(0,round(beam['y_px']+.095*h)):]=0
    n,_,stats,_=cv2.connectedComponentsWithStats(residual,8)
    unknown=[list(map(int,b[:4])) for b in stats[1:] if b[4]>=max(25,CONFIG['unexplained_area_fraction']*w*h)]
    result['unexplained_components_xywh']=unknown
    if unknown:issue('unexplained_load_region_ink','Additional ink in load region: unsupported load or unreadable annotation; no automatic solve.')
    if not issues:result.update(status='passed',passed=True)
    return result
