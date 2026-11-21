"""Verify real payloads, paired diagnostic seeds, and preserved source files."""
from pathlib import Path
import importlib.util,json
out=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',out/'code/run.py');r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
checks=[]
for c in r.cases():
    for rid in r.ids(c):
        for stage,key in [(1,'s1'),(2,'s2')]:
            f=out/f'stage{stage}'/rid
            if not (f/'input.json').exists():continue
            p=r.read(f/'input.json');m=r.read(f/'messages.json')
            assert m==[dict(role='user',content=r.render(key,p))]
            assert r.read(f/'sampling.json')['seed']==r.seed(stage,rid)==r.read(r.OLD/f'stage{stage}'/rid/'sampling.json')['seed']
            if stage==1:assert p==r.read(r.OLD/'stage1'/rid/'input.json')
            else:
                assert set(p['target'])=={'essay_id','text'}
                assert set(p)=={'rubric','score_specification','rater_id','history','target','reference_analysis'}
                assert p['history']==c['history'] and p['reference_analysis']==r.read(out/'stage1'/rid/'parsed.json')['score_free_analysis']
            checks.append(dict(stage=stage,rid=rid,passed=True))
for name in ['A','B','C']:
    folders=[out/'stage2_diagnostics'/name/v for v in ['v1_0','v1_1']]
    if all((f/'input.json').exists() for f in folders):
        assert r.read(folders[0]/'input.json')==r.read(folders[1]/'input.json')
        assert r.read(folders[0]/'sampling.json')==r.read(folders[1]/'sampling.json')
        for f,key in zip(folders,['s2_old','s2']):assert r.read(f/'messages.json')==[dict(role='user',content=r.render(key,r.read(f/'input.json')))]
        checks.append(dict(diagnostic=name,same_payload_and_sampling=True))
m=r.read(out/'run_manifest.json');assert m['baseline_files_sha256']==r.freeze_files();assert r.sha(out/'code/run.py')==m['code_sha256']
for k,p in r.PROMPTS.items():assert r.sha(p)==m['prompts'][k]['sha256_before']
r.save(out/'invariant_checks.json',dict(timestamp=r.now(),passed=True,checks=checks,baseline_and_prompts_unchanged=True))
print('Invariant checks passed:',len(checks))
