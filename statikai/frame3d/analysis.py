"""Linear solution, equilibrium audit, member peaks, envelopes and storey drifts."""
import importlib.metadata
import math
import time

import numpy as np

from .model import build_frame, node_name

QUANTITIES=('N','Vy','Vz','My','Mz','T')
LIMITATIONS=[
    'Goruntuden 3B model cikarilmadi; kullanici/ornek parametreleri kullanildi.',
    'Birinci mertebe, izotrop dogrusal elastik cubuk modeli; kayma deformasyonu yok.',
    'Doseme plagi, perde, temel-zemin etkilesimi ve P-Delta modellenmedi.',
    'Rijit diyafram secenegi kat duzleminde cok rijit eksenel baglantilarla yaklasik modellenir; dugumlerin dusey eksen etrafindaki donmeleri birbirine baglanmaz.',
    'Doseme alan yukleri 45 derece zarf kuraliyla kirislere ucgen/trapez yayili yuk olarak aktarilir.',
    'Doseme plaginin kendi agirligi otomatik eklenmez; G alan yukune dahil edilmelidir.',
    'Kat yatay yukleri dugumlere plan tesir alani oraninda dagitilir (bileske plan alan merkezinde).',
    'Hareketli yuk tum aciklik/katlara birlikte uygulanir; dama (pattern) yuklemesi yapilmaz.',
    'E yukleri elle girilen yatay kuvvetlerdir; TBDY 2018 deprem yuku uretilmez, %30 dik yon kurali uygulanmaz.',
    'Kat otelemeleri girilen yuklerin elastik degerleridir; TBDY etkin (R/I ile buyutulmus) oteleme kontrolu degildir.',
    'Yonetmelik kontrolu, betonarme/ahsap boyutlandirmasi yapilmaz; gercek yapi guvenligi degerlendirilmez.']


def _peak(member,quantity,combo):
    if quantity=='N':
        low,high=member.min_axial(combo),member.max_axial(combo)
    elif quantity=='T':
        low,high=member.min_torque(combo),member.max_torque(combo)
    elif quantity in ('Vy','Vz'):
        direction='F'+quantity[1]
        low,high=member.min_shear(direction,combo),member.max_shear(direction,combo)
    else:
        low,high=member.min_moment(quantity,combo),member.max_moment(quantity,combo)
    return max(abs(float(low)),abs(float(high)))


def member_diagram(model,member_name,quantity,combo,points=31):
    """[[x...],[value...]] along the member in local axes (PyNite sign convention)."""
    m=model.members[member_name]
    if quantity=='N':
        array=m.axial_array(points,combo)
    elif quantity=='T':
        array=m.torque_array(points,combo)
    elif quantity in ('Vy','Vz'):
        array=m.shear_array('F'+quantity[1],points,combo)
    elif quantity in ('My','Mz'):
        array=m.moment_array(quantity,points,combo)
    else:
        raise ValueError(f'Bilinmeyen buyukluk: {quantity}')
    return np.asarray(array,dtype=float).tolist()


def story_drifts(config,displacements):
    """Inter-storey drift per floor from node pairs on the same column line.

    The largest drift of any column line is reported separately for X and Z,
    with Delta/h of that storey. Elastic drifts of the entered loads, not
    TBDY 2018 effective (R/I amplified) seismic drifts.
    """
    by_name={d['node']:d for d in displacements}
    rows=[]
    for floor,h in enumerate(config.story_heights_m,1):
        best={'x':(0.,None),'z':(0.,None)}
        top={'x':0.,'z':0.}
        for ix in range(config.bays_x+1):
            for iz in range(config.bays_z+1):
                upper=by_name[node_name(floor,ix,iz)];lower=by_name[node_name(floor-1,ix,iz)]
                for axis in ('x','z'):
                    key=f'd{axis}_mm'
                    top[axis]=max(top[axis],abs(upper[key]))
                    drift=upper[key]-lower[key]
                    if abs(drift)>abs(best[axis][0]):
                        best[axis]=(drift,upper['node'])
        rows.append(dict(floor=floor,height_m=h,max_dx_mm=top['x'],max_dz_mm=top['z'],
                         drift_x_mm=best['x'][0],drift_z_mm=best['z'][0],
                         ratio_x=abs(best['x'][0])/1000/h,ratio_z=abs(best['z'][0])/1000/h,
                         node_x=best['x'][1],node_z=best['z'][1]))
    return rows


