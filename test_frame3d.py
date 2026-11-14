from dataclasses import asdict, replace
import json
import numpy as np
import pytest
FEModel3D=pytest.importorskip('Pynite',reason='3B testleri için requirements-desktop.txt kurulmalı').FEModel3D
from statikai.frame3d import (FrameConfig,rectangle_properties,build_frame,solve_frame,
                              envelope_segments,member_diagram,tributary_weights)

GRAVITY_OFF=dict(self_weight=False,dead_load_kn_m2=0.,live_load_kn_m2=0.)
EX_ONLY=(('EX',0.,0.,1.,0.),)
EZ_ONLY=(('EZ',0.,0.,0.,1.),)


def cantilever(direction,axis,E=30e6,L=3.,P=10.):
    model=FEModel3D();section=rectangle_properties(.3,.5)
    model.add_material('M',E,E/2.4,.2,0.)
    model.add_section('S',**section)
    model.add_node('A',0.,0.,0.);model.add_node('B',L,0.,0.)
    model.add_member('C','A','B','M','S')
    model.def_support('A',True,True,True,True,True,True)
    model.add_node_load('B',direction,-P,case='P')
    model.add_load_combo('TEST',{'P':1.})
    model.analyze_linear()
    observed=float(getattr(model.nodes['B'],axis)['TEST'])
    return observed,section,model


def sway_drift_mm(P,h,E_kn_m2,inertias):
    """Stiff-beam storey: columns act as fixed-fixed springs 12EI/h^3 in parallel."""
    return P/sum(12*E_kn_m2*I/h**3 for I in inertias)*1000


# ---- solver building blocks ------------------------------------------------
@pytest.mark.parametrize('force,displacement,inertia',[('FY','DY','Iz'),('FZ','DZ','Iy')])
def test_cantilever_matches_independent_hand_solution(force,displacement,inertia):
    observed,section,model=cantilever(force,displacement)
    expected=-10*3**3/(3*30e6*section[inertia])
    assert observed==pytest.approx(expected,rel=1e-9)
    assert getattr(model.nodes['A'],'Rxn'+force)['TEST']==pytest.approx(10.)


def test_axial_and_torsion_hand_solutions():
    axial,section,_=cantilever('FX','DX')
    assert axial==pytest.approx(-10*3/(30e6*section['A']),rel=1e-9)
    rotation,section,_=cantilever('MX','RX')
    assert rotation==pytest.approx(-10*3/((30e6/2.4)*section['J']),rel=1e-9)


def test_rectangle_square_and_axis_swap():
    a=rectangle_properties(.4,.4)
    assert a['J']/.4**4==pytest.approx(.1408333333333,rel=1e-9)
    b,c=rectangle_properties(.3,.5),rectangle_properties(.5,.3)
    assert b['J']==c['J']
    assert b['Iy']==pytest.approx(c['Iz'])


@pytest.mark.parametrize('length,half',[(4.,2.),(5.,2.),(6.,1.5)])
def test_envelope_segment_area(length,half):
    peak=3.
    area=sum((w1+w2)/2*(x2-x1) for w1,w2,x1,x2 in envelope_segments(length,half,peak))
    assert area==pytest.approx(peak*(length-half),rel=1e-12)


@pytest.mark.parametrize('lx,lz',[(4.,4.),(5.,4.),(6.,3.)])
def test_fixed_end_moment_matches_hand_formula(lx,lz):
    """Clamped beam under the 45 degree slab strip: M=w*L^2/12*(1-2a^2+a^3), a=ramp/L."""
    w=5.;half=min(lx,lz)/2;peak=w*half;L=lx
    model=FEModel3D();section=rectangle_properties(.3,.5)
    model.add_material('M',30e6,12.5e6,.2,0.);model.add_section('S',**section)
    model.add_node('A',0.,0.,0.);model.add_node('B',L,0.,0.)
    model.add_member('B1','A','B','M','S')
    for name in 'AB': model.def_support(name,True,True,True,True,True,True)
    for w1,w2,x1,x2 in envelope_segments(L,half,peak):
        model.add_member_dist_load('B1','FY',-w1,-w2,x1,x2,case='G')
    model.add_load_combo('G',{'G':1.});model.analyze_linear()
    alpha=half/L
    expected=peak*L**2/12*(1-2*alpha**2+alpha**3)
    assert abs(model.nodes['A'].RxnMZ['G'])==pytest.approx(expected,rel=1e-9)
    assert model.nodes['A'].RxnFY['G']==pytest.approx(peak*(L-half)/2,rel=1e-9)


