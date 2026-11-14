"""Scientific data contracts and deliberate corruption, not model-score tests."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

import pytest
from audit_dataset import audit
from generate_extended_dataset import generate_extended
from statikai.dataset_v2 import generate_dimensions
from statikai.dataset_v2_audit import parse_quantity


@pytest.fixture(scope='module')
def versioned(tmp_path_factory):
    parent=tmp_path_factory.mktemp('dimension_data')
    source=parent/'source';target=parent/'v2'
    generate_extended(source,10,12345)
    generate_dimensions(target,source,20261109)
    return source,target


def rows_at(path):
    with (path/'ground_truth.csv').open(encoding='utf8',newline='') as f:return list(csv.DictReader(f))


def write_rows(path,rows):
    with (path/'ground_truth.csv').open('w',encoding='utf8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)


def rebind_manifest(path,filename):
    # Simulate a bad annotation produced at authoring time, beyond checksum detection.
    p=path/'manifest.json';manifest=json.loads(p.read_text(encoding='utf8'))
    manifest['files'][filename]=hashlib.sha256((path/filename).read_bytes()).hexdigest()
    p.write_text(json.dumps(manifest),encoding='utf8')


def test_v2_lineage_units_labels_and_split_contract(versioned):
    source,target=versioned
    before=hashlib.sha256((source/'ground_truth.csv').read_bytes()).hexdigest()
    result=audit(target)
    assert result['passed'],result['errors'][:5]
    assert result['split_problems']=={'train':7,'val':2,'test':1}
    assert result['images']==50 and result['boxes']==200
    assert result['unique_physical_configurations']==20
    extended=result['dimensions_v2']
    assert extended['text_raster_checks']==extended['text_annotations']==370
    assert extended['dimension_annotations']==170
    assert len(extended['fonts'])>=2 and len(extended['resolutions'])==3
    assert set(extended['dimension_layouts'])=={'chain_total','datum','chain_only','mixed'}
    assert extended['cross_split_preprocessed_image_hash_leaks']==0
    assert extended['cross_split_symbol_crop_hashes']==0
    assert hashlib.sha256((source/'ground_truth.csv').read_bytes()).hexdigest()==before
    assert {(r['problem_id'],r['variant'],r['split']) for r in rows_at(source)}=={
        (r['problem_id'],r['variant'],r['split']) for r in rows_at(target)}


def test_segment_dimensions_reconstruct_physics_without_parameter_summary(versioned):
    _,target=versioned
    for row in rows_at(target):
        if row['dimension_layout']!='chain_only':continue
        annotation=json.loads((target/row['annotation_json']).read_text(encoding='utf8'))
        lengths=[parse_quantity(annotation['texts'][d['text_index']]['text'])[0] for d in annotation['dimensions']]
        # Only the printed segment measurements are used to reconstruct L/x1/x2.
        assert float(sum(lengths))==pytest.approx(float(row['L_m']),abs=1e-9)
        assert float(lengths[0])==pytest.approx(float(row['x1_m']),abs=1e-9)
        assert float(sum(lengths[:2]))==pytest.approx(float(row['x2_m']),abs=1e-9)
        assert all('=' not in t['text'] for t in annotation['texts'])


def test_controlled_intervention_and_no_overwrite(versioned):
    source,target=versioned
    a=json.loads((target/'annotations/beam_0000_v0.json').read_text())
    b=json.loads((target/'annotations/beam_0000_v4.json').read_text())
    assert a['render']==b['render']
    digest=hashlib.sha256((target/'manifest.json').read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):generate_dimensions(target,source,20261109)
    assert hashlib.sha256((target/'manifest.json').read_bytes()).hexdigest()==digest


def test_same_seed_reproduces_all_dataset_bytes(versioned,tmp_path):
    source,target=versioned;repeat=tmp_path/'repeat'
    generate_dimensions(repeat,source,20261109)
    original=json.loads((target/'manifest.json').read_text())
    new=json.loads((repeat/'manifest.json').read_text())
    assert original==new


@pytest.mark.parametrize('fault,expected',[
    ('reaction','wrong reaction reference'),
    ('split','problem crosses splits'),
    ('duplicate_physics','repeat across families'),
    ('class_swap','YOLO class/bbox'),
    ('dimension_text','wrong dimension text/unit/value'),
    ('force_transcription','text transcription/raster mismatch'),
    ('image_duplicate','resized full-image inputs repeat'),
    ('malformed_label','Malformed or unreadable'),
    ('missing_image','Malformed or unreadable')])
def test_corruptions_are_detected_beyond_file_checksums(versioned,tmp_path,fault,expected):
    _,target=versioned;bad=tmp_path/'bad';shutil.copytree(target,bad)
    rows=rows_at(bad);first=rows[0]
    if fault=='reaction':
        rows[0]['RA_kN']='999';write_rows(bad,rows);rebind_manifest(bad,'ground_truth.csv')
    elif fault=='split':
        rows[1]['split']='test';write_rows(bad,rows);rebind_manifest(bad,'ground_truth.csv')
    elif fault=='duplicate_physics':
        for i in range(5,10):
            for key in ('L_m','P1_kN','x1_m','P2_kN','x2_m','RA_kN','RB_kN'):rows[i][key]=rows[i-5][key]
        write_rows(bad,rows);rebind_manifest(bad,'ground_truth.csv')
    elif fault=='class_swap':
        path=bad/first['symbol_labels'];lines=path.read_text().splitlines()
        lines[0]='1'+lines[0][1:];lines[1]='0'+lines[1][1:]
        path.write_text('\n'.join(lines)+'\n');rebind_manifest(bad,first['symbol_labels'])
    elif fault in ('dimension_text','force_transcription'):
        path=bad/first['annotation_json'];data=json.loads(path.read_text())
        if fault=='dimension_text':data['texts'][data['dimensions'][0]['text_index']]['text']='999 m'
        else:
            t=next(t for t in data['texts'] if t['kind']=='force')
            value,unit=parse_quantity(t['text'])
            t['text']=f'{value} kN' if unit=='N' else f'{value*1000} N'
        path.write_text(json.dumps(data));rebind_manifest(bad,first['annotation_json'])
    elif fault=='image_duplicate':
        heldout=next(r for r in rows if r['split']=='test')
        shutil.copy2(bad/first['image'],bad/heldout['image']);rebind_manifest(bad,heldout['image'])
    elif fault=='malformed_label':(bad/first['symbol_labels']).write_text('not an annotation')
    elif fault=='missing_image':(bad/first['image']).unlink()
    result=audit(bad)
    assert not result['passed']
    assert any(expected in error for error in result['errors']),result['errors'][:8]
