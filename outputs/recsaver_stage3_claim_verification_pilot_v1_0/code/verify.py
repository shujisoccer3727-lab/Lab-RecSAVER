"""CPU-only mechanical checks, independent of 3C's claim verdicts."""
import sys
sys.dont_write_bytecode=True
import pipeline as p
checks=[];requests=[]
def ck(kind,ok,**details):checks.append(dict(kind=kind,pass_=bool(ok),**details))
manifest=p.read(p.OUT/'run_manifest.json')
old=p.read(p.BASE/'run_manifest.json')
for k in ['model','generation','max_tokens','sampling','seed','system_message','chat']:ck('same_manifest_setting',manifest[k]==old[k],field=k)
ck('selection_unchanged',manifest['selection_sha256']==p.sha(p.OUT/'selection_manifest.json'))
for gid in p.GROUPS:
    folder=p.OUT/'groups'/gid;inp=p.read(folder/'input_3b.json');cp=p.read(folder/'input_3c.json');sources={s['essay_id']:s for s in p.read(folder/'sources.json')}
    ck('same_draft_for_A_B',cp['draft']==p.read(folder/'A/parsed.json'),group=gid)
    ck('3C_input_fields_only',set(cp)=={'draft','evidence','rubric_entries','evidence_limitations'},group=gid)
    ck('rater_and_target_ids',cp['evidence']['rater_id']==inp['rater_id'] and cp['evidence']['accepted_target_ids']==inp['accepted_target_ids'],group=gid)
    ck('same_rubric',cp['rubric_entries']==inp['rubric_entries'],group=gid)
    obs={o['observation_key']:o for o in inp['verified_observations']}
    for e in cp['evidence']['observations']:
        key=e['observation_key'];o=obs[key];eid=e['target_essay_id'];text=sources[eid]['text'];catalog={s['span_id']:s for s in p.read(folder/'evidence_spans'/f'{eid.replace(":","_")}.json')}
        expected=sources[eid].get('Overall') if o['dimension']=='Overall' else sources[eid]['Traits'][o['dimension']]
        ck('own_score_attached',e['recorded_score']==o['observed_score']==expected,group=gid,key=key)
        ck('interpretation_is_separate',e['upstream_interpretation']=={k:o[k] for k in e['upstream_interpretation']},group=gid,key=key)
        for q in e['source_excerpts']:
            i=q['quote_index'];s=catalog[o['evidence_span_ids'][i]];para=catalog[s['paragraph_id']];pos=q['source_position']
            ck('fixed_quote_and_correct_essay',q['span_id']==s['span_id'] and q['exact_quote']==o['quotes'][i]==text[s['start']:s['end']],group=gid,key=key,quote_index=i)
            ck('positions_and_boundaries',pos['start']==s['start'] and pos['end']==s['end'] and pos['paragraph_id']==s['paragraph_id'] and pos['paragraph_start']==para['start'] and pos['paragraph_end']==para['end'] and pos['essay_start']==0 and pos['essay_end']==len(text) and pos['at_essay_start']==(not text[:s['start']].strip()) and pos['at_essay_end']==(not text[s['end']:].strip()) and pos['at_paragraph_start']==(not text[para['start']:s['start']].strip()) and pos['at_paragraph_end']==(not text[s['end']:para['end']].strip()),group=gid,key=key,quote_index=i)
    for condition in ['A','B']:
        target=folder/condition
        if condition=='B' and not p.read(target/'status.json')['processing_success']:
            ck('B_failure_not_replaced_with_A',not (target/'feedback_paragraph.txt').exists() and not p.read(target/'status.json')['fallback_to_A'],group=gid);continue
        decision=p.read(target/'parsed.json');render=p.render_safely(decision,inp)
        ck('same_renderer',render==p.read(target/'render_result.json'),group=gid,condition=condition)
        ck('display_reproduces',render['pass_'] and render['feedback_paragraph']==(target/'feedback_paragraph.txt').read_text(encoding='utf-8'),group=gid,condition=condition)
        if condition=='B':ck('revision_matches_raw',decision==p.read(folder/'stage3c/parsed.json')['revised_decision'],group=gid)
    if gid!='known':
        for e in sources.values():
            name=e['essay_id'].replace(':','_');payload=p.read(folder/'stage3a'/name/'input.json')
            ck('3A_text_input',payload['target_text']==e['text'] and set(payload)=={'target_essay_id','target_text','evidence_spans','dimension_names'},group=gid,target=e['essay_id'])
            ck('all_catalog_slices',all(s['text']==e['text'][s['start']:s['end']] for s in payload['evidence_spans']),group=gid,target=e['essay_id'])
    else:
        for src,dst in [('stage3b/rater_7/input.json','input_3b.json'),('stage3b/rater_7/parsed.json','A/parsed.json'),('stage3b/rater_7/feedback_paragraph.txt','A/feedback_paragraph.txt')]:ck('known_A_byte_reuse',p.sha(p.BASE/src)==p.sha(folder/dst),file=dst)

for entry in p.read(p.OUT/'request_ledger.json'):
    folder=p.OUT/entry['request'];key=entry['stage'];payload=p.read(folder/'input.json');messages=p.read(folder/'messages.json')
    user=p.PROMPTS[key].read_bytes().decode('utf-8').replace('{{INPUT_JSON}}',p.json.dumps(payload,ensure_ascii=False,allow_nan=False))
    ck('only_placeholder_replaced',messages==[dict(role='user',content=user)],request=entry['request'])
    ck('sampling_identical',p.read(folder/'sampling.json')==manifest['sampling'],request=entry['request'])
    raw=(folder/'raw.txt').read_text(encoding='utf-8')
    if (folder/'parsed.json').exists():
        value=p.read(folder/'parsed.json')
        ck('raw_parsed_unchanged',p.json.loads(raw)==value and p.sha(folder/'raw.txt')==p.read(folder/'generation.json')['raw_sha256'],request=entry['request'])
    else:
        ck('strict_parse_failure_retained',not p.read(folder/'result.json')['json_valid'] and p.sha(folder/'raw.txt')==p.read(folder/'generation.json')['raw_sha256'],request=entry['request'])
    # The tokenizer's system and user wrapper are fixed; only the prompt differs.
    chat=(folder/'rendered_chat.txt').read_bytes().decode('utf-8')
    ck('default_system_and_template',chat=='<|im_start|>system\n'+manifest['system_message']+'<|im_end|>\n<|im_start|>user\n'+user+'<|im_end|>\n<|im_start|>assistant\n',request=entry['request'])
    generation=p.read(folder/'generation.json');result=p.read(folder/'result.json')
    ck('one_shot_no_transport_retry',generation['attempt']==0,request=entry['request'])
    requests.append(dict(request=entry['request'],stage=key,**generation,**result))
env=p.read(p.OUT/'environment.json');oldenv=p.read(p.BASE/'environment.json')
for k in ['model_snapshot','vllm','torch','transformers','gpu']:ck('runtime_same',env[k]==oldenv[k],field=k)
ck('request_budget',len(requests)==9 and len(requests)<=11)
p.save(p.OUT/'request_summary.json',requests)
p.save(p.OUT/'mechanical_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),failed=[c for c in checks if not c['pass_']],checks=checks,semantic_support_certified=False))
p.finish()
print('Mechanical checks:',sum(c['pass_'] for c in checks),'/',len(checks))
assert all(c['pass_'] for c in checks),[c for c in checks if not c['pass_']]