def _combo_result(model,data,config,combo):
    name=combo['name'];factors=combo['factors']
    applied_force=sum(f*np.asarray(data['applied_by_case'][c]['force_kn']) for c,f in factors.items())
    applied_moment=sum(f*np.asarray(data['applied_by_case'][c]['moment_knm']) for c,f in factors.items())
    displacements=[];reactions=[]
    support_force=np.zeros(3);support_moment=np.zeros(3)
    for item in data['nodes']:
        node=model.nodes[item['name']]
        d=[float(getattr(node,key)[name]) for key in ('DX','DY','DZ','RX','RY','RZ')]
        if not all(math.isfinite(v) for v in d):
            raise ValueError('Sonlu olmayan yer degistirme; sonuc reddedildi.')
        displacements.append(dict(node=item['name'],floor=item['floor'],dx_mm=d[0]*1000,
                                  dy_mm=d[1]*1000,dz_mm=d[2]*1000,rx_rad=d[3],ry_rad=d[4],rz_rad=d[5]))
        if item['base']:
            force=np.array([float(getattr(node,k)[name]) for k in ('RxnFX','RxnFY','RxnFZ')])
            moment=np.array([float(getattr(node,k)[name]) for k in ('RxnMX','RxnMY','RxnMZ')])
            support_force+=force
            support_moment+=moment+np.cross([item['x'],item['y'],item['z']],force)
            reactions.append(dict(node=item['name'],fx_kn=float(force[0]),fy_kn=float(force[1]),fz_kn=float(force[2]),
                                  mx_knm=float(moment[0]),my_knm=float(moment[1]),mz_knm=float(moment[2])))
    residual_force=support_force+applied_force
    residual_moment=support_moment+applied_moment
    # Stiff diaphragm links raise round-off; the tolerance stays relative to the load.
    relative=1e-6 if config.rigid_diaphragm else 1e-7
    force_tolerance=max(1e-6,relative*np.linalg.norm(applied_force))
    moment_tolerance=max(1e-6,relative*np.linalg.norm(applied_moment))
    if np.max(np.abs(residual_force))>force_tolerance or np.max(np.abs(residual_moment))>moment_tolerance:
        raise ValueError(f'{name}: global denge artigi toleransi asti; sonuc reddedildi.')
    peaks={item['name']:{q:_peak(model.members[item['name']],q,name) for q in QUANTITIES}
           for item in data['members']}
    return dict(displacements=displacements,reactions=reactions,member_peak_abs=peaks,
                story_drifts=story_drifts(config,displacements),
                max_displacement_mm=max(math.sqrt(n['dx_mm']**2+n['dy_mm']**2+n['dz_mm']**2) for n in displacements),
                applied_force_kn=applied_force.tolist(),applied_moment_knm=applied_moment.tolist(),
                force_residual_kn=residual_force.tolist(),moment_residual_knm=residual_moment.tolist())


def _envelope(data,results):
    envelope={}
    for item in data['members']:
        entry={}
        for q in QUANTITIES:
            combo=max(results,key=lambda n:results[n]['member_peak_abs'][item['name']][q])
            entry[q]=dict(value=results[combo]['member_peak_abs'][item['name']][q],combo=combo)
        envelope[item['name']]=entry
    return envelope


def solve_frame(config,return_model=False):
    start=time.perf_counter()
    model,data=build_frame(config)
    try:
        model.analyze_linear(log=False,check_stability=True,sparse=True)
    except Exception as error:
        raise ValueError(f'Model cozulemedi; geometri ve mesnetleri kontrol edin: {error}') from error
    results={combo['name']:_combo_result(model,data,config,combo) for combo in data['combinations']}
    worst_force=np.max([np.abs(r['force_residual_kn']) for r in results.values()],axis=0)
    worst_moment=np.max([np.abs(r['moment_residual_knm']) for r in results.values()],axis=0)
    data.update(results=results,envelope=_envelope(data,results),
        analysis='first_order_linear_elastic_3d_frame_load_combinations',
        source='manual_parameters_or_demonstration',
        solver='PyniteFEA '+importlib.metadata.version('PyniteFEA'),
        units=dict(length='m',force='kN',moment='kNm',displacement='mm',rotation='rad'),
        force_residual_kn=worst_force.tolist(),moment_residual_knm=worst_moment.tolist(),
        max_displacement_mm=max(r['max_displacement_mm'] for r in results.values()),
        elapsed_seconds=time.perf_counter()-start,limitations=list(LIMITATIONS))
    return (model,data) if return_model else data
