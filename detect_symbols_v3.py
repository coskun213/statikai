"""Standalone V3 detection from one image; no labels/CSV at inference."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from PIL import Image
from statikai.lite_detector import LiteFPNCenter,ARCHITECTURE,detect


def main():
    p=argparse.ArgumentParser();p.add_argument('--image',type=Path,required=True)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();protocol=json.loads((args.run/'evaluation/frozen_thresholds.json').read_text())
    checkpoint=args.run/'lite/best.pt'
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest()!=protocol['checkpoints']['lite']:raise ValueError('Checkpoint/protocol mismatch')
    saved=torch.load(checkpoint,map_location='cpu',weights_only=True)
    if saved['architecture']!=ARCHITECTURE:raise ValueError('Unsupported architecture')
    torch.set_num_threads(2);model=LiteFPNCenter();model.load_state_dict(saved['model_state'])
    with Image.open(args.image) as im:boxes=detect(model,im,protocol['thresholds']['lite'])
    output=dict(image=str(args.image),architecture=ARCHITECTURE,symbols=boxes,coordinate_system='original image pixels, xyxy',
        scope='symbol_detection_only',ocr_status='not_implemented',RA_kN=None,RB_kN=None,review_required=True)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf8') as f:json.dump(output,f,indent=2)
    print(json.dumps(output,indent=2))


if __name__=='__main__':main()
