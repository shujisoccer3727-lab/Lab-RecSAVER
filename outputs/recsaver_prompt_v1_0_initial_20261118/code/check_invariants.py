"""CPU-only checks of the actual frozen inputs and stage isolation."""
from pathlib import Path
import hashlib, importlib.util, json

out=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('experiment',out/'code/run.py')
run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
m=run.read(out/'run_manifest.json');cases=run.read(out/'case_manifest.json')
reserved={r['essay_id'] for r in cases['reserved']}
checks=[]
for c in cases['development']:
    assert c['target']['essay_id'] not in reserved
    assert len(c['history'])==3
    assert all(e['essay_id'] not in reserved|{c['target']['essay_id']} for e in c['history'])
    for rid in run.ids(c):
        for stage in [1,2]:
            f=out/f'stage{stage}'/rid
            if not (f/'input.json').exists():continue
            payload=run.read(f/'input.json');messages=run.read(f/'messages.json')
            template=run.prompt_paths()[stage-1].read_bytes().decode('utf-8')
            expected=template.replace('{{INPUT_JSON}}',json.dumps(payload,ensure_ascii=False,allow_nan=False))
            assert messages==[dict(role='user',content=expected)]
            assert payload['history']==c['history']
            if stage==2:
                assert payload['target']=={k:c['target'][k] for k in ['essay_id','text']}
                assert set(payload)=={'rubric','score_specification','rater_id','history','target','reference_analysis'}
                assert payload['reference_analysis']==run.read(out/'stage1'/rid/'parsed.json')['score_free_analysis']
            checks.append(dict(stage=stage,candidate_id=rid,canonical_substitution=True,history_same=True,target_scores_structurally_absent=stage==2))
assert {run.source(p):run.sha(p) for p in run.prompt_paths()}==m['prompt_sha256_before']
assert run.sha(out/'code/run.py')==m['code_sha256']
try: json.loads('{"a":1,"a":2}',object_pairs_hook=run.no_dupes)
except ValueError: pass
else: raise AssertionError('duplicate JSON accepted')
assert run.leak_scan({'decision_explanation':'The target Overall score is 3.'})
assert not run.leak_scan({'quotes':['There are 3 reasons.'],'support':[{'relevant_observed_history_scores':{'Overall':3}}]})
run.save(out/'invariant_checks.json',dict(passed=True,checked_at=run.now(),checks=checks,duplicate_json_rejected=True,leak_detector_controls_passed=True,prompt_and_code_hashes_match=True,reserved_excluded=True))
print('All input, prompt, score-separation and detector-control checks passed:',len(checks))
