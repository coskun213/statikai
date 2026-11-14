"""Actual OCR on corrupted copies of a training image; originals stay immutable.

Reference annotations are used ONLY to construct fixtures, never for extraction.
These are safety diagnostics, not part of the locked test accuracy denominator.
"""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from read_beam_diagram import extract, DEFAULT_DETECTOR, DEFAULT_OCR_MODELS
from statikai.symbol_reader import SymbolReader
from statikai.ocr_engine import LocalOCR
from statikai.compat import load_font


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out;out.mkdir(parents=True,exist_ok=False)
    source=ROOT/'dataset_dimensions_v2/images/beam_0000_v0.png'
    annotation=json.loads((ROOT/'dataset_dimensions_v2/annotations/beam_0000_v0.json').read_text(encoding='utf8'))
    detector=SymbolReader(DEFAULT_DETECTOR);ocr=LocalOCR(DEFAULT_OCR_MODELS)
    force=next(t for t in annotation['texts'] if t['kind']=='force')
    total=next(t for t in annotation['texts'] if t['kind']=='dimension' and t['value_si']==15.88)
    dimension=next(t for t in annotation['texts'] if t['kind']=='dimension')
    reports=[]
    for name in ('erased_force','unsupported_force_unit','contradictory_total','erased_dimensions','wrong_dimension_unit','extra_force_text'):
        with Image.open(source) as original:im=original.convert('RGB')
        d=ImageDraw.Draw(im)
        def replace(text,value):
            a,b,c,e=text['bbox'];d.rectangle((a-8,b-8,c+12,e+8),fill='white')
            if value:d.text((a,b-4),value,font=load_font(22),fill='black')
        if name=='erased_force':replace(force,None)
        if name=='unsupported_force_unit':replace(force,'17 kg')
        if name=='contradictory_total':replace(total,'20000 mm')
        if name=='erased_dimensions':
            for text in annotation['texts']:
                if text['kind']=='dimension':replace(text,None)
        if name=='wrong_dimension_unit':replace(dimension,'5242 kg')
        if name=='extra_force_text':d.text((280,90),'23 kN',font=load_font(22),fill='black')
        image=out/(name+'.png');im.save(image)
        result=extract(image,detector,ocr)
        (out/(name+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        passed=result['review_required'] and result['extracted_inputs'] is None and result['static_solution']['status']=='not_run'
        reports.append(dict(case=name,status='BAŞARILI' if passed else 'BAŞARISIZ',
                            expected='review required, no complete input and no static solution',
                            observed_issues=[i['code'] for i in result['issues']]))
    summary=dict(status='BAŞARILI' if all(r['status']=='BAŞARILI' for r in reports) else 'BAŞARISIZ',
                 actual_ocr=True,training_image_copy_only=True,cases=reports)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if summary['status']!='BAŞARILI':raise SystemExit(1)


if __name__=='__main__':main()
