"""Mask/source/request invariants and quote metrics, with no model calls."""
import run as r
import importlib.util,json,csv,collections
sp=importlib.util.spec_from_file_location('prior_audit',r.BASE/'code/audit_common.py');old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
checks=[];metrics={}
for scope,root in [('saved_v1_1',r.BASE),('v1_2',r.OUT)]:
    metrics[scope]={}
    for c in r.cases():
        for rid in r.p.ids(c):
            f=root/'stage1'/rid
            if scope=='v1_2' and (f/'input.json').exists():
                assert r.read(f/'input.json')==r.read(r.BASE/'stage1'/rid/'input.json')
                assert r.read(f/'sampling.json')==r.read(r.BASE/'stage1'/rid/'sampling.json')
            if (f/'result.json').exists():metrics[scope][rid]=old.metric(root,rid)
            mask=r.OUT/('saved_v1_1_masks' if scope=='saved_v1_1' else 'masks')/rid
            if not (mask/'mask_audit.json').exists():continue
            original=r.read(mask/'original_record.json')['score_free_analysis']
            assert original==r.read(f/'parsed.json')['score_free_analysis']
            computed=r.mask_analysis(original,c['history'],c['target'])
            assert computed['masked_analysis']==r.read(mask/'masked_analysis.json')
            assert computed['audit']==r.read(mask/'mask_audit.json')
            checks.append(dict(scope=scope,rid=rid,value_only_and_original_preserved=True,automatic_pass=computed['audit']['automatic_pass']))
            if scope=='v1_2' and (r.OUT/'stage2'/rid/'input.json').exists():
                actual=r.read(r.OUT/'stage2'/rid/'input.json');expected=r.stage2payload(c,computed['masked_analysis']);assert actual==expected
                assert set(actual['target'])=={'essay_id','text'}
                assert set(actual)=={'rater_id','rubric','score_specification','history','target','reference_analysis'}
                assert r.read(r.OUT/'stage2'/rid/'sampling.json')['seed']==r.p.seed(2,rid)
                checks.append(dict(scope='stage2',rid=rid,independent_masked_request_verified=True))
for test in ['A','B','C']:
    f=r.OUT/'stage2_diagnostics'/test/'masked'
    if (f/'input.json').exists():
        payload=r.read(f/'input.json');assert payload==r.read(r.OUT/'diagnostic_masks'/test/'input.json')
        assert set(payload['target'])=={'essay_id','text'} and set(payload)=={'rater_id','rubric','score_specification','history','target','reference_analysis'}
        checks.append(dict(scope='diagnostic',test=test,no_original_scores_or_audit_in_request=True))
for f in list((r.OUT/'stage1').glob('*/messages.json'))+list((r.OUT/'stage2').glob('*/messages.json'))+list((r.OUT/'stage2_diagnostics').glob('*/*/messages.json'))+list((r.OUT/'stage3').glob('*/messages.json')):
    folder=f.parent;stage=1 if folder.parent.name=='stage1' else 3 if folder.parent.name=='stage3' else 2;key={1:'s1',2:'s2',3:'s3'}[stage]
    assert r.read(f)==[dict(role='user',content=r.p.render(key,r.read(folder/'input.json')))]
    if (folder/'raw.txt').exists():assert r.sha(folder/'raw.txt')==r.read(folder/'generation.json')['raw_sha256']
f=r.OUT/'stage3/rater_7/input.json'
if f.exists():
    payload=r.read(f)
    for record in payload['accepted_records']:
        rid=record['record_id'];assert {k:v for k,v in record.items() if k!='record_id'}==r.read(r.OUT/'stage1'/rid/'parsed.json')
    checks.append(dict(scope='stage3',unmasked_original_records_verified=True,records=len(payload['accepted_records']),distinct_targets=len({v['target_essay_id'] for v in payload['accepted_records']})))
r.save(r.OUT/'source_and_quote_audit.json',dict(timestamp=r.now(),metrics=metrics))
r.finalize();r.save(r.OUT/'invariant_checks.json',dict(timestamp=r.now(),passed=True,checks=checks,baseline_unchanged=True,canonical_prompts_unchanged=True,masking_tests_passed=r.read(r.OUT/'masking_tests.json')['passed']))
print('Invariant checks passed:',len(checks))
