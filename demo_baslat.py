"""Run the existing symbol detector and open a labelled result; no OCR/solver."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

from PIL import Image, ImageDraw
from statikai.compat import load_font


def main():
    root=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',type=Path,default=root/'dataset_extended/images/beam_0009_v0.png')
    parser.add_argument('--output-dir',type=Path,default=root.parent)
    parser.add_argument('--no-open',action='store_true')
    args=parser.parse_args()
    image_path=args.image.resolve()
    if not image_path.is_file():
        raise FileNotFoundError(f'Goruntu bulunamadi: {image_path}')
    output=args.output_dir.resolve()
    output.mkdir(parents=True,exist_ok=True)
    json_path=output/'StatikAI_Son_Tespit.json'
    png_path=output/'StatikAI_Son_Tespit.png'
    log_path=output/'StatikAI_Baslatma.log'
    command=[sys.executable,'-X','utf8',str(root/'detect_image.py'),
             '--image',str(image_path),'--method','learned','--out',str(json_path)]
    print('StatikAI sembol tespit demosu calisiyor...',flush=True)
    print('Bu surum OCR yapmaz ve RA/RB hesaplamaz.',flush=True)
    result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          encoding='utf8',errors='replace')
    log_path.write_text(f'Zaman: {datetime.now().isoformat()}\nKomut: {command!r}\n'
                        f'Cikis kodu: {result.returncode}\n{result.stdout}',encoding='utf8')
    if result.returncode:
        print(result.stdout,flush=True)
        print(f'Hata kaydi: {log_path}',flush=True)
        return result.returncode
    data=json.loads(json_path.read_text(encoding='utf8'))
    with Image.open(image_path) as source:
        source=source.convert('RGB')
        width=max(800,source.width)
        canvas=Image.new('RGB',(width,source.height+126),'white')
        x_offset=(width-source.width)//2
        canvas.paste(source,(x_offset,110))
    draw=ImageDraw.Draw(canvas)
    draw.text((16,12),'StatikAI - Deneysel Sembol Tespiti',fill='#17364d',font=load_font(23))
    draw.text((16,46),'Kirmizi kutular: modelin buldugu semboller.',fill='#17364d',font=load_font(16))
    draw.text((16,72),'Sayisal degerler okunmadi. OCR ve RA/RB cozumu henuz yok.',fill='#a32b2b',font=load_font(16))
    names={0:'Mafsal',1:'Hareketli mesnet',2:'Kuvvet oku'}
    for symbol in data['symbols']:
        x0,y0,x1,y1=symbol['bbox']
        box=(x0+x_offset,y0+110,x1+x_offset,y1+110)
        draw.rectangle(box,outline='#db2929',width=3)
        label=f"{names[symbol['class_id']]} (skor {symbol['score']:.2f})"
        text_width=draw.textbbox((0,0),label,font=load_font(13))[2]
        tx=min(max(8,box[0]),width-text_width-8)
        draw.text((tx,max(110,box[1]-17)),label,fill='#b52020',font=load_font(13))
    canvas.save(png_path)
    print(f"Bulunan sembol sayisi: {len(data['symbols'])}",flush=True)
    print(f'Sonuc goruntusu: {png_path}',flush=True)
    print(f'Sayisal kayit: {json_path}',flush=True)
    if not args.no_open:
        if os.name=='nt':
            os.startfile(str(png_path))
        elif sys.platform=='darwin':
            subprocess.Popen(['open',str(png_path)])
        else:
            subprocess.Popen(['xdg-open',str(png_path)])
        with log_path.open('a',encoding='utf8') as handle:
            handle.write('\nSonuc goruntusu sistem goruntuleyicisine gonderildi.\n')
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'StatikAI acilamadi: {error}',flush=True)
        raise
