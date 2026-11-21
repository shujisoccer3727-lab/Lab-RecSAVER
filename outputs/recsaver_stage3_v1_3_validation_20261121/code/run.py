"""A: source-span selection; B: paired fixed input; C: new handoff. No retries/repair."""
from pathlib import Path
import sys,json,re,subprocess,shutil,importlib.util,traceback
from copy import deepcopy
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_v1_2_pipeline_20261121';COMMIT='10a0f0a0486114aa9bdc7b94358072a55e86feb1'
sp=importlib.util.spec_from_file_location('pipeline12',BASE/'code/run.py');base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
p=base.p;read,save,sha=base.read,base.save,base.sha
PROMPTS={k:ROOT/'prompts/en'/name for k,name in [('a','recsaver_03a_case_evidence_review_v1_3.txt'),('b','recsaver_03b_integrated_feedback_v1_3.txt')]}
TARGETS=['1868:1','4902:1'];SEED=925847335
OLD_GATE=base.gate_a
OLD_B_SCHEMA=base.b_schema

def spans(text,eid):
    result=[];prefix='E'+eid.replace(':','_');start=0;paragraphs=[]
    delimiters=list(re.finditer(r'(?:\r?\n[ \t]*){2,}|(?:\\r\\n[ \t]*){2,}',text))
    for match in delimiters:
        if start<match.start():paragraphs.append((start,match.start()))
        start=match.end()
    if start<len(text):paragraphs.append((start,len(text)))
    for pi,(a,b) in enumerate(paragraphs,1):
        pid=f'{prefix}_P{pi:03d}'
        result.append(dict(span_id=pid,paragraph_id=pid,start=a,end=b,text=text[a:b],kind='paragraph'))
        cuts=[a]+[a+m.end() for m in re.finditer(r'[.!?]+["”]?',text[a:b])]+[b];cuts=sorted(set(cuts));units=[]
        for left,right in zip(cuts,cuts[1:]):
            while left<right and text[left].isspace():left+=1
            while right>left and text[right-1].isspace():right-=1
            while right-left>360:
                cut=text.rfind(' ',left+150,left+360)
                if cut<left:cut=left+360
                units.append((left,cut));left=cut
                while left<right and text[left].isspace():left+=1
            if left<right:units.append((left,right))
        for si,(left,right) in enumerate(units,1):result.append(dict(span_id=f'{pid}_S{si:03d}',paragraph_id=pid,start=left,end=right,text=text[left:right],kind='short_contiguous'))
        for si,((left,_),(_,right)) in enumerate(zip(units,units[1:]),1):
            if right-left<=720:result.append(dict(span_id=f'{pid}_W{si:03d}',paragraph_id=pid,start=left,end=right,text=text[left:right],kind='adjacent_pair'))
    assert len({s['span_id'] for s in result})==len(result)
    assert all(s['text']==text[s['start']:s['end']] for s in result)
    return result

