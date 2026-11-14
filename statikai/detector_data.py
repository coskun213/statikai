"""CPU-friendly uint8 cache; stochastic transforms occur ONLY in training."""
import csv
from pathlib import Path
import cv2
import numpy as np
import torch
from torch.utils.data import Dataset
from PIL import Image
from statikai.detection import annotations


def load_rows(root,split):
    with (Path(root)/'ground_truth.csv').open(encoding='utf8',newline='') as f:
        return [r for r in csv.DictReader(f) if r['split']==split]


def augment(array,boxes,rng):
    h,w=array.shape;transformed=[dict(p,bbox=list(p['bbox'])) for p in boxes]
    if rng.random()<.5:
        array=array[:,::-1].copy()
        for p in transformed:
            x0,y0,x1,y1=p['bbox'];p['bbox']=[w-x1,y0,w-x0,y1]
    for _ in range(4):
        matrix=cv2.getRotationMatrix2D((w/2,h/2),rng.uniform(-5,5),rng.uniform(.8,1.12))
        matrix[:,2]+=rng.uniform(-.06,.06,2)*[w,h]
        new=[];valid=True
        for p in transformed:
            x0,y0,x1,y1=p['bbox'];corners=np.array([[x0,y0,1],[x1,y0,1],[x1,y1,1],[x0,y1,1]])@matrix.T
            low=corners.min(0);high=corners.max(0);clow=np.maximum(low,0);chigh=np.minimum(high,[w,h])
            if np.prod(chigh-clow)<.6*np.prod(high-low) or np.any(chigh-clow<2):valid=False;break
            new.append(dict(p,bbox=[*clow,*chigh]))
        if valid:
            array=cv2.warpAffine(array,matrix,(w,h),flags=cv2.INTER_LINEAR,borderValue=255)
            transformed=new;break
    ar=array.astype(np.float32)/255
    ar=np.clip((ar-.5)*rng.uniform(.55,1.3)+.5,0,1)*rng.uniform(.65,1.15)
    ar=np.clip(ar,0,1)**rng.uniform(.75,1.3)
    if rng.random()<.35:ar=cv2.GaussianBlur(ar,(3,3),rng.uniform(.15,.9))
    ar=np.clip(ar+rng.normal(0,rng.uniform(0,.025),ar.shape).astype(np.float32),0,1)
    if rng.random()<.08:ar=1-ar
    return ar.astype(np.float32),transformed


def negative_image(index,width,height):
    rng=np.random.default_rng(333000+index);im=np.full((height,width),255,np.uint8)
    if index%3==1:cv2.line(im,(width//7,height//2),(width*6//7,height//2),int(rng.integers(20,70)),2)
    if index%3==2:cv2.putText(im,f'{index+5} kN  {index/7:.2f} m',(width//8,height//2),cv2.FONT_HERSHEY_SIMPLEX,.6,30,1)
    return im


class CachedSymbols(Dataset):
    def __init__(self,root,rows,width,height,target_builder,training=False,seed=22091108):
        self.samples=[];self.target_builder=target_builder;self.training=training;self.seed=seed;self.epoch=0
        for row in rows:
            with Image.open(Path(root)/row['image']) as image:
                sw,sh=image.size;array=np.array(image.convert('L').resize((width,height),Image.Resampling.BILINEAR))
            boxes=[dict(class_id=p['class_id'],bbox=[v*scale for v,scale in zip(p['bbox'],[width/sw,height/sh,width/sw,height/sh])]) for p in annotations(root,row)]
            self.samples.append((array,boxes))
        if training:
            self.samples.extend((negative_image(i,width,height),[]) for i in range(96))
    def __len__(self):return len(self.samples)
    def __getitem__(self,index):
        ar,boxes=self.samples[index]
        if self.training:ar,boxes=augment(ar,boxes,np.random.default_rng(self.seed+self.epoch*100000+index))
        else:ar=ar.astype(np.float32)/255
        h,w=ar.shape;target=self.target_builder(boxes,(w,h))
        return torch.from_numpy(ar.copy())[None],*target
