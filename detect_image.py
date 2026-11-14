"""Inference on one full image; annotation files are not needed or read."""
import argparse
import json
import hashlib
from pathlib import Path
from PIL import Image
from statikai.detection import classical_detect


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    parser.add_argument('--method',choices=['classical','learned'],default='classical')
    parser.add_argument('--protocol',default='detector_results/evaluation/frozen_protocol.json')
    parser.add_argument('--checkpoint',default='detector_results/best_full_image_detector.pt')
    parser.add_argument('--out',default='symbol_detection.json')
    args=parser.parse_args()
    protocol=json.loads(Path(args.protocol).read_text(encoding='utf8'))
    with Image.open(args.image) as image:
        if args.method=='classical':
            predictions=classical_detect(image,protocol['classical']['fill_cutoff'])
        else:
            import torch
            from statikai.detector_model import TinyDetector,learned_detect
            torch.set_num_threads(2)
            checkpoint=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
            if checkpoint.get('architecture')!='TinyDetector-v1':
                raise ValueError('This is not a full-image detector checkpoint')
            if hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest()!=protocol['checkpoint_sha256']:
                raise ValueError('Checkpoint does not match the frozen threshold protocol')
            model=TinyDetector();model.load_state_dict(checkpoint['model_state'])
            predictions=learned_detect(model,image,protocol['learned']['score_threshold'])
    result=dict(image=str(args.image),method=args.method,symbols=predictions,
                scope='symbol_detection_only',ocr_status='not_implemented',
                extracted_physical_inputs=None,RA_kN=None,RB_kN=None,
                end_to_end_solution_status='not_implemented',review_required=True)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
