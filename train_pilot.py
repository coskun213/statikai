"""StatikAI: REAL, narrowly scoped patch-classification pilot.

Trains a small CNN from scratch to classify ANNOTATED, PRE-CROPPED patches
as pin support, roller support, point-load arrow or background.
This is NOT end-to-end object detection, OCR, or solved diagram interpretation.
Problem-level train/val/test splitting already exists in ground_truth.csv.
"""
from __future__ import annotations
import argparse, csv, json, random, time
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score

NAMES = ['background','pin_support','roller_support','point_load']
YOLO_TO_CLASS = {0:1,1:2,2:3}
SIZE = 48


def crop_patch(im, box, pad_fraction=.22):
    x0,y0,x1,y1 = box
    dx=(x1-x0)*pad_fraction; dy=(y1-y0)*pad_fraction
    return im.crop((int(x0-dx),int(y0-dy),int(x1+dx),int(y1+dy))).resize((SIZE,SIZE),Image.Resampling.BICUBIC)


def annotation_boxes(label_path, width, height):
    out=[]
    for ln in Path(label_path).read_text(encoding='utf8').splitlines():
        fields=ln.split()
        if not fields: continue
        c=int(fields[0]); cx,cy,w,h=map(float,fields[1:])
        out.append((YOLO_TO_CLASS[c], ((cx-w/2)*width,(cy-h/2)*height,(cx+w/2)*width,(cy+h/2)*height)))
    return out


class Patches(Dataset):
    def __init__(self, root, split, n_background=3):
        root=Path(root)
        records=list(csv.DictReader((root/'ground_truth.csv').open(encoding='utf8')))
        self.samples=[]
        for r in records:
            if r['split'] != split: continue
            im=Image.open(root/r['image']).convert('RGB')
            boxes=annotation_boxes(root/r['symbol_labels'],*im.size)
            for c,box in boxes:
                arr=np.asarray(crop_patch(im,box), dtype=np.uint8).copy()
                self.samples.append((arr,c,r['problem_id']))
            # Controlled negatives: below beam, where no annotated object lies.
            # Avoid all true symbol bounding boxes and numeric labels at the top.
            for cx in (180,360,540)[:n_background]:
                x0,y0,x1,y1=cx-28,268,cx+28,305
                arr=np.asarray(im.crop((x0,y0,x1,y1)).resize((SIZE,SIZE)),dtype=np.uint8).copy()
                self.samples.append((arr,0,r['problem_id']))
        if not self.samples: raise ValueError(f'No records for {split}')

    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        arr,c,_=self.samples[idx]
        return torch.from_numpy(arr.transpose(2,0,1).copy()).float()/255.0, c


class TinyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features=nn.Sequential(nn.Conv2d(3,16,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(16,32,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.Conv2d(32,64,3,padding=1),nn.ReLU(),nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((1,1)))
        self.head=nn.Linear(64,len(NAMES))
    def forward(self,x): return self.head(self.features(x).flatten(1))


def evaluate(model, loader, device):
    model.eval(); ys=[]; preds=[]
    with torch.no_grad():
        for x,y in loader:
            z=model(x.to(device)); p=z.argmax(1).cpu().tolist()
            ys.extend(y.tolist()); preds.extend(p)
    result={'accuracy':float(accuracy_score(ys,preds)),
            'macro_f1':float(f1_score(ys,preds,labels=list(range(4)),average='macro',zero_division=0)),
            'confusion_matrix':confusion_matrix(ys,preds,labels=list(range(4))).tolist(),
            'classification_report':classification_report(ys,preds,labels=list(range(4)),target_names=NAMES,
                                                         output_dict=True,zero_division=0),
            'n_patches':len(ys)}
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',default='dataset')
    parser.add_argument('--out',default='pilot_results')
    parser.add_argument('--epochs',type=int,default=5)
    parser.add_argument('--batch-size',type=int,default=32)
    parser.add_argument('--seed',type=int,default=2209)
    a=parser.parse_args(); t0=time.time()
    random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
    torch.set_num_threads(min(2,torch.get_num_threads()))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    ds={s:Patches(a.dataset,s) for s in ('train','val','test')}
    loaders={s:DataLoader(ds[s], batch_size=a.batch_size,shuffle=(s=='train'),num_workers=0) for s in ds}
    model=TinyCNN(); device=torch.device('cuda' if torch.cuda.is_available() else 'cpu');model.to(device)
    opt=torch.optim.Adam(model.parameters(),lr=0.002)
    criterion=nn.CrossEntropyLoss()
    history=[];best_val=-1.0;best_epoch=0
    for epoch in range(1,a.epochs+1):
        model.train();loss_total=0;num=0
        for x,y in loaders['train']:
            x=x.to(device);y=y.to(device)
            opt.zero_grad();loss=criterion(model(x),y);loss.backward();opt.step()
            loss_total+=loss.item()*len(y);num+=len(y)
        val=evaluate(model,loaders['val'],device)
        history.append({'epoch':epoch,'train_loss':loss_total/num,'val_macro_f1':val['macro_f1']})
        if val['macro_f1'] > best_val:
            best_val=val['macro_f1']; best_epoch=epoch
            torch.save({'model_state':model.state_dict(),'class_names':NAMES,'epoch':epoch},out/'best_patch_cnn.pt')
        print(f'epoch {epoch} loss={loss_total/num:.4f} val_macro_F1={val["macro_f1"]:.4f}')
    checkpoint=torch.load(out/'best_patch_cnn.pt',map_location=device,weights_only=True)
    model.load_state_dict(checkpoint['model_state'])
    results={s:evaluate(model,loaders[s],device) for s in ('val','test')}
    report={'pilot_scope':'cropped symbol patch classification; NOT diagram-level detection or OCR',
            'seed':a.seed,'epochs':a.epochs,'best_epoch':best_epoch,
            'split_counts':{s: {'n_patches':len(ds[s]), 'n_base_problems':len({z[2] for z in ds[s].samples}),
                     'class_counts':dict(Counter(NAMES[z[1]] for z in ds[s].samples))} for s in ds},
            'history':history,'val':results['val'],'test':results['test'],
            'device':str(device),'elapsed_s':round(time.time()-t0,2),
            'cautions':['Dataset is synthetic and simple','Crops are taken using ground-truth boxes, not detected by the model',
                         'No OCR or end-to-end reaction estimates','Same generator produces train/test diagrams; no independent style-domain test']}
    (out/'pilot_metrics.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf8')
    with (out/'history.csv').open('w',newline='',encoding='utf8') as f:
        wr=csv.DictWriter(f,fieldnames=history[0].keys());wr.writeheader();wr.writerows(history)
    print('RESULTS: val F1',results['val']['macro_f1'],'test F1',results['test']['macro_f1'])
    print('Saved:',out.resolve())

if __name__=='__main__':main()