def test_tributary_weights_sum_and_centroid():
    spans_x,spans_z=(6.,3.),(4.,)
    w=tributary_weights(spans_x,spans_z)
    assert sum(w.values())==pytest.approx(1.)
    xs=[0.,6.,9.]
    centroid=sum(w[(ix,iz)]*xs[ix] for ix,iz in w)
    assert centroid==pytest.approx(4.5)      # plan centre of a 9 m wide rectangle


# ---- whole-frame checks ----------------------------------------------------
def test_grid_load_area_and_global_force_moment_balance():
    config=FrameConfig.regular(floors=2,bays_x=1,bays_z=1)
    model,data=build_frame(config)
    assert len(data['nodes'])==12
    assert len(data['members'])==16
    for case,w in (('G',config.dead_load_kn_m2),('Q',config.live_load_kn_m2)):
        line_total=sum((v['w1_kn_m']+v['w2_kn_m'])/2*(v['x2_m']-v['x1_m'])
                       for v in data['line_loads'] if v['case']==case)
        assert line_total==pytest.approx(2*w*4*5,rel=1e-12)
    solved=solve_frame(config)
    assert np.max(np.abs(solved['force_residual_kn']))<1e-6
    assert np.max(np.abs(solved['moment_residual_knm']))<1e-5
    service=solved['results']['G+Q']
    assert len(service['reactions'])==4
    own=25*(2*4*3*.4*.4+2*(2*5+2*4)*.3*.5)
    assert sum(r['fy_kn'] for r in service['reactions'])==pytest.approx(2*20*(4.5+2.)+own,rel=1e-10)


def test_irregular_grid_loads_sections_and_balance():
    config=FrameConfig(spans_x_m=(6.,4.5,3.),spans_z_m=(5.,3.5),story_heights_m=(4.,3.,3.),
                       beam_sections_cm=((30.,60.),(25.,50.),(25.,50.)),
                       column_sections_cm=((50.,50.),(40.,60.),(40.,60.)),lateral_z_kn_per_floor=20.)
    _,data=build_frame(config)
    assert [n['y'] for n in data['nodes'] if n['name'].endswith('_0_0')]==[0.,4.,7.,10.]
    sections={m['name']:tuple(m['dims_cm']) for m in data['members']}
    assert sections['C_1_0_0']==(50.,50.) and sections['C_3_3_2']==(40.,60.)
    assert sections['BX_1_2_0']==(30.,60.) and sections['BZ_2_0_1']==(25.,50.)
    lengths={m['name']:m['length_m'] for m in data['members']}
    assert lengths['BX_1_0_0']==6. and lengths['BX_1_2_0']==3. and lengths['BZ_1_0_1']==3.5
    assert lengths['C_1_0_0']==4. and lengths['C_2_0_0']==3.
    area=13.5*8.5
    total_g=sum((v['w1_kn_m']+v['w2_kn_m'])/2*(v['x2_m']-v['x1_m']) for v in data['line_loads'] if v['case']=='G')
    assert total_g==pytest.approx(3*area*config.dead_load_kn_m2,rel=1e-12)
    solved=solve_frame(config)
    assert np.max(np.abs(solved['force_residual_kn']))<1e-6
    assert np.max(np.abs(solved['moment_residual_knm']))<1e-5
    # Independent hand total of G+Q vertical reaction.
    column=12*(.5*.5*4)+12*2*(.4*.6*3)
    beam_len=3*(13.5*3+8.5*4)
    beams=beam_len*(.3*.6)/3+2*beam_len*(.25*.5)/3
    expected=3*area*(4.5+2.)+25*(column+beams)
    vertical=sum(r['fy_kn'] for r in solved['results']['G+Q']['reactions'])
    assert vertical==pytest.approx(expected,rel=1e-10)


