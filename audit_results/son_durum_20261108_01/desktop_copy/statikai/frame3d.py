"""User-defined regular 3D elastic frame analysis, not image reconstruction.

Units: m, kN, kNm; global Y is vertical. Rectangular gross sections, rigid
joints, Euler-Bernoulli members, first-order small-displacement analysis.
No slab/wall/shell, diaphragm, seismic-code load or reinforced-concrete design.
"""
from dataclasses import asdict, dataclass
import importlib.metadata
import math
import os
from pathlib import Path
import time

_cache=Path(__file__).resolve().parents[1]/'work'/'matplotlib'
_cache.mkdir(parents=True,exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(_cache))

import numpy as np
from Pynite import FEModel3D

COMBO='USER_1.0'


@dataclass(frozen=True)
class FrameConfig:
    floors: int=6
    bays_x: int=2
    bays_z: int=2
    span_x_m: float=5.
    span_z_m: float=4.
    story_height_m: float=3.
    elastic_modulus_gpa: float=30.
    poisson: float=.2
    unit_weight_kn_m3: float=25.
    beam_width_cm: float=30.
    beam_depth_cm: float=50.
    column_width_cm: float=40.
    column_depth_cm: float=40.
    floor_load_kn_m2: float=5.
    lateral_x_kn_per_floor: float=30.
    lateral_z_kn_per_floor: float=0.
    self_weight: bool=True
    base_support: str='fixed'
    model_name: str='Ornek 3B cerceve — goruntuden cikarilmadi'

    def validate(self):
        for name,limit in [('floors',10),('bays_x',4),('bays_z',4)]:
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=limit:
                raise ValueError(f'{name}: 1 ile {limit} arasinda tam sayi olmali.')
        for key,value in asdict(self).items():
            if isinstance(value,(int,float)) and not isinstance(value,bool) and not math.isfinite(value):
                raise ValueError(f'{key}: sonlu bir sayi girilmeli.')
        for key in ['span_x_m','span_z_m','story_height_m','elastic_modulus_gpa',
                    'beam_width_cm','beam_depth_cm','column_width_cm','column_depth_cm']:
            if getattr(self,key)<=0: raise ValueError(f'{key}: sifirdan buyuk olmali.')
        if not 0<self.poisson<.49: raise ValueError('Poisson orani 0 ile 0.49 arasinda olmali.')
        if self.floor_load_kn_m2<0 or self.unit_weight_kn_m3<0:
            raise ValueError('Alan yuku ve birim hacim agirligi negatif olamaz.')
        if self.base_support not in ('fixed','pinned'):
            raise ValueError('Mesnet fixed veya pinned olmali.')
        if not isinstance(self.self_weight,bool): raise ValueError('self_weight boolean olmali.')


def rectangle_properties(width_m,depth_m):
    """Local z width and local y depth; J is a Saint-Venant approximation.

    J=a*b**3*(1/3-.21*(b/a)*(1-(b/a)**4/12)), a>=b.
    Reference: Oasys GSA Rectangular Sections theory documentation.
    """
    if not all(math.isfinite(v) and v>0 for v in (width_m,depth_m)):
        raise ValueError('Kesit boyutlari pozitif ve sonlu olmali.')
    a,b=max(width_m,depth_m),min(width_m,depth_m)
    return dict(A=width_m*depth_m,Iy=depth_m*width_m**3/12,
                Iz=width_m*depth_m**3/12,
                J=a*b**3*(1/3-.21*(b/a)*(1-(b/a)**4/12)))


