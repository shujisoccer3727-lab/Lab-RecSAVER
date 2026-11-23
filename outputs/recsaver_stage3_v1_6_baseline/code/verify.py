"""CPU-only provenance, isolation and deterministic renderer checks."""
import sys
sys.dont_write_bytecode=True
import run as r
checks=[]
def ck(kind,ok,**details):checks.append(dict(kind=kind,pass_=bool(ok),**details))
fixed=r.read(r.OUT/'fixed_input.json');sources={e['essay_id']:e for e in fixed['source_essays']}
ck('fixed_source_bytes',r.sha(r.OUT/'fixed_input.json')==r.sha(r.BASE/'fixed_input.json'))
for eid in r.TARGETS:
    n=eid.replace(':','_');folder=r.OUT/'stage3a'/n;payload=r.read(folder/'input.json');catalog=r.read(r.OUT/'evidence_spans'/f'{n}.json')
    ck('3A_only_text_spans_dimension_names',set(payload)=={'target_essay_id','target_text','evidence_spans','dimension_names'},target=eid)
    ck('3A_target_source',payload['target_text']==sources[eid]['text'],target=eid)
    ck('catalog_unchanged',r.sha(r.OUT/'evidence_spans'/f'{n}.json')==r.sha(r.BASE/'evidence_spans'/f'{n}.json'),target=eid)
    ck('Unicode_slices',all(s['text']==payload['target_text'][s['start']:s['end']] for s in catalog),target=eid)
    if (folder/'parsed.json').exists():ck('3A_gate_reproducible',r.gate_a(r.read(folder/'parsed.json'),payload)==r.read(folder/'mechanical_checks.json'),target=eid)
inp=r.read(r.OUT/'handoff/input_3b.json');folder=r.OUT/'stage3b/rater_7'
ck('3B_actual_handoff',r.read(folder/'input.json')==inp)
ck('3B_audit_path_absent',set(inp)=={'rater_id','accepted_target_ids','verified_observations','rubric_entries','evidence_limitations'})
ck('unique_global_keys',len({o['observation_key'] for o in inp['verified_observations']})==len(inp['verified_observations']))
for o in inp['verified_observations']:
    source=sources[o['target_essay_id']];expected=source.get('Overall') if o['dimension']=='Overall' else source.get('Traits',{}).get(o['dimension'])
    ck('attached_original_score',o['observed_score']==expected,key=o['observation_key'])
    gate=r.read(r.OUT/'stage3a'/o['target_essay_id'].replace(':','_')/'mechanical_checks.json')
    ck('only_passed_observations',any({k:v for k,v in o.items() if k not in ['observation_key','target_essay_id','observed_score']}==x for x in gate['passed_observations']),key=o['observation_key'])
for e in inp['rubric_entries']:ck('official_reference',e['descriptor']==fixed['rubric']['scores'][str(e['score_band'])][e['dimension']] and e['rubric_ref_id']==e['dimension']+':'+str(e['score_band']),ref=e['rubric_ref_id'])
if (folder/'parsed.json').exists():
    v=r.read(folder/'parsed.json');expected=r.review_and_render(v,inp);saved=r.read(folder/'render_result.json');ck('render_reproduces',expected==saved)
    if saved['pass_']:
        ck('saved_display_matches',(folder/'feedback_paragraph.txt').read_bytes().decode('utf-8')==saved['feedback_paragraph'])
        for item in saved['selected_evidence']:
            o=next(x for x in inp['verified_observations'] if x['observation_key']==item['observation_key']);quote=o['quotes'][item['quote_index']]
            ck('selected_quote_ID_exact',item['target_essay_id']==o['target_essay_id'] and item['exact_quote']==quote and quote in sources[o['target_essay_id']]['text'])
        if v['rubric_review']['band_assessment']=='indeterminate':ck('fixed_indeterminate_language','This evidence alone does not establish whether that band is appropriate.' in saved['feedback_paragraph'])
        if v['rubric_review']['comparison_band_ref_id'] is None:ck('renderer_no_alternative_band','comparison band' not in saved['feedback_paragraph'])
oldchat=(r.BASE/'stage3b/rater_7/rendered_chat.txt').read_bytes().decode('utf-8');olduser=r.read(r.BASE/'stage3b/rater_7/messages.json')[0]['content'];requests=[]
for phase,key in [('stage3a','a'),('stage3b','b')]:
    for f in (r.OUT/phase).glob('*'):
        if not (f/'input.json').exists():continue
        rid=str(f.relative_to(r.OUT));user=r.PROMPTS[key].read_bytes().decode('utf-8').replace('{{INPUT_JSON}}',r.json.dumps(r.read(f/'input.json'),ensure_ascii=False,allow_nan=False))
        ck('only_placeholder_replaced',r.read(f/'messages.json')==[dict(role='user',content=user)],request=rid)
        # Git checkout converted saved rendered chats to CRLF; compare the
        # template after normalizing only line endings, leaving artifacts intact.
        norm=lambda text:text.replace('\r\n','\n')
        actual_chat=(f/'rendered_chat.txt').read_bytes().decode('utf-8')
        ck('chat_template_identical',norm(oldchat).count(norm(olduser))==1 and norm(oldchat).replace(norm(olduser),norm(user))==norm(actual_chat),request=rid,line_ending_normalization_only=True)
        ck('sampling_identical',r.read(f/'sampling.json')==r.read(r.BASE/'stage3b/rater_7/sampling.json'),request=rid)
        ck('raw_hash_unchanged',r.sha(f/'raw.txt')==r.read(f/'generation.json')['raw_sha256'],request=rid)
        requests.append(dict(request=rid,**r.read(f/'result.json'),**r.read(f/'generation.json')))
env=r.read(r.OUT/'environment.json');oldenv=r.read(r.BASE/'environment.json')
for k in ['model_snapshot','vllm','torch','transformers','gpu']:ck('runtime_identical',env[k]==oldenv[k],field=k)
audit=r.read(r.OUT/'isolated_candidate_score_audit.json');k2=[c for x in audit['rows'] if x['record_id']=='1868_1__K2' for c in x['score_conflicts']];k1=[x for x in audit['rows'] if x['record_id']=='1868_1__K1']
r.save(r.OUT/'candidate_audit_regression.json',dict(method='Separate deterministic parser on saved candidates, not 3A generation.',K2_Vocabulary_detected=any(x['dimension']=='Vocabulary' and x['claimed_score']==3 and x['observed_score']==4 for x in k2),K2_Phraseology_detected=any(x['dimension']=='Phraseology' and x['claimed_score']==3 and x['observed_score']==4 for x in k2),K1_not_automatically_attributed_to_Vocabulary=not any(x['score_conflicts'] for x in k1),sent_to_3B=False))
r.save(r.OUT/'request_summary.json',requests);r.save(r.OUT/'invariant_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),checks=checks,failed=[c for c in checks if not c['pass_']]))
r.finalize();m=r.read(r.OUT/'run_manifest.json');m['request_invariants_passed']=all(c['pass_'] for c in checks);m['stage1_calls']=0;m['stage2_calls']=0;m['actual_requests_by_condition']={phase:sum(x['request'].startswith(phase+'/') for x in requests) for phase in ['stage3a','stage3b']};m['optional_fixed_3B_calls']=0;m['reused_engine']=dict(path=str(r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py'),sha256=r.sha(r.ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py'));r.save(r.OUT/'run_manifest.json',m)
print('Invariants',sum(c['pass_'] for c in checks),'/',len(checks))
if not m['request_invariants_passed']:raise SystemExit('Invariant failures retained')
