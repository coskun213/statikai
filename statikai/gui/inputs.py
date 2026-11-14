"""Left-hand parameter panel: geometry, materials, sections, loads, combinations."""
import tkinter as tk
from tkinter import ttk, messagebox

from statikai.frame3d import FrameConfig, default_combinations
from .parsing import (format_combinations, format_lengths, format_sections, parse_combinations,
                      parse_lengths, parse_sections)
from .theme import MUTED, TEXT

# (key, label, default, kind) -- kind: 'lengths' | 'sections' | 'number'
FIELDS=[
    ('Geometri (ayırıcı ;  tekrar 3@5)',[
        ('spans_x_m','X açıklıkları (m)','5;5','lengths'),
        ('spans_z_m','Z açıklıkları (m)','4;4','lengths'),
        ('story_heights_m','Kat yükseklikleri, alttan (m)','6@3','lengths')]),
    ('Malzeme — kullanıcı tanımlı',[
        ('elastic_modulus_gpa','Elastisite modülü E (GPa)','30','number'),
        ('poisson','Poisson oranı','0.2','number'),
        ('unit_weight_kn_m3','Birim hacim ağırlığı (kN/m³)','25','number')]),
    ('Kesitler (cm), tek değer ya da kat kat',[
        ('beam_sections_cm','Kiriş b×h','30x50','sections'),
        ('column_sections_cm','Kolon X×Z boyutu','40x40','sections')]),
    ('Yük durumları',[
        ('dead_load_kn_m2','G: döşeme ölü yükü, plak dahil (kN/m²)','4.5','number'),
        ('live_load_kn_m2','Q: hareketli yük (kN/m²)','2','number'),
        ('lateral_x_kn_per_floor','EX: her kata yatay X yükü (kN)','30','number'),
        ('lateral_z_kn_per_floor','EZ: her kata yatay Z yükü (kN)','0','number')])]

LABELS={key:label for _,fields in FIELDS for key,label,_,_ in fields}
SUPPORTS={'Ankastre':'fixed','Mafsallı':'pinned'}


def _float(text,label):
    try:
        return float(text.strip().replace(',','.'))
    except ValueError:
        raise ValueError(f'{label}: sayı girilmeli.') from None


