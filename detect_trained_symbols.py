"""Expose either finished candidate without changing its weights or threshold.

Export-only entry point added after the locked comparison. --model is explicit;
this script does not train, select parameters, or read image annotation files.
"""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from train_detector_v3 import specification,predict
from statikai.detection import NAMES


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=['lite','tiny'],required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();protocol=json.loads((args.run/'evaluation/frozen_thresholds.json').read_text())
    path=args.run/args.model/'best.pt'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=protocol['checkpoints'][args.model]:raise ValueError('Checkpoint/protocol mismatch')
    if hashlib.sha256((args.run/'data_protocol.json').read_bytes()).hexdigest()!=protocol['data_protocol_sha256']:raise ValueError('Data protocol mismatch')
    checkpoint=torch.load(path,map_location='cpu',weights_only=True);spec=specification(args.model)
    if checkpoint['architecture']!=spec[7] or checkpoint['input_size']!=list(spec[1:3]):raise ValueError('Architecture/input mismatch')
    if checkpoint['data_protocol_sha256']!=protocol['data_protocol_sha256']:raise ValueError('Checkpoint data lineage mismatch')
    torch.set_num_threads(2);model=spec[0]();model.load_state_dict(checkpoint['model_state'])
    source=args.image.resolve();row=dict(image=source.name)
    found=predict(model,[row],source.parent,args.model,protocol['thresholds'][args.model],1)[source.name]
    result=dict(image=str(source),model=args.model,architecture=spec[7],class_names=NAMES,symbols=found,
        coordinate_system='original image pixels, xyxy',scope='symbol_detection_only',
        ocr_status='not_implemented',RA_kN=None,RB_kN=None,review_required=True)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
