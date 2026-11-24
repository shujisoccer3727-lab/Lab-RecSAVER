"""One-shot paired Stage 3B / source-position-aware Stage 3C pilot."""
from pathlib import Path
import sys,json,importlib.util,subprocess,time,traceback,hashlib,ast,re
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_v1_6_baseline'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=module('baseline16',BASE/'code/run.py')
engine_module=module('pilot_engine',OUT/'code/engine.py')
read,save,sha=r.read,r.save,r.sha
PROMPTS={k:ROOT/v['path'] for k,v in read(OUT/'run_manifest.json')['prompts'].items()}
GROUPS=['known','contrast','limited']

# Reuse the existing source-span function exactly; avoid loading GPU modules.
span_source=ROOT/'outputs/recsaver_stage3_v1_3_validation_20261121/code/run.py'
tree=ast.parse(span_source.read_text(encoding='utf-8'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='spans')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(span_source),'exec'))

def render_safely(decision,payload):
    """Existing renderer, fail closed on malformed/unhashable references."""
    try:return r.review_and_render(decision,payload)
    except (TypeError,KeyError,ValueError,IndexError) as exc:
        return dict(pass_=False,schema_errors=[type(exc).__name__+': '+str(exc)],checks=[],feedback_paragraph=None)

def validate_c(value,payload):
    errors=r.need(value,dict(claim_checks=list,revised_decision=dict),'$')
    if errors:return errors
    evidence={o['observation_key']:o for o in payload['evidence']['observations']}
    refs={e['rubric_ref_id']:e for e in payload['rubric_entries']}
    for i,c in enumerate(value['claim_checks']):
        path=f'$.claim_checks[{i}]'
        fields=r.need(c,dict(field=str,claim=str,verdict=str,observation_key=(str,type(None)),quote_indices=list,rubric_ref_id=(str,type(None)),reason=str),path)
        errors+=fields
        if fields:continue
        if c['verdict'] not in ['supported','contradicted','insufficient']:errors.append(path+': invalid verdict')
        if not all(c[k].strip() for k in ['field','claim','reason']):errors.append(path+': empty claim/check')
        key=c['observation_key'];rep=evidence.get(key)
        if key is not None and rep is None:errors.append(path+': unknown observation key')
        indices=c['quote_indices']
        if not all(type(ix) is int and rep is not None and 0<=ix<len(rep['source_excerpts']) for ix in indices):errors.append(path+': invalid/cross-observation quote index')
        if len({ix for ix in indices if type(ix) is int})!=len(indices):errors.append(path+': duplicate/invalid quote indices')
        if c['rubric_ref_id'] is not None and c['rubric_ref_id'] not in refs:errors.append(path+': unknown rubric reference')
    errors+=r.b_schema(value['revised_decision'])
    # Use exactly the existing 3B references and display logic for the revision.
    result=render_safely(value['revised_decision'],c_to_b_payload(payload))
    if not result['pass_']:errors.append('revised_decision failed existing 3B reference/render checks')
    return errors

def c_to_b_payload(payload):
    evidence=payload['evidence'];observations=[]
    for o in evidence['observations']:
        observations.append(dict(o['upstream_interpretation'],observation_key=o['observation_key'],target_essay_id=o['target_essay_id'],dimension=o['dimension'],observed_score=o['recorded_score'],quotes=[q['exact_quote'] for q in o['source_excerpts']]))
    return dict(rater_id=evidence['rater_id'],accepted_target_ids=evidence['accepted_target_ids'],verified_observations=observations,rubric_entries=payload['rubric_entries'],evidence_limitations=payload['evidence_limitations'])

def structural(stage,value,payload):
    if 'draft' in payload:return validate_c(value,payload)
    return r.a_schema(value) if 'target_text' in payload else r.b_schema(value)

def prepare_new_inputs():
    fixed=read(BASE/'fixed_input.json');dimensions=fixed['rubric']['structure']['holistic']+fixed['rubric']['structure']['analytic']
    for gid in GROUPS[1:]:
        folder=OUT/'groups'/gid;sources=read(folder/'sources.json')
        save(folder/'fixed_input.json',dict(rater_id='rater_7',rubric=fixed['rubric'],source_essays=sources))
        for e in sources:
            eid=e['essay_id'];name=eid.replace(':','_');catalog=spans(e['text'],eid)
            save(folder/'evidence_spans'/f'{name}.json',catalog)
            save(folder/'prepared_3a'/name/'input.json',dict(target_essay_id=eid,target_text=e['text'],evidence_spans=catalog,dimension_names=dimensions))

