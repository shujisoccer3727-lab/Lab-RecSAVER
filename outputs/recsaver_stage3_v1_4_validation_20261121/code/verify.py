"""CPU-only immutable-source/request/assembly verification and corrected schema audit."""
import sys
sys.dont_write_bytecode=True
import run as r
r.configure();checks=[]
def ck(kind,ok,**kw):checks.append(dict(kind=kind,pass_=bool(ok),**kw))
fixed=r.read(r.OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']}
ck('fixed_source_bytes',r.sha(r.OUT/'fixed_input.json')==r.sha(r.BASE/'fixed_input.json'))
ck('B_fixed_input_bytes',r.sha(r.OUT/'fixed_3b_input.json')==r.sha(r.BASE/'stage3b_pipeline/rater_7/input.json'))
for eid in r.TARGETS:
    n=eid.replace(':','_');f=r.OUT/'stage3a'/n;payload=r.read(f/'input.json');catalog=r.read(r.OUT/'evidence_spans'/f'{n}.json')
    ck('C_3A_same_input_bytes',r.sha(f/'input.json')==r.sha(r.BASE/'prepared_3a'/n/'input.json'),target=eid)
    ck('C_span_catalog_bytes',r.sha(r.OUT/'evidence_spans'/f'{n}.json')==r.sha(r.BASE/'evidence_spans'/f'{n}.json'),target=eid)
    ck('C_Unicode_slices',all(x['text']==sources[eid]['text'][x['start']:x['end']] for x in catalog),target=eid)
    if (f/'parsed.json').exists():ck('C_gate_reproduces',r.gate_a(r.read(f/'parsed.json'),payload)==r.read(f/'mechanical_checks.json'),target=eid)
handoff=r.read(r.OUT/'handoff/input_3b.json');ck('C_actual_handoff',r.read(r.OUT/'stage3b_pipeline/rater_7/input.json')==handoff)
ck('B_actual_input_bytes',r.sha(r.OUT/'stage3b_fixed/rater_7/input.json')==r.sha(r.BASE/'stage3b_pipeline/rater_7/input.json'))
ck('C_allowed_input_fields',set(handoff)=={'rater_id','accepted_target_ids','accepted_record_count','verified_observations','rubric_entries','source_analysis_issues','evidence_limitations'} and all(set(x)=={'record_id','issue_type','explanation'} for x in handoff['source_analysis_issues']))
for o in handoff['verified_observations']:
    source=sources[o['target_essay_id']];expected=source.get('Overall') if o['dimension']=='Overall' else source['Traits'].get(o['dimension'])
    ck('C_observed_score_attached',o['observed_score']==expected,key=o['observation_key'])
    gate=r.read(r.OUT/'stage3a'/o['target_essay_id'].replace(':','_')/'mechanical_checks.json')
    ck('C_only_passed_restored_observations',any({k:v for k,v in o.items() if k not in ['observation_key','target_essay_id','observed_score']}==x for x in gate['passed_observations']),key=o['observation_key'])
for e in handoff['rubric_entries']:ck('C_official_descriptor',e['descriptor']==fixed['rubric']['scores'][str(e['score_band'])][e['dimension']] and e['rubric_ref_id']==e['dimension']+':'+str(e['score_band']),ref=e['rubric_ref_id'])
for phase,payload in [('stage3b_fixed',r.read(r.OUT/'fixed_3b_input.json')),('stage3b_pipeline',handoff)]:
    f=r.OUT/phase/'rater_7'
    for name in ['mechanical_checks.json','assembly_result.json']:
        source=f/name;archive=f/(source.stem+'_generation_time.json')
        if source.exists() and not archive.exists():r.shutil.copyfile(source,archive)
    r.process_b(f,payload)
    if (f/'parsed.json').exists():
        v=r.read(f/'parsed.json');got=r.read(f/'assembly_result.json');expected=r.assemble(v,payload)
        ck('assembly_reproduces',got==expected,condition=phase)
        ck('parsed_template_bytes_unchanged',r.sha(f/'parsed_template.json')==r.sha(f/'parsed.json'),condition=phase)
        if got['pass_']:
            ck('assembled_display_exact',(f/'assembled_feedback.txt').read_bytes().decode('utf-8')==got['feedback_paragraph'],condition=phase)
            if got['representative_observation_key'] is not None:
                o=next(o for o in payload['verified_observations'] if o['observation_key']==got['representative_observation_key']);q=o['quotes'][got['representative_quote_index']]
                ck('exact_index_quote_and_id',got['exact_quote']==q and got['target_essay_id']==o['target_essay_id'] and got['evidence_sentence']==f'In essay {o["target_essay_id"]}, the relevant excerpt is “{q}”.',condition=phase)
requests=[];oldchat=(r.BASE/'stage3b_pipeline/rater_7/rendered_chat.txt').read_bytes().decode('utf-8');olduser=r.read(r.BASE/'stage3b_pipeline/rater_7/messages.json')[0]['content']
for phase,key in [('stage3a','a'),('stage3b_fixed','b'),('stage3b_pipeline','b')]:
    for f in (r.OUT/phase).glob('*'):
        if not (f/'input.json').exists():continue
        rid=str(f.relative_to(r.OUT));payload=r.read(f/'input.json');user=r.PROMPTS[key].read_bytes().decode('utf-8').replace('{{INPUT_JSON}}',r.json.dumps(payload,ensure_ascii=False,allow_nan=False))
        ck('only_placeholder_substitution',r.read(f/'messages.json')==[dict(role='user',content=user)],request=rid)
        ck('chat_template_identical',oldchat.replace(olduser,user)==(f/'rendered_chat.txt').read_bytes().decode('utf-8'),request=rid)
        ck('sampling_identical',r.read(f/'sampling.json')==r.read(r.BASE/'stage3b_pipeline/rater_7/sampling.json'),request=rid)
        ck('raw_hash_unchanged',r.sha(f/'raw.txt')==r.read(f/'generation.json')['raw_sha256'],request=rid)
        requests.append(dict(request=rid,**r.read(f/'result.json'),**r.read(f/'generation.json')))
env=r.read(r.OUT/'environment.json');oldenv=r.read(r.BASE/'environment.json')
for k in ['model_snapshot','vllm','torch','transformers','gpu']:ck('runtime_identical',env[k]==oldenv[k],field=k)
r.save(r.OUT/'request_summary.json',requests);r.save(r.OUT/'invariant_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),checks=checks,failed=[c for c in checks if not c['pass_']]))
r.finalize();m=r.read(r.OUT/'run_manifest.json');m['stage1_calls']=0;m['stage2_calls']=0;m['actual_requests_by_condition']={phase:sum(x['request'].startswith(phase+'/') for x in requests) for phase in ['stage3a','stage3b_fixed','stage3b_pipeline']};m['request_invariants_passed']=all(c['pass_'] for c in checks);m['post_launch_audit_fix']='Fixed projection of template to legacy feedback field; removed leftover field in inspection copy only. Model inputs, raw/parsed output and assembly selection unchanged. Generation-time audits archived; corrected audits recalculated without model calls.';m['reused_code']={str(f.relative_to(r.ROOT)):r.sha(f) for f in [r.BASE/'code/run.py',r.ROOT/'outputs/recsaver_stage3_v1_2_pipeline_20261121/code/run.py',r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py']};r.save(r.OUT/'run_manifest.json',m)
print('Invariants',sum(c['pass_'] for c in checks),'/',len(checks))
if not m['request_invariants_passed']:raise SystemExit('Invariant failures retained')
