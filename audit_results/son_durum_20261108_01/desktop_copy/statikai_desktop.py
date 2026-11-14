"""Native desktop interface for the explicitly bounded 3D frame prototype."""
import argparse
from dataclasses import asdict
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'work'/'desktop'
WORK.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'work'/'matplotlib'))

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from statikai.frame3d import FrameConfig,build_frame,solve_frame


FIELDS=[
 ('Geometri',[
  ('floors','Kat sayısı','6'),('bays_x','X doğrultusunda açıklık sayısı','2'),
  ('bays_z','Z doğrultusunda açıklık sayısı','2'),('span_x_m','X açıklığı (m)','5'),
  ('span_z_m','Z açıklığı (m)','4'),('story_height_m','Kat yüksekliği (m)','3')]),
 ('Malzeme — kullanıcı tanımlı',[
  ('elastic_modulus_gpa','Elastisite modülü E (GPa)','30'),('poisson','Poisson oranı','0.2'),
  ('unit_weight_kn_m3','Birim hacim ağırlığı (kN/m³)','25')]),
 ('Dikdörtgen kesitler',[
  ('beam_width_cm','Kiriş genişliği b (cm)','30'),('beam_depth_cm','Kiriş yüksekliği h (cm)','50'),
  ('column_width_cm','Kolon boyutu b (cm)','40'),('column_depth_cm','Kolon boyutu h (cm)','40')]),
 ('Yükler — katsayı 1.0',[
  ('floor_load_kn_m2','Her katın alan yükü (kN/m²)','5'),
  ('lateral_x_kn_per_floor','Her kata yatay X yükü (kN)','30'),
  ('lateral_z_kn_per_floor','Her kata yatay Z yükü (kN)','0')])]


