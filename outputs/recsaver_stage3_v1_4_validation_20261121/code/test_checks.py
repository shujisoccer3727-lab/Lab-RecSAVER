"""CPU schema/direction gates; synthetic model-shaped data are not model results."""
import sys
sys.dont_write_bytecode=True
import run as r
from copy import deepcopy
r.prepare();r.configure();inp=r.read(r.OUT/'fixed_3b_input.json');old=r.read(r.BASE/'stage3b_pipeline/rater_7/parsed.json')
v=deepcopy(old);v['schema_version']='1.4';v['representative_quote_index']=0;v['rubric_comparison']['comparison_direction']='higher';v.pop('feedback_paragraph');v['feedback_paragraph_template']='Please inspect the passage. [REPRESENTATIVE_EVIDENCE] Check its scope.'
assert not r.b_schema(v)
def audit(name,value,payload):
    f=r.OUT/'mechanical_test_fixtures'/name;f.mkdir(parents=True,exist_ok=True);r.save(f/'parsed.json',value);r.process_b(f,payload);return r.read(f/'mechanical_checks.json')
assert not audit('valid_higher',v,inp)['failed']
w=deepcopy(v);w['rubric_comparison'].update(comparison_band_ref_id='Cohesion:2',comparison_direction='lower');assert not audit('valid_lower',w,inp)['failed']
w=deepcopy(v);w['rubric_comparison']['comparison_direction']='lower';assert any(x.get('kind')=='comparison_direction' for x in audit('wrong_direction',w,inp)['failed'])
w=deepcopy(v);w['rubric_comparison'].update(comparison_band_ref_id=None,comparison_direction='higher');assert any(x.get('kind')=='comparison_direction' for x in audit('null_requires_none',w,inp)['failed'])
w=deepcopy(v);w['representative_quote_index']=999;assert any(x.get('kind')=='assembly' for x in audit('out_of_range_no_rescue',w,inp)['failed'])
w=deepcopy(v);w['representative_quote_index']=True;assert r.b_schema(w)
payload=r.read(r.OUT/'prepared_3a/1868_1/input.json');a=r.read(r.BASE/'stage3a/1868_1/parsed.json');a['schema_version']='1.4';assert not r.a_schema(a);assert len(r.gate_a(a,payload)['passed_observations'])==3
w=deepcopy(a);w['observations'][0]['evidence_span_ids']=['unknown'];assert len(r.gate_a(w,payload)['passed_observations'])==2
w=deepcopy(a);w['source_analysis_issues']=[dict(record_id='1868_1__K2',issue_type='observed_score_conflict',candidate_excerpt='consistent with the observed scores of 3 for both Overall and Traits',score_conflicts=[dict(dimension=d,claimed_score=3,observed_score=4) for d in ['Vocabulary','Phraseology']],explanation='Both Traits differ.')];assert r.gate_a(w,payload)['passed_issues']
w['source_analysis_issues'][0]['score_conflicts'][0]['observed_score']=3;assert not r.gate_a(w,payload)['passed_issues']
r.save(r.OUT/'gate_tests.json',dict(passed=True,cases=10,actual_model_calls=0,not_main_results=True,scope='Synthetic version/schema/direction/index/source/conflict gate tests.'))
print('10 CPU gate tests passed')