def build_frame(config):
    config.validate()
    model=FEModel3D()
    E=config.elastic_modulus_gpa*1e6  # GPa -> kN/m2
    G=E/(2*(1+config.poisson))
    model.add_material('USER',E,G,config.poisson,config.unit_weight_kn_m3)
    sections={
        'BEAM':rectangle_properties(config.beam_width_cm/100,config.beam_depth_cm/100),
        'COLUMN':rectangle_properties(config.column_width_cm/100,config.column_depth_cm/100)}
    for name,properties in sections.items(): model.add_section(name,**properties)
    nodes=[];members=[];loads=[]
    node_name=lambda floor,x,z:f'N_{floor}_{x}_{z}'
    for floor in range(config.floors+1):
        for x in range(config.bays_x+1):
            for z in range(config.bays_z+1):
                name=node_name(floor,x,z)
                xyz=(x*config.span_x_m,floor*config.story_height_m,z*config.span_z_m)
                model.add_node(name,*xyz)
                nodes.append(dict(name=name,x=xyz[0],y=xyz[1],z=xyz[2],floor=floor,base=floor==0))
                if floor==0:
                    fixed=config.base_support=='fixed'
                    model.def_support(name,True,True,True,fixed,fixed,fixed)
                else:
                    trib_x=config.span_x_m*(.5 if x in (0,config.bays_x) else 1.)
                    trib_z=config.span_z_m*(.5 if z in (0,config.bays_z) else 1.)
                    total_nodes=(config.bays_x+1)*(config.bays_z+1)
                    vector=np.array([config.lateral_x_kn_per_floor/total_nodes,
                                     -config.floor_load_kn_m2*trib_x*trib_z,
                                     config.lateral_z_kn_per_floor/total_nodes])
                    for direction,value in zip(('FX','FY','FZ'),vector):
                        if value: model.add_node_load(name,direction,float(value),case='USER')
                    loads.append(dict(node=name,xyz=list(xyz),force=vector.tolist(),moment=[0.,0.,0.]))
    by_name={n['name']:n for n in nodes}
    def member(name,i,j,kind):
        section='COLUMN' if kind=='column' else 'BEAM'
        model.add_member(name,i,j,'USER',section)
        a,b=by_name[i],by_name[j]
        length=math.dist((a['x'],a['y'],a['z']),(b['x'],b['y'],b['z']))
        members.append(dict(name=name,i=i,j=j,kind=kind,length_m=length,section=section))
    for floor in range(1,config.floors+1):
        for x in range(config.bays_x+1):
            for z in range(config.bays_z+1):
                member(f'C_{floor}_{x}_{z}',node_name(floor-1,x,z),node_name(floor,x,z),'column')
        for x in range(config.bays_x):
            for z in range(config.bays_z+1):
                member(f'BX_{floor}_{x}_{z}',node_name(floor,x,z),node_name(floor,x+1,z),'beam_x')
        for x in range(config.bays_x+1):
            for z in range(config.bays_z):
                member(f'BZ_{floor}_{x}_{z}',node_name(floor,x,z),node_name(floor,x,z+1),'beam_z')
    if config.self_weight: model.add_member_self_weight('FY',-1.,case='USER')
    model.add_load_combo(COMBO,{'USER':1.})
    applied_force=np.zeros(3);applied_moment=np.zeros(3)
    for load in loads:
        force=np.asarray(load['force'])
        applied_force+=force
        applied_moment+=np.cross(load['xyz'],force)
    if config.self_weight:
        for item in members:
            i,j=by_name[item['i']],by_name[item['j']]
            centroid=(np.array([i['x'],i['y'],i['z']])+np.array([j['x'],j['y'],j['z']]))/2
            force=np.array([0.,-config.unit_weight_kn_m3*sections[item['section']]['A']*item['length_m'],0.])
            applied_force+=force;applied_moment+=np.cross(centroid,force)
    return model,dict(config=asdict(config),nodes=nodes,members=members,loads=loads,
                      sections=sections,applied_force_kn=applied_force.tolist(),
                      applied_moment_knm=applied_moment.tolist())