def a_schema(v):
    errors=base.need(v,dict(schema_version=str,target_essay_id=str,observations=list,source_analysis_issues=list,insufficient_evidence=list),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.3':errors.append('schema_version !=1.3')
    if len(base.array(v,'observations'))>3:errors.append('more than 3 observations')
    for i,o in enumerate(base.array(v,'observations')):
        errors+=base.need(o,dict(observation_id=str,dimension=str,scope=str,origin=str,related_record_ids=list,evidence_span_ids=list,feature=str,scoring_relevance=str,limitation=str,next_check=str),f'$.observations[{i}]')
        if isinstance(o,dict):
            converted={k:x for k,x in o.items() if k!='evidence_span_ids'};converted['quotes']=['placeholder'];errors+=base.obs_schema(converted,f'$.observations[{i}]')
    for i,x in enumerate(base.array(v,'source_analysis_issues')):errors+=issue_schema(x,f'$.issues[{i}]')
    return errors
def issue_schema(x,path):
    errors=base.need(x,dict(record_id=str,issue_type=str,candidate_excerpt=str,score_conflicts=list,explanation=str),path)
    if not isinstance(x,dict):return errors
    if x.get('issue_type') not in ['observed_score_conflict','ambiguous_score_reference','scope_overreach','unsupported_interpretation','source_role_error','conflicting_candidates']:errors.append('invalid issue_type')
    for c in base.array(x,'score_conflicts'):errors+=base.need(c,dict(dimension=str,claimed_score=(int,float),observed_score=(int,float)),path+'.score_conflicts')
    return errors
def b_schema(v):
    if not isinstance(v,dict):return OLD_B_SCHEMA(v)
    copy=deepcopy(v);copy['schema_version']='1.2';errors=OLD_B_SCHEMA(copy)
    if v.get('schema_version')!='1.3':errors.append('schema_version !=1.3')
    return errors
def structural(stage,v,payload):return a_schema(v) if 'evidence_spans' in payload else b_schema(v)

def gate_a(v,payload):
    eid=payload['target']['essay_id'];text=payload['target']['text'];catalog={s['span_id']:s for s in payload['evidence_spans']}
    top=base.a_top(dict(v,schema_version='1.2',source_analysis_issues=[]) if isinstance(v,dict) else v)
    if not isinstance(v,dict) or v.get('schema_version')!='1.3':top.append('schema_version !=1.3')
    converted=dict(schema_version='1.2',target_essay_id=(v.get('target_essay_id') if isinstance(v,dict) else None),observations=[],source_analysis_issues=[],insufficient_evidence=[])
    span_audits=[]
    for i,o in enumerate(base.array(v,'observations')):
        errors=base.need(o,dict(observation_id=str,dimension=str,scope=str,origin=str,related_record_ids=list,evidence_span_ids=list,feature=str,scoring_relevance=str,limitation=str,next_check=str),f'observation[{i}]')
        ids=base.array(o,'evidence_span_ids');selected=[]
        for sid in ids:
            if not isinstance(sid,str) or sid not in catalog:errors.append('unknown or other-target span ID')
            else:selected.append(catalog[sid])
        if len(set(x for x in ids if isinstance(x,str)))!=len(ids):errors.append('duplicate or invalid span ID')
        if not ids:errors.append('no selected spans')
        distinct=[]
        for s in selected:
            if not any(s['start']<b and s['end']>a for a,b in distinct):distinct.append((s['start'],s['end']))
        if isinstance(o,dict) and o.get('scope') in ['multiple_passages','whole_essay'] and len(distinct)<2:errors.append('fewer than two independent nonoverlapping source spans')
        quotes=[text[s['start']:s['end']] for s in selected]
        c={k:x for k,x in o.items() if k!='evidence_span_ids'} if isinstance(o,dict) else {}
        c['quotes']=quotes;converted['observations'].append(c)
        span_audits.append(dict(index=i,span_ids=ids,selected_spans=selected,reconstructed_quotes=quotes,independent_nonoverlapping_spans=len(distinct),errors=top+errors))
    old=OLD_GATE(converted,payload)
    passed=[]
    for c,s,o in zip(old['observation_checks'],span_audits,converted['observations']):
        c['reasons']+=s['errors'];c['pass_']=not c['reasons'];c['span_audit']=s
        if c['pass_']:passed.append(o)
    old['passed_observations']=passed;old['top_errors']+=top
    records={r['record_id']:r for r in payload['accepted_records']};ia=[];issues=[]
    for i,x in enumerate(base.array(v,'source_analysis_issues')):
        reasons=top+issue_schema(x,f'issue[{i}]');rid=x.get('record_id') if isinstance(x,dict) else None;rid=rid if isinstance(rid,str) else None
        if rid not in records:reasons.append('issue record not associated with target')
        q=x.get('candidate_excerpt') if isinstance(x,dict) else None
        if not isinstance(q,str) or not q or not any(q in s for s in base.strings(records.get(rid,{}))):reasons.append('issue quote not in candidate string value')
        conflicts=base.array(x,'score_conflicts')
        if isinstance(x,dict) and x.get('issue_type')=='observed_score_conflict' and not conflicts:reasons.append('score conflict without explicit conflict items')
        if isinstance(x,dict) and x.get('issue_type')!='observed_score_conflict' and conflicts:reasons.append('non-numeric issue has score_conflicts')
        for c in conflicts:
            if not isinstance(c,dict):continue
            d=c.get('dimension');actual=payload['observed_scores'].get('Overall') if d=='Overall' else payload['observed_scores']['Traits'].get(d)
            if d not in payload['dimension_names'] or actual!=c.get('observed_score') or c.get('claimed_score')==actual:reasons.append('numeric conflict does not match authoritative dimension/observed score')
        ia.append(dict(index=i,pass_=not reasons,reasons=reasons,classification_and_explicit_claim_require_semantic_review=True))
        if not reasons:issues.append(x)
    old['issue_checks']=ia;old['passed_issues']=issues
    return old

def freeze():return {str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run_manifest.json').exists():return
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
    shutil.copyfile(BASE/'fixed_input.json',OUT/'fixed_input.json');(OUT/'fixed_source').mkdir(exist_ok=True);shutil.copyfile(BASE/'fixed_input.json',OUT/'fixed_source/input.json');fixed=read(OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']}
    for eid in TARGETS:
        e=sources[eid];catalog=spans(e['text'],eid);save(OUT/'evidence_spans'/f'{eid.replace(":","_")}.json',catalog)
        old=read(BASE/'prepared_3a'/eid.replace(':','_')/'input.json');assert old['target']['text']==e['text']
        save(OUT/'prepared_3a'/eid.replace(':','_')/'input.json',dict(old,evidence_spans=catalog))
    shutil.copyfile(BASE/'handoff/input_3b.json',OUT/'fixed_3b_input.json')
    for f in PROMPTS.values():assert f.read_bytes().decode('utf-8').count('{{INPUT_JSON}}')==1
    m=read(BASE/'run_manifest.json')
    save(OUT/'run_manifest.json',dict(created_at=p.now(),comparison_commit=COMMIT,code_commit=COMMIT,baseline_path=str(BASE),baseline_files_sha256=freeze(),fixed_input_sha256=sha(OUT/'fixed_input.json'),fixed_3b_input_sha256=sha(OUT/'fixed_3b_input.json'),prompts={k:dict(path=str(f),windows_path=str(f).replace('/mnt/c/','C:/'),sha256=sha(f),same_name_locations=[str(x) for x in ROOT.rglob(f.name)]) for k,f in PROMPTS.items()},model=m['model'],generation=m['generation'],max_tokens=m['max_tokens'],sampling=m['sampling'],seed=SEED,seed_policy='Saved seed 925847335 independently for every request.',system_message=m['system_message'],chat=m['chat'],code_sha256_before=sha(__file__),planned_requests=dict(A_3a=2,B_fixed_3b=1,C_pipeline_3b=1),span_policy='Unicode code-point offsets into exact unnormalized source; paragraphs plus punctuation-bounded <=360 character contiguous units and adjacent pairs <=720; paragraph fallback retained; stable target-qualified IDs.',differences=['A changes 3A prompt and replaces copied quotes with programmatically resolved span IDs.','B changes only 3B prompt, keeping saved handoff JSON and order byte-identical.','C uses new 3A observations and same 3B v1.3; B/C differences are input/pipeline effects, not 3B prompt-only effects.','Same cached model, 5000 output budget per request, temperature/top_p/seed/chat; 4 independent requests; no guided decoding, repair, reselection, or Stage1/2 calls.']))

def configure():
    base.OUT=OUT;base.BF=BASE/'fixed_input.json';base.PROMPTS=PROMPTS;base.gate_a=gate_a;base.b_schema=b_schema
def handoff():
    # Reuse official-score/rubric attachment and issue-excerpt exclusion unchanged.
    configure();base.BF=OUT/'fixed_source'
    result=base.handoff()
    provenance=read(OUT/'handoff/rubric_provenance.json')
    for row in provenance:row['source_file']=str(BASE/'fixed_input.json');row['source_sha256']=sha(BASE/'fixed_input.json')
    save(OUT/'handoff/rubric_provenance.json',provenance)
    return result
def audit_b(v,inp):
    # base.audit_b calls base.b_schema, now version-aware without altering model output.
    return base.audit_b(v,inp)
def finalize():
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=freeze()==m['baseline_files_sha256'];m['prompts_unchanged']=all(sha(PROMPTS[k])==v['sha256'] for k,v in m['prompts'].items());assert m['baseline_unchanged'] and m['prompts_unchanged']
    m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')};m['last_checked_at']=p.now();m['actual_requests']=sum(1 for f in OUT.glob('stage3*/*/raw.txt'));save(OUT/'run_manifest.json',m)
def worker():
    prepare();p.OUT=OUT;p.PROMPTS.update(PROMPTS);p.seed=lambda stage,rid:SEED;p.legacy.structural=structural
    engine=p.Engine();jobs=[p.job(OUT/'stage3a'/eid.replace(':','_'),'a',3,eid,read(OUT/'prepared_3a'/eid.replace(':','_')/'input.json')) for eid in TARGETS]
    jobs.append(p.job(OUT/'stage3b_fixed/rater_7','b',3,'rater_7',read(OUT/'fixed_3b_input.json')))
    engine.run(jobs);configure()
    inp=handoff();engine.run([p.job(OUT/'stage3b_pipeline/rater_7','b',3,'rater_7',inp)])
    for label,ip in [('stage3b_fixed',read(OUT/'fixed_3b_input.json')),('stage3b_pipeline',inp)]:
        f=OUT/label/'rater_7'
        if (f/'parsed.json').exists():save(f/'mechanical_checks.json',audit_b(read(f/'parsed.json'),ip))
    finalize()
if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','worker','launch','finalize']);args=a.parse_args()
    if args.phase=='launch':
        prepare();assert not (OUT/'process.json').exists()
        with (OUT/'execution.log').open('ab',buffering=0) as log:proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));raise
