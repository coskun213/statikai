"""Separate 2D image-loading interface. The existing 3D app stays unchanged."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from uuid import uuid4
from PIL import Image,ImageTk,ImageDraw
from read_beam_diagram import DEFAULT_DETECTOR,DEFAULT_OCR_MODELS
from statikai.beam_pipeline import analyze_image
from statikai.symbol_reader import SymbolReader
from statikai.ocr_engine import LocalOCR

ROOT=Path(__file__).resolve().parent


class BeamApp:
    def __init__(self,root):
        self.root=root;self.path=None;self.result=None;self.detector=None;self.ocr=None
        self.messages=queue.Queue();self.busy=False;self.output=None
        root.title('StatikAI — 2B görüntüden deneysel kiriş çözümü');root.geometry('1120x780')
        toolbar=ttk.Frame(root,padding=10);toolbar.pack(fill='x')
        self.load=ttk.Button(toolbar,text='Görüntü yükle',command=self.choose);self.load.pack(side='left',padx=5)
        self.run=ttk.Button(toolbar,text='Algıla → Oku → Doğrula → Hesapla',command=self.start,state='disabled');self.run.pack(side='left',padx=5)
        self.save=ttk.Button(toolbar,text='JSON farklı kaydet',command=self.export,state='disabled');self.save.pack(side='left',padx=5)
        ttk.Label(root,text='Yatay kiriş · solda mafsal, sağda hareketli mesnet · iki aşağı yönlü tekil yük',padding=5).pack()
        self.status=tk.StringVar(value='Bir PNG/JPEG görüntüsü seçin.');ttk.Label(root,textvariable=self.status,padding=5,wraplength=1050).pack(fill='x')
        self.preview=ttk.Label(root,anchor='center');self.preview.pack(fill='both',expand=True,padx=8,pady=5)
        self.text=tk.Text(root,height=11,wrap='word');self.text.pack(fill='x',padx=8,pady=5)
        self._show('Girdiler okunamazsa veya kapsam doğrulanamazsa hesap durur. Denge sağlanması doğru görüntü yorumu kanıtı değildir. Araştırma prototipi; gerçek yapı tasarımına uygun değildir.')
        root.after(100,self.poll)

    def _show(self,text):
        self.text.configure(state='normal');self.text.delete('1.0','end');self.text.insert('end',text);self.text.configure(state='disabled')

    def choose(self):
        path=filedialog.askopenfilename(filetypes=[('Kiriş görüntüleri','*.png *.jpg *.jpeg *.bmp'),('Tüm dosyalar','*.*')])
        if path:self.load_image(Path(path))

    def load_image(self,path):
        try:
            with Image.open(path) as im:im.verify()
            self.path=Path(path);self.result=None;self.output=None;self.show_preview()
            self.run.configure(state='normal');self.save.configure(state='disabled');self.status.set(str(self.path))
        except (OSError,ValueError) as exc:
            self.path=None;self.run.configure(state='disabled');self.status.set('Görüntü okunamadı: '+str(exc))

    def show_preview(self):
        with Image.open(self.path) as im:im=im.convert('RGB')
        if self.result and self.result.get('extraction'):
            d=ImageDraw.Draw(im)
            for s in self.result['extraction']['symbols']:d.rectangle(s['bbox'],outline='blue',width=3)
            for t in self.result['extraction']['ocr_readings']:
                if t.get('accepted'):d.rectangle(t['bbox'],outline='green',width=2)
        im.thumbnail((1050,440));self.photo=ImageTk.PhotoImage(im);self.preview.configure(image=self.photo)

    def start(self):
        if self.busy or self.path is None:return
        self.busy=True;self.run.configure(state='disabled');self.load.configure(state='disabled');self.save.configure(state='disabled')
        self.status.set('Semboller, OCR, ölçü zinciri, kapsam ve denge kontrol ediliyor…')
        path=self.path
        def work():
            try:
                if self.detector is None:self.detector=SymbolReader(DEFAULT_DETECTOR)
                if self.ocr is None:self.ocr=LocalOCR(DEFAULT_OCR_MODELS)
                result=analyze_image(path,self.detector,self.ocr)
                folder=ROOT/'work/beam_pipeline';folder.mkdir(parents=True,exist_ok=True)
                output=folder/(datetime.now().strftime('%Y%m%d_%H%M%S_')+uuid4().hex[:8]+'.json')
                with output.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
                self.messages.put((result,output,None))
            except Exception as exc:self.messages.put((None,None,str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def poll(self):
        try:
            result,output,error=self.messages.get_nowait();self.busy=False
            self.load.configure(state='normal');self.run.configure(state='normal')
            if error:self.status.set('İşlem tamamlanamadı: '+error);self._show('Hesap yapılmadı. '+error)
            else:
                self.result=result;self.output=output;self.save.configure(state='normal');self.show_preview()
                if result['status']=='computed':
                    sol=result['static_solution'];title=f'Okunan girdilere göre RA={sol["RA_kN"]:.6g} kN, RB={sol["RB_kN"]:.6g} kN'
                else:title='İNCELEME GEREKLİ — mesnet tepkileri hesaplanmadı.'
                self.status.set(title)
                details=dict(girdiler=result['validated_inputs'],mesnet_tepkileri=result['static_solution'],
                             denge=result['equilibrium'],asamalar=result['stages'],
                             uyarilar=result['issues'],json=str(output),aciklama=result['interpretation_warning'])
                if result.get('extraction') and result['extraction'].get('issues'):details['okuma_uyarilari']=result['extraction']['issues']
                if result.get('scope_check') and result['scope_check'].get('issues'):details['kapsam_uyarilari']=result['scope_check']['issues']
                self._show(json.dumps(details,ensure_ascii=False,indent=2))
        except queue.Empty:pass
        self.root.after(100,self.poll)

    def export(self):
        if self.result is None:return
        name=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')])
        if not name:return
        try:
            with Path(name).open('x',encoding='utf8') as f:json.dump(self.result,f,ensure_ascii=False,indent=2,allow_nan=False)
        except OSError as exc:messagebox.showerror('Kaydedilemedi','Mevcut dosyanın üzerine yazılmaz. '+str(exc))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--smoke-test',action='store_true')
    p.add_argument('--image',type=Path);args=p.parse_args();root=tk.Tk();app=BeamApp(root)
    if args.image:app.load_image(args.image)
    if args.smoke_test:
        root.withdraw()
        if not args.image:p.error('--smoke-test requires --image')
        app.start()
        def done():
            if app.busy:root.after(200,done)
            else:root.quit()
        root.after(200,done);root.after(120000,root.quit);root.mainloop();root.destroy()
        if app.result is None:raise SystemExit('GUI smoke failed')
        print(json.dumps(dict(status='BAŞARILI',pipeline_status=app.result['status'],output=str(app.output)),ensure_ascii=False))
    else:root.mainloop()


if __name__=='__main__':main()
