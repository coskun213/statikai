"""Reproducible integration checks on examples, never on the user's photographs."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from statikai.frame3d import FrameConfig,solve_frame


def main():
    cases={
        'ornek_beton':FrameConfig(),
        'ornek_ahsap':FrameConfig(floors=2,bays_x=2,bays_z=1,span_x_m=4,span_z_m=4,
            elastic_modulus_gpa=11,poisson=.3,unit_weight_kn_m3=5,
            beam_width_cm=20,beam_depth_cm=40,column_width_cm=25,column_depth_cm=25,
            floor_load_kn_m2=3,lateral_x_kn_per_floor=5),
        'ornek_mafsalli_cift_yon':FrameConfig(floors=2,bays_x=1,bays_z=1,
            base_support='pinned',lateral_x_kn_per_floor=10,lateral_z_kn_per_floor=-7)}
    target=ROOT/'audit_results'/'desktop';target.mkdir(exist_ok=True,parents=True)
    examples=ROOT/'examples';examples.mkdir(exist_ok=True)
    summaries={}
    for name,c in cases.items():
        result=solve_frame(c)
        floor_weight=c.floors*c.bays_x*c.span_x_m*c.bays_z*c.span_z_m*c.floor_load_kn_m2
        column_length=c.floors*(c.bays_x+1)*(c.bays_z+1)*c.story_height_m
        beam_length=c.floors*(c.bays_x*(c.bays_z+1)*c.span_x_m+(c.bays_x+1)*c.bays_z*c.span_z_m)
        own_weight=c.unit_weight_kn_m3*(column_length*c.column_width_cm*c.column_depth_cm/1e4+
                                      beam_length*c.beam_width_cm*c.beam_depth_cm/1e4) if c.self_weight else 0
        # Independent hand total: no PyNite model/load list is used here.
        vertical_reaction=sum(r['fy_kn'] for r in result['reactions'])
        assert abs(vertical_reaction-floor_weight-own_weight)<1e-6
        assert max(abs(v) for v in result['force_residual_kn'])<1e-6
        assert max(abs(v) for v in result['moment_residual_knm'])<1e-5
        (target/f'{name}_sonuc.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
        (examples/f'{name}.json').write_text(json.dumps(dict(schema='statikai_regular_frame_v1',
            config=asdict(c)),indent=2,ensure_ascii=False),encoding='utf8')
        summaries[name]={k:result[k] for k in ('solver','max_displacement_mm','force_residual_kn',
                                               'moment_residual_knm','elapsed_seconds')}
        summaries[name].update(nodes=len(result['nodes']),members=len(result['members']),
            floor_weight_kn=floor_weight,member_self_weight_kn=own_weight,
            sum_vertical_reactions_kn=vertical_reaction,source='example_parameters_not_photos')
    (target/'integration_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf8')
    print(json.dumps(summaries,indent=2))


if __name__=='__main__':main()
