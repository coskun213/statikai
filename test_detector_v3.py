import csv
import copy
from pathlib import Path
import numpy as np
import pytest
import torch
from PIL import Image
from statikai import lite_detector as lite
from statikai.detector_data import augment,CachedSymbols
from statikai.detector_metrics import score_detailed,aggregate,paired_family_bootstrap
from statikai.detection import iou,annotations
from statikai.independent_benchmark import create_benchmark


def test_class_specific_geometry_round_trip_and_different_class_same_center():
    boxes=[dict(class_id=0,bbox=[100,140,140,180]),dict(class_id=1,bbox=[100,140,140,180]),dict(class_id=2,bbox=[200,30,220,120])]
    heat,geo,mask=lite.targets(boxes,(lite.WIDTH,lite.HEIGHT))
    reg=geo.clone();reg[:,2:]=torch.logit(reg[:,2:].clamp(1e-5,1-1e-5))
    pred=lite.decode((torch.logit(heat.clamp(1e-5,1-1e-5))[None],reg[None]),[(lite.WIDTH,lite.HEIGHT)],.9)[0]
    assert len(pred)==3
    for b in boxes:assert max(iou(p['bbox'],b['bbox']) for p in pred if p['class_id']==b['class_id'])>.999


def test_model_backprop_and_negative_only_loss_are_finite():
    torch.set_num_threads(2);model=lite.LiteFPNCenter()
    for boxes in ([dict(class_id=1,bbox=[250,140,290,180])],[]):
        heat,geo,mask=lite.targets(boxes,(lite.WIDTH,lite.HEIGHT))
        value=lite.loss(model(torch.rand(1,1,lite.HEIGHT,lite.WIDTH)),heat[None],geo[None],mask[None])
        model.zero_grad();value.backward()
        assert torch.isfinite(value) and model.heat[-1].weight.grad.abs().sum()>0


def test_inference_reads_only_image_pixels(monkeypatch):
    model=lite.LiteFPNCenter()
    monkeypatch.setattr(Path,'read_text',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No annotation access')))
    assert isinstance(lite.detect(model,Image.new('RGB',(700,450),'white'),.99),list)


def test_training_augmentation_preserves_classes_bounds_and_seed():
    pixels=np.full((180,260),255,np.uint8)
    boxes=[dict(class_id=1,bbox=[170,100,220,145])];original=copy.deepcopy(boxes)
    a,p=augment(pixels,boxes,np.random.default_rng(123));b,q=augment(pixels,boxes,np.random.default_rng(123))
    assert np.array_equal(a,b) and p==q and boxes==original
    assert p[0]['class_id']==1
    x0,y0,x1,y1=p[0]['bbox'];assert 0<=x0<x1<=260 and 0<=y0<y1<=180
    assert pixels.min()==255 and a.dtype==np.float32 and 0<=a.min()<=a.max()<=1


def test_metrics_count_misses_confusions_and_negative_false_alarms():
    truth=[dict(class_id=1,bbox=[0,0,10,10])]
    wrong=[dict(class_id=0,bbox=[0,0,10,10],score=.9)]
    detail=score_detailed(wrong,truth)
    assert detail['count'].tolist()==[[0,1,0],[0,0,1],[0,0,0]]
    rows=[dict(image='a',problem_id='1'),dict(image='b',problem_id='2')]
    report,_=aggregate(rows,{'a':wrong,'b':wrong},{'a':truth,'b':[]})
    assert report['f1']==0 and report['mean_best_class_iou_all_gt']==0 and report['mean_iou_matched_tp'] is None
    assert report['negative_false_alarm_rate']==1


def test_fresh_benchmark_groups_profiles_references_and_no_overwrite(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'ground_truth.csv').write_text('L_m,P1_kN,x1_m,P2_kN,x2_m\n10,8,3,6,7\n')
    target=tmp_path/'fresh';result=create_benchmark(target,source,2,999,4)
    assert result['positive_images']==12 and result['negative_images']==4
    with (target/'ground_truth.csv').open() as f:rows=list(csv.DictReader(f))
    for row in rows:
        boxes=annotations(target,row)
        assert len(boxes)==(0 if row['negative']=='True' else 4)
    assert len({r['problem_id'] for r in rows if r['negative']=='False'})==2
    assert len({r['condition'] for r in rows if r['negative']=='False'})==6
    with pytest.raises(FileExistsError):create_benchmark(target,source,2,999,4)


def test_validation_dataset_is_deterministic_and_unaugmented(tmp_path):
    (tmp_path/'labels').mkdir();(tmp_path/'images').mkdir()
    Image.new('RGB',(300,200),'white').save(tmp_path/'images/a.png')
    (tmp_path/'labels/a.txt').write_text('1 .5 .5 .1 .2\n')
    rows=[dict(image='images/a.png',symbol_labels='labels/a.txt')]
    ds=CachedSymbols(tmp_path,rows,lite.WIDTH,lite.HEIGHT,lite.targets,training=False)
    ds.epoch=1;first=ds[0];ds.epoch=5;last=ds[0]
    assert len(ds)==1 and all(torch.equal(a,b) for a,b in zip(first,last))


def test_paired_bootstrap_equal_methods_have_zero_difference():
    data=[dict(problem_id=str(i//2),tp=3,fp=1,fn=1) for i in range(6)]
    result=paired_family_bootstrap(data,data,100)
    assert result['clusters']==3 and result['paired_f1_difference_ci']==[0.,0.]