def handoff(gid):
    folder=OUT/'groups'/gid
    # Reuse the complete v1.6 gate, authoritative score attachment and rubric handoff.
    original=(r.OUT,r.BASE,r.TARGETS)
    try:
        r.OUT=folder;r.BASE=BASE;r.TARGETS=[s['essay_id'] for s in read(folder/'sources.json')]
        payload=r.handoff()
        # The old runner's first limitation described its own two Overall=3
        # cases. Retain its contract, replacing only that case-specific datum.
        payload['evidence_limitations'][0]='Two fixed essays from the same rater; mechanical provenance does not establish scoring causation or band validity.'
        save(folder/'handoff/input_3b.json',payload);save(folder/'input_3b.json',payload);return payload
    finally:r.OUT,r.BASE,r.TARGETS=original

def make_c_input(gid):
    folder=OUT/'groups'/gid;payload=read(folder/'input_3b.json');sources={e['essay_id']:e for e in read(folder/'sources.json')}
    observations=[];audit=[]
    for o in payload['verified_observations']:
        eid=o['target_essay_id'];text=sources[eid]['text'];catalog={s['span_id']:s for s in read(folder/'evidence_spans'/f'{eid.replace(":","_")}.json')}
        assert len(o['evidence_span_ids'])==len(o['quotes'])
        quoted=[]
        for ix,(sid,q) in enumerate(zip(o['evidence_span_ids'],o['quotes'])):
            s=catalog[sid];p=catalog[s['paragraph_id']]
            assert s['text']==q==text[s['start']:s['end']]
            assert p['start']<=s['start']<s['end']<=p['end']
            pos=dict(paragraph_id=s['paragraph_id'],start=s['start'],end=s['end'],offset_unit='Unicode code points; zero based [start,end)',essay_start=0,essay_end=len(text),paragraph_start=p['start'],paragraph_end=p['end'],at_essay_start=not text[:s['start']].strip(),at_essay_end=not text[s['end']:].strip(),at_paragraph_start=not text[p['start']:s['start']].strip(),at_paragraph_end=not text[s['end']:p['end']].strip(),rhetorical_role_not_inferred=True)
            quoted.append(dict(quote_index=ix,span_id=sid,exact_quote=q,source_position=pos))
            audit.append(dict(observation_key=o['observation_key'],target_essay_id=eid,quote_index=ix,span_id=sid,exact_quote=q,source_position=pos,source_text_sha256=hashlib.sha256(text.encode()).hexdigest()))
        proposal={k:o[k] for k in ['observation_id','feature','scoring_relevance','limitation','next_check']}
        observations.append(dict(observation_key=o['observation_key'],target_essay_id=eid,dimension=o['dimension'],recorded_score=o['observed_score'],source_excerpts=quoted,upstream_interpretation=proposal))
    result=dict(draft=read(folder/'A/parsed.json'),evidence=dict(rater_id=payload['rater_id'],accepted_target_ids=payload['accepted_target_ids'],observations=observations),rubric_entries=payload['rubric_entries'],evidence_limitations=payload['evidence_limitations'])
    save(folder/'source_positions.json',audit);save(folder/'input_3c.json',result)
    # Adding source positions cannot change any reference or quote available for display.
    rebuilt=c_to_b_payload(result)
    for a,b in zip(rebuilt['verified_observations'],payload['verified_observations']):
        assert all(a[k]==b[k] for k in a)
    assert rebuilt['rubric_entries']==payload['rubric_entries']
    return result

def write_display(gid,condition,decision,payload):
    folder=OUT/'groups'/gid/condition
    result=render_safely(decision,payload);save(folder/'render_result.json',result)
    if result['pass_']:(folder/'feedback_paragraph.txt').write_text(result['feedback_paragraph'],encoding='utf-8')
    return result

