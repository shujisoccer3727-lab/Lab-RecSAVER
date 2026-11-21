"""CPU regression checks; synthetic cases never enter model inputs."""
import sys
sys.dont_write_bytecode=True
import run as r
from copy import deepcopy
r.prepare();p=r.read(r.OUT/'prepared_3a/4902_1/input.json');catalog=p['evidence_spans'];sid=next(s['span_id'] for s in catalog if s['kind']=='short_contiguous')
o=dict(observation_id='O1',dimension='Conventions',scope='local',origin='direct_text_review',related_record_ids=[],evidence_span_ids=[sid],feature='Capitalization.',scoring_relevance='Inspect conventions.',limitation='Local.',next_check='Inspect another sentence.')
v=dict(schema_version='1.3',target_essay_id='4902:1',observations=[o],source_analysis_issues=[],insufficient_evidence=[])
assert not r.a_schema(v);assert len(r.gate_a(v,p)['passed_observations'])==1
for ids in [['unknown'],['E1868_1_P001'],[sid,sid]]:
    w=deepcopy(v);w['observations'][0]['evidence_span_ids']=ids;assert not r.gate_a(w,p)['passed_observations']
w=deepcopy(v);w['observations'][0].update(scope='multiple_passages',evidence_span_ids=[catalog[0]['span_id'],sid]);assert not r.gate_a(w,p)['passed_observations']
sentence_spans=[s for s in catalog if s['kind']=='short_contiguous'];w=deepcopy(v);w['observations'][0].update(scope='multiple_passages',evidence_span_ids=[sentence_spans[0]['span_id'],sentence_spans[1]['span_id']]);assert r.gate_a(w,p)['passed_observations']
text='😀One.No gap!\r\n\r\nThird sentence?';ss=r.spans(text,'test:1');assert all(text[s['start']:s['end']]==s['text'] for s in ss);assert len([s for s in ss if s['kind']=='paragraph'])==2;assert ss[0]['end']==12
p2=r.read(r.OUT/'prepared_3a/1868_1/input.json');rec=next(x for x in p2['accepted_records'] if x['record_id']=='1868_1__K2');excerpt='consistent with the observed scores of 3 for both Overall and Traits'
w=dict(schema_version='1.3',target_essay_id='1868:1',observations=[],source_analysis_issues=[dict(record_id='1868_1__K2',issue_type='observed_score_conflict',candidate_excerpt=excerpt,score_conflicts=[dict(dimension=d,claimed_score=3,observed_score=4) for d in ['Vocabulary','Phraseology']],explanation='Explicit all Traits statement.')],insufficient_evidence=[])
assert r.gate_a(w,p2)['passed_issues'];w['source_analysis_issues'][0]['score_conflicts'][0]['observed_score']=3;assert not r.gate_a(w,p2)['passed_issues']
inp=r.read(r.OUT/'fixed_3b_input.json');old=r.read(r.BASE/'stage3b/rater_7/parsed.json');old['schema_version']='1.3';r.configure();assert not r.b_schema(old);assert not r.audit_b(old,inp)['failed']
# Mechanical pass does not detect the old semantic error; keep that distinction explicit.
r.save(r.OUT/'gate_tests.json',dict(passed=True,cases=10,scope='Synthetic source/schema gates only, not model results or semantic validation.'))
print('10 CPU regression cases passed')
