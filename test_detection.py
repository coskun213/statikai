import numpy as np
from PIL import Image,ImageDraw
import pytest
import torch
from statikai.detection import classical_detect,iou,score_image
from statikai.detector_model import TinyDetector,make_target,decode_batch,detection_loss,learned_detect,WIDTH,HEIGHT


def test_one_to_one_matching_counts_duplicate_as_false_positive():
    truth=[dict(class_id=0,bbox=[10,10,30,30])]
    prediction=[dict(class_id=0,bbox=[10,10,30,30],score=.9)]*2
    assert score_image(prediction,truth).tolist()==[[1,1,0],[0,0,0],[0,0,0]]
    assert score_image([dict(class_id=1,bbox=[10,10,30,30],score=.9)],truth).tolist()==[[0,0,1],[0,1,0],[0,0,0]]


def test_box_geometry_round_trip_and_empty_image():
    source=(800,450)
    boxes=[dict(class_id=0,bbox=[80,220,120,260]),dict(class_id=2,bbox=[290,100,310,210])]
    heat,geo,mask=make_target(boxes,source)
    logits=torch.logit(heat.clamp(.00001,.99999)).unsqueeze(0)
    prediction=geo.clone()
    prediction[2:]=torch.logit(prediction[2:].clamp(.00001,.99999))
    decoded=decode_batch((logits,prediction.unsqueeze(0)),[source],.9)[0]
    assert len(decoded)==2
    for b in boxes:
        assert max(iou(b['bbox'],p['bbox']) for p in decoded if p['class_id']==b['class_id'])>.99
    assert classical_detect(Image.new('RGB',(640,360),'white'))==[]


def test_classical_finds_arrow_from_pixels_without_annotation_access(monkeypatch):
    im=Image.new('RGB',(600,350),'white');draw=ImageDraw.Draw(im)
    draw.line((60,180,540,180),fill='black',width=5)
    draw.line((250,80,250,165),fill='black',width=3)
    draw.polygon([(250,177),(240,160),(260,160)],fill='black')
    from pathlib import Path
    monkeypatch.setattr(Path,'read_text',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('labels unavailable')))
    found=classical_detect(im)
    assert any(p['class_id']==2 and iou(p['bbox'],[238,78,262,179])>.7 for p in found)


def test_full_image_model_loss_backprop_and_inference_have_no_oracle(monkeypatch):
    torch.set_num_threads(2)
    model=TinyDetector()
    heat,geo,mask=make_target([dict(class_id=2,bbox=[100,30,120,100])],(WIDTH,HEIGHT))
    prediction=model(torch.rand(1,1,HEIGHT,WIDTH))
    assert prediction[0].shape==(1,3,HEIGHT//4,WIDTH//4)
    loss=detection_loss(prediction,heat[None],geo[None],mask[None])
    loss.backward()
    assert torch.isfinite(loss) and model.heat.weight.grad.abs().sum()>0
    from pathlib import Path
    monkeypatch.setattr(Path,'read_text',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('labels unavailable')))
    found=learned_detect(model,Image.new('RGB',(640,360),'white'),.99)
    assert isinstance(found,list)
