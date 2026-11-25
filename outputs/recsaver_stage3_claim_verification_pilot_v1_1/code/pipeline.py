"""Atomic-claim regression diagnosis: fixed decomposition, code boundaries, JSON-guided LLM."""
from pathlib import Path
import sys,json,hashlib,importlib.util,re,time,subprocess,traceback
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_claim_verification_pilot_v1_0'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=module('render16',ROOT/'outputs/recsaver_stage3_v1_6_baseline/code/run.py')
engine_module=module('atomic_engine',OUT/'code/engine.py')
read,save,sha=r.read,r.save,r.sha

def groups():return read(OUT/'claim_manifest.json')['groups']
def schema_for(payload):
    ids=[c['claim_id'] for c in payload['claims']]
    return dict(type='object',additionalProperties=False,required=['verdicts'],properties=dict(verdicts=dict(type='array',minItems=len(ids),maxItems=len(ids),items=dict(type='object',additionalProperties=False,required=['claim_id','verdict','reason'],properties=dict(claim_id=dict(type='string',enum=ids),verdict=dict(type='string',enum=['supported','contradicted','insufficient']),reason=dict(type='string',minLength=1))))))

def validate(value,payload):
    errors=[]
    if not isinstance(value,dict) or set(value)!= {'verdicts'}:return ['Expected verdicts object with no extra fields']
    if not isinstance(value['verdicts'],list):return ['verdicts must be an array']
    expected=[c['claim_id'] for c in payload['claims']];ids=[]
    for row in value['verdicts']:
        if not isinstance(row,dict) or set(row)!= {'claim_id','verdict','reason'}:
            errors.append('Missing/extra verdict fields');continue
        cid=row['claim_id']
        if not isinstance(cid,str):errors.append('claim_id must be a string');continue
        ids.append(cid)
        if cid not in expected:errors.append('Unknown claim ID: '+cid)
        if row['verdict'] not in ['supported','contradicted','insufficient']:errors.append('Undefined verdict label')
        if not isinstance(row['reason'],str) or not row['reason'].strip():errors.append('Missing reason')
    if len(ids)!=len(set(ids)):errors.append('Duplicate claim ID')
    if set(ids)!=set(expected) or len(value['verdicts'])!=len(expected):errors.append('Missing/extra claim IDs')
    return errors

