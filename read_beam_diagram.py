"""Image-only OCR and dimension extraction. This command never runs statics."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from PIL import Image
from statikai.diagram_reading import interpret
from statikai.ocr_engine import LocalOCR
from statikai.symbol_reader import SymbolReader

ROOT = Path(__file__).resolve().parent
DEFAULT_DETECTOR = ROOT/'experiments/detector_v3_20261108_01'
DEFAULT_OCR_MODELS = ROOT/'experiments/ocr_v1_20261108_01/ocr_models'


def extract(image_path, detector, ocr):
    start = time.perf_counter()
    with Image.open(image_path) as im:
        im = im.convert('RGB')
        result = interpret(im, detector.read(im), ocr.read(im))
        result['image'] = dict(path=str(Path(image_path).resolve()), width=im.width, height=im.height,
                               sha256=hashlib.sha256(Path(image_path).read_bytes()).hexdigest())
    result['detector'] = detector.metadata
    result['ocr_engine'] = ocr.metadata()
    result['elapsed_seconds'] = time.perf_counter()-start
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--detector-run', type=Path, default=DEFAULT_DETECTOR)
    parser.add_argument('--detector', choices=['tiny', 'lite'], default='tiny')
    parser.add_argument('--ocr-models', type=Path, default=DEFAULT_OCR_MODELS)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output already exists; choose a new path to preserve previous results.')
    detector = SymbolReader(args.detector_run, args.detector)
    ocr = LocalOCR(args.ocr_models)
    result = extract(args.image, detector, ocr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(dict(output=str(args.out), review_required=result['review_required'],
                         extracted_inputs=result['extracted_inputs'], issues=result['issues']), ensure_ascii=False))


if __name__ == '__main__':
    main()
