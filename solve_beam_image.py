"""End-to-end image-only beam solution with mandatory OCR/scope validation."""
import argparse
import json
from pathlib import Path
from read_beam_diagram import DEFAULT_DETECTOR,DEFAULT_OCR_MODELS
from statikai.beam_pipeline import analyze_image
from statikai.symbol_reader import SymbolReader
from statikai.ocr_engine import LocalOCR


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--detector-run',type=Path,default=DEFAULT_DETECTOR)
    p.add_argument('--ocr-models',type=Path,default=DEFAULT_OCR_MODELS)
    args=p.parse_args()
    if args.out.exists():p.error('Output exists; choose a new filename.')
    result=analyze_image(args.image,SymbolReader(args.detector_run),LocalOCR(args.ocr_models))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(dict(output=str(args.out),status=result['status'],static_solution=result['static_solution'],
                         issues=result['issues']),ensure_ascii=False))


if __name__=='__main__':main()
