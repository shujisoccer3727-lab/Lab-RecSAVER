"""CPU post-run provenance, parsing, identity and fixed assembly checks."""
import sys
sys.dont_write_bytecode=True
import pipeline as p
checks=[];requests=[]
def ck(kind,ok,**details):checks.append(dict(kind=kind,pass_=bool(ok),**details))
m=p.read(p.OUT/'run_manifest.json');old=p.read(p.BASE/'run_manifest.json')
for key in ['model','generation','max_tokens','sampling','seed','system_message','chat']:ck('same_generation_setting',m[key]==old[key],field=key)
reference=p.read(p.OUT/'independent_reference_review.json')
ck('reference_verdicts_not_used_by_pipeline','independent_reference_review' not in (p.OUT/'code/pipeline.py').read_text(encoding='utf-8'))
for group in p.groups():
    gid=group['group_id'];folder=p.OUT/'groups'/gid;f=folder/'stage3c'
    expected=p.read(folder/'input_3c.json');actual=p.read(f/'input.json')
    ck('fixed_actual_input',actual==expected,group=gid)
    ck('only_claims_input',set(actual)=={'claims'} and all(set(c)=={'claim_id','claim','evidence'} for c in actual['claims']),group=gid)
    ck('only_selected_llm_ids',{c['claim_id'] for c in actual['claims']}=={c['claim_id'] for c in group['claims'] if c['route']=='llm'},group=gid)
    ck('sampling_identical',p.read(f/'sampling.json')==m['sampling'],group=gid)
    ck('schema_matches_frozen_ids',p.read(folder/'guided_schema.json')==p.schema_for(actual),group=gid)
    raw=(f/'raw.txt').read_text(encoding='utf-8');result=p.read(f/'result.json');generation=p.read(f/'generation.json')
    ck('raw_hash_unchanged',p.sha(f/'raw.txt')==generation['raw_sha256'],group=gid)
    ck('no_retry',generation['attempt']==0,group=gid)
    if (f/'parsed.json').exists():
        value=p.read(f/'parsed.json');ck('strict_raw_equals_parsed',p.strict_parse(raw)==value,group=gid)
        valid=not p.validate(value,actual);ck('all_ids_once_or_failed',valid==p.read(folder/'B/status.json')['processing_success'],group=gid)
        if valid:
            assembly=p.read(folder/'B/assembly.json');decision={d['claim_id']:d for d in assembly['decisions']};llm={v['claim_id']:v for v in value['verdicts']};code=p.read(folder/'code_verdicts.json')
            for claim in group['claims']:
                cid=claim['claim_id'];v=code.get(cid,llm.get(cid));ck('supported_only',not decision[cid]['keep'] or v['verdict']=='supported',group=gid,claim=cid)
                ck('fixed_display_candidate',decision[cid]['candidate']==claim['display_candidate'],group=gid,claim=cid)
            for a in group['next_check_candidates']:
                keep=a['action_id'] in assembly['next_check_ids']
                ck('next_check_premises',keep==all(decision[c]['keep'] for c in a['depends_on']),group=gid,action=a['action_id'])
            ck('display_saved_exactly',assembly['feedback_paragraph']==(folder/'B/feedback_paragraph.txt').read_text(encoding='utf-8'),group=gid)
            ob=next(o for o in p.read(folder/'input_3b.json')['verified_observations'] if o['observation_key']==group['representative_observation_key'])
            ck('quote_strings_unchanged',all(q['exact_quote']==ob['quotes'][q['quote_index']] for q in assembly['reviewed_quotes']),group=gid)
            ck('not_using_model_reasons_as_feedback',all(d['candidate'] in [c['display_candidate'] for c in group['claims']] for d in assembly['decisions']),group=gid)
        else:ck('invalid_no_fallback',not (folder/'B/feedback_paragraph.txt').exists() and not p.read(folder/'B/status.json')['fallback_to_A'],group=gid)
    else:ck('parse_failure_no_fallback',not result['json_valid'] and not (folder/'B/feedback_paragraph.txt').exists(),group=gid)
    prompt=(p.ROOT/m['prompt']['path']).read_bytes().decode('utf-8');user=prompt.replace('{{INPUT_JSON}}',p.json.dumps(actual,ensure_ascii=False,allow_nan=False))
    ck('only_placeholder_replaced',p.read(f/'messages.json')==[dict(role='user',content=user)],group=gid)
    chat=(f/'rendered_chat.txt').read_bytes().decode('utf-8')
    ck('same_system_and_chat_template',chat=='<|im_start|>system\n'+m['system_message']+'<|im_end|>\n<|im_start|>user\n'+user+'<|im_end|>\n<|im_start|>assistant\n',group=gid)
    if gid!='retention':
        for name in ['input_3b.json','A/parsed.json','A/feedback_paragraph.txt','sources.json']:
            ck('saved_A_bytes_reused',p.sha(folder/name)==p.sha(p.BASE/'groups'/gid/name),group=gid,file=name)
    requests.append(dict(group_id=gid,**generation,**result,outer_fence_removal_used=False,guided_json_backend='outlines'))
env=p.read(p.OUT/'environment.json');oldenv=p.read(p.BASE/'environment.json')
for key in ['model_snapshot','vllm','torch','transformers','gpu']:ck('same_runtime',env[key]==oldenv[key],field=key)
ck('exactly_four_requests',len(p.read(p.OUT/'request_ledger.json'))==4)
p.save(p.OUT/'request_summary.json',requests);p.save(p.OUT/'mechanical_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),checks=checks,failed=[c for c in checks if not c['pass_']],semantic_evaluation_separate=True))
p.finish();print('Mechanical:',sum(c['pass_'] for c in checks),'/',len(checks))
assert all(c['pass_'] for c in checks),[c for c in checks if not c['pass_']]