def generate(engine,jobs):
    manifest=read(OUT/'run_manifest.json')
    ledger=read(OUT/'request_ledger.json') if (OUT/'request_ledger.json').exists() else []
    for job in jobs:
        rel=str(job['folder'].relative_to(OUT))
        assert not any(x['request']==rel for x in ledger),'No request may be repeated'
        assert len(ledger)<manifest['hard_request_limit']
        ledger.append(dict(request=rel,stage=job['key'],attempted_at=r.p.now()))
    save(OUT/'request_ledger.json',ledger)
    started=time.perf_counter();engine.run(jobs);elapsed=time.perf_counter()-started
    batches=read(OUT/'batch_costs.json') if (OUT/'batch_costs.json').exists() else []
    batches.append(dict(requests=[str(j['folder'].relative_to(OUT)) for j in jobs],wall_seconds=elapsed,includes_model_initialization=not batches))
    save(OUT/'batch_costs.json',batches)

def finish():
    m=read(OUT/'run_manifest.json')
    assert m['selection_sha256']==sha(OUT/'selection_manifest.json')
    m['prompts_unchanged']=all(sha(ROOT/v['path'])==v['sha256'] for v in m['prompts'].values())
    m['baseline_unchanged']=m['baseline_files_sha256']=={str(p.relative_to(BASE)):sha(p) for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert m['baseline_unchanged'] and m['prompts_unchanged']
    ledger=read(OUT/'request_ledger.json') if (OUT/'request_ledger.json').exists() else []
    m['actual_new_requests']=len(ledger);m['actual_requests_by_stage']={stage:sum(x['stage']==stage for x in ledger) for stage in ['a','b','c']}
    m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')}
    m['last_checked_at']=r.p.now();save(OUT/'run_manifest.json',m)

def worker():
    assert read(OUT/'pre_gpu_tests.json')['all_passed']
    prepare_new_inputs()
    e=engine_module;e.OUT=OUT;e.PROMPTS=PROMPTS;e.seed=lambda stage,rid:read(OUT/'run_manifest.json')['seed'];e.legacy.structural=structural
    engine=e.Engine()
    known_payload=read(OUT/'groups/known/input_3b.json');known_draft=read(OUT/'groups/known/A/parsed.json')
    check=render_safely(known_draft,known_payload);assert check['pass_']
    saved=(OUT/'groups/known/A/feedback_paragraph.txt').read_text(encoding='utf-8')
    assert saved==check['feedback_paragraph'];save(OUT/'groups/known/A/render_result.json',check)
    # One known-example verification; it never changes selection or the prompts.
    cp=make_c_input('known');generate(engine,[e.job(OUT/'groups/known/stage3c','c',3,'known',cp)])
    jobs=[]
    for gid in GROUPS[1:]:
        folder=OUT/'groups'/gid
        for src in read(folder/'sources.json'):
            name=src['essay_id'].replace(':','_');jobs.append(e.job(folder/'stage3a'/name,'a',3,src['essay_id'],read(folder/'prepared_3a'/name/'input.json')))
    generate(engine,jobs)
    jobs=[]
    for gid in GROUPS[1:]:
        payload=handoff(gid);jobs.append(e.job(OUT/'groups'/gid/'A','b',3,gid,payload))
    generate(engine,jobs)
    jobs=[]
    for gid in GROUPS[1:]:
        folder=OUT/'groups'/gid
        if (folder/'A/parsed.json').exists():
            result=write_display(gid,'A',read(folder/'A/parsed.json'),read(folder/'input_3b.json'))
            if result['pass_']:jobs.append(e.job(folder/'stage3c','c',3,gid,make_c_input(gid)))
    if jobs:generate(engine,jobs)
    for gid in GROUPS:
        folder=OUT/'groups'/gid;cf=folder/'stage3c';status=dict(processing_success=False,fallback_to_A=False)
        if (cf/'parsed.json').exists():
            value=read(cf/'parsed.json');errors=validate_c(value,read(folder/'input_3c.json'));status['errors']=errors
            if not errors:
                save(folder/'B/parsed.json',value['revised_decision'])
                result=write_display(gid,'B',value['revised_decision'],read(folder/'input_3b.json'));status['processing_success']=result['pass_']
        else:status['errors']=['Strict parsed 3C output unavailable; B is a processing failure.']
        save(folder/'B/status.json',status)
    finish();print('Pilot generation complete; no further model calls.',flush=True)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['launch','worker','finish']);args=ap.parse_args()
    if args.phase=='launch':
        assert not (OUT/'process.json').exists() and not (OUT/'request_ledger.json').exists()
        assert read(OUT/'pre_gpu_tests.json')['all_passed']
        with (OUT/'execution.log').open('ab',buffering=0) as log:
            proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=r.p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:
            save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));finish();raise
