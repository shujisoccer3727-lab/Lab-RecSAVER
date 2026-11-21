"""Reproduce mechanical audits, compare frozen requests; no inference."""
import sys
sys.dont_write_bytecode=True
import run as r
r.configure();checks=[]
def ck(kind,ok,**kw):checks.append(dict(kind=kind,pass_=bool(ok),**kw))
def same_audit(a,b):
    # Legacy audit traverses a set of textual target IDs; independent checks may reorder.
    a=r.deepcopy(a);b=r.deepcopy(b)
    for x in [a,b]:
        for key in ['checks','failed']:
            if key in x:x[key]=sorted(x[key],key=lambda c:r.json.dumps(c,sort_keys=True,ensure_ascii=False))
    return a==b
fixed=r.read(r.OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']}
ck('fixed_source_byte_identical',r.sha(r.OUT/'fixed_input.json')==r.sha(r.BASE/'fixed_input.json'))
ck('B_fixed_handoff_byte_identical',r.sha(r.OUT/'fixed_3b_input.json')==r.sha(r.BASE/'handoff/input_3b.json'))
for eid in r.TARGETS:
    f=r.OUT/'stage3a'/eid.replace(':','_');payload=r.read(f/'input.json');catalog=r.read(r.OUT/'evidence_spans'/f'{eid.replace(":","_")}.json')
    ck('A_original_input_except_catalog', {k:v for k,v in payload.items() if k!='evidence_spans'}==r.read(r.BASE/'prepared_3a'/eid.replace(':','_')/'input.json'),target=eid)
    ck('A_catalog_matches_actual_request',catalog==payload['evidence_spans'],target=eid)
    ck('A_unique_catalog_ids',len({s['span_id'] for s in catalog})==len(catalog),target=eid)
    ck('A_Unicode_slices_exact',all(s['text']==sources[eid]['text'][s['start']:s['end']] for s in catalog),target=eid)
    ck('A_paragraph_fallback_retained',any(s['kind']=='paragraph' for s in catalog),target=eid)
    if (f/'parsed.json').exists():ck('A_gate_reproduces',r.gate_a(r.read(f/'parsed.json'),payload)==r.read(f/'mechanical_checks.json'),target=eid)
inp=r.read(r.OUT/'handoff/input_3b.json');obs=inp['verified_observations']
ck('C_actual_handoff_identical',r.read(r.OUT/'stage3b_pipeline/rater_7/input.json')==inp)
ck('B_actual_input_byte_identical',r.sha(r.OUT/'stage3b_fixed/rater_7/input.json')==r.sha(r.BASE/'handoff/input_3b.json'))
ck('C_no_raw_candidate_or_history_fields',set(inp)=={'rater_id','accepted_target_ids','accepted_record_count','verified_observations','rubric_entries','source_analysis_issues','evidence_limitations'} and all(set(x)=={'record_id','issue_type','explanation'} for x in inp['source_analysis_issues']))
for o in obs:
    eid=o['target_essay_id'];source=sources[eid];expected=source.get('Overall') if o['dimension']=='Overall' else source.get('Traits',{}).get(o['dimension'])
    ck('C_attached_original_score',o['observed_score']==expected,key=o['observation_key'])
    ck('C_global_observation_key',o['observation_key']==eid+'::'+o['observation_id'],key=o['observation_key'])
    gate=r.read(r.OUT/'stage3a'/eid.replace(':','_')/'mechanical_checks.json')
    ck('C_only_passed_restored_observations',any({k:v for k,v in o.items() if k not in ['observation_key','target_essay_id','observed_score']}==x for x in gate['passed_observations']),key=o['observation_key'])
for e in inp['rubric_entries']:ck('C_official_descriptor',e['descriptor']==fixed['rubric']['scores'][str(e['score_band'])][e['dimension']] and e['rubric_ref_id']==e['dimension']+':'+str(e['score_band']),ref=e['rubric_ref_id'])
oldchat=(r.BASE/'stage3b/rater_7/rendered_chat.txt').read_bytes().decode('utf-8');olduser=r.read(r.BASE/'stage3b/rater_7/messages.json')[0]['content'];requests=[]
for phase,key in [('stage3a','a'),('stage3b_fixed','b'),('stage3b_pipeline','b')]:
    for f in (r.OUT/phase).glob('*'):
        if not (f/'input.json').exists():continue
        messages=r.read(f/'messages.json');user=r.PROMPTS[key].read_bytes().decode('utf-8').replace('{{INPUT_JSON}}',r.json.dumps(r.read(f/'input.json'),ensure_ascii=False,allow_nan=False));rid=str(f.relative_to(r.OUT))
        ck('canonical_placeholder_only',messages==[dict(role='user',content=user)],request=rid)
        ck('chat_template_identical',oldchat.replace(olduser,user)==(f/'rendered_chat.txt').read_bytes().decode('utf-8'),request=rid)
        ck('sampling_identical',r.read(f/'sampling.json')==r.read(r.BASE/'stage3b/rater_7/sampling.json'),request=rid)
        ck('raw_hash_unchanged',r.sha(f/'raw.txt')==r.read(f/'generation.json')['raw_sha256'],request=rid)
        requests.append(dict(request=rid,**r.read(f/'result.json'),**r.read(f/'generation.json')))
for phase,ip in [('stage3b_fixed',r.read(r.OUT/'fixed_3b_input.json')),('stage3b_pipeline',inp)]:
    f=r.OUT/phase/'rater_7'
    if (f/'parsed.json').exists():ck('3B_audit_reproduces',same_audit(r.audit_b(r.read(f/'parsed.json'),ip),r.read(f/'mechanical_checks.json')),condition=phase)
env=r.read(r.OUT/'environment.json');oldenv=r.read(r.BASE/'environment.json')
for k in ['model_snapshot','vllm','torch','transformers','gpu']:ck('runtime_identical',env[k]==oldenv[k],field=k)
r.save(r.OUT/'request_summary.json',requests);r.save(r.OUT/'invariant_checks.json',dict(checks=checks,total=len(checks),passed=sum(c['pass_'] for c in checks),failed=[c for c in checks if not c['pass_']]))
r.finalize();m=r.read(r.OUT/'run_manifest.json');m['request_invariants_passed']=all(c['pass_'] for c in checks);m['stage1_calls']=0;m['stage2_calls']=0;m['actual_requests_by_condition']={phase:sum(x['request'].startswith(phase+'/') for x in requests) for phase in ['stage3a','stage3b_fixed','stage3b_pipeline']};m['reused_code']={str(f.relative_to(r.ROOT)):r.sha(f) for f in [r.BASE/'code/run.py',r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py']};r.save(r.OUT/'run_manifest.json',m)
print('Invariants',sum(c['pass_'] for c in checks),'/',len(checks))
if not m['request_invariants_passed']:raise SystemExit('Invariant failures retained')
