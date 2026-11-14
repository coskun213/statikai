from collections import Counter
import csv
from pathlib import Path
import pytest
from audit_dataset import audit
from generate_extended_dataset import generate_extended


def test_extended_qa_and_controlled_interventions(tmp_path):
    rows=generate_extended(tmp_path/'generated',10,12345)
    result=audit(tmp_path/'generated')
    assert result['passed'], result['errors']
    assert result['images']==50 and result['unique_physical_configurations']==20
    assert result['styles']=={'A':40,'B':10}
    assert len({r['beam_left_px'] for r in rows})>1
    assert len({(r['width_px'],r['height_px']) for r in rows})>1
    with pytest.raises(FileExistsError): generate_extended(tmp_path/'generated',10,12345)


def test_qa_detects_cross_split_family_leakage(tmp_path):
    root=tmp_path/'generated'
    generate_extended(root,10,12345)
    path=root/'ground_truth.csv'
    with path.open(encoding='utf8',newline='') as handle:
        rows=list(csv.DictReader(handle))
    rows[1]['split']='test'
    with path.open('w',encoding='utf8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    result=audit(root)
    assert not result['passed'] and any('crosses splits' in e for e in result['errors'])


def test_qa_rejects_wrong_reference_and_invalid_box(tmp_path):
    root=tmp_path/'generated'
    generate_extended(root,10,555)
    path=root/'ground_truth.csv'
    with path.open(encoding='utf8',newline='') as handle:
        rows=list(csv.DictReader(handle))
    rows[0]['RA_kN']='999'
    with path.open('w',encoding='utf8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    labels=root/rows[0]['symbol_labels']
    labels.write_text('0 -1 0.5 0.1 0.1\n1 0.8 0.6 0.1 0.1\n2 0.3 0.3 0.1 0.2\n2 0.6 0.3 0.1 0.2\n')
    result=audit(root)
    assert not result['passed']
    assert any('wrong reaction' in e for e in result['errors'])
    assert any('out-of-image' in e for e in result['errors'])