@pytest.mark.parametrize('combos,key,dims',[(EX_ONLY,'drift_x_mm',(30.,60.)),(EZ_ONLY,'drift_z_mm',(30.,60.)),
                                            (EX_ONLY,'drift_x_mm',(60.,30.))])
def test_column_orientation_matches_hand_sway(combos,key,dims):
    """Column 'AxB' = A along global X, B along global Z: X sway uses I=B*A^3/12."""
    P=40.;h=3.;E=30e6
    config=FrameConfig(spans_x_m=(4.,),spans_z_m=(4.,),story_heights_m=(h,),
                       beam_sections_cm=((100.,300.),),column_sections_cm=(dims,),
                       lateral_x_kn_per_floor=P,lateral_z_kn_per_floor=P,combinations=combos,**GRAVITY_OFF)
    a,b=dims[0]/100,dims[1]/100
    I=b*a**3/12 if key=='drift_x_mm' else a*b**3/12
    row=solve_frame(config)['results'][combos[0][0]]['story_drifts'][0]
    # Beam flexibility and column shortening add a few percent to the ideal value;
    # the swapped orientation would differ by a factor of 4, so this is decisive.
    assert abs(row[key])==pytest.approx(sway_drift_mm(P,h,E,[I]*4),rel=4e-2)


def test_story_drift_variable_heights():
    config=FrameConfig(spans_x_m=(4.,),spans_z_m=(4.,),story_heights_m=(4.5,3.),
                       beam_sections_cm=((100.,300.),),column_sections_cm=((40.,40.),),
                       lateral_x_kn_per_floor=20.,combinations=EX_ONLY,**GRAVITY_OFF)
    rows=solve_frame(config)['results']['EX']['story_drifts']
    assert [r['height_m'] for r in rows]==[4.5,3.]
    I=.4**4/12
    # Storey 1 carries both floor loads. (Storey 2 also rotates rigidly with the
    # axially shortened storey-1 columns, which the shear-only formula ignores.)
    assert rows[0]['drift_x_mm']==pytest.approx(sway_drift_mm(40.,4.5,30e6,[I]*4),rel=3e-2)
    assert rows[0]['ratio_x']==pytest.approx(abs(rows[0]['drift_x_mm'])/1000/4.5,rel=1e-12)
    assert rows[1]['ratio_x']==pytest.approx(abs(rows[1]['drift_x_mm'])/1000/3.,rel=1e-12)
    assert sway_drift_mm(20.,3.,30e6,[I]*4)<rows[1]['drift_x_mm']<1.3*sway_drift_mm(20.,3.,30e6,[I]*4)


def test_rigid_diaphragm_moves_each_floor_as_rigid_plane():
    """Irregular plan: mass centre (z=4.0) and column stiffness centre (z=4.33) differ,
    so the floor also twists. A rigid plane keeps every in-plane node distance."""
    base=FrameConfig(spans_x_m=(6.,4.),spans_z_m=(5.,3.),story_heights_m=(3.,3.,3.),
                     lateral_x_kn_per_floor=60.,combinations=EX_ONLY,**GRAVITY_OFF)
    results={}
    for flag in (False,True):
        solved=solve_frame(replace(base,rigid_diaphragm=flag))
        assert np.max(np.abs(solved['force_residual_kn']))<1e-4
        assert len(solved['members'])==3*(9+6+6)
        results[flag]=solved
    def max_stretch(solved,floor):
        nodes={n['name']:n for n in solved['nodes'] if n['floor']==floor}
        moves={d['node']:np.array([d['dx_mm'],d['dz_mm']]) for d in solved['results']['EX']['displacements']
               if d['floor']==floor}
        names=sorted(nodes);worst=0.
        for a in names:
            for b in names:
                if a<b:
                    e=np.array([nodes[b]['x']-nodes[a]['x'],nodes[b]['z']-nodes[a]['z']])
                    worst=max(worst,abs(np.dot(moves[b]-moves[a],e/np.linalg.norm(e))))
        return worst,max(np.linalg.norm(v) for v in moves.values())
    for floor in (1,2,3):
        free,_=max_stretch(results[False],floor);tied,size=max_stretch(results[True],floor)
        assert tied<1e-3*size and tied<1e-2*free
    # The twist itself is physical: dx differs along z on the rigid floor.
    top=[d['dx_mm'] for d in results[True]['results']['EX']['displacements'] if d['floor']==3]
    assert max(top)-min(top)>1e-3
    assert len(results[True]['diaphragm_links'])==3*(6+6+8)
    beam_axial=max(results[True]['results']['EX']['member_peak_abs'][m['name']]['N']
                   for m in results[True]['members'] if m['kind']!='column')
    assert beam_axial<1e-2
    # Diaphragm off: no link members are created.
    assert results[False]['diaphragm_links']==[]


