"""PyNite model assembly: nodes, members, sections, diaphragm links and loads.

Units: m, kN, kNm; global Y is vertical.
"""
from dataclasses import asdict
import math

import numpy as np
from Pynite import FEModel3D

from .config import CASES
from .loads import envelope_segments, segment_resultant, tributary_weights

# Rigid diaphragm: pin-ended axial links much stiffer than the frame, placed on
# every panel edge and both diagonals. They make each storey plane rigid in its
# own plane but add no vertical, bending or out-of-plane stiffness. Nodal
# rotations about the vertical axis are not tied together (minor difference to
# a full diaphragm constraint).
DIAPHRAGM_STIFFNESS_FACTOR=1e3
DIAPHRAGM_AREA_M2=1.


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


def node_name(floor,ix,iz):
    return f'N_{floor}_{ix}_{iz}'


class _Builder:
    def __init__(self,config):
        config.validate()
        self.config=config
        self.model=FEModel3D()
        self.nodes=[];self.members=[];self.links=[]
        self.node_loads=[];self.line_loads=[]
        self.sections={}
        self.applied={case:dict(force=np.zeros(3),moment=np.zeros(3)) for case in CASES}
        self.by_name={}

    # ---- helpers ------------------------------------------------------
    def point(self,name):
        n=self.by_name[name]
        return np.array([n['x'],n['y'],n['z']])

    def add_applied(self,case,force,at):
        self.applied[case]['force']+=force
        self.applied[case]['moment']+=np.cross(at,force)

    def section(self,kind,dims):
        """Register a rectangular section once per unique size; returns its name."""
        a,b=dims
        if kind=='COLUMN':
            # PyNite vertical member: local y (depth) lies along global X.
            name=f'COL_{a:g}x{b:g}';props=rectangle_properties(b/100,a/100)
        else:
            name=f'BEAM_{a:g}x{b:g}';props=rectangle_properties(a/100,b/100)
        if name not in self.sections:
            self.model.add_section(name,**props)
            self.sections[name]=dict(props,kind=kind,dims_cm=[a,b])
        return name

    def member(self,name,i,j,kind,section):
        self.model.add_member(name,i,j,'USER',section)
        length=float(np.linalg.norm(self.point(j)-self.point(i)))
        self.members.append(dict(name=name,i=i,j=j,kind=kind,length_m=length,section=section,
                                 dims_cm=self.sections[section]['dims_cm']))

    # ---- stages -------------------------------------------------------
    def materials(self):
        c=self.config
        E=c.elastic_modulus_gpa*1e6  # GPa -> kN/m2
        self.model.add_material('USER',E,E/(2*(1+c.poisson)),c.poisson,c.unit_weight_kn_m3)
        if c.rigid_diaphragm:
            Er=E*DIAPHRAGM_STIFFNESS_FACTOR
            self.model.add_material('RIGID',Er,Er/2.4,.2,0.)
            self.model.add_section('DIAPHRAGM',A=DIAPHRAGM_AREA_M2,Iy=1e-6,Iz=1e-6,J=1e-6)

    def grid(self):
        c=self.config
        xs,zs,ys=c.grid_x(),c.grid_z(),c.levels()
        weights=tributary_weights(c.spans_x_m,c.spans_z_m)
        storey_force={'EX':np.array([c.lateral_x_kn_per_floor,0.,0.]),
                      'EZ':np.array([0.,0.,c.lateral_z_kn_per_floor])}
        fixed=c.base_support=='fixed'
        for floor,y in enumerate(ys):
            for ix,x in enumerate(xs):
                for iz,z in enumerate(zs):
                    name=node_name(floor,ix,iz)
                    self.model.add_node(name,x,y,z)
                    node=dict(name=name,x=x,y=y,z=z,floor=floor,ix=ix,iz=iz,base=floor==0)
                    self.nodes.append(node);self.by_name[name]=node
                    if floor==0:
                        self.model.def_support(name,True,True,True,fixed,fixed,fixed)
                        continue
                    for case,total in storey_force.items():
                        if not total.any():
                            continue
                        vector=total*weights[(ix,iz)]
                        for direction,value in zip(('FX','FY','FZ'),vector):
                            if value:
                                self.model.add_node_load(name,direction,float(value),case=case)
                        self.node_loads.append(dict(node=name,case=case,xyz=[x,y,z],force=vector.tolist()))
                        self.add_applied(case,vector,np.array([x,y,z]))

    def frame_members(self):
        c=self.config
        for floor in range(1,c.floors+1):
            column=self.section('COLUMN',c.column_section(floor))
            beam=self.section('BEAM',c.beam_section(floor))
            for ix in range(c.bays_x+1):
                for iz in range(c.bays_z+1):
                    self.member(f'C_{floor}_{ix}_{iz}',node_name(floor-1,ix,iz),node_name(floor,ix,iz),'column',column)
            for ix in range(c.bays_x):
                for iz in range(c.bays_z+1):
                    self.member(f'BX_{floor}_{ix}_{iz}',node_name(floor,ix,iz),node_name(floor,ix+1,iz),'beam_x',beam)
            for ix in range(c.bays_x+1):
                for iz in range(c.bays_z):
                    self.member(f'BZ_{floor}_{ix}_{iz}',node_name(floor,ix,iz),node_name(floor,ix,iz+1),'beam_z',beam)

    def diaphragm(self):
        c=self.config
        if not c.rigid_diaphragm:
            return
        def link(name,i,j):
            self.model.add_member(name,i,j,'RIGID','DIAPHRAGM')
            # Axial-only: bending released at both ends, torsion at one end.
            self.model.def_releases(name,Rxi=True,Ryi=True,Rzi=True,Ryj=True,Rzj=True)
            self.links.append(dict(name=name,i=i,j=j))
        for floor in range(1,c.floors+1):
            for ix in range(c.bays_x):
                for iz in range(c.bays_z+1):
                    link(f'DX_{floor}_{ix}_{iz}',node_name(floor,ix,iz),node_name(floor,ix+1,iz))
            for ix in range(c.bays_x+1):
                for iz in range(c.bays_z):
                    link(f'DZ_{floor}_{ix}_{iz}',node_name(floor,ix,iz),node_name(floor,ix,iz+1))
            for ix in range(c.bays_x):
                for iz in range(c.bays_z):
                    link(f'DD1_{floor}_{ix}_{iz}',node_name(floor,ix,iz),node_name(floor,ix+1,iz+1))
                    link(f'DD2_{floor}_{ix}_{iz}',node_name(floor,ix+1,iz),node_name(floor,ix,iz+1))

    def slab_loads(self):
        """G and Q area loads -> bordering beams of each panel (45 degree rule)."""
        c=self.config
        by_member={m['name']:m for m in self.members}
        for case,w in (('G',c.dead_load_kn_m2),('Q',c.live_load_kn_m2)):
            if not w:
                continue
            for floor in range(1,c.floors+1):
                for px,lx in enumerate(c.spans_x_m):
                    for pz,lz in enumerate(c.spans_z_m):
                        half=min(lx,lz)/2;peak=w*half
                        edges=[f'BX_{floor}_{px}_{pz}',f'BX_{floor}_{px}_{pz+1}',
                               f'BZ_{floor}_{px}_{pz}',f'BZ_{floor}_{px+1}_{pz}']
                        for beam in edges:
                            item=by_member[beam]
                            for w1,w2,x1,x2 in envelope_segments(item['length_m'],half,peak):
                                self.model.add_member_dist_load(beam,'FY',-w1,-w2,x1,x2,case=case)
                                self.line_loads.append(dict(member=beam,case=case,w1_kn_m=w1,w2_kn_m=w2,
                                                            x1_m=x1,x2_m=x2))
                                force,at=segment_resultant(self.point(item['i']),self.point(item['j']),w1,w2,x1,x2)
                                self.add_applied(case,force,at)

    def self_weight(self):
        c=self.config
        if not c.self_weight:
            return
        # Diaphragm links use a weightless material, so they add nothing here.
        self.model.add_member_self_weight('FY',-1.,case='G')
        for item in self.members:
            centroid=(self.point(item['i'])+self.point(item['j']))/2
            area=self.sections[item['section']]['A']
            self.add_applied('G',np.array([0.,-c.unit_weight_kn_m3*area*item['length_m'],0.]),centroid)

    def combinations(self):
        combos=self.config.load_combinations()
        for name,*factors in combos:
            self.model.add_load_combo(name,{case:float(f) for case,f in zip(CASES,factors) if f})
        return [dict(name=name,factors=dict(zip(CASES,factors))) for name,*factors in combos]

    def build(self):
        self.materials();self.grid();self.frame_members();self.diaphragm()
        self.slab_loads();self.self_weight()
        combos=self.combinations()
        c=self.config
        plan_area=sum(c.spans_x_m)*sum(c.spans_z_m)
        data=dict(config=asdict(c),nodes=self.nodes,members=self.members,diaphragm_links=self.links,
                  node_loads=self.node_loads,line_loads=self.line_loads,sections=self.sections,
                  cases=list(CASES),combinations=combos,
                  slab_area_load_kn={'G':c.dead_load_kn_m2*plan_area*c.floors,
                                     'Q':c.live_load_kn_m2*plan_area*c.floors},
                  applied_by_case={case:dict(force_kn=v['force'].tolist(),moment_knm=v['moment'].tolist())
                                   for case,v in self.applied.items()})
        return self.model,data


def build_frame(config):
    return _Builder(config).build()
