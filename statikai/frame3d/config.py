"""Frame input model (schema v3) and migration of older regular-grid files.

Geometry is an orthogonal grid: one span list per plan direction and one
height per storey, so spans and storey heights may differ. Sections are given
per storey (one entry = same section on every storey).

Column sections are written as (dimension along global X, dimension along
global Z) in cm, so the orientation in plan is always explicit.
Beam sections are (width b, depth h) in cm.
"""
from dataclasses import asdict, dataclass, fields
import math

SCHEMA='statikai_frame_v3'
LEGACY_SCHEMAS=('statikai_regular_frame_v1','statikai_regular_frame_v2')
CASES=('G','Q','EX','EZ')
MAX_FLOORS=10
MAX_BAYS=5
MAX_COMBINATIONS=30
TUPLE_FIELDS=('spans_x_m','spans_z_m','story_heights_m','beam_sections_cm','column_sections_cm')
LEGACY_GEOMETRY=('floors','bays_x','bays_z','span_x_m','span_z_m','story_height_m',
                 'beam_width_cm','beam_depth_cm','column_width_cm','column_depth_cm')


def is_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def default_combinations(lateral_x=1.,lateral_z=0.):
    """TS 500 / TBDY 2018 style set as (name, G, Q, EX, EZ) factor rows.

    Lateral combinations are generated only for a non-zero lateral input.
    E is the user's lateral force, not a code-generated seismic load.
    """
    combos=[('G+Q',1.,1.,0.,0.),('1.4G+1.6Q',1.4,1.6,0.,0.)]
    for case,value in (('EX',lateral_x),('EZ',lateral_z)):
        if not value:
            continue
        ex,ez=(1.,0.) if case=='EX' else (0.,1.)
        for prefix,gravity,live in (('G+Q',1.,1.),('0.9G',.9,0.)):
            for sign in (1.,-1.):
                symbol='+' if sign>0 else '-'
                combos.append((f'{prefix}{symbol}{case}',gravity,live,sign*ex,sign*ez))
    return tuple(combos)


def validate_combinations(combos):
    if not isinstance(combos,tuple) or not 1<=len(combos)<=MAX_COMBINATIONS:
        raise ValueError(f'1 ile {MAX_COMBINATIONS} arasinda yuk kombinasyonu tanimlanmali.')
    names=set()
    for row in combos:
        if not isinstance(row,tuple) or len(row)!=5:
            raise ValueError('Her kombinasyon: ad, G, Q, EX, EZ katsayilarindan olusmali.')
        name,*factors=row
        if not isinstance(name,str) or not name.strip() or len(name)>40:
            raise ValueError('Kombinasyon adi bos olamaz (en fazla 40 karakter).')
        if name in names:
            raise ValueError(f'Kombinasyon adi tekrar ediyor: {name}')
        names.add(name)
        for value in factors:
            if not is_number(value):
                raise ValueError(f'{name}: katsayilar sonlu sayi olmali.')
            if abs(value)>10:
                raise ValueError(f'{name}: katsayi mutlak degeri 10 u asamaz.')
        if not any(factors):
            raise ValueError(f'{name}: en az bir katsayi sifirdan farkli olmali.')


def _as_tuple(value):
    if isinstance(value,(list,tuple)):
        return tuple(_as_tuple(v) for v in value)
    return value


