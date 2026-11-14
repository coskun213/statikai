import csv
import math
from pathlib import Path
import subprocess
import sys
import pytest
from evaluate_equilibrium import evaluate
from generate_dataset import fonts, reactions
from statikai.physics import residuals


@pytest.mark.parametrize('values', [
    (0,8,3,6,7), (10,-8,3,6,7), (10,8,7,6,3), (10,8,12,6,13),
    (float('nan'),8,3,6,7), (10,float('inf'),3,6,7), (10,8,None,6,7)])
def test_invalid_physics_is_rejected(values):
    with pytest.raises(ValueError): reactions(*values)


def test_validation_survives_python_optimized_mode():
    result=subprocess.run([sys.executable,'-O','-c',
        'from generate_dataset import reactions; reactions(10,8,12,6,13)'],capture_output=True,text=True)
    assert result.returncode!=0 and 'ValueError' in result.stderr


def test_symmetric_and_mirror_properties():
    assert reactions(10,5,2,5,8)==(5,5)
    a,b=reactions(12,7,2,9,8)
    mirrored=reactions(12,9,4,7,10)
    assert mirrored==pytest.approx((b,a))


def test_wrong_reading_can_be_self_consistent():
    wrong=reactions(10,8,4,6,7)
    assert residuals(10,8,4,6,7,*wrong)==pytest.approx((0,0),abs=1e-12)
    assert abs(residuals(10,8,3,6,7,*wrong)[1])>1


def prediction_file(tmp_path, values, count=1):
    root=Path(__file__).parent
    with (root/'dataset/ground_truth.csv').open(encoding='utf8') as handle:
        first=next(csv.DictReader(handle))
    path=tmp_path/'pred.csv'
    with path.open('w',newline='',encoding='utf8') as handle:
        writer=csv.DictWriter(handle,fieldnames=['image','predicted_RA_kN','predicted_RB_kN'])
        writer.writeheader()
        for _ in range(count):
            writer.writerow(dict(image=first['image'],predicted_RA_kN=values[0],predicted_RB_kN=values[1]))
    return root/'dataset/ground_truth.csv',path,first


@pytest.mark.parametrize('values', [('nan','nan'),('inf',1)])
def test_nonfinite_predictions_rejected(tmp_path, values):
    truth,pred,_=prediction_file(tmp_path,values)
    with pytest.raises(ValueError,match='finite'):
        evaluate(truth,pred,tmp_path/'out.csv')


def test_duplicate_and_empty_predictions_rejected(tmp_path):
    truth,pred,_=prediction_file(tmp_path,(1,1),2)
    with pytest.raises(ValueError,match='duplicate'): evaluate(truth,pred,tmp_path/'out.csv')
    truth,pred,_=prediction_file(tmp_path,(1,1),0)
    with pytest.raises(ValueError,match='data rows'): evaluate(truth,pred,tmp_path/'out.csv')


def test_missing_predictions_do_not_inflate_full_accuracy(tmp_path):
    truth,pred,first=prediction_file(tmp_path,(1,1))
    truth,pred,_=prediction_file(tmp_path,(first['RA_kN'],first['RB_kN']))
    report=evaluate(truth,pred,tmp_path/'out.csv')
    assert report['coverage']==1/200
    assert report['conditional_solution_accuracy']==1
    assert report['full_truth_solution_accuracy']==1/200


def test_font_is_available_without_linux_path():
    assert fonts(18).getbbox('10 kN')[2]>0
