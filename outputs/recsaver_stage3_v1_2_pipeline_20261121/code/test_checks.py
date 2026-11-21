"""CPU-only gates: source identity, duplicate quotes, candidate issues, references."""
import sys
sys.dont_write_bytecode=True
import run as r
from copy import deepcopy
r.prepare();payload=r.read(r.OUT/'prepared_3a/1868_1/input.json');q='The main piece to improve your skills is during the process of keep learning.'
o=dict(observation_id='O1',dimension='Phraseology',scope='local',origin='direct_text_review',related_record_ids=[],quotes=[q],feature='A local phrase.',scoring_relevance='Check word combination.',limitation='One passage only.',next_check='Compare another passage.')
v=dict(schema_version='1.2',target_essay_id='1868:1',observations=[o],source_analysis_issues=[],insufficient_evidence=[])
assert len(r.gate_a(v,payload)['passed_observations'])==1
w=deepcopy(v);w.update(observations=None,source_analysis_issues=None)
assert r.gate_a(w,payload)['top_errors'] and not r.gate_a(w,payload)['passed_observations']
for change in [dict(dimension='Invented'),dict(related_record_ids=['4902_1__K1'],origin='candidate_review'),dict(quotes=['invented quote']),dict(scope='multiple_passages',quotes=[q,q])]:
    w=deepcopy(v);w['observations'][0].update(change);assert not r.gate_a(w,payload)['passed_observations']
w=deepcopy(v);w['observations']=[o,deepcopy(o)];assert not r.gate_a(w,payload)['passed_observations']
w=deepcopy(v);w['target_essay_id']='8722:1';assert not r.gate_a(w,payload)['passed_observations']
excerpt='consistent with the observed scores of 3 for both Overall and Traits'
w=deepcopy(v);w['source_analysis_issues']=[dict(record_id='1868_1__K2',issue_type='observed_score_conflict',candidate_excerpt=excerpt,explanation='Vocabulary and Phraseology are 4.')]
assert len(r.gate_a(w,payload)['passed_issues'])==1
w['source_analysis_issues'][0]['candidate_excerpt']='invented candidate quote';assert not r.gate_a(w,payload)['passed_issues']
b=dict(schema_version='1.2',rater_id='rater_7',pattern_status='insufficient_evidence',patterns=[],case_specific_observation_keys=[],representative_observation_key=None,rubric_comparison=dict(observed_band_ref_id=None,comparison_band_ref_id=None,relationship='indeterminate',explanation='No evidence.'),next_scoring_check=dict(inspect='Collect text.',distinguish='Compare comparable cases.',retain_if='Enough evidence.',reconsider_if='Contradictory evidence.'),insufficient_evidence=['No observations.'],feedback_paragraph='Collect evidence before drawing a pattern.')
inp=dict(rater_id='rater_7',verified_observations=[],rubric_entries=[],accepted_target_ids=['1868:1','4902:1'])
assert not r.audit_b(b,inp)['failed']
inp['verified_observations']=[dict(o,observation_key='1868:1::O1',target_essay_id='1868:1',observed_score=4)]
inp['rubric_entries']=[dict(rubric_ref_id='Phraseology:4',dimension='Phraseology',score_band=4,descriptor='official'),dict(rubric_ref_id='Vocabulary:4',dimension='Vocabulary',score_band=4,descriptor='official')]
b.update(case_specific_observation_keys=['1868:1::O1'],representative_observation_key='1868:1::O1',feedback_paragraph='1868:1 '+q);b['rubric_comparison']['observed_band_ref_id']='Phraseology:4'
assert not r.audit_b(b,inp)['failed']
w=deepcopy(b);w['rubric_comparison']['observed_band_ref_id']='Vocabulary:4';assert any(c['kind']=='observed_band_identity' for c in r.audit_b(w,inp)['failed'])
w=deepcopy(b);w.update(pattern_status='supported',patterns=[dict(statement='Unsupported',support=[dict(observation_key='1868:1::O1',supports_how='x'),dict(observation_key='1868:1::O1',supports_how='x')],limitation='x')]);assert any(c['kind']=='independent_support' for c in r.audit_b(w,inp)['failed'])
r.save(r.OUT/'gate_tests.json',dict(passed=True,cases=14,notes='Synthetic CPU checks, including malformed 3A arrays and zero-observation 3B validation; no synthetic examples are model requests or main results.'))
print('14 gate regression cases passed')
