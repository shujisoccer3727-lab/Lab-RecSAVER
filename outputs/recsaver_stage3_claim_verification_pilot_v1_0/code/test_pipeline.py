"""CPU contract tests; fixtures never enter model inputs or evaluation counts."""
import sys
sys.dont_write_bytecode=True
from copy import deepcopy
import pipeline as p

payload=p.make_c_input('known')
base=dict(claim_checks=[dict(field='textual_finding',claim='Synthetic fixture claim.',verdict='insufficient',observation_key='1868:1::O1',quote_indices=[0],rubric_ref_id=None,reason='Synthetic fixture reason.')],revised_decision=payload['draft'])
results=[]
def check(name,value,valid):
    errors=p.validate_c(value,payload);assert bool(errors)!=valid,(name,errors)
    results.append(dict(name=name,expected_valid=valid,errors=errors,pass_=True,synthetic_fixture_not_model_success=True))
check('unchanged valid decision',base,True)
v=deepcopy(base);v['claim_checks'][0]['observation_key']='another_group::O1';check('unknown audit observation',v,False)
for indices in [[-1],[999],[True],[0.5],[0,0]]:
    v=deepcopy(base);v['claim_checks'][0]['quote_indices']=indices;check('bad audit indices '+str(indices),v,False)
v=deepcopy(base);v['claim_checks'][0]['rubric_ref_id']='Grammar:999';check('unknown audit rubric',v,False)
v=deepcopy(base);v['claim_checks'][0]['verdict']='correct';check('invalid verdict',v,False)
v=deepcopy(base);v['revised_decision']['representative_observation_key']='another_group::O1';check('cross-group revision key',v,False)
v=deepcopy(base);v['revised_decision']['quote_indices']=[True];check('boolean revision index',v,False)
v=deepcopy(base);v['revised_decision']['rater_id']='rater_18';check('wrong rater',v,False)
v=deepcopy(base);v['revised_decision']['rubric_review']['observed_band_ref_id']='Cohesion:2';check('wrong observed score reference',v,False)
v=deepcopy(base);v['revised_decision']['quote_indices']=[999];check('revision quote outside observation',v,False)
v=deepcopy(base);v['revised_decision']['source_position']={'start':999};check('invented output position rejected',v,False)
v=deepcopy(base);v['revised_decision']['representative_observation_key']=[];check('unhashable key fails closed',v,False)
v=deepcopy(base);v['revised_decision'].update(representative_observation_key='4902:1::O1',quote_indices=[0,1]);v['revised_decision']['rubric_review']['observed_band_ref_id']='Cohesion:2';check('coordinated switch to supplied observation',v,True)
# The quoted source position is derived from the exact catalog, not interpretation.
o=payload['evidence']['observations'][0];s=o['source_excerpts'][1]['source_position']
assert s['start']==368 and s['end']==610 and s['paragraph_end']==765 and not s['at_paragraph_end']
assert 'verdict' not in p.json.dumps(payload)
assert p.read(p.OUT/'selection_manifest.json')['before_new_3A_3B_3C_outputs']
p.save(p.OUT/'pre_gpu_tests.json',dict(all_passed=True,total=len(results)+2,contract_cases=results,source_position_derivation_passed=True,selection_frozen_before_outputs=True,model_calls=0))
print('CPU checks passed:',len(results)+2)
