"""Audit-only probes; never modify project code, weights or old experiment outputs."""
from pathlib import Path
import sys,os,json,subprocess,time,hashlib,shutil,importlib,importlib.metadata as md,ast
ROOT=Path(r'C:\Users\HP\Documents\Codex\2026-11-08\t\outputs\StatikAI')
OUT=ROOT/'audit_results/son_durum_20261108_01'
sys.path.insert(0,str(ROOT))
os.environ['MPLCONFIGDIR']=str(OUT/'matplotlib_cache')
ENV=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf8')
def save(name,data): (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf8')
def command(name,args,cwd=ROOT,timeout=120):
    start=time.perf_counter()
    try:
        r=subprocess.run([sys.executable,*args],cwd=cwd,env=ENV,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=timeout)
        (OUT/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8')
        result=dict(command=[sys.executable,*args],cwd=str(cwd),exit_code=r.returncode,seconds=time.perf_counter()-start,status='BAŞARILI' if r.returncode==0 else 'BAŞARISIZ')
    except subprocess.TimeoutExpired as e:
        result=dict(command=[sys.executable,*args],cwd=str(cwd),status='ÇALIŞTIRILAMADI',error='timeout',seconds=time.perf_counter()-start)
    save(name+'.json',result);return result

def dependencies():
    from pip._vendor.packaging.requirements import Requirement
    from pip._vendor.packaging.markers import default_environment
    rows=[]
    for filename in ('requirements.txt','requirements-desktop.txt'):
        for line in (ROOT/filename).read_text(encoding='utf8').splitlines():
            if not line.strip() or line.lstrip().startswith('#'):continue
            r=Requirement(line); active=r.marker is None or r.marker.evaluate()
            version=md.version(r.name) if active else None
            rows.append(dict(file=filename,requirement=line,active=active,installed=version,status=('BAŞARILI' if version in r.specifier else 'BAŞARISIZ') if active else 'ÇALIŞTIRILAMADI'))
    imports={}
    for name in ('PIL','numpy','pandas','sklearn','torch','cv2','Pynite','matplotlib','tkinter'):
        try: m=importlib.import_module(name);imports[name]=dict(status='BAŞARILI',version=getattr(m,'__version__',None))
        except Exception as e:imports[name]=dict(status='BAŞARISIZ',error=repr(e))
    parsed=[]
    for p in sorted(list(ROOT.glob('*.py'))+list((ROOT/'statikai').glob('*.py'))+list((ROOT/'tools').glob('*.py'))):
        ast.parse(p.read_text(encoding='utf-8-sig'));parsed.append(str(p.relative_to(ROOT)))
    save('dependencies.json',dict(python=sys.version,executable=sys.executable,platform=sys.platform,requirements=rows,imports=imports,parsed_sources=parsed,pynite_requires=md.requires('PyniteFEA')))
    print(json.dumps(command('pip_check',['-m','pip','check']),ensure_ascii=False))
    print('Dependencies and AST checked:',len(parsed))

def benchmark():
    import torch
    from PIL import Image
    from statikai.detector_model import TinyDetector
    from train_detector import predict_rows
    from statikai.detection import records,evaluate_rows,classical_detect
    from train_pilot import TinyCNN
    torch.set_num_threads(2)
    protocol=json.loads((ROOT/'detector_results/evaluation/frozen_protocol.json').read_text())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(ROOT/'detector_results/best_full_image_detector.pt')==protocol['checkpoint_sha256']
    assert digest(ROOT/'dataset_extended/ground_truth.csv')==protocol['data_csv_sha256']
    checkpoint=torch.load(ROOT/'detector_results/best_full_image_detector.pt',map_location='cpu',weights_only=True)
    model=TinyDetector();model.load_state_dict(checkpoint['model_state'])
    pilot=torch.load(ROOT/'pilot_results/best_patch_cnn.pt',map_location='cpu',weights_only=True)
    patch=TinyCNN();patch.load_state_dict(pilot['model_state'])
    save('checkpoints.json',{name:dict(keys=list(ck),metadata={k:v for k,v in ck.items() if k!='model_state'},parameters=sum(p.numel() for p in network.parameters()),sha256=digest(ROOT/path)) for name,ck,network,path in [('patch',pilot,patch,'pilot_results/best_patch_cnn.pt'),('full_image',checkpoint,model,'detector_results/best_full_image_detector.pt')]})
    rows=records(ROOT/'dataset_extended','test')
    predictions={'learned':predict_rows(model,ROOT/'dataset_extended',rows,protocol['learned']['score_threshold']),'classical':{}}
    for row in rows:
        with Image.open(ROOT/'dataset_extended'/row['image']) as image:
            predictions['classical'][row['image']]=classical_detect(image,protocol['classical']['fill_cutoff'])
    actual={}
    stored=json.loads((ROOT/'detector_results/evaluation/metrics.json').read_text())
    for method,p in predictions.items():
        report,details=evaluate_rows(rows,p,ROOT/'dataset_extended')
        report['by_style']={style:evaluate_rows([r for r in rows if r['style']==style],p,ROOT/'dataset_extended')[0] for style in ('A','B')}
        for key in ('tp','fp','fn','precision','recall','f1','exact_image_rate'):assert abs(report[key]-stored['methods'][method][key])<1e-12,(method,key)
        actual[method]=report
    save('frozen_test_recomputed.json',dict(status='BAŞARILI',selection='existing frozen protocol only; no validation selection or training',images=len(rows),families=len({r['problem_id'] for r in rows}),methods=actual))
    save('frozen_test_predictions.json',predictions)
    print('Frozen benchmark reproduced, 250 images; no threshold changes')
    print(json.dumps(command('pilot_shift',['test_visual_shift.py','--out',str(OUT/'pilot_shift.csv')]),ensure_ascii=False))

def datasets():
    print(json.dumps(command('dataset_original',['audit_dataset.py','--dataset','dataset','--out',str(OUT/'dataset_original_audit.json')]),ensure_ascii=False),flush=True)
    print(json.dumps(command('dataset_extended',['audit_dataset.py','--dataset','dataset_extended','--out',str(OUT/'dataset_extended_audit.json')]),ensure_ascii=False),flush=True)

def desktop():
    isolated=OUT/'desktop_copy';isolated.mkdir()
    shutil.copy2(ROOT/'statikai_desktop.py',isolated/'statikai_desktop.py')
    shutil.copytree(ROOT/'statikai',isolated/'statikai',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'examples',isolated/'examples')
    (isolated/'tools').mkdir();shutil.copy2(ROOT/'tools/verify_desktop.py',isolated/'tools/verify_desktop.py')
    (isolated/'audit_results').mkdir()
    print(json.dumps(command('desktop_integration',['tools/verify_desktop.py'],isolated),ensure_ascii=False),flush=True)
    print(json.dumps(command('desktop_gui',['statikai_desktop.py','--smoke-test'],isolated,timeout=45),ensure_ascii=False),flush=True)


def probes():
    import numpy as np
    from collections import defaultdict,Counter
    from train_pilot import Patches
    fingerprints={};counts={};families={}
    for split in ('train','val','test'):
        ds=Patches(ROOT/'dataset',split);table=defaultdict(list)
        for ar,cls,pid in ds.samples:
            table[hashlib.sha256(ar.tobytes()).hexdigest()].append((cls,pid))
        fingerprints[split]=table;counts[split]=len(ds);families[split]=len({r[2] for r in ds.samples})
    overlaps={}
    for a,b in [('train','val'),('train','test'),('val','test')]:
        common=set(fingerprints[a])&set(fingerprints[b])
        duplicates=[entry for h in common for entry in fingerprints[b][h]]
        overlaps[a+'_'+b]=dict(shared_unique_input_hashes=len(common),later_split_samples_already_seen=len(duplicates),
            total_later_split_samples=counts[b],by_class=dict(Counter(str(c) for c,p in duplicates)),
            fraction=len(duplicates)/counts[b],conflicting_labels=sum(len({c for c,p in fingerprints[a][h]+fingerprints[b][h]})>1 for h in common))
    save('patch_input_duplicates.json',dict(status='BAŞARISIZ' if overlaps['train_test']['shared_unique_input_hashes'] else 'BAŞARILI',
        hash_scope='exact RGB uint8 48x48 inputs from Patches before float conversion; includes GT crop and resize',
        split_counts=counts,base_families=families,overlaps=overlaps))
    print('PATCH_DUPLICATES',json.dumps(overlaps,ensure_ascii=False),flush=True)
    inputs=OUT/'image_only';inputs.mkdir()
    inference=[]
    for style,variant in [('A',0),('B',3)]:
        source=ROOT/f'dataset_extended/images/beam_0009_v{variant}.png'
        image=inputs/(style+'.png');shutil.copy2(source,image)
        for method in ('classical','learned'):
            name='cli_'+style+'_'+method;target=OUT/(name+'_output.json')
            result=command(name,['detect_image.py','--image',str(image),'--method',method,'--out',str(target)])
            if result['exit_code']==0:
                data=json.loads(target.read_text());result.update(symbols=len(data['symbols']),scope=data['scope'],ocr=data['ocr_status'],RA=data['RA_kN'],RB=data['RB_kN'])
                assert data['RA_kN'] is None and data['RB_kN'] is None and data['ocr_status']=='not_implemented'
            inference.append(result)
    protocol=json.loads((ROOT/'detector_results/evaluation/frozen_protocol.json').read_text());protocol['checkpoint_sha256']='0'*64
    bad=OUT/'mismatched_protocol.json';save(bad.name,protocol)
    guard=command('cli_mismatched_checkpoint',['detect_image.py','--image',str(inputs/'A.png'),'--method','learned','--protocol',str(bad),'--out',str(OUT/'should_not_exist.json')])
    guard['status']='BAŞARILI' if guard['exit_code']!=0 and 'does not match' in (OUT/'cli_mismatched_checkpoint.log').read_text() else 'BAŞARISIZ'
    guard['expectation']='mismatched checkpoint/protocol must be rejected';save('cli_mismatch_guard.json',guard)
    save('inference_summary.json',dict(image_only_directory_has_no_annotations=not list(inputs.glob('*.txt')) and not list(inputs.glob('*.csv')),runs=inference,guard=guard))
    # Demonstrate overwrite risk ONLY in an audit-owned toy directory.
    from generate_dataset import generate
    toy=OUT/'overwrite_probe';generate(toy,1,2209)
    target=toy/'ground_truth.csv';target.write_text('AUDIT_SENTINEL',encoding='utf8')
    generate(toy,1,2209)
    overwritten=target.read_text(encoding='utf8')!='AUDIT_SENTINEL'
    save('overwrite_guard.json',dict(status='BAŞARISIZ' if overwritten else 'BAŞARILI',
        expected='existing data should be protected',actual='generate_dataset.generate replaced existing ground_truth.csv' if overwritten else 'protected',
        scope='isolated audit toy directory; original dataset unchanged'))
    print('CLI audits done; legacy generator overwrite reproduced in isolated toy only')

if __name__=='__main__':globals()[sys.argv[1]]()
