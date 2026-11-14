"""Main window: wires the input and result panels, background solving and files."""
from datetime import datetime
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from statikai.frame3d import LEGACY_SCHEMAS, SCHEMA, FrameConfig, solve_frame
from .inputs import InputPanel
from .results import ENVELOPE, ResultsPanel
from .theme import STATUS_BG, TEXT, WARNING_BG, WARNING_FG, apply_styles

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work'/'desktop'
SUPPORTED_SCHEMAS=(*LEGACY_SCHEMAS,SCHEMA)

PRESETS={
    'concrete':FrameConfig(),
    'timber':FrameConfig(spans_x_m=(4.,4.),spans_z_m=(4.,),story_heights_m=(3.,3.),
        elastic_modulus_gpa=11.,poisson=.3,unit_weight_kn_m3=5.,
        beam_sections_cm=((20.,40.),),column_sections_cm=((25.,25.),),
        dead_load_kn_m2=1.,live_load_kn_m2=2.,lateral_x_kn_per_floor=5.),
    'irregular':FrameConfig(spans_x_m=(6.,4.5,3.),spans_z_m=(5.,3.5),story_heights_m=(4.,3.,3.,3.),
        beam_sections_cm=((30.,60.),(30.,60.),(25.,50.),(25.,50.)),
        column_sections_cm=((50.,50.),(50.,50.),(40.,60.),(40.,60.)),
        lateral_x_kn_per_floor=40.,lateral_z_kn_per_floor=25.,rigid_diaphragm=True)}

LIMITS_TEXT=('• Ortogonal akslı 3B çubuk çerçeve; açıklık, kat yüksekliği ve kat kat kesit serbest.\n'
    '• Dikdörtgen kesit, rijit birleşimler, birinci mertebe, doğrusal elastik izotrop kabul.\n'
    '• Yük durumları: G (öz ağırlık + döşeme ölü), Q (hareketli), EX, EZ (elle yatay).\n'
    '• Döşeme alan yükleri 45° zarf kuralıyla kirişlere üçgen/trapez yayılı yük olarak aktarılır.\n'
    '• Döşeme plağı eleman olarak yok; plak ağırlığını G içine yazın.\n'
    '• Rijit diyafram: kat düzleminde çok rijit eksenel bağlantılarla yaklaşık modellenir.\n'
    '• Kat yatay yükleri düğümlere plan tesir alanına göre dağıtılır.\n'
    '• Hareketli yük dama (pattern) düzeninde uygulanmaz.\n'
    '• Varsayılan kombinasyonlar TS 500 / TBDY 2018 biçimindedir; E elle girilen kuvvettir, '
    'deprem yükü ve %30 dik yön kuralı üretilmez.\n'
    '• Kat ötelemeleri elastik değerlerdir; TBDY etkin öteleme kontrolü değildir.\n'
    '• Perde, zemin ve P-Delta hesabı yok; betonarme/ahşap boyutlandırması yapılmaz.\n'
    '• Fotoğraftan 3B geometri, malzeme, kesit veya yük okunmaz.\n'
    '• Gerçek yapı güvenliği kararı için kullanılmaz.')


