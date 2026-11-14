"""Small center-heatmap detector trained on FULL images, without pretrained weights."""
import math
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import Dataset
from statikai.detection import annotations, iou

WIDTH,HEIGHT,STRIDE=256,160,4


def _block(a,b,stride=1):
    return nn.Sequential(nn.Conv2d(a,b,3,stride=stride,padding=1),nn.GroupNorm(4,b),nn.ReLU())


class TinyDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.e1=_block(1,12,2);self.e2=_block(12,20,2)
        self.e3=_block(20,32,2);self.e4=nn.Sequential(_block(32,48,2),_block(48,48))
        self.d3=_block(48+32,32);self.d2=_block(32+20,24)
        self.heat=nn.Conv2d(24,3,1);self.geometry=nn.Conv2d(24,4,1)
        nn.init.constant_(self.heat.bias,-2.19)

    def forward(self,x):
        a=self.e1(x);b=self.e2(a);c=self.e3(b);d=self.e4(c)
        d=self.d3(torch.cat((F.interpolate(d,size=c.shape[-2:],mode='bilinear',align_corners=False),c),1))
        d=self.d2(torch.cat((F.interpolate(d,size=b.shape[-2:],mode='bilinear',align_corners=False),b),1))
        return self.heat(d),self.geometry(d)


def image_tensor(image):
    array=np.asarray(image.convert('L').resize((WIDTH,HEIGHT),Image.Resampling.BILINEAR),dtype=np.uint8).copy()
    return torch.from_numpy(array).unsqueeze(0).float()/255.


def make_target(boxes,source_size):
    sw,sh=source_size
    heat=np.zeros((3,HEIGHT//STRIDE,WIDTH//STRIDE),np.float32)
    geo=np.zeros((4,HEIGHT//STRIDE,WIDTH//STRIDE),np.float32)
    mask=np.zeros((HEIGHT//STRIDE,WIDTH//STRIDE),bool)
    for box in boxes:
        x0,y0,x1,y1=box['bbox']
        cx=(x0+x1)*WIDTH/(2*sw*STRIDE);cy=(y0+y1)*HEIGHT/(2*sh*STRIDE)
        gx,gy=int(cx),int(cy)
        if mask[gy,gx]: raise ValueError('Two object centers collide on the output grid')
        for yy in range(max(0,gy-2),min(heat.shape[1],gy+3)):
            for xx in range(max(0,gx-2),min(heat.shape[2],gx+3)):
                value=math.exp(-((xx-gx)**2+(yy-gy)**2)/2)
                heat[box['class_id'],yy,xx]=max(heat[box['class_id'],yy,xx],value)
        geo[:,gy,gx]=[math.log((x1-x0)*WIDTH/(sw*STRIDE)),math.log((y1-y0)*HEIGHT/(sh*STRIDE)),cx-gx,cy-gy]
        mask[gy,gx]=True
    return torch.from_numpy(heat),torch.from_numpy(geo),torch.from_numpy(mask)


class FullImages(Dataset):
    def __init__(self,root,rows,training=False):
        self.samples=[];self.training=training
        for row in rows:
            with Image.open(Path(root)/row['image']) as image:
                self.samples.append((image_tensor(image),make_target(annotations(root,row),image.size)))
        if training:
            # Explicit empty negatives; no annotation-based crop is used.
            empty=make_target([], (WIDTH,HEIGHT))
            for level in np.linspace(.8,1.,30):
                self.samples.append((torch.full((1,HEIGHT,WIDTH),float(level)),empty))

    def __len__(self): return len(self.samples)

    def __getitem__(self,index):
        image,target=self.samples[index]
        if self.training:
            gain=.8+torch.rand(()).item()*.4
            image=(image*gain).clamp(0,1)
        return image,*target


def detection_loss(prediction,heat,geo,mask):
    logits,geometry=prediction
    p=logits.sigmoid().clamp(1e-5,1-1e-5)
    positive=heat.eq(1)
    negative=~positive
    denominator=positive.sum().clamp_min(1)
    focal=-(torch.log(p)*(1-p).pow(2)*positive +
            torch.log(1-p)*p.pow(2)*(1-heat).pow(4)*negative).sum()/denominator
    if mask.any():
        reg=geometry.permute(0,2,3,1)[mask]
        truth=geo.permute(0,2,3,1)[mask]
        size=F.smooth_l1_loss(reg[:,:2],truth[:,:2])
        offset=F.smooth_l1_loss(reg[:,2:].sigmoid(),truth[:,2:])
    else: size=offset=geometry.sum()*0
    return focal+size+offset


def decode_batch(prediction,sizes,score_threshold=.2):
    logits,geometry=prediction
    heat=logits.sigmoid()
    peaks=heat.eq(F.max_pool2d(heat,3,stride=1,padding=1))*heat
    result=[]
    for batch,(sw,sh) in enumerate(sizes):
        flat=peaks[batch].flatten()
        values,indices=torch.topk(flat,min(30,flat.numel()))
        found=[]
        for score,index in zip(values.tolist(),indices.tolist()):
            if score<score_threshold: continue
            cells=(WIDTH//STRIDE)*(HEIGHT//STRIDE)
            cls=index//cells;cell=index%cells
            gy,gx=divmod(cell,WIDTH//STRIDE)
            reg=geometry[batch,:,gy,gx].detach().cpu()
            bw,bh=reg[:2].clamp(-2,5).exp().tolist()
            ox,oy=reg[2:].sigmoid().tolist()
            cx,cy=(gx+ox)*STRIDE,(gy+oy)*STRIDE
            box=[max(0,(cx-bw*STRIDE/2)*sw/WIDTH),max(0,(cy-bh*STRIDE/2)*sh/HEIGHT),
                 min(sw,(cx+bw*STRIDE/2)*sw/WIDTH),min(sh,(cy+bh*STRIDE/2)*sh/HEIGHT)]
            if box[2]<=box[0] or box[3]<=box[1]: continue
            if any(q['class_id']==cls and iou(box,q['bbox'])>.3 for q in found): continue
            found.append(dict(class_id=int(cls),score=float(score),bbox=box))
        result.append(found)
    return result


def learned_detect(model,image,score_threshold=.2):
    model.eval()
    with torch.inference_mode():
        return decode_batch(model(image_tensor(image).unsqueeze(0)),[image.size],score_threshold)[0]
