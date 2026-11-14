"""Out-of-distribution robustness diagnostic on the synthetic held-out patches.
No fine-tuning on test. Crops are provided using ground truth annotations.
"""
import argparse,csv,json
from pathlib import Path
import numpy as np
import torch
from PIL import Image,ImageFilter,ImageEnhance
from sklearn.metrics import f1_score,accuracy_score
from train_pilot import Patches,TinyCNN


def main():
    p=argparse.ArgumentParser();p.add_argument('--dataset',default='dataset');p.add_argument('--checkpoint',default='pilot_results/best_patch_cnn.pt');p.add_argument('--out',default='pilot_results/shift_results.csv')
    a=p.parse_args();torch.set_num_threads(2)
    checkpoint=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    model=TinyCNN();model.load_state_dict(checkpoint['model_state']);model.eval()
    ds=Patches(a.dataset,'test');yt=[s[1] for s in ds.samples]
    conditions={
       'normal':lambda im:im,
       'greyscale':lambda im:im.convert('L').convert('RGB'),
       'low_light':lambda im:ImageEnhance.Brightness(im).enhance(0.38),
       'blur_sigma_2':lambda im:im.filter(ImageFilter.GaussianBlur(2)),
       'contrast_low':lambda im:ImageEnhance.Contrast(im).enhance(0.45)
    }
    rows=[]
    for name,transform in conditions.items():
        pred=[]
        with torch.no_grad():
            for start in range(0,len(ds.samples),64):
                batch=ds.samples[start:start+64]
                xx=[]
                for ar,_,_ in batch:
                    x=np.asarray(transform(Image.fromarray(ar)).convert('RGB'),dtype=np.float32)/255
                    xx.append(x.transpose(2,0,1))
                pred+=model(torch.from_numpy(np.stack(xx))).argmax(1).tolist()
        rows.append(dict(condition=name,n=len(yt),accuracy=round(float(accuracy_score(yt,pred)),4),macro_f1=round(float(f1_score(yt,pred,average='macro',labels=range(4),zero_division=0)),4)))
    out=Path(a.out);out.parent.mkdir(exist_ok=True,parents=True)
    with out.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    for r in rows:print(r)

if __name__=='__main__':main()