@dataclass(frozen=True)
class FrameConfig:
    spans_x_m: tuple=(5.,5.)
    spans_z_m: tuple=(4.,4.)
    story_heights_m: tuple=(3.,)*6
    elastic_modulus_gpa: float=30.
    poisson: float=.2
    unit_weight_kn_m3: float=25.
    beam_sections_cm: tuple=((30.,50.),)
    column_sections_cm: tuple=((40.,40.),)
    dead_load_kn_m2: float=4.5
    live_load_kn_m2: float=2.
    lateral_x_kn_per_floor: float=30.
    lateral_z_kn_per_floor: float=0.
    self_weight: bool=True
    base_support: str='fixed'
    rigid_diaphragm: bool=False
    combinations: tuple|None=None
    model_name: str='Ornek 3B cerceve — goruntuden cikarilmadi'

    # ---- derived geometry -------------------------------------------
    @property
    def floors(self): return len(self.story_heights_m)

    @property
    def bays_x(self): return len(self.spans_x_m)

    @property
    def bays_z(self): return len(self.spans_z_m)

    def grid_x(self): return _cumulative(self.spans_x_m)

    def grid_z(self): return _cumulative(self.spans_z_m)

    def levels(self): return _cumulative(self.story_heights_m)

    def beam_section(self,floor):
        """(b, h) cm of the beams on storey ``floor`` (1-based)."""
        return self.beam_sections_cm[0 if len(self.beam_sections_cm)==1 else floor-1]

    def column_section(self,floor):
        """(along X, along Z) cm of the columns below level ``floor`` (1-based)."""
        return self.column_sections_cm[0 if len(self.column_sections_cm)==1 else floor-1]

    def load_combinations(self):
        if self.combinations is not None:
            return self.combinations
        return default_combinations(self.lateral_x_kn_per_floor,self.lateral_z_kn_per_floor)

    # ---- construction -----------------------------------------------
    @classmethod
    def regular(cls,floors=6,bays_x=2,bays_z=2,span_x_m=5.,span_z_m=4.,story_height_m=3.,
                beam_width_cm=30.,beam_depth_cm=50.,column_width_cm=40.,column_depth_cm=40.,**rest):
        """Uniform grid, the v1/v2 input style.

        In v1/v2 the column width was the local-z (global Z) size and the depth
        the local-y (global X) size; that orientation is preserved here.
        """
        for name,value in (('floors',floors),('bays_x',bays_x),('bays_z',bays_z)):
            if isinstance(value,bool) or not isinstance(value,int):
                raise ValueError(f'{name}: tam sayi olmali.')
        return cls(spans_x_m=(float(span_x_m),)*bays_x,spans_z_m=(float(span_z_m),)*bays_z,
                   story_heights_m=(float(story_height_m),)*floors,
                   beam_sections_cm=((float(beam_width_cm),float(beam_depth_cm)),),
                   column_sections_cm=((float(column_depth_cm),float(column_width_cm)),),**rest)

    @classmethod
    def from_dict(cls,values):
        """Build from saved JSON; migrates v1 (single area load) and v1/v2 regular grids."""
        values=dict(values)
        if 'floor_load_kn_m2' in values:
            values.setdefault('dead_load_kn_m2',values.pop('floor_load_kn_m2'))
            values.setdefault('live_load_kn_m2',0.)
        if values.get('combinations') is not None:
            values['combinations']=_as_tuple(values['combinations'])
        known={f.name for f in fields(cls)}
        legacy={k:values.pop(k) for k in LEGACY_GEOMETRY if k in values}
        unknown=set(values)-known
        if unknown:
            raise ValueError('Bilinmeyen model alanlari: '+', '.join(sorted(unknown)))
        if legacy:
            return cls.regular(**legacy,**values)
        for key in TUPLE_FIELDS:
            if key in values:
                values[key]=_as_tuple(values[key])
        return cls(**values)

    def to_dict(self):
        return asdict(self)

    # ---- validation -------------------------------------------------
    def validate(self):
        for name,items,limit in (('Kat yukseklikleri',self.story_heights_m,MAX_FLOORS),
                                 ('X acikliklari',self.spans_x_m,MAX_BAYS),
                                 ('Z acikliklari',self.spans_z_m,MAX_BAYS)):
            if not isinstance(items,tuple) or not 1<=len(items)<=limit:
                raise ValueError(f'{name}: 1 ile {limit} arasinda deger girilmeli.')
            for value in items:
                if not is_number(value) or not 0<value<=30:
                    raise ValueError(f'{name}: her deger 0 ile 30 m arasinda sonlu sayi olmali.')
        for name,items in (('Kiris kesitleri',self.beam_sections_cm),('Kolon kesitleri',self.column_sections_cm)):
            if not isinstance(items,tuple) or len(items) not in (1,self.floors):
                raise ValueError(f'{name}: tek kesit ya da her kat icin bir kesit ({self.floors}) girilmeli.')
            for pair in items:
                if not isinstance(pair,tuple) or len(pair)!=2 or not all(is_number(v) and 0<v<=300 for v in pair):
                    raise ValueError(f'{name}: boyutlar 0 ile 300 cm arasinda olmali.')
        for key in ('elastic_modulus_gpa','poisson','unit_weight_kn_m3','dead_load_kn_m2',
                    'live_load_kn_m2','lateral_x_kn_per_floor','lateral_z_kn_per_floor'):
            if not is_number(getattr(self,key)):
                raise ValueError(f'{key}: sonlu bir sayi girilmeli.')
        if self.elastic_modulus_gpa<=0:
            raise ValueError('Elastisite modulu sifirdan buyuk olmali.')
        if not 0<self.poisson<.49:
            raise ValueError('Poisson orani 0 ile 0.49 arasinda olmali.')
        if self.dead_load_kn_m2<0 or self.live_load_kn_m2<0 or self.unit_weight_kn_m3<0:
            raise ValueError('Alan yukleri ve birim hacim agirligi negatif olamaz.')
        if self.base_support not in ('fixed','pinned'):
            raise ValueError('Mesnet fixed veya pinned olmali.')
        for key in ('self_weight','rigid_diaphragm'):
            if not isinstance(getattr(self,key),bool):
                raise ValueError(f'{key} boolean olmali.')
        validate_combinations(self.load_combinations())


def _cumulative(values):
    out=[0.]
    for value in values:
        out.append(out[-1]+value)
    return out
