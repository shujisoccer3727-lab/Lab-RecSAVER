"""CPU regression checks for band identity, source roles and schema additions."""
import sys
sys.dont_write_bytecode=True
import run as r
from copy import deepcopy
p=r.read(r.BF/'input.json');old=r.read(r.BF/'parsed.json')
a=r.audit_value(old,p)
assert any(c['kind']=='accepted_target_role' and c['actual']=='8722:1' for c in a['failed'])
assert any(c['kind']=='legacy_claimed_band_matches_quote' for c in a['failed'])
v=deepcopy(old);v['schema_version']='1.1';pat=v['patterns'][0];pat['counterexamples_and_scope']=[]
rc=pat['rubric_comparison'];rc.update(observed_essay_id='4902:1',observed_score=3)
q=p['rubric']['scores']['3']['Overall'];rc.update(rubric_quote=q,rubric_refs=[dict(dimension='Overall',score_band=3,role='observed_band',quote=q)])
assert not r.schema(3,v,p)
assert not r.audit_value(v,p)['failed']
w=deepcopy(v);w['patterns'][0]['rubric_comparison']['rubric_refs'][0]['score_band']=4
assert any(c['kind']=='rubric_dimension_band_quote' for c in r.audit_value(w,p)['failed'])
w=deepcopy(v);w['patterns'][0]['rubric_comparison']['rubric_refs'][0]['role']='comparison_band'
assert any(c['kind']=='rubric_band_role' for c in r.audit_value(w,p)['failed'])
w=deepcopy(v);w['patterns'][0]['supporting_cases'][0]['reference_record_ids']=['4902_1__K1']
assert any(c['kind']=='candidate_target_mapping' for c in r.audit_value(w,p)['failed'])
w=deepcopy(v);w['case_specific_observations']=[dict(target_essay_id='1868:1',quotes=['invented quote'],dimension='Vocabulary',observed_score=3,observation='x',scoring_implication='x',uncertainty='x')]
assert {c['kind'] for c in r.audit_value(w,p)['failed']} >= {'source_quote_exact','observed_score'}
w=deepcopy(v);del w['patterns'][0]['rubric_comparison']['observed_essay_id'];assert r.schema(3,w,p)
r.save(r.OUT/'audit_tests.json',dict(passed=True,cases=8,scope='Synthetic validator regression tests; no model calls; excluded from comparison.'))
for e in p['source_essays']:
    if e['essay_id'] in ['1868:1','4902:1']:print(e)
print('Overall3:',p['rubric']['scores']['3']['Overall']);print('Overall4:',p['rubric']['scores']['4']['Overall'])