class InputPanel:
    def __init__(self,parent,app):
        self.app=app
        self.vars={};self.kinds={};self.controls=[]
        self.custom_combos=None
        self.muted=True
        top=ttk.Frame(parent,padding=(6,0,6,8));top.pack(fill='x')
        ttk.Label(top,text='Model parametreleri',style='Group.TLabel').pack(anchor='w')
        presets=ttk.Frame(top);presets.pack(fill='x',pady=5)
        ttk.Button(presets,text='Örnek beton',command=lambda:app.preset('concrete')).pack(side='left',expand=True,fill='x')
        ttk.Button(presets,text='Örnek ahşap',command=lambda:app.preset('timber')).pack(side='left',expand=True,fill='x',padx=(4,0))
        ttk.Button(presets,text='Düzensiz örnek',command=lambda:app.preset('irregular')).pack(side='left',expand=True,fill='x',padx=(4,0))
        self.calc_button=ttk.Button(top,text='3B HESAPLA',style='Action.TButton',command=app.calculate)
        self.calc_button.pack(fill='x',pady=(4,0))
        self.progress=ttk.Progressbar(top,mode='indeterminate');self.progress.pack(fill='x',pady=(5,0))
        content=self._scrollable(parent)
        for title,fields in FIELDS:
            ttk.Label(content,text=title,style='Group.TLabel').pack(anchor='w',pady=(10,6))
            for key,label,default,kind in fields:
                row=ttk.Frame(content);row.pack(fill='x',pady=3)
                ttk.Label(row,text=label).pack(side='left')
                variable=tk.StringVar(value=default)
                variable.trace_add('write',self.changed)
                self.vars[key]=variable;self.kinds[key]=kind
                entry=ttk.Entry(row,textvariable=variable,width=9 if kind=='number' else 16,justify='right')
                entry.pack(side='right');self.controls.append(entry)
        ttk.Label(content,text='Kolon kesiti: 1. değer global X, 2. değer global Z yönündeki boyut. '
                  'Kat kat girişte sıra alttan üste.',foreground=MUTED,wraplength=320).pack(anchor='w',pady=(4,0))
        self.self_weight=tk.BooleanVar(value=True)
        self.rigid_diaphragm=tk.BooleanVar(value=False)
        for text,variable in (('Kolon/kiriş öz ağırlığını G durumuna ekle',self.self_weight),
                              ('Rijit diyafram (her kat kendi düzleminde rijit)',self.rigid_diaphragm)):
            variable.trace_add('write',self.changed)
            check=ttk.Checkbutton(content,text=text,variable=variable)
            check.pack(anchor='w',pady=(8,0));self.controls.append(check)
        ttk.Label(content,text='Yük kombinasyonları',style='Group.TLabel').pack(anchor='w',pady=(12,4))
        self.combo_info=tk.StringVar()
        ttk.Label(content,textvariable=self.combo_info,foreground=TEXT,wraplength=320).pack(anchor='w')
        button=ttk.Button(content,text='Kombinasyonları düzenle…',command=self.edit_combinations)
        button.pack(fill='x',pady=(4,0));self.controls.append(button)
        ttk.Label(content,text='Taban mesneti',style='Group.TLabel').pack(anchor='w',pady=(10,4))
        self.support=tk.StringVar(value='Ankastre');self.support.trace_add('write',self.changed)
        combo=ttk.Combobox(content,textvariable=self.support,values=list(SUPPORTS),state='readonly')
        combo.pack(fill='x');self.controls.append(combo)
        ttk.Label(content,text='G ve Q alan yükleri 45° zarf kuralıyla kirişlere üçgen/trapez yayılı yük olarak '
                  'aktarılır. Döşeme plağının ağırlığını G içine yazın. Kat yatay yükleri düğümlere plan '
                  'tesir alanına göre dağıtılır.\nEX/EZ elle girilir; deprem yönetmeliği hesabı değildir.',
                  foreground=MUTED,wraplength=320).pack(anchor='w',pady=12)
        files=ttk.Frame(content);files.pack(fill='x',pady=8)
        ttk.Button(files,text='Model aç',command=app.load_model).pack(side='left',fill='x',expand=True)
        ttk.Button(files,text='Model kaydet',command=app.save_model).pack(side='left',fill='x',expand=True,padx=4)
        self.export_button=ttk.Button(content,text='Sonuçları dışa aktar',command=app.export_results,state='disabled')
        self.export_button.pack(fill='x',pady=4)
        ttk.Button(content,text='Kapsam ve varsayımlar',command=app.show_limits).pack(fill='x',pady=4)
        self.muted=False
        self.update_combo_info()

    @staticmethod
    def _scrollable(parent):
        container=ttk.Frame(parent);container.pack(fill='both',expand=True)
        canvas=tk.Canvas(container,background='#f3f6fa',highlightthickness=0,width=370)
        bar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        content=ttk.Frame(canvas,padding=8)
        window=canvas.create_window((0,0),window=content,anchor='nw')
        content.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        return content

    # ---- state --------------------------------------------------------
    def changed(self,*_):
        if self.muted:
            return
        self.update_combo_info()
        self.app.inputs_changed()

    def set_busy(self,busy):
        flag=['disabled'] if busy else ['!disabled']
        self.calc_button.state(flag)
        for control in self.controls:
            control.state(flag)
            if not busy and isinstance(control,ttk.Combobox):
                control.state(['readonly'])
        if busy:
            self.progress.start(12);self.export_button.state(['disabled'])
        else:
            self.progress.stop()

    def lateral_values(self):
        values=[]
        for key in ('lateral_x_kn_per_floor','lateral_z_kn_per_floor'):
            try:
                values.append(float(self.vars[key].get().strip().replace(',','.')))
            except ValueError:
                values.append(0.)
        return values

    def current_combinations(self):
        if self.custom_combos is not None:
            return self.custom_combos
        return default_combinations(*self.lateral_values())

    def update_combo_info(self):
        combos=self.current_combinations()
        kind='Özel tanımlı' if self.custom_combos is not None else 'Otomatik (TS 500 / TBDY 2018)'
        self.combo_info.set(f'{kind}: {len(combos)} kombinasyon — '+', '.join(c[0] for c in combos))

    # ---- config <-> widgets ------------------------------------------
    def read_config(self):
        values={}
        for key,var in self.vars.items():
            text=var.get();label=LABELS[key];kind=self.kinds[key]
            if kind=='lengths':
                values[key]=parse_lengths(text,label)
            elif kind=='sections':
                values[key]=parse_sections(text,label)
            else:
                values[key]=_float(text,label)
        config=FrameConfig(**values,self_weight=self.self_weight.get(),
                           rigid_diaphragm=self.rigid_diaphragm.get(),
                           base_support=SUPPORTS[self.support.get()],combinations=self.custom_combos)
        config.validate()
        return config

    def apply_config(self,config):
        self.muted=True
        for key,var in self.vars.items():
            value=getattr(config,key);kind=self.kinds[key]
            if kind=='lengths':
                var.set(format_lengths(value))
            elif kind=='sections':
                var.set(format_sections(value))
            else:
                var.set(f'{value:g}')
        self.self_weight.set(config.self_weight)
        self.rigid_diaphragm.set(config.rigid_diaphragm)
        self.support.set(next(k for k,v in SUPPORTS.items() if v==config.base_support))
        self.custom_combos=config.combinations
        self.muted=False
        self.changed()

    # ---- combinations dialog ----------------------------------------
    def edit_combinations(self):
        root=self.calc_button.winfo_toplevel()
        dialog=tk.Toplevel(root);dialog.title('Yük kombinasyonları');dialog.transient(root)
        dialog.geometry('560x460');dialog.grab_set()
        frame=ttk.Frame(dialog,padding=12);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Her satır:  ad ; G ; Q ; EX ; EZ   (katsayılar)',style='Group.TLabel').pack(anchor='w')
        ttk.Label(frame,text='G: öz ağırlık + döşeme ölü yükü, Q: hareketli, EX/EZ: elle girilen yatay yükler. '
                  '# ile başlayan satırlar yok sayılır.',foreground=MUTED,wraplength=520).pack(anchor='w',pady=(2,6))
        text=tk.Text(frame,height=14,font=('Consolas',11),undo=True)
        text.pack(fill='both',expand=True)
        text.insert('1.0',format_combinations(self.current_combinations()))
        ttk.Label(frame,text='Varsayılan listeyle aynı bırakılırsa otomatik mod korunur: '
                  'yatay yükler değişince kombinasyonlar yeniden üretilir.',
                  foreground=TEXT,wraplength=520).pack(anchor='w',pady=4)
        def use_default():
            text.delete('1.0','end')
            text.insert('1.0',format_combinations(default_combinations(*self.lateral_values())))
        def apply():
            try:
                combos=parse_combinations(text.get('1.0','end'))
            except ValueError as error:
                messagebox.showerror('Kombinasyon hatası',str(error),parent=dialog);return
            self.custom_combos=None if combos==default_combinations(*self.lateral_values()) else combos
            dialog.destroy();self.changed()
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=(6,0))
        ttk.Button(buttons,text='Varsayılan (TS 500 / TBDY 2018)',command=use_default).pack(side='left')
        ttk.Button(buttons,text='İptal',command=dialog.destroy).pack(side='right')
        ttk.Button(buttons,text='Uygula',command=apply).pack(side='right',padx=6)