class StatikApp:
    def __init__(self,root,smoke=False):
        WORK.mkdir(parents=True,exist_ok=True)
        self.root=root;self.smoke=smoke;self.smoke_error=None
        self.busy=False;self.events=queue.Queue()
        root.title('StatikAI — 3B Çerçeve Analizi')
        root.geometry(f'{min(1420,root.winfo_screenwidth()-80)}x{min(920,root.winfo_screenheight()-100)}')
        root.minsize(min(1100,root.winfo_screenwidth()-80),min(700,root.winfo_screenheight()-100))
        if os.name=='nt':
            root.after(150,lambda:root.state('zoomed'))
        apply_styles(root)
        header=ttk.Frame(root,padding=(20,12));header.pack(fill='x')
        ttk.Label(header,text='StatikAI',style='Title.TLabel').pack(side='left')
        ttk.Label(header,text='3B çerçeve analizi  |  Doğrusal elastik araştırma prototipi',
                  foreground=TEXT).pack(side='left',padx=22)
        ttk.Button(header,text='Kiriş sembol demosu',command=self.open_symbol_demo).pack(side='right')
        ttk.Label(root,text='ÖRNEK MODEL • Resimlerden model çıkarılmadı. Ölçü, kesit ve yükler aşağıdan tanımlanır.',
                  foreground=WARNING_FG,padding=(20,6),background=WARNING_BG).pack(fill='x')
        body=ttk.Panedwindow(root,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=10)
        left=ttk.Frame(body,width=385);right=ttk.Frame(body)
        body.add(left,weight=0);body.add(right,weight=1)
        self.status=tk.StringVar(value='Örnek model hazırlanıyor…')
        self.results=ResultsPanel(right)
        self.inputs=InputPanel(left,self)
        ttk.Label(root,textvariable=self.status,anchor='w',padding=(16,8),background=STATUS_BG).pack(fill='x')
        root.after(100,self.poll)
        root.after(350,self.calculate)

    # ---- inputs -------------------------------------------------------
    def inputs_changed(self):
        if self.busy:
            return
        self.inputs.export_button.state(['disabled'])
        self.results.clear('Parametreler değişti — önceki hesap sonuçları temizlendi.')
        self.status.set('Yeni sonuç için 3B HESAPLA düğmesine basın.')

    def preset(self,name):
        if self.busy:
            return
        self.inputs.apply_config(PRESETS[name]);self.calculate()

    # ---- solving ------------------------------------------------------
    def calculate(self):
        if self.busy:
            return
        try:
            config=self.inputs.read_config()
        except (ValueError,OverflowError) as error:
            messagebox.showerror('Girdi kontrolü',str(error),parent=self.root);return
        self.busy=True;self.inputs.set_busy(True)
        self.status.set(f'3B model çözülüyor — {len(config.load_combinations())} kombinasyon…')
        def worker():
            try:
                self.events.put(('success',solve_frame(config,return_model=True)))
            except Exception as error:
                (WORK/'son_hata.log').write_text(traceback.format_exc(),encoding='utf8')
                self.events.put(('error',str(error)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            state,payload=self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy=False;self.inputs.set_busy(False)
            if state=='success':
                self.on_solved(*payload)
            else:
                self.on_failed(payload)
        if self.root.winfo_exists():
            self.root.after(100,self.poll)

    def on_solved(self,model,result):
        self.results.show(model,result)
        rf=max(abs(v) for v in result['force_residual_kn']);rm=max(abs(v) for v in result['moment_residual_knm'])
        self.status.set(f"Hesaplandı: {result['elapsed_seconds']:.2f} s  |  En büyük denge artıkları (tüm kombinasyonlar): "
                        f"{rf:.2e} kN / {rm:.2e} kNm  |  Kullanıcı/örnek modeli")
        self.inputs.export_button.state(['!disabled'])
        (WORK/'son_sonuc.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
        if self.smoke:
            self.finish_smoke()

    def on_failed(self,message):
        self.results.clear('Hesap tamamlanamadı.')
        self.status.set('Hesap tamamlanamadı: '+message)
        if self.smoke:
            self.smoke_error=message;self.root.after(50,self.root.destroy)
        else:
            messagebox.showerror('Hesap tamamlanamadı',message,parent=self.root)

    # ---- files --------------------------------------------------------
    def _write(self,target,text):
        try:
            Path(target).write_text(text,encoding='utf8');return True
        except OSError as error:
            messagebox.showerror('Dosya yazılamadı',str(error),parent=self.root);return False

    def save_model(self):
        if self.busy:
            return
        try:
            config=self.inputs.read_config()
        except ValueError as error:
            messagebox.showerror('Girdi',str(error),parent=self.root);return
        target=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',initialfile='statikai_model.json',
                                            filetypes=[('StatikAI modeli','*.json')])
        if target:
            self._write(target,json.dumps(dict(schema=SCHEMA,config=config.to_dict()),indent=2,ensure_ascii=False))

    def load_model(self):
        if self.busy:
            return
        target=filedialog.askopenfilename(parent=self.root,filetypes=[('StatikAI modeli','*.json')])
        if not target:
            return
        try:
            data=json.loads(Path(target).read_text(encoding='utf-8-sig'))
            if data.get('schema') not in SUPPORTED_SCHEMAS:
                raise ValueError('Desteklenen StatikAI model dosyası değil.')
            config=FrameConfig.from_dict(data['config']);config.validate()
        except Exception as error:
            messagebox.showerror('Model açılamadı',str(error),parent=self.root);return
        self.inputs.apply_config(config);self.calculate()

    def export_results(self):
        if not self.results.result:
            return
        target=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',
                                            initialfile='statikai_hesap_sonucu.json',filetypes=[('JSON sonuçları','*.json')])
        if target:
            self._write(target,json.dumps(self.results.result,indent=2,ensure_ascii=False,allow_nan=False))

    def show_limits(self):
        messagebox.showinfo('Kapsam ve varsayımlar',LIMITS_TEXT,parent=self.root)

    def open_symbol_demo(self):
        subprocess.Popen([sys.executable,str(ROOT/'demo_baslat.py')],cwd=ROOT)

    # ---- automated GUI check -----------------------------------------
    def finish_smoke(self):
        r=self.results;root=self.root
        root.update_idletasks()
        visited=[]
        for index in range(r.tabs.index('end')):
            r.tabs.select(index);root.update_idletasks()
            visited.append(r.tabs.tab(index,'text'))
        assert len(r.drifts_tree.get_children())==len(r.result['config']['story_heights_m'])
        assert len(r.drift_axis.lines)==3
        r.members_tree.selection_set(r.members_tree.get_children()[-1]);r.plot_diagram()
        assert len(r.diagram_axis.lines[-1].get_xdata())==31
        names=r.combo_names()
        r.combo_var.set(names[1]);r.refresh()
        assert r.members_tree.set(r.members_tree.get_children()[0],'gov')==names[1]
        r.members_tree.selection_set(r.members_tree.get_children()[-1]);r.plot_diagram()
        assert len(r.diagram_axis.lines[-1].get_xdata())==31
        r.deformed.set(True);r.plot_model();root.update_idletasks()
        assert len(r.axis.lines)==2*len(r.result['members'])
        r.deformed.set(False);r.combo_var.set(ENVELOPE);r.refresh();r.tabs.select(0)
        report=dict(success=True,nodes_rows=len(r.nodes_tree.get_children()),
            members_rows=len(r.members_tree.get_children()),reaction_rows=len(r.reactions_tree.get_children()),
            drift_rows=len(r.drifts_tree.get_children()),combinations=names,
            max_displacement_mm=r.result['max_displacement_mm'],visited_tabs=visited,diagram_points=31,
            deformed_overlay_verified=True,window_geometry=root.geometry(),window_state=root.state(),
            source='example_parameters_not_photos',time=datetime.now().isoformat())
        r.figure.savefig(WORK/'StatikAI_3B_Model.png',dpi=140)
        (ROOT/'audit_results').mkdir(exist_ok=True)
        (ROOT/'audit_results'/'desktop_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        root.after(300,root.destroy)