def solve_frame(config):
    start=time.perf_counter()
    model,data=build_frame(config)
    try:
        model.analyze_linear(log=False,check_stability=True,sparse=True)
    except Exception as error:
        raise ValueError(f'Model cozulemedi; geometri ve mesnetleri kontrol edin: {error}') from error
    displacements=[];reactions=[];member_results=[]
    support_force=np.zeros(3);support_moment=np.zeros(3)
    for item in data['nodes']:
        node=model.nodes[item['name']]
        d=[float(getattr(node,key)[COMBO]) for key in ('DX','DY','DZ','RX','RY','RZ')]
        if not all(math.isfinite(v) for v in d): raise ValueError('Sonlu olmayan yer degistirme; sonuc reddedildi.')
        displacements.append(dict(node=item['name'],floor=item['floor'],dx_mm=d[0]*1000,
                                  dy_mm=d[1]*1000,dz_mm=d[2]*1000,rx_rad=d[3],ry_rad=d[4],rz_rad=d[5]))
        if item['base']:
            force=np.array([float(getattr(node,k)[COMBO]) for k in ('RxnFX','RxnFY','RxnFZ')])
            moment=np.array([float(getattr(node,k)[COMBO]) for k in ('RxnMX','RxnMY','RxnMZ')])
            support_force+=force;support_moment+=moment+np.cross([item['x'],item['y'],item['z']],force)
            reactions.append(dict(node=item['name'],fx_kn=force[0],fy_kn=force[1],fz_kn=force[2],
                                  mx_knm=moment[0],my_knm=moment[1],mz_knm=moment[2]))
    for item in data['members']:
        m=model.members[item['name']]
        diagrams={
            'N':m.axial_array(31,COMBO),
            'Vy':m.shear_array('Fy',31,COMBO),'Vz':m.shear_array('Fz',31,COMBO),
            'My':m.moment_array('My',31,COMBO),'Mz':m.moment_array('Mz',31,COMBO),
            'T':m.torque_array(31,COMBO)}
        peaks={
            'N':max(abs(float(m.min_axial(COMBO))),abs(float(m.max_axial(COMBO)))),
            'Vy':max(abs(float(m.min_shear('Fy',COMBO))),abs(float(m.max_shear('Fy',COMBO)))),
            'Vz':max(abs(float(m.min_shear('Fz',COMBO))),abs(float(m.max_shear('Fz',COMBO)))),
            'My':max(abs(float(m.min_moment('My',COMBO))),abs(float(m.max_moment('My',COMBO)))),
            'Mz':max(abs(float(m.min_moment('Mz',COMBO))),abs(float(m.max_moment('Mz',COMBO)))),
            'T':max(abs(float(m.min_torque(COMBO))),abs(float(m.max_torque(COMBO))))}
        member_results.append(dict(**item,peak_abs=peaks,
            diagrams={key:np.asarray(value,dtype=float).tolist() for key,value in diagrams.items()}))
    residual_force=support_force+np.asarray(data['applied_force_kn'])
    residual_moment=support_moment+np.asarray(data['applied_moment_knm'])
    force_tolerance=max(1e-6,1e-7*np.linalg.norm(data['applied_force_kn']))
    moment_tolerance=max(1e-6,1e-7*np.linalg.norm(data['applied_moment_knm']))
    if np.max(np.abs(residual_force))>force_tolerance or np.max(np.abs(residual_moment))>moment_tolerance:
        raise ValueError('Global denge artigi toleransi asti; sonuc reddedildi.')
    data.update(displacements=displacements,reactions=reactions,member_results=member_results,
        analysis='first_order_linear_elastic_3d_frame',source='manual_parameters_or_demonstration',
        solver='PyniteFEA '+importlib.metadata.version('PyniteFEA'),
        units=dict(length='m',force='kN',moment='kNm',displacement='mm',rotation='rad'),
        force_residual_kn=residual_force.tolist(),moment_residual_knm=residual_moment.tolist(),
        max_displacement_mm=max(math.sqrt(n['dx_mm']**2+n['dy_mm']**2+n['dz_mm']**2) for n in displacements),
        elapsed_seconds=time.perf_counter()-start,
        limitations=['Goruntuden 3B model cikarilmadi; kullanici/ornek parametreleri kullanildi.',
            'Birinci mertebe, izotrop dogrusal elastik cubuk modeli; kayma deformasyonu yok.',
            'Doseme, perde, rijit diyafram, temel-zemin etkilesimi ve P-Delta modellenmedi.',
            'Alan yukleri dugumlere tesir alaniyla esdegerlenir; doseme egilme hesabi yapilmaz.',
            'Doseme yuklerinin kirislerde olusturdugu egilme bu dugum-yuku modelinde yoktur.',
            'Malzeme ve yukler ornek/girdidir; yonetmelik deprem veya betonarme tasarimi yapilmaz.',
            'Goruntudeki gercek yapinin guvenligi/kapasitesi degerlendirilmez.'])
    return data