def test_rigid_diaphragm_symmetric_frame_matches_hand_sway():
    P=60.;h=3.;E=30e6
    config=FrameConfig(spans_x_m=(4.,4.),spans_z_m=(4.,),story_heights_m=(h,),
                       beam_sections_cm=((100.,300.),),column_sections_cm=((40.,40.),),
                       lateral_x_kn_per_floor=P,rigid_diaphragm=True,combinations=EX_ONLY,**GRAVITY_OFF)
    row=solve_frame(config)['results']['EX']['story_drifts'][0]
    assert row['drift_x_mm']==pytest.approx(sway_drift_mm(P,h,E,[.4**4/12]*6),rel=2e-2)


def test_combinations_superpose_cases():
    combos=(('G',1.,0.,0.,0.),('Q',0.,1.,0.,0.),('EX',0.,0.,1.,0.),('C',1.4,1.6,-1.,0.))
    config=FrameConfig.regular(floors=2,bays_x=2,bays_z=1,combinations=combos)
    model,solved=solve_frame(config,return_model=True)
    r=solved['results']
    for index,node in enumerate(r['C']['displacements']):
        for key in ('dx_mm','dy_mm','dz_mm'):
            expected=1.4*r['G']['displacements'][index][key]+1.6*r['Q']['displacements'][index][key]-r['EX']['displacements'][index][key]
            assert node[key]==pytest.approx(expected,abs=1e-9)
    beam='BX_1_0_1'
    parts={n:np.array(member_diagram(model,beam,'Mz',n)[1]) for n in ('G','Q','EX','C')}
    assert np.allclose(parts['C'],1.4*parts['G']+1.6*parts['Q']-parts['EX'],atol=1e-8)
    assert solved['envelope'][beam]['Mz']['value']>10


def test_story_drifts_sum_to_roof_displacement():
    config=FrameConfig.regular(floors=4,bays_x=2,bays_z=1,lateral_z_kn_per_floor=15)
    solved=solve_frame(config)
    for result in solved['results'].values():
        rows=result['story_drifts']
        assert [r['floor'] for r in rows]==[1,2,3,4]
        line=rows[-1]['node_x'].split('_')[2:]
        chain=[next(d['dx_mm'] for d in result['displacements'] if d['node']==f'N_{f}_{line[0]}_{line[1]}')
               for f in range(5)]
        assert sum(chain[f]-chain[f-1] for f in range(1,5))==pytest.approx(chain[-1],abs=1e-12)


def test_zero_load_and_linear_load_scaling():
    zero=FrameConfig.regular(floors=1,bays_x=1,bays_z=1,lateral_x_kn_per_floor=0,**GRAVITY_OFF)
    assert solve_frame(zero)['max_displacement_mm']==0
    one=replace(zero,lateral_x_kn_per_floor=10.)
    two=replace(one,lateral_x_kn_per_floor=20.)
    assert solve_frame(two)['max_displacement_mm']==pytest.approx(2*solve_frame(one)['max_displacement_mm'],rel=1e-8)


