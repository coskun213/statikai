"""Right-hand result panel: 3D view, tables, member diagrams and storey drifts."""
import math
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from statikai.frame3d import QUANTITIES, member_diagram
from .theme import ACCENT, BEAM, COLUMN, DEFORMED, HEADING, MUTED, OVER_LIMIT_BG, WARNING_FG

ENVELOPE='Zarf (tüm kombinasyonlar)'
DISPLACEMENT_KEYS=('dx_mm','dy_mm','dz_mm')
REACTION_KEYS=('fx_kn','fy_kn','fz_kn','mx_knm','my_knm','mz_knm')
DEFAULT_DRIFT_LIMIT='0.008'


def make_tree(parent,columns):
    frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
    tree=ttk.Treeview(frame,columns=[key for key,_ in columns],show='headings')
    for key,label in columns:
        tree.heading(key,text=label);tree.column(key,width=110,anchor='e',stretch=True)
    bar=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
    tree.configure(yscrollcommand=bar.set)
    bar.pack(side='right',fill='y');tree.pack(fill='both',expand=True)
    return tree


def ratio_text(ratio):
    return f'{ratio:.5f}  (1/{1/ratio:.0f})' if ratio>0 else '0'


class ResultsPanel:
    def __init__(self,parent):
        self.result=None;self.model=None;self.preview=None
        self.summary=tk.StringVar(value='Geometri ve yükleri kontrol edip hesaplayın.')
        ttk.Label(parent,textvariable=self.summary,font=('Segoe UI',12,'bold'),padding=9,
                  foreground=HEADING).pack(fill='x')
        selector=ttk.Frame(parent,padding=(9,0,9,6));selector.pack(fill='x')
        ttk.Label(selector,text='Gösterilen sonuç:').pack(side='left')
        self.combo_var=tk.StringVar(value=ENVELOPE)
        self.combo_select=ttk.Combobox(selector,textvariable=self.combo_var,values=[ENVELOPE],
                                       state='readonly',width=30)
        self.combo_select.pack(side='left',padx=7)
        self.combo_select.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        ttk.Label(selector,text='Zarf: her değer için tüm kombinasyonların mutlak en büyüğü',
                  foreground=MUTED).pack(side='left')
        self.tabs=ttk.Notebook(parent);self.tabs.pack(fill='both',expand=True)
        self._model_tab();self._table_tabs();self._member_tab();self._drift_tab()

    # ---- layout -------------------------------------------------------
    def _model_tab(self):
        view=ttk.Frame(self.tabs);self.tabs.add(view,text='3B Model')
        controls=ttk.Frame(view);controls.pack(fill='x',pady=5)
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
        self.canvas=FigureCanvasTkAgg(self.figure,master=view)
        self.canvas.get_tk_widget().pack(fill='both',expand=True)
        NavigationToolbar2Tk(self.canvas,view)
        ttk.Label(view,text='Fareyle döndürün • Tekerlek/araç çubuğuyla yakınlaştırın • Düşey eksen global Y',
                  foreground=MUTED).pack(fill='x',padx=8,pady=4)

    def _table_tabs(self):
        nodes=ttk.Frame(self.tabs);self.tabs.add(nodes,text='Düğüm Deplasmanları')
        self.nodes_tree=make_tree(nodes,[('node','Düğüm'),('floor','Kat'),('dx','DX (mm)'),('dy','DY (mm)'),
                                         ('dz','DZ (mm)'),('norm','Toplam (mm)')])
        reactions=ttk.Frame(self.tabs);self.tabs.add(reactions,text='Mesnet Tepkileri')
        self.reactions_tree=make_tree(reactions,[('node','Düğüm'),('fx','FX (kN)'),('fy','FY (kN)'),('fz','FZ (kN)'),
                                                 ('mx','MX (kNm)'),('my','MY (kNm)'),('mz','MZ (kNm)')])

    def _member_tab(self):
        members=ttk.Frame(self.tabs);self.tabs.add(members,text='Eleman Kuvvetleri')
        split=ttk.Panedwindow(members,orient='vertical');split.pack(fill='both',expand=True)
        listing=ttk.Frame(split);diagram=ttk.Frame(split)
        split.add(listing,weight=1);split.add(diagram,weight=1)
        self.members_tree=make_tree(listing,[('name','Eleman'),('type','Tür'),('section','Kesit (cm)'),('length','L (m)'),
            ('n','|N|max kN'),('vy','|Vy|max kN'),('vz','|Vz|max kN'),('my','|My|max kNm'),('mz','|Mz|max kNm'),
            ('t','|T|max kNm'),('gov','Belirleyici (seçili büyüklük)')])
        self.members_tree.column('gov',width=170,anchor='w')
        self.members_tree.bind('<<TreeviewSelect>>',lambda e:self.plot_diagram())
        picker=ttk.Frame(diagram);picker.pack(fill='x',pady=4)
        ttk.Label(picker,text='Seçili elemanın diyagramı:').pack(side='left')
        self.quantity=tk.StringVar(value='Mz')
        choice=ttk.Combobox(picker,textvariable=self.quantity,values=list(QUANTITIES),state='readonly',width=7)
        choice.pack(side='left',padx=7);choice.bind('<<ComboboxSelected>>',lambda e:self.on_quantity())
        ttk.Label(picker,text='Yerel eleman eksenleri; işaretler PyNite tanımına göre',foreground=MUTED).pack(side='left')
        self.diagram_figure=Figure(figsize=(8,3),dpi=100,facecolor='white')
        self.diagram_axis=self.diagram_figure.add_subplot(111)
        self.diagram_canvas=FigureCanvasTkAgg(self.diagram_figure,master=diagram)
        self.diagram_canvas.get_tk_widget().pack(fill='both',expand=True)

    def _drift_tab(self):
        drifts=ttk.Frame(self.tabs);self.tabs.add(drifts,text='Kat Ötelemeleri')
        bar=ttk.Frame(drifts);bar.pack(fill='x',pady=4)
        ttk.Label(bar,text='Uyarı sınırı Δ/h:').pack(side='left',padx=(4,5))
        self.drift_limit=tk.StringVar(value=DEFAULT_DRIFT_LIMIT)
        limit=ttk.Entry(bar,textvariable=self.drift_limit,width=8);limit.pack(side='left')
        limit.bind('<Return>',lambda e:self.fill_drifts())
        ttk.Button(bar,text='Uygula',command=self.fill_drifts).pack(side='left',padx=5)
        ttk.Label(bar,text='Elastik öteleme (girilen yükler). TBDY 2018 etkin öteleme kontrolü için deprem yükü '
                  've R/I büyütmesi gerekir; bu bir yönetmelik kontrolü değildir.',
                  foreground=MUTED,wraplength=620).pack(side='left',padx=8)
        split=ttk.Panedwindow(drifts,orient='vertical');split.pack(fill='both',expand=True)
        listing=ttk.Frame(split);plot=ttk.Frame(split)
        split.add(listing,weight=1);split.add(plot,weight=1)
        self.drifts_tree=make_tree(listing,[('floor','Kat'),('h','h (m)'),('dx','Δx max (mm)'),('rx','Δx/h'),
                                            ('dz','Δz max (mm)'),('rz','Δz/h'),('gov','Belirleyici')])
        self.drifts_tree.column('gov',width=200,anchor='w')
        self.drifts_tree.tag_configure('over',background=OVER_LIMIT_BG)
        self.drift_figure=Figure(figsize=(8,3),dpi=100,facecolor='white')
        self.drift_axis=self.drift_figure.add_subplot(111)
        self.drift_canvas=FigureCanvasTkAgg(self.drift_figure,master=plot)
        self.drift_canvas.get_tk_widget().pack(fill='both',expand=True)

    # ---- state --------------------------------------------------------
    def clear(self,message):
        self.result=None;self.model=None;self.preview=None
        self.summary.set(message)
        for tree in (self.nodes_tree,self.members_tree,self.reactions_tree,self.drifts_tree):
            tree.delete(*tree.get_children())
        for axis,canvas in ((self.diagram_axis,self.diagram_canvas),(self.drift_axis,self.drift_canvas)):
            axis.clear();canvas.draw_idle()
        self.axis.clear();self.axis.set_title('Parametreler değişti — 3B HESAPLA ile yenileyin')
        self.canvas.draw_idle()

    def show(self,model,result):
        self.model,self.result=model,result;self.preview=result
        names=self.combo_names()
        self.combo_select.configure(values=[ENVELOPE,*names])
        if self.combo_var.get() not in (ENVELOPE,*names):
            self.combo_var.set(ENVELOPE)
        governing=max(names,key=lambda n:result['results'][n]['max_displacement_mm'])
        extra='  •  rijit diyafram' if result['config']['rigid_diaphragm'] else ''
        self.summary.set(f"{len(result['nodes'])} düğüm  •  {len(result['members'])} eleman  •  {len(names)} kombinasyon"
                         f"{extra}  •  En büyük deplasman: {result['max_displacement_mm']:.3f} mm ({governing})")
        self.refresh()

    def combo_names(self):
        return [c['name'] for c in self.result['combinations']] if self.result else []

    def selected_combo(self):
        """None for the envelope, else a combination name."""
        value=self.combo_var.get()
        return value if value in self.combo_names() else None

    def refresh(self):
        if not self.result:
            return
        selected=self.members_tree.selection()
        self.fill_tables()
        if selected and self.members_tree.exists(selected[0]):
            self.members_tree.selection_set(selected[0])
        else:
            first=self.members_tree.get_children()
            if first:
                self.members_tree.selection_set(first[0])
        self.plot_model();self.plot_diagram();self.fill_drifts()

    def on_quantity(self):
        if self.result and self.selected_combo() is None:
            self.refresh()
        else:
            self.plot_diagram()

    # ---- tables -------------------------------------------------------
    def fill_tables(self):
        r=self.result;combo=self.selected_combo()
        for tree in (self.nodes_tree,self.members_tree,self.reactions_tree):
            tree.delete(*tree.get_children())
        sets=[r['results'][combo]] if combo else [r['results'][n] for n in self.combo_names()]
        # One combination: signed values. Envelope: absolute maxima per component.
        pick=(lambda values:values[0]) if combo else (lambda values:max(abs(v) for v in values))
        for index,d in enumerate(sets[0]['displacements']):
            values=[pick([s['displacements'][index][k] for s in sets]) for k in DISPLACEMENT_KEYS]
            norm=max(math.sqrt(sum(s['displacements'][index][k]**2 for k in DISPLACEMENT_KEYS)) for s in sets)
            self.nodes_tree.insert('','end',values=[d['node'],d['floor'],*[f'{v:.5f}' for v in values],f'{norm:.5f}'])
        for index,d in enumerate(sets[0]['reactions']):
            values=[pick([s['reactions'][index][k] for s in sets]) for k in REACTION_KEYS]
            self.reactions_tree.insert('','end',values=[d['node'],*[f'{v:.4f}' for v in values]])
        quantity=self.quantity.get()
        for item in r['members']:
            name=item['name']
            if combo:
                peaks=r['results'][combo]['member_peak_abs'][name];gov=combo
            else:
                entry=r['envelope'][name];peaks={q:v['value'] for q,v in entry.items()}
                gov=entry[quantity]['combo'] or '—'
            a,b=item['dims_cm']
            self.members_tree.insert('','end',iid=name,values=[name,'Kolon' if item['kind']=='column' else 'Kiriş',
                f'{a:g}x{b:g}',f"{item['length_m']:.2f}",*[f'{peaks[k]:.3f}' for k in QUANTITIES],gov])

    def drift_rows(self):
        """Per floor: (row, |drift x|, |drift z|, ratio x, ratio z, governing text)."""
        combo=self.selected_combo()
        if combo:
            return [(d,abs(d['drift_x_mm']),abs(d['drift_z_mm']),d['ratio_x'],d['ratio_z'],combo)
                    for d in self.result['results'][combo]['story_drifts']]
        names=self.combo_names();rows=[]
        for index,d in enumerate(self.result['results'][names[0]]['story_drifts']):
            per=[(n,self.result['results'][n]['story_drifts'][index]) for n in names]
            gx=max(per,key=lambda p:p[1]['ratio_x']);gz=max(per,key=lambda p:p[1]['ratio_z'])
            rows.append((d,abs(gx[1]['drift_x_mm']),abs(gz[1]['drift_z_mm']),gx[1]['ratio_x'],gz[1]['ratio_z'],
                         f'X: {gx[0]}  •  Z: {gz[0]}'))
        return rows

    def fill_drifts(self):
        if not self.result:
            return
        try:
            limit=float(self.drift_limit.get().replace(',','.'))
        except ValueError:
            limit=float('nan')
        if not math.isfinite(limit) or limit<=0:
            messagebox.showerror('Öteleme sınırı','Sınır pozitif bir sayı olmalı (örn. 0.008).',
                                 parent=self.tabs.winfo_toplevel())
            self.drift_limit.set(DEFAULT_DRIFT_LIMIT);limit=float(DEFAULT_DRIFT_LIMIT)
        tree=self.drifts_tree;tree.delete(*tree.get_children())
        rows=self.drift_rows();over=0
        for d,dx,dz,rx,rz,gov in rows:
            exceeded=max(rx,rz)>limit;over+=exceeded
            tree.insert('','end',values=[d['floor'],f"{d['height_m']:.2f}",f'{dx:.4f}',ratio_text(rx),
                f'{dz:.4f}',ratio_text(rz),gov],tags=('over',) if exceeded else ())
        ax=self.drift_axis;ax.clear()
        floors=[d['floor'] for d,*_ in rows]
        ax.plot([r[3] for r in rows],floors,marker='o',color=ACCENT,label='Δx/h')
        ax.plot([r[4] for r in rows],floors,marker='s',color=COLUMN,label='Δz/h')
        largest=max([max(r[3],r[4]) for r in rows]+[0.])
        # Keep small drifts readable: the limit line only stretches the axis when it is close.
        limit_visible=largest>=limit/4
        ax.axvline(limit,color=WARNING_FG,linestyle='--',linewidth=1.2,label=f'Sınır {limit:g}',
                   visible=limit_visible)
        ax.set_yticks(floors);ax.set_ylabel('Kat');ax.set_xlabel('Göreli kat ötelemesi oranı Δ/h')
        right=max(limit,largest)*1.08 if limit_visible else (largest*1.15 or limit)
        ax.set_xlim(0,right);ax.grid(alpha=.2)
        ax.legend(handles=ax.lines[:3 if limit_visible else 2],loc='best',fontsize=8)
        title='Kat ötelemeleri — '+(self.selected_combo() or 'zarf')
        if over:
            title+=f'  •  {over} katta sınır aşıldı'
        elif not limit_visible:
            title+=f'  •  en büyük {largest:.5f}, sınır {limit:g} (grafik dışında)'
        ax.set_title(title,fontsize=11);self.drift_figure.tight_layout();self.drift_canvas.draw_idle()

    # ---- plots --------------------------------------------------------
    def plot_model(self):
        data=self.result or self.preview
        if not data:
            return
        ax=self.axis;ax.clear()
        nodes={n['name']:n for n in data['nodes']}
        combo=None
        if self.result:
            combo=self.selected_combo() or self.combo_names()[0]
        displacements={n['node']:n for n in data['results'][combo]['displacements']} if combo else {}
        try:
            scale=float(self.scale.get().replace(',','.'))
        except ValueError:
            scale=100.
        if not math.isfinite(scale) or abs(scale)>1e5:
            scale=100.
        for item in data['members']:
            ends=[nodes[item['i']],nodes[item['j']]]
            color=COLUMN if item['kind']=='column' else BEAM
            ax.plot([v['x'] for v in ends],[v['z'] for v in ends],[v['y'] for v in ends],color=color,linewidth=2.2)
            if combo and self.deformed.get():
                moved=[]
                for n in ends:
                    d=displacements[n['name']]
                    moved.append((n['x']+scale*d['dx_mm']/1000,n['z']+scale*d['dz_mm']/1000,n['y']+scale*d['dy_mm']/1000))
                ax.plot(*zip(*moved),color=DEFORMED,linewidth=1.4,linestyle='--')
        bases=[n for n in nodes.values() if n['base']]
        ax.scatter([n['x'] for n in bases],[n['z'] for n in bases],[n['y'] for n in bases],marker='^',s=32,color='#263e51')
        ax.set_xlabel('X (m)');ax.set_ylabel('Z (m)');ax.set_zlabel('Y / yükseklik (m)')
        config=data['config']
        ax.set_box_aspect([sum(config['spans_x_m']),sum(config['spans_z_m']),sum(config['story_heights_m'])])
        ax.view_init(elev=24,azim=-53)
        title='Örnek/kullanıcı modeli — resimden türetilmedi'
        if combo and self.deformed.get():
            title+=f'\nŞekil değiştirme: {combo}'
        ax.set_title(title,fontsize=11,pad=12)
        self.figure.subplots_adjust(left=.02,right=.94,bottom=.06,top=.90);self.canvas.draw_idle()

    def plot_diagram(self):
        if not self.result or not self.model:
            return
        selected=self.members_tree.selection()
        if not selected:
            return
        name=selected[0];quantity=self.quantity.get();combo=self.selected_combo()
        ax=self.diagram_axis;ax.clear();ax.axhline(0,color='#718192',linewidth=.8)
        if combo:
            x,y=member_diagram(self.model,name,quantity,combo)
            ax.plot(x,y,color=ACCENT,linewidth=2);ax.fill_between(x,y,0,color=ACCENT,alpha=.15)
            ax.set_title(f'{name} — {quantity} — {combo}',fontsize=11)
        else:
            curves=[member_diagram(self.model,name,quantity,n) for n in self.combo_names()]
            x=curves[0][0]
            for cx,cy in curves:
                ax.plot(cx,cy,color='#8aa4b8',linewidth=.8,alpha=.7)
            low=[min(c[1][i] for c in curves) for i in range(len(x))]
            high=[max(c[1][i] for c in curves) for i in range(len(x))]
            ax.fill_between(x,low,high,color=ACCENT,alpha=.15)
            ax.plot(x,low,color=COLUMN,linewidth=1.8,label='Zarf min')
            ax.plot(x,high,color=ACCENT,linewidth=2,label='Zarf maks')
            ax.legend(loc='best',fontsize=8)
            ax.set_title(f'{name} — {quantity} — zarf ({len(curves)} kombinasyon)',fontsize=11)
        ax.set_xlabel('Eleman boyunca x (m)');ax.set_ylabel('kN' if quantity in ('N','Vy','Vz') else 'kNm')
        ax.grid(alpha=.2);self.diagram_figure.tight_layout();self.diagram_canvas.draw_idle()
