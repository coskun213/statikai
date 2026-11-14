"""Train full-image pilot on style A train; select using style A val only."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import numpy as np
from PIL import Image
import torch
from torch.utils.data import DataLoader
from statikai.detection import records,annotations,score_image,summarize
from statikai.detector_model import TinyDetector,FullImages,detection_loss,decode_batch,WIDTH,HEIGHT,image_tensor


def predict_rows(model,root,rows,threshold=.2,batch_size=32):
    predictions={}
    model.eval()
    with torch.inference_mode():
        for start in range(0,len(rows),batch_size):
            chunk=rows[start:start+batch_size];images=[];sizes=[]
            for row in chunk:
                with Image.open(Path(root)/row['image']) as image:
                    images.append(image_tensor(image));sizes.append(image.size)
            decoded=decode_batch(model(torch.stack(images)),sizes,threshold)
            predictions.update({r['image']:p for r,p in zip(chunk,decoded)})
    return predictions


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dataset',default='dataset_extended')
    parser.add_argument('--out',default='detector_results')
    parser.add_argument('--epochs',type=int,default=20)
    parser.add_argument('--seed',type=int,default=2209)
    args=parser.parse_args()
    if args.epochs<1: raise ValueError('epochs must be positive')
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    out=Path(args.out)
    if (out/'best_full_image_detector.pt').exists(): raise FileExistsError('Use a new experiment output directory')
    out.mkdir(parents=True,exist_ok=True)
    train=records(args.dataset,'train','A');val=records(args.dataset,'val','A')
    if not train or not val: raise ValueError('Both train and val records are required')
    if {r['problem_id'] for r in train}&{r['problem_id'] for r in val}: raise ValueError('Leaking problem IDs')
    dataset=FullImages(args.dataset,train,training=True)
    loader=DataLoader(dataset,batch_size=32,shuffle=True,num_workers=0,
                      generator=torch.Generator().manual_seed(args.seed))
    model=TinyDetector()
    optimizer=torch.optim.Adam(model.parameters(),lr=.001)
    history=[];best=-1.;start=time.perf_counter()
    for epoch in range(1,args.epochs+1):
        model.train();loss_sum=0.;n=0
        for images,heat,geo,mask in loader:
            optimizer.zero_grad()
            loss=detection_loss(model(images),heat,geo,mask)
            if not torch.isfinite(loss): raise RuntimeError('Nonfinite training loss')
            loss.backward();optimizer.step()
            loss_sum+=loss.item()*len(images);n+=len(images)
        predictions=predict_rows(model,args.dataset,val,.2)
        counts=sum((score_image(predictions[r['image']],annotations(args.dataset,r)) for r in val),np.zeros((3,3),int))
        metrics=summarize(counts)
        row=dict(epoch=epoch,loss=loss_sum/n,val_f1=metrics['f1'],val_precision=metrics['precision'],
                 val_recall=metrics['recall'],elapsed_seconds=time.perf_counter()-start)
        history.append(row)
        if metrics['f1']>best:
            best=metrics['f1']
            torch.save(dict(model_state=model.state_dict(),architecture='TinyDetector-v1',
                            class_names=['pin_support','roller_support','point_load'],epoch=epoch,
                            seed=args.seed,input_size=[WIDTH,HEIGHT],training_style='A',
                            pretrained_weights=False),out/'best_full_image_detector.pt')
        (out/'training_history.json').write_text(json.dumps(history,indent=2),encoding='utf8')
        print(json.dumps(row),flush=True)
    metadata=dict(seed=args.seed,torch=str(torch.__version__),device='cpu',epochs=args.epochs,
                  train_images=len(train),train_families=len({r['problem_id'] for r in train}),
                  blank_training_negatives=30,val_images=len(val),
                  val_families=len({r['problem_id'] for r in val}),parameters=sum(p.numel() for p in model.parameters()),
                  elapsed_seconds=time.perf_counter()-start,
                  manifest_sha256=hashlib.sha256((Path(args.dataset)/'ground_truth.csv').read_bytes()).hexdigest(),
                  test_used=False,held_out_style_used=False,pretrained_weights=False)
    (out/'training_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf8')
    print(json.dumps(metadata,indent=2),flush=True)


if __name__=='__main__': main()