def test_isotropic_square_plan_rotates_symmetrically():
    first=FrameConfig.regular(floors=1,bays_x=1,bays_z=1,span_x_m=4,span_z_m=4,
                              beam_width_cm=40,beam_depth_cm=40,lateral_x_kn_per_floor=10,
                              lateral_z_kn_per_floor=0,**GRAVITY_OFF)
    second=replace(first,lateral_x_kn_per_floor=0,lateral_z_kn_per_floor=10)
    assert solve_frame(first)['max_displacement_mm']==pytest.approx(solve_frame(second)['max_displacement_mm'],rel=1e-7)


# ---- inputs, files, validation -------------------------------------------
def test_default_combinations_follow_lateral_inputs():
    names=lambda c:[row[0] for row in c.load_combinations()]
    assert names(FrameConfig(lateral_x_kn_per_floor=0))==['G+Q','1.4G+1.6Q']
    both=names(FrameConfig(lateral_x_kn_per_floor=10,lateral_z_kn_per_floor=5))
    assert len(both)==10 and 'G+Q-EZ' in both and '0.9G+EX' in both


def test_schema_migration_v1_v2_to_v3():
    v1=dict(floors=3,bays_x=2,bays_z=1,span_x_m=5.,span_z_m=4.,story_height_m=3.2,
            elastic_modulus_gpa=30.,poisson=.2,unit_weight_kn_m3=25.,beam_width_cm=30.,beam_depth_cm=50.,
            column_width_cm=40.,column_depth_cm=60.,floor_load_kn_m2=5.,lateral_x_kn_per_floor=30.,
            lateral_z_kn_per_floor=0.,self_weight=True,base_support='fixed',model_name='x')
    config=FrameConfig.from_dict(v1)
    assert config.dead_load_kn_m2==5. and config.live_load_kn_m2==0.
    assert config.spans_x_m==(5.,5.) and config.story_heights_m==(3.2,)*3
    # v1/v2 column depth was local y = global X.
    assert config.column_sections_cm==((60.,40.),)
    v2={k:v for k,v in v1.items() if k!='floor_load_kn_m2'}
    v2.update(dead_load_kn_m2=4.,live_load_kn_m2=2.,combinations=[['A',1.,1.,0.,0.]])
    config=FrameConfig.from_dict(v2)
    assert config.combinations==(('A',1.,1.,0.,0.),) and config.live_load_kn_m2==2.
    saved=json.loads(json.dumps(asdict(config)))
    assert FrameConfig.from_dict(saved)==config
    with pytest.raises(ValueError): FrameConfig.from_dict({**v1,'unknown':1})


@pytest.mark.parametrize('combos',[(),(('A',1.,0.,0.,0.),('A',1.,1.,0.,0.)),(('A',float('nan'),0.,0.,0.),),
    (('',1.,0.,0.,0.),),(('A',0.,0.,0.,0.),),(('A',1.,0.,0.),)])
def test_invalid_combinations_rejected(combos):
    with pytest.raises(ValueError): FrameConfig(combinations=combos).validate()


@pytest.mark.parametrize('changes',[{'floors':0},{'bays_x':1.5},{'span_x_m':0},
    {'elastic_modulus_gpa':float('nan')},{'poisson':.5},{'dead_load_kn_m2':-1},{'live_load_kn_m2':-1},
    {'column_width_cm':-10},{'base_support':'unknown'},{'floors':11},{'bays_x':6}])
def test_invalid_regular_input_rejected(changes):
    with pytest.raises(ValueError): build_frame(FrameConfig.regular(**changes))


@pytest.mark.parametrize('changes',[{'spans_x_m':()},{'spans_x_m':(5.,-1.)},{'story_heights_m':(3.,float('inf'))},
    {'column_sections_cm':((40.,40.),(40.,40.))},{'beam_sections_cm':((30.,0.),)},{'rigid_diaphragm':'yes'},
    {'spans_z_m':(31.,)}])
def test_invalid_irregular_input_rejected(changes):
    with pytest.raises(ValueError): replace(FrameConfig(),**changes).validate()
