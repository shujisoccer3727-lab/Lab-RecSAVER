"""CPU-only reproducible request/handoff invariants, retaining failed outputs."""
import sys
sys.dont_write_bytecode=True
import run as r
checks=[]
def ck(kind,ok,**kw):checks.append(dict(kind=kind,pass_=bool(ok),**kw))
fixed=r.read(r.OUT/'fixed_input.json');original=r.read(r.BF/'input.json');sources={s['essay_id']:s for s in fixed['source_essays']}
ck('fixed_input_bytes',r.sha(r.OUT/'fixed_input.json')==r.sha(r.BF/'input.json'))
for eid in ['1868:1','4902:1']:
    f=r.OUT/'stage3a'/eid.replace(':','_');p=r.read(f/'input.json');src=sources[eid]
    ck('3a_exact_keys',set(p)=={'target','observed_scores','accepted_records','dimension_names'},target=eid)
    ck('3a_target_and_observed_data',p['target']=={k:src[k] for k in ['essay_id','text']} and p['observed_scores']==dict(Overall=src.get('Overall'),Traits=src.get('Traits',{})),target=eid)
    ck('3a_only_own_candidates',p['accepted_records']==[x for x in fixed['accepted_records'] if x['target_essay_id']==eid] and len(p['accepted_records'])==2,target=eid)
    if (f/'parsed.json').exists():
        recomputed=r.gate_a(r.read(f/'parsed.json'),p);ck('3a_gate_reproducible',recomputed==r.read(f/'mechanical_checks.json'),target=eid)
inp=r.read(r.OUT/'handoff/input_3b.json');bf=r.OUT/'stage3b/rater_7'
ck('3b_actual_handoff',r.read(bf/'input.json')==inp)
ck('3b_only_allowed_keys',set(inp)=={'rater_id','accepted_target_ids','accepted_record_count','verified_observations','rubric_entries','source_analysis_issues','evidence_limitations'})
ck('3b_issues_have_no_candidate_excerpt',all(set(x)=={'record_id','issue_type','explanation'} for x in inp['source_analysis_issues']))
for o in inp['verified_observations']:
    src=sources[o['target_essay_id']];expected=src.get('Overall') if o['dimension']=='Overall' else src.get('Traits',{}).get(o['dimension'])
    ck('attached_score_from_original',o['observed_score']==expected,observation_key=o['observation_key'],actual=o['observed_score'],expected=expected)
    ck('global_key',o['observation_key']==o['target_essay_id']+'::'+o['observation_id'],key=o['observation_key'])
    gate=r.read(r.OUT/'stage3a'/o['target_essay_id'].replace(':','_')/'mechanical_checks.json')
    ck('only_passed_observations',any({k:v for k,v in o.items() if k not in ['observation_key','target_essay_id','observed_score']}==x for x in gate['passed_observations']),key=o['observation_key'])
for e in inp['rubric_entries']:
    b=str(e['score_band']);ck('reference_from_official_saved_rubric',e['descriptor']==fixed['rubric']['scores'][b][e['dimension']] and e['rubric_ref_id']==e['dimension']+':'+b,ref=e['rubric_ref_id'])
for o in inp['verified_observations']:
    if o['observed_score'] is None:continue
    d=o['dimension'];s=o['observed_score'];bands=sorted(float(b) for b,ds in fixed['rubric']['scores'].items() if d in ds)
    expected={s}
    if any(b<s for b in bands):expected.add(max(b for b in bands if b<s))
    if any(b>s for b in bands):expected.add(min(b for b in bands if b>s))
    ck('observed_and_nearest_neighbors_available',expected<={e['score_band'] for e in inp['rubric_entries'] if e['dimension']==d},key=o['observation_key'])
oldchat=(r.BF/'rendered_chat.txt').read_bytes().decode('utf-8');olduser=r.read(r.BF/'messages.json')[0]['content']
requests=[]
for phase,key in [('stage3a','a'),('stage3b','b')]:
    for f in (r.OUT/phase).glob('*'):
        if not (f/'input.json').exists():continue
        payload=r.read(f/'input.json');messages=r.read(f/'messages.json');canonical=r.PROMPTS[key].read_bytes().decode('utf-8')
        user=canonical.replace('{{INPUT_JSON}}',r.json.dumps(payload,ensure_ascii=False,allow_nan=False))
        ck('only_placeholder_substitution',messages==[dict(role='user',content=user)],request=str(f.relative_to(r.OUT)))
        ck('chat_template_unchanged',oldchat.replace(olduser,user)==(f/'rendered_chat.txt').read_bytes().decode('utf-8'),request=str(f.relative_to(r.OUT)))
        ck('sampling_unchanged',r.read(f/'sampling.json')==r.read(r.BF/'sampling.json'),request=str(f.relative_to(r.OUT)))
        ck('raw_unchanged',r.sha(f/'raw.txt')==r.read(f/'generation.json')['raw_sha256'],request=str(f.relative_to(r.OUT)))
        requests.append(dict(request=str(f.relative_to(r.OUT)),**r.read(f/'result.json'),**r.read(f/'generation.json')))
if (bf/'parsed.json').exists():
    recomputed=r.audit_b(r.read(bf/'parsed.json'),inp);ck('3b_audit_reproducible',recomputed==r.read(bf/'mechanical_checks.json'))
env=r.read(r.OUT/'environment.json');oldenv=r.read(r.BASE/'environment.json')
for k in ['model_snapshot','vllm','torch','transformers','gpu']:ck('runtime_unchanged',env[k]==oldenv[k],field=k)
r.save(r.OUT/'invariant_checks.json',dict(checks=checks,total=len(checks),passed=sum(x['pass_'] for x in checks),failed=[x for x in checks if not x['pass_']]))
r.save(r.OUT/'request_summary.json',requests)
r.finalize();m=r.read(r.OUT/'run_manifest.json');m['stage1_calls']=0;m['stage2_calls']=0;m['actual_3a_requests']=2;m['actual_3b_requests']=1;m['chat_template_identity_checked']=True;m['request_invariants_passed']=not any(not c['pass_'] for c in checks)
for v in m['prompts'].values():v['windows_path']=v['path'].replace('/mnt/c/','C:/')
r.save(r.OUT/'run_manifest.json',m)
runtime_manifest=r.read(r.ROOT/'outputs/recsaver_prompt_v1_0_initial_20261118/run_manifest.json')
m['system_message']=runtime_manifest['system_message'];m['chat']=runtime_manifest['chat']
m['chat_template_evidence']=[str(f.relative_to(r.OUT)) for f in r.OUT.glob('stage3*/*/rendered_chat.txt')]
m['reused_engine']=dict(path=str(r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py'),sha256=r.sha(r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py'))
m['post_run_code_change']='Malformed-array rejection hardened after generation; actual valid observations, gates and handoff reproduced unchanged. No model rerun.'
r.save(r.OUT/'run_manifest.json',m)
print('Request/handoff invariants:',sum(c['pass_'] for c in checks),'/',len(checks))
if any(not c['pass_'] for c in checks):raise SystemExit('Invariant failures retained in invariant_checks.json')
