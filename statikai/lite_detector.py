"""Small custom MobileNet/FPN/center-point inspired detector, no pretrained weights.

This is not an official MobileNet or CenterNet implementation. Only pixels enter
inference. Original-image pixel boxes are returned; no OCR or beam solution.
"""
import math
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from PIL import Image
from statikai.detection import iou

WIDTH,HEIGHT,STRIDE=384,256,4
ARCHITECTURE='LiteFPNCenter-v1'


def conv(a,b,stride=1):
    return nn.Sequential(nn.Conv2d(a,b,3,stride,1,bias=False),nn.GroupNorm(4,b),nn.ReLU())


class Separable(nn.Module):
    def __init__(self,a,b,stride=1):
        super().__init__()
        self.layers=nn.Sequential(nn.Conv2d(a,a,3,stride,1,groups=a,bias=False),
            nn.Conv2d(a,b,1,bias=False),nn.GroupNorm(4,b),nn.ReLU())
    def forward(self,x):return self.layers(x)


class LiteFPNCenter(nn.Module):
    def __init__(self):
        super().__init__()
        self.stem=conv(1,16,2);self.s4=nn.Sequential(Separable(16,24,2),Separable(24,24))
        self.s8=nn.Sequential(Separable(24,40,2),Separable(40,40))
        self.s16=nn.Sequential(Separable(40,64,2),Separable(64,64))
        self.lat4=nn.Conv2d(24,32,1);self.lat8=nn.Conv2d(40,32,1);self.lat16=nn.Conv2d(64,32,1)
        self.fuse8=Separable(32,32);self.fuse4=Separable(32,32)
        self.heat=nn.Sequential(Separable(32,32),nn.Conv2d(32,3,1))
        self.geometry=nn.Sequential(Separable(32,32),nn.Conv2d(32,12,1))
        nn.init.constant_(self.heat[-1].bias,-2.19)
    def forward(self,x):
        c4=self.s4(self.stem(x));c8=self.s8(c4);c16=self.s16(c8)
        p8=self.fuse8(self.lat8(c8)+F.interpolate(self.lat16(c16),size=c8.shape[-2:],mode='bilinear',align_corners=False))
        p4=self.fuse4(self.lat4(c4)+F.interpolate(p8,size=c4.shape[-2:],mode='bilinear',align_corners=False))
        batch,_,h,w=p4.shape
        return self.heat(p4),self.geometry(p4).reshape(batch,3,4,h,w)


def image_tensor(image):
    ar=np.array(image.convert('L').resize((WIDTH,HEIGHT),Image.Resampling.BILINEAR))
    return torch.from_numpy(ar.copy())[None].float()/255


def targets(boxes,size):
    sw,sh=size;h,w=HEIGHT//4,WIDTH//4
    heat=torch.zeros(3,h,w);geo=torch.zeros(3,4,h,w);mask=torch.zeros(3,h,w,dtype=torch.bool)
    for box in boxes:
        cls=box['class_id'];x0,y0,x1,y1=box['bbox']
        cx=(x0+x1)*WIDTH/(2*sw*4);cy=(y0+y1)*HEIGHT/(2*sh*4);gx,gy=int(cx),int(cy)
        if not (0<=gx<w and 0<=gy<h) or mask[cls,gy,gx]:raise ValueError('Invalid/colliding object centers')
        for yy in range(max(0,gy-2),min(h,gy+3)):
            for xx in range(max(0,gx-2),min(w,gx+3)):
                heat[cls,yy,xx]=max(heat[cls,yy,xx],math.exp(-((xx-gx)**2+(yy-gy)**2)/2))
        geo[cls,:,gy,gx]=torch.tensor([math.log((x1-x0)*WIDTH/(sw*4)),math.log((y1-y0)*HEIGHT/(sh*4)),cx-gx,cy-gy])
        mask[cls,gy,gx]=True
    return heat,geo,mask


def loss(prediction,heat,geo,mask):
    logits,geometry=prediction;p=logits.sigmoid().clamp(1e-5,1-1e-5);positive=heat.eq(1)
    values=-(torch.log(p)*(1-p).pow(2)*positive+torch.log(1-p)*p.pow(2)*(1-heat).pow(4)*(~positive))
    # Equal contribution per class; not a roller weight tuned on an old test.
    focal=(values.sum((0,2,3))/positive.sum((0,2,3)).clamp_min(1)).mean()
    if not mask.any():return focal+geometry.sum()*0
    reg=geometry.permute(0,1,3,4,2)[mask];truth=geo.permute(0,1,3,4,2)[mask]
    offsets=reg[:,2:].sigmoid();size=reg[:,:2].clamp(-3,6).exp()
    target_size=truth[:,:2].exp();target_center=truth[:,2:]
    lo,hi=offsets-size/2,offsets+size/2;tlo,thi=target_center-target_size/2,target_center+target_size/2
    intersection=(torch.minimum(hi,thi)-torch.maximum(lo,tlo)).clamp_min(0).prod(1)
    union=size.prod(1)+target_size.prod(1)-intersection
    enclosure=(torch.maximum(hi,thi)-torch.minimum(lo,tlo)).prod(1).clamp_min(1e-6)
    giou=intersection/union.clamp_min(1e-6)-(enclosure-union)/enclosure
    return focal+.5*F.smooth_l1_loss(reg[:,:2],truth[:,:2])+F.smooth_l1_loss(offsets,target_center)+.5*(1-giou).mean()


def decode(prediction,sizes,threshold=.2):
    logits,geometry=prediction;heat=logits.sigmoid()
    peaks=heat.eq(F.max_pool2d(heat,3,1,1))*heat;result=[]
    for batch,(sw,sh) in enumerate(sizes):
        scores,indices=torch.topk(peaks[batch].flatten(),40);found=[];cells=(WIDTH//4)*(HEIGHT//4)
        for score,index in zip(scores.tolist(),indices.tolist()):
            if score<threshold:continue
            cls,cell=divmod(index,cells);gy,gx=divmod(cell,WIDTH//4)
            reg=geometry[batch,cls,:,gy,gx].detach().cpu();bw,bh=reg[:2].clamp(-3,6).exp().tolist()
            ox,oy=reg[2:].sigmoid().tolist();cx,cy=(gx+ox)*4,(gy+oy)*4
            box=[max(0,(cx-bw*2)*sw/WIDTH),max(0,(cy-bh*2)*sh/HEIGHT),
                 min(sw,(cx+bw*2)*sw/WIDTH),min(sh,(cy+bh*2)*sh/HEIGHT)]
            if box[2]<=box[0] or box[3]<=box[1]:continue
            if any(p['class_id']==cls and iou(box,p['bbox'])>.3 for p in found):continue
            found.append(dict(class_id=cls,score=float(score),bbox=box))
        result.append(found)
    return result


def detect(model,image,threshold=.2):
    model.eval()
    with torch.inference_mode():return decode(model(image_tensor(image)[None]),[image.size],threshold)[0]
