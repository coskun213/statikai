"""Reproducible integration checks on examples, never on the user's photographs."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from statikai.frame3d import SCHEMA,FrameConfig,solve_frame
from statikai.gui.app import PRESETS


def hand_vertical_total(c):
    """Independent G+Q vertical load: slab area loads + gross member self weight."""
    plan=sum(c.spans_x_m)*sum(c.spans_z_m)
    slab=c.floors*plan*(c.dead_load_kn_m2+c.live_load_kn_m2)
    if not c.self_weight:
        return slab,0.
    own=0.
    lines_x=(c.bays_z+1)*sum(c.spans_x_m);lines_z=(c.bays_x+1)*sum(c.spans_z_m)
    columns=(c.bays_x+1)*(c.bays_z+1)
    for floor,h in enumerate(c.story_heights_m,1):
        ax,az=c.column_section(floor);bb,bh=c.beam_section(floor)
        own+=c.unit_weight_kn_m3*(columns*h*ax*az/1e4+(lines_x+lines_z)*bb*bh/1e4)
    return slab,own


def main():
    cases={
        'ornek_beton':PRESETS['concrete'],
        'ornek_ahsap':PRESETS['timber'],
        'ornek_duzensiz_diyaframli':PRESETS['irregular'],
        'ornek_mafsalli_cift_yon':FrameConfig.regular(floors=2,bays_x=1,bays_z=1,
            base_support='pinned',lateral_x_kn_per_floor=10,lateral_z_kn_per_floor=-7)}
    target=ROOT/'audit_results'/'desktop';target.mkdir(exist_ok=True,parents=True)
    examples=ROOT/'examples';examples.mkdir(exist_ok=True)
    summaries={}
    for name,c in cases.items():
        result=solve_frame(c)
        slab,own=hand_vertical_total(c)
        vertical_reaction=sum(r['fy_kn'] for r in result['results']['G+Q']['reactions'])
        assert abs(vertical_reaction-slab-own)<1e-6*max(1.,slab+own)
        tolerance=1e-4 if c.rigid_diaphragm else 1e-6
        assert max(abs(v) for v in result['force_residual_kn'])<tolerance
        assert max(abs(v) for v in result['moment_residual_knm'])<10*tolerance
        (target/f'{name}_sonuc.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
        (examples/f'{name}.json').write_text(json.dumps(dict(schema=SCHEMA,config=asdict(c)),
                                                        indent=2,ensure_ascii=False),encoding='utf8')
        summaries[name]={k:result[k] for k in ('solver','max_displacement_mm','force_residual_kn',
                                               'moment_residual_knm','elapsed_seconds')}
        summaries[name].update(nodes=len(result['nodes']),members=len(result['members']),
            diaphragm_links=len(result['diaphragm_links']),slab_load_kn=slab,member_self_weight_kn=own,
            sum_vertical_reactions_kn=vertical_reaction,source='example_parameters_not_photos')
    (target/'integration_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
