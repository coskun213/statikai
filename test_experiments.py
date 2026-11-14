import csv, tempfile
from pathlib import Path
from train_pilot import Patches, TinyCNN
from evaluate_equilibrium import evaluate
from generate_dataset import generate

def test_patches_and_model_shapes():
    with tempfile.TemporaryDirectory() as d:
        generate(d,10,2026)
        ds=Patches(d,'train'); x,c=ds[0]
        assert x.shape==(3,48,48)
        assert TinyCNN()(x.unsqueeze(0)).shape==(1,4)
        assert set(z[2] for z in ds.samples).isdisjoint(set(z[2] for z in Patches(d,'test').samples))

def test_oracle_prediction_evaluation():
    with tempfile.TemporaryDirectory() as d:
        generate(d,10,2026);truth=Path(d)/'ground_truth.csv'
        rows=list(csv.DictReader(truth.open(encoding='utf8')))
        preds=Path(d)/'pred.csv'; out=Path(d)/'scored.csv'
        with preds.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['image','predicted_RA_kN','predicted_RB_kN']);writer.writeheader()
            for r in rows:
                writer.writerow({'image':r['image'],'predicted_RA_kN':r['RA_kN'],'predicted_RB_kN':r['RB_kN']})
        evaluate(truth,preds,out)
        scored=list(csv.DictReader(out.open()))
        assert all(float(s['max_abs_reaction_error_kN'])==0 for s in scored)
        assert all(s['physics_flag_0_1']=='0' for s in scored)