def strict_parse(text):
    value=json.loads(text,object_pairs_hook=engine_module.legacy.no_dupes,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
    return value

def source_material(gid,reference):
    folder=OUT/'groups'/gid;payload=read(folder/'input_3b.json')
    observation=next(o for o in payload['verified_observations'] if o['observation_key']==reference['observation_key'])
    eid=observation['target_essay_id'];src=next(s for s in read(folder/'sources.json') if s['essay_id']==eid);text=src['text']
    catalog={s['span_id']:s for s in read(folder/'evidence_spans'/f'{eid.replace(":","_")}.json')}
    results=[]
    for ix in reference['quote_indices']:
        assert type(ix) is int and 0<=ix<len(observation['quotes'])
        span=catalog[observation['evidence_span_ids'][ix]];para=catalog[span['paragraph_id']]
        assert text[span['start']:span['end']]==span['text']==observation['quotes'][ix]
        assert para['start']<=span['start']<span['end']<=para['end']
        results.append(dict(observation_key=observation['observation_key'],target_essay_id=eid,quote_index=ix,span_id=span['span_id'],exact_quote=span['text'],source_position=dict(start=span['start'],end=span['end'],paragraph_id=span['paragraph_id'],paragraph_start=para['start'],paragraph_end=para['end'],essay_start=0,essay_end=len(text),offset_unit='Unicode code points, zero based [start,end)')))
    score=src['Overall'] if observation['dimension']=='Overall' else src['Traits'][observation['dimension']]
    assert score==observation['observed_score']
    return results,observation

def code_position(claim,quotes):
    check=claim['position_check'];q=next((q for q in quotes if q['quote_index']==check['quote_index']),None)
    if q is None:return dict(verdict='insufficient',reason='The selected quote boundary is unavailable.')
    pos=q['source_position'];boundary=check['boundary']
    point='end' if boundary.endswith('_end') else 'start'
    actual=pos.get(point);expected=pos.get(boundary)
    if actual is None or expected is None:return dict(verdict='insufficient',reason='The relevant source boundary is unavailable.')
    return dict(verdict='supported' if actual==expected else 'contradicted',reason=f"Selected quote {point}={actual}; {boundary}={expected}.",actual_quote_boundary=actual,required_source_boundary=expected,span_id=q['span_id'])

def prepare_inputs():
    allcode={};catalog=[]
    for group in groups():
        gid=group['group_id'];folder=OUT/'groups'/gid;payload=read(folder/'input_3b.json');refs={x['rubric_ref_id']:x for x in payload['rubric_entries']};items=[];code={}
        for claim in group['claims']:
            quotes=[];observations={}
            for ref in claim['selected_quote_references']:
                qs,ob=source_material(gid,ref);quotes+=qs;observations[ob['observation_key']]=ob
            catalog.append(dict(group_id=gid,claim_id=claim['claim_id'],source_quotes=quotes))
            if claim['route']=='code_position':
                code[claim['claim_id']]=code_position(claim,quotes);continue
            # No draft, upstream interpretation, split rationale, display candidate,
            # code verdict, previous review, or expected result enters this payload.
            evidence=dict(excerpts=[{k:q[k] for k in ['observation_key','target_essay_id','quote_index','exact_quote']} for q in quotes])
            if claim['kind'] in ['band_abstention','limitation','pattern_abstention'] or claim['claim_id'] in ['K06','K08']:
                dimensions={o['dimension'] for o in observations.values()}
                evidence['rubric_entries']=[e for e in refs.values() if e['dimension'] in dimensions and any(o['dimension']==e['dimension'] and o['observed_score']==e['score_band'] for o in observations.values())]
            if claim['kind'] in ['band_abstention','pattern_abstention']:
                evidence['recorded_scores']=[dict(observation_key=o['observation_key'],dimension=o['dimension'],score=o['observed_score']) for o in observations.values()]
            items.append(dict(claim_id=claim['claim_id'],claim=claim['claim'],evidence=evidence))
        result=dict(claims=items);save(folder/'input_3c.json',result);save(folder/'guided_schema.json',schema_for(result));save(folder/'code_verdicts.json',code);allcode[gid]=code
    save(OUT/'source_quotes.json',catalog);save(OUT/'code_verdicts.json',allcode)

def assemble(group,value):
    gid=group['group_id'];folder=OUT/'groups'/gid;payload=read(folder/'input_3c.json');errors=validate(value,payload)
    if errors:
        save(folder/'B/status.json',dict(processing_success=False,errors=errors,fallback_to_A=False));return
    llm={v['claim_id']:v for v in value['verdicts']};code=read(folder/'code_verdicts.json');verdicts=dict(llm,**code)
    keep={c['claim_id']:verdicts[c['claim_id']]['verdict']=='supported' for c in group['claims']}
    for c in group['claims']:
        if any(not keep.get(cid,False) for cid in c.get('display_dependencies',[])+c['depends_on']):keep[c['claim_id']]=False
    retained=[c for c in group['claims'] if keep[c['claim_id']]]
    actions=[a for a in group['next_check_candidates'] if all(keep.get(cid,False) for cid in a['depends_on'])]
    local=[c for c in retained if c['kind']=='local' and c['route']=='llm']
    representative=next(o for o in read(folder/'input_3b.json')['verified_observations'] if o['observation_key']==group['representative_observation_key'])
    parts=[]
    pattern=[c for c in retained if c['kind']=='pattern_abstention']
    parts += [r.sentence(c['display_candidate']) for c in pattern]
    # Display the exact fixed reviewed excerpts, even when the local finding is
    # withheld. A quotation is not a replacement finding.
    reviewed=[]
    for ix in group['representative_quote_indices']:
        quote=representative['quotes'][ix]
        parts.append(r.quoted_sentence(f"In essay {representative['target_essay_id']}, the reviewed excerpt is ",quote));reviewed.append(dict(quote_index=ix,exact_quote=quote))
    if local:
        parts += [r.sentence(c['display_candidate']) for c in retained if c['kind']=='local']
    else:parts.append(read(OUT/'claim_manifest.json')['display_only_statuses']['no_local_finding'])
    # Recorded scores and verbatim official descriptors are provenance data,
    # never an assertion that the score is appropriate.
    inp=read(folder/'input_3b.json');observed=next(e for e in inp['rubric_entries'] if e['dimension']==representative['dimension'] and e['score_band']==representative['observed_score'])
    parts.append(f"The recorded {representative['dimension']} score is {representative['observed_score']}.")
    parts.append(r.quoted_sentence(f"The official descriptor for {observed['rubric_ref_id']} is ",observed['descriptor']))
    parts += [r.sentence(c['display_candidate']) for c in retained if c['kind'] in ['limitation','band_abstention']]
    if actions:parts += [r.sentence('Next inspect: '+a['text']) for a in actions]
    else:parts.append(read(OUT/'claim_manifest.json')['display_only_statuses']['no_next_check'])
    decisions=[dict(claim_id=c['claim_id'],code_verdict=code.get(c['claim_id']),llm_verdict=llm.get(c['claim_id']),keep=keep[c['claim_id']],candidate=c['display_candidate'],rendered=keep[c['claim_id']] and (c['kind']!='local' or bool(local))) for c in group['claims']]
    result=dict(processing_success=True,local_finding_retained=bool(local),retained_claim_ids=[c['claim_id'] for c in retained],displayed_claim_ids=[d['claim_id'] for d in decisions if d['rendered']],next_check_ids=[a['action_id'] for a in actions],dropped_next_check_ids=[a['action_id'] for a in group['next_check_candidates'] if a not in actions],decisions=decisions,reviewed_quotes=reviewed,observed_rubric=observed,feedback_paragraph=' '.join(parts),fallback_to_A=False)
    save(folder/'B/assembly.json',result);save(folder/'B/status.json',dict(processing_success=True,fallback_to_A=False));(folder/'B/feedback_paragraph.txt').write_text(result['feedback_paragraph'],encoding='utf-8')
    if gid=='retention':
        # Fixed positive-control text, not a newly generated Stage 3B.
        source=group['control_source_observation'];(folder/'A').mkdir(exist_ok=True)
        (folder/'A/feedback_paragraph.txt').write_text(source['feature']+' '+source['scoring_relevance']+' '+source['limitation']+' Next inspect: '+source['next_check'],encoding='utf-8')
        save(folder/'A/control_source.json',dict(source='existing 4902:1::O1 observation; no new Stage 3B call',observation=source))

def finish():
    m=read(OUT/'run_manifest.json');assert m['claim_manifest_sha256']==sha(OUT/'claim_manifest.json')
    m['prompt_unchanged']=m['prompt']['sha256']==sha(ROOT/m['prompt']['path'])
    m['baseline_unchanged']=m['baseline_files_sha256']=={str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
    assert m['prompt_unchanged'] and m['baseline_unchanged']
    m['actual_new_requests']=len(read(OUT/'request_ledger.json')) if (OUT/'request_ledger.json').exists() else 0
    m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')};m['last_checked_at']=r.p.now();save(OUT/'run_manifest.json',m)

def worker():
    assert read(OUT/'pre_gpu_tests.json')['all_passed'];assert not (OUT/'request_ledger.json').exists()
    e=engine_module;e.OUT=OUT;e.PROMPTS={'c':ROOT/read(OUT/'run_manifest.json')['prompt']['path']};e.seed=lambda stage,rid:read(OUT/'run_manifest.json')['seed'];e.legacy.structural=lambda stage,value,payload:validate(value,payload);e.SCHEMA_FACTORY=schema_for
    jobs=[e.job(OUT/'groups'/g['group_id']/'stage3c','c',3,g['group_id'],read(OUT/'groups'/g['group_id']/'input_3c.json')) for g in groups()]
    assert len(jobs)==4
    save(OUT/'request_ledger.json',[dict(group=g['group_id'],stage='3C',started=r.p.now()) for g in groups()])
    started=time.perf_counter();engine=e.Engine();engine.run(jobs);save(OUT/'batch_costs.json',dict(requests=4,wall_seconds=time.perf_counter()-started,includes_model_initialization=True))
    for group in groups():
        folder=OUT/'groups'/group['group_id'];f=folder/'stage3c'
        if (f/'parsed.json').exists():assemble(group,read(f/'parsed.json'))
        else:save(folder/'B/status.json',dict(processing_success=False,errors=['Strict JSON output unavailable.'],fallback_to_A=False))
    finish();print('Four one-shot atomic requests complete.',flush=True)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','launch','worker','finish']);args=ap.parse_args()
    if args.phase=='prepare':prepare_inputs()
    elif args.phase=='launch':
        assert read(OUT/'pre_gpu_tests.json')['all_passed'];assert not (OUT/'process.json').exists()
        with (OUT/'execution.log').open('ab',buffering=0) as log:proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=r.p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));finish();raise