class StatikApp:
    def __init__(self,root,smoke=False):
        self.root=root;self.result=None;self.preview=None;self.busy=False
        self.vars={};self.controls=[];self.muted=True;self.events=queue.Queue();self.smoke=smoke
        self.smoke_error=None
        root.title('StatikAI — 3B Çerçeve Analizi')
        root.geometry(f'{min(1420,root.winfo_screenwidth()-80)}x{min(920,root.winfo_screenheight()-100)}')
        root.minsize(min(1100,root.winfo_screenwidth()-80),min(700,root.winfo_screenheight()-100))
        if os.name=='nt': root.after(150,lambda:root.state('zoomed'))
        style=ttk.Style(root);style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background='#f3f6fa')
        style.configure('TFrame',background='#f3f6fa')
        style.configure('Title.TLabel',font=('Segoe UI',22,'bold'),foreground='#12304b')
        style.configure('Group.TLabel',font=('Segoe UI',11,'bold'),foreground='#12304b')
        style.configure('Action.TButton',font=('Segoe UI',12,'bold'),padding=9,background='#176d9c',foreground='white')
        style.configure('Treeview',rowheight=25,fieldbackground='white',background='white')
        style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'))
        header=ttk.Frame(root,padding=(20,12));header.pack(fill='x')
        ttk.Label(header,text='StatikAI',style='Title.TLabel').pack(side='left')
        ttk.Label(header,text='3B çerçeve analizi  |  Doğrusal elastik araştırma prototipi',
                  foreground='#40566c').pack(side='left',padx=22)
        ttk.Button(header,text='Kiriş sembol demosu',command=self.open_symbol_demo).pack(side='right')
        ttk.Label(root,text='ÖRNEK MODEL • Resimlerden model çıkarılmadı. Ölçü, kesit ve yükler aşağıdan tanımlanır.',
                  foreground='#944c00',padding=(20,6),background='#fff3d5').pack(fill='x')
        body=ttk.Panedwindow(root,orient='horizontal');body.pack(fill='both',expand=True,padx=12,pady=10)
        left=ttk.Frame(body,width=365);right=ttk.Frame(body)
        body.add(left,weight=0);body.add(right,weight=1)
        self._make_parameters(left)
        self._make_results(right)
        self.status=tk.StringVar(value='Örnek model hazırlanıyor…')
        ttk.Label(root,textvariable=self.status,anchor='w',padding=(16,8),background='#e3edf6').pack(fill='x')
        self.muted=False
        self.root.after(100,self.poll)
        self.root.after(350,self.calculate)

    def _make_parameters(self,parent):
        top=ttk.Frame(parent,padding=(6,0,6,8));top.pack(fill='x')
        ttk.Label(top,text='Model parametreleri',style='Group.TLabel').pack(anchor='w')
        buttons=ttk.Frame(top);buttons.pack(fill='x',pady=5)
        ttk.Button(buttons,text='Örnek beton',command=lambda:self.preset('concrete')).pack(side='left',expand=True,fill='x')
        ttk.Button(buttons,text='Örnek ahşap',command=lambda:self.preset('timber')).pack(side='left',expand=True,fill='x',padx=(4,0))
        self.calc_button=ttk.Button(top,text='3B HESAPLA',style='Action.TButton',command=self.calculate)
        self.calc_button.pack(fill='x',pady=(4,0))
        self.progress=ttk.Progressbar(top,mode='indeterminate');self.progress.pack(fill='x',pady=(5,0))
        container=ttk.Frame(parent);container.pack(fill='both',expand=True)
        canvas=tk.Canvas(container,background='#f3f6fa',highlightthickness=0,width=350)
        bar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas,padding=8);window=canvas.create_window((0,0),window=content,anchor='nw')
        content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        for title,fields in FIELDS:
            ttk.Label(content,text=title,style='Group.TLabel').pack(anchor='w',pady=(10,6))
            for key,label,default in fields:
                row=ttk.Frame(content);row.pack(fill='x',pady=3)
                ttk.Label(row,text=label).pack(side='left')
                variable=tk.StringVar(value=default)
                self.vars[key]=variable;variable.trace_add('write',self.mark_dirty)
                entry=ttk.Entry(row,textvariable=variable,width=9,justify='right')
                entry.pack(side='right');self.controls.append(entry)
        self.self_weight=tk.BooleanVar(value=True)
        self.self_weight.trace_add('write',self.mark_dirty)
        check=ttk.Checkbutton(content,text='Kolon/kiriş öz ağırlığını ekle',variable=self.self_weight)
        check.pack(anchor='w',pady=(15,5));self.controls.append(check)
        ttk.Label(content,text='Taban mesneti',style='Group.TLabel').pack(anchor='w',pady=(10,4))
        self.support=tk.StringVar(value='Ankastre');self.support.trace_add('write',self.mark_dirty)
        combo=ttk.Combobox(content,textvariable=self.support,values=['Ankastre','Mafsallı'],state='readonly')
        combo.pack(fill='x');self.controls.append(combo)
        ttk.Label(content,text='Alan yükleri düğümlere dağıtılır; döşeme yükünün kirişte oluşturduğu eğilme bu modelde yoktur.\nYatay yükler elle girilir; deprem yönetmeliği hesabı değildir.',
                  foreground='#53697c',wraplength=320).pack(anchor='w',pady=12)
        files=ttk.Frame(content);files.pack(fill='x',pady=8)
        ttk.Button(files,text='Model aç',command=self.load_model).pack(side='left',fill='x',expand=True)
        ttk.Button(files,text='Model kaydet',command=self.save_model).pack(side='left',fill='x',expand=True,padx=4)
        self.export_button=ttk.Button(content,text='Sonuçları dışa aktar',command=self.export_results,state='disabled')
        self.export_button.pack(fill='x',pady=4)
        ttk.Button(content,text='Kapsam ve varsayımlar',command=self.show_limits).pack(fill='x',pady=4)

    def _tree(self,parent,columns):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
        tree=ttk.Treeview(frame,columns=[key for key,label in columns],show='headings')
        for key,label in columns:
            tree.heading(key,text=label);tree.column(key,width=110,anchor='e',stretch=True)
        bar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
        tree.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
        return tree

    def _make_results(self,parent):
        self.summary=tk.StringVar(value='Geometri ve yükleri kontrol edip hesaplayın.')
        ttk.Label(parent,textvariable=self.summary,font=('Segoe UI',12,'bold'),padding=9,foreground='#12304b').pack(fill='x')
        self.tabs=ttk.Notebook(parent);self.tabs.pack(fill='both',expand=True)
        self.view=ttk.Frame(self.tabs);self.tabs.add(self.view,text='3B Model')
        controls=ttk.Frame(self.view);controls.pack(fill='x',pady=5)
        self.deformed=tk.BooleanVar(value=False)
        ttk.Checkbutton(controls,text='Büyütülmüş düğüm deplasmanlarını göster',variable=self.deformed,
                        command=self.plot_model).pack(side='left')
        ttk.Label(controls,text='Ölçek:').pack(side='left',padx=(18,5))
        self.scale=tk.StringVar(value='100')
        scale=ttk.Entry(controls,textvariable=self.scale,width=7);scale.pack(side='left')
        scale.bind('<Return>',lambda e:self.plot_model())
        ttk.Button(controls,text='Görünümü yenile',command=self.plot_model).pack(side='left',padx=5)
        self.figure=Figure(figsize=(8,6),dpi=100,facecolor='white')
        self.axis=self.figure.add_subplot(111,projection='3d')
        self.canvas=FigureCanvasTkAgg(self.figure,master=self.view)
        self.canvas.get_tk_widget().pack(fill='both',expand=True)
        NavigationToolbar2Tk(self.canvas,self.view)
        ttk.Label(self.view,text='Fareyle döndürün • Tekerlek/araç çubuğuyla yakınlaştırın • Düşey eksen global Y',
                  foreground='#53697c').pack(fill='x',padx=8,pady=4)
        nodes=ttk.Frame(self.tabs);self.tabs.add(nodes,text='Düğüm Deplasmanları')
        self.nodes_tree=self._tree(nodes,[('node','Düğüm'),('floor','Kat'),('dx','DX (mm)'),('dy','DY (mm)'),('dz','DZ (mm)'),('norm','Toplam (mm)')])
        reactions=ttk.Frame(self.tabs);self.tabs.add(reactions,text='Mesnet Tepkileri')
        self.reactions_tree=self._tree(reactions,[('node','Düğüm'),('fx','FX (kN)'),('fy','FY (kN)'),('fz','FZ (kN)'),('mx','MX (kNm)'),('my','MY (kNm)'),('mz','MZ (kNm)')])
        members=ttk.Frame(self.tabs);self.tabs.add(members,text='Eleman Kuvvetleri')
        split=ttk.Panedwindow(members,orient='vertical');split.pack(fill='both',expand=True)
        listing=ttk.Frame(split);diagram=ttk.Frame(split)
        split.add(listing,weight=1);split.add(diagram,weight=1)
        self.members_tree=self._tree(listing,[('name','Eleman'),('type','Tür'),('length','L (m)'),('n','|N|max kN'),('vy','|Vy|max kN'),('vz','|Vz|max kN'),('my','|My|max kNm'),('mz','|Mz|max kNm'),('t','|T|max kNm')])
        self.members_tree.bind('<<TreeviewSelect>>',lambda e:self.plot_diagram())
        picker=ttk.Frame(diagram);picker.pack(fill='x',pady=4)
        ttk.Label(picker,text='Seçili elemanın diyagramı:').pack(side='left')
        self.quantity=tk.StringVar(value='Mz')
        choice=ttk.Combobox(picker,textvariable=self.quantity,values=['N','Vy','Vz','My','Mz','T'],state='readonly',width=7)
        choice.pack(side='left',padx=7);choice.bind('<<ComboboxSelected>>',lambda e:self.plot_diagram())
        ttk.Label(picker,text='Yerel eleman eksenleri; işaretler PyNite tanımına göre',foreground='#53697c').pack(side='left')
        self.diagram_figure=Figure(figsize=(8,3),dpi=100,facecolor='white')
        self.diagram_axis=self.diagram_figure.add_subplot(111)
        self.diagram_canvas=FigureCanvasTkAgg(self.diagram_figure,master=diagram)
        self.diagram_canvas.get_tk_widget().pack(fill='both',expand=True)

    def read_config(self):
        values={}
        for key,var in self.vars.items():
            text=var.get().strip().replace(',','.')
            if key in ('floors','bays_x','bays_z'):
                value=float(text)
                if not value.is_integer(): raise ValueError('Kat ve açıklık sayıları tam sayı olmalı.')
                values[key]=int(value)
            else: values[key]=float(text)
        config=FrameConfig(**values,self_weight=self.self_weight.get(),
                           base_support='fixed' if self.support.get()=='Ankastre' else 'pinned')
        config.validate();return config

    def mark_dirty(self,*args):
        if self.muted or self.busy: return
        self.result=None;self.preview=None;self.export_button.state(['disabled'])
        self.summary.set('Parametreler değişti — önceki hesap sonuçları temizlendi.')
        self.status.set('Yeni sonuç için 3B HESAPLA düğmesine basın.')
        for tree in (self.nodes_tree,self.members_tree,self.reactions_tree):
            tree.delete(*tree.get_children())
        self.diagram_axis.clear();self.diagram_canvas.draw_idle()
        self.axis.clear();self.axis.set_title('Parametreler değişti — 3B HESAPLA ile yenileyin')
        self.canvas.draw_idle()

    def preset(self,name):
        if self.busy: return
        config=FrameConfig() if name=='concrete' else FrameConfig(floors=2,bays_x=2,bays_z=1,
            span_x_m=4,span_z_m=4,elastic_modulus_gpa=11,poisson=.3,unit_weight_kn_m3=5,
            beam_width_cm=20,beam_depth_cm=40,column_width_cm=25,column_depth_cm=25,
            floor_load_kn_m2=3,lateral_x_kn_per_floor=5)
        self.apply_config(asdict(config));self.calculate()

    def apply_config(self,values):
        self.muted=True
        for key,var in self.vars.items(): var.set(str(values[key]))
        self.self_weight.set(values['self_weight'])
        self.support.set('Ankastre' if values['base_support']=='fixed' else 'Mafsallı')
        self.muted=False;self.mark_dirty()

    def calculate(self):
        if self.busy: return
        try: config=self.read_config()
        except (ValueError,OverflowError) as error:
            messagebox.showerror('Girdi kontrolü',str(error),parent=self.root);return
        self.busy=True;self.calc_button.state(['disabled']);self.export_button.state(['disabled'])
        for control in self.controls: control.state(['disabled'])
        self.progress.start(12);self.status.set('3B model çözülüyor…')
        def worker():
            try: self.events.put(('success',solve_frame(config)))
            except Exception as error:
                (WORK/'son_hata.log').write_text(traceback.format_exc(),encoding='utf8')
                self.events.put(('error',str(error)))
        threading.Thread(target=worker,daemon=True).start()

    def poll(self):
        try:
            state,payload=self.events.get_nowait()
            self.busy=False;self.progress.stop();self.calc_button.state(['!disabled'])
            for control in self.controls: control.state(['!disabled'])
            # Restore the support combobox to selection-only editing.
            for control in self.controls:
                if isinstance(control,ttk.Combobox): control.state(['readonly'])
            if state=='success':
                self.result=payload;self.preview=payload;self.show_result()
                if self.smoke: self.finish_smoke()
            else:
                self.result=None;self.status.set('Hesap tamamlanamadı: '+payload)
                if self.smoke:
                    self.smoke_error=payload;self.root.after(50,self.root.destroy)
                else: messagebox.showerror('Hesap tamamlanamadı',payload,parent=self.root)
        except queue.Empty: pass
        if self.root.winfo_exists(): self.root.after(100,self.poll)

    def show_result(self):
        r=self.result
        self.summary.set(f"{len(r['nodes'])} düğüm  •  {len(r['members'])} eleman  •  En büyük düğüm deplasmanı: {r['max_displacement_mm']:.3f} mm")
        rf=max(abs(v) for v in r['force_residual_kn']);rm=max(abs(v) for v in r['moment_residual_knm'])
        self.status.set(f"Hesaplandı: {r['elapsed_seconds']:.2f} s  |  Denge artıkları: {rf:.2e} kN / {rm:.2e} kNm  |  Kullanıcı/örnek modeli")
        for tree in (self.nodes_tree,self.members_tree,self.reactions_tree): tree.delete(*tree.get_children())
        for d in r['displacements']:
            norm=math.sqrt(sum(d[k]**2 for k in ('dx_mm','dy_mm','dz_mm')))
            self.nodes_tree.insert('', 'end',values=[d['node'],d['floor'],*[f'{d[k]:.5f}' for k in ('dx_mm','dy_mm','dz_mm')],f'{norm:.5f}'])
        for d in r['reactions']:
            self.reactions_tree.insert('', 'end',values=[d['node'],*[f'{d[k]:.4f}' for k in ('fx_kn','fy_kn','fz_kn','mx_knm','my_knm','mz_knm')]])
        for item in r['member_results']:
            self.members_tree.insert('', 'end',iid=item['name'],values=[item['name'],'Kolon' if item['kind']=='column' else 'Kiriş',f"{item['length_m']:.2f}",*[f"{item['peak_abs'][k]:.3f}" for k in ('N','Vy','Vz','My','Mz','T')]])
        self.export_button.state(['!disabled']);self.plot_model()
        first=self.members_tree.get_children()
        if first: self.members_tree.selection_set(first[0]);self.plot_diagram()
        (WORK/'son_sonuc.json').write_text(json.dumps(r,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')

    def plot_model(self):
        data=self.result or self.preview
        if not data: return
        ax=self.axis;ax.clear()
        nodes={n['name']:n for n in data['nodes']}
        displacements={n['node']:n for n in data.get('displacements',[])}
        try: scale=float(self.scale.get().replace(',','.'))
        except ValueError: scale=100.
        if not math.isfinite(scale) or abs(scale)>1e5: scale=100.
        for item in data['members']:
            ends=[nodes[item['i']],nodes[item['j']]]
            color='#c43b42' if item['kind']=='column' else '#1d6b9a'
            ax.plot([v['x'] for v in ends],[v['z'] for v in ends],[v['y'] for v in ends],color=color,linewidth=2.2)
            if self.result and self.deformed.get():
                moved=[]
                for n in ends:
                    d=displacements[n['name']]
                    moved.append((n['x']+scale*d['dx_mm']/1000,n['z']+scale*d['dz_mm']/1000,n['y']+scale*d['dy_mm']/1000))
                ax.plot(*zip(*moved),color='#e59b27',linewidth=1.4,linestyle='--')
        bases=[n for n in nodes.values() if n['base']]
        ax.scatter([n['x'] for n in bases],[n['z'] for n in bases],[n['y'] for n in bases],marker='^',s=32,color='#263e51')
        ax.set_xlabel('X (m)');ax.set_ylabel('Z (m)');ax.set_zlabel('Y / yükseklik (m)')
        config=data['config']
        ax.set_box_aspect([config['bays_x']*config['span_x_m'],config['bays_z']*config['span_z_m'],config['floors']*config['story_height_m']])
        ax.view_init(elev=24,azim=-53)
        ax.set_title('Örnek/kullanıcı modeli — resimden türetilmedi',fontsize=11,pad=12)
        self.figure.subplots_adjust(left=.02,right=.94,bottom=.06,top=.90);self.canvas.draw_idle()

    def plot_diagram(self):
        if not self.result: return
        selected=self.members_tree.selection()
        if not selected: return
        item=next(v for v in self.result['member_results'] if v['name']==selected[0])
        quantity=self.quantity.get();x,y=item['diagrams'][quantity]
        ax=self.diagram_axis;ax.clear();ax.axhline(0,color='#718192',linewidth=.8)
        ax.plot(x,y,color='#176d9c',linewidth=2);ax.fill_between(x,y,0,color='#176d9c',alpha=.15)
        ax.set_title(f"{item['name']} — {quantity}",fontsize=11)
        ax.set_xlabel('Eleman boyunca x (m)');ax.set_ylabel('kN' if quantity in ('N','Vy','Vz') else 'kNm')
        ax.grid(alpha=.2);self.diagram_figure.tight_layout();self.diagram_canvas.draw_idle()

    def save_model(self):
        if self.busy: return
        try: config=self.read_config()
        except ValueError as error: messagebox.showerror('Girdi',str(error));return
        target=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',initialfile='statikai_model.json',filetypes=[('StatikAI modeli','*.json')])
        if target: Path(target).write_text(json.dumps(dict(schema='statikai_regular_frame_v1',config=asdict(config)),indent=2,ensure_ascii=False),encoding='utf8')

    def load_model(self):
        if self.busy: return
        target=filedialog.askopenfilename(parent=self.root,filetypes=[('StatikAI modeli','*.json')])
        if not target: return
        try:
            data=json.loads(Path(target).read_text(encoding='utf-8-sig'))
            if data.get('schema')!='statikai_regular_frame_v1': raise ValueError('Desteklenen StatikAI model dosyası değil.')
            config=FrameConfig(**data['config']);config.validate()
            self.apply_config(asdict(config));self.calculate()
        except Exception as error: messagebox.showerror('Model açılamadı',str(error),parent=self.root)

    def export_results(self):
        if not self.result: return
        target=filedialog.asksaveasfilename(parent=self.root,defaultextension='.json',initialfile='statikai_hesap_sonucu.json',filetypes=[('JSON sonuçları','*.json')])
        if target: Path(target).write_text(json.dumps(self.result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')

    def show_limits(self):
        messagebox.showinfo('Kapsam ve varsayımlar',
            '• Düzenli akslı 3B çubuk çerçeve; dikdörtgen kesit ve rijit birleşimler.\n'
            '• Birinci mertebe, küçük deplasman ve izotrop doğrusal elastik kabul.\n'
            '• Döşeme/perde/rijit diyafram, zemin ve P-Delta hesabı yok.\n'
            '• Alan yükleri düğümlere tesir alanıyla eşdeğerlenir.\n'
            '• Döşeme yükünün kirişte oluşturduğu eğilme hesaplanmaz.\n'
            '• Deprem yönetmeliği ve betonarme/ahşap boyutlandırması yapılmaz.\n'
            '• Ahşap örneği de izotrop idealizasyondur.\n'
            '• Fotoğraftan 3B geometri, malzeme, kesit veya yük okunmaz.\n'
            '• Gerçek yapı güvenliği kararı için kullanılmaz.',parent=self.root)

    def open_symbol_demo(self):
        subprocess.Popen([sys.executable,str(ROOT/'demo_baslat.py')],cwd=ROOT)

    def finish_smoke(self):
        self.root.update_idletasks()
        visited=[]
        for index in range(4):
            self.tabs.select(index);self.root.update_idletasks()
            visited.append(self.tabs.tab(index,'text'))
        self.members_tree.selection_set(self.members_tree.get_children()[-1]);self.plot_diagram()
        self.deformed.set(True);self.plot_model();self.root.update_idletasks()
        assert len(self.diagram_axis.lines[-1].get_xdata())==31
        assert len(self.axis.lines)==2*len(self.result['members'])
        self.deformed.set(False);self.plot_model();self.tabs.select(0)
        report=dict(success=True,nodes_rows=len(self.nodes_tree.get_children()),
            members_rows=len(self.members_tree.get_children()),reaction_rows=len(self.reactions_tree.get_children()),
            max_displacement_mm=self.result['max_displacement_mm'],
            visited_tabs=visited,diagram_points=31,deformed_overlay_verified=True,
            window_geometry=self.root.geometry(),window_state=self.root.state(),
            source='example_parameters_not_photos',time=datetime.now().isoformat())
        self.figure.savefig(ROOT.parent/'StatikAI_3B_Model.png',dpi=140)
        (ROOT/'audit_results/desktop_smoke.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        self.root.after(300,self.root.destroy)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke-test',action='store_true')
    args=parser.parse_args();root=tk.Tk();app=StatikApp(root,args.smoke_test)
    root.mainloop()
    if app.smoke_error: raise RuntimeError(app.smoke_error)


if __name__=='__main__':
    try: main()
    except Exception:
        text=traceback.format_exc();(WORK/'baslatma_hatasi.log').write_text(text,encoding='utf8')
        try: messagebox.showerror('StatikAI başlatılamadı','Hata kaydı: '+str(WORK/'baslatma_hatasi.log'))
        except Exception: pass
        raise
