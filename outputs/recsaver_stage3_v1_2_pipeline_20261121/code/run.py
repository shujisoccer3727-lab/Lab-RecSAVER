"""Stage 3A -> mechanical gate -> 3B; immutable raw outputs, no repair."""
from pathlib import Path
import sys, json, importlib.util, subprocess, shutil, re, traceback
from collections import Counter
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1]; ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_v1_1_validation_20261121'
BF=BASE/'stage3/rater_7'; COMMIT='5d24e8f589d651e8ae806d14c5afebd2599ea4ef'
sp=importlib.util.spec_from_file_location('prior',ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
read,save,sha=p.read,p.save,p.sha
PROMPTS={k:ROOT/'prompts/en'/name for k,name in [('a','recsaver_03a_case_evidence_review_v1_2.txt'),('b','recsaver_03b_integrated_feedback_v1_2.txt')]}
SEED=925847335

def strict(text):return json.loads(text,object_pairs_hook=p.legacy.no_dupes,parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
def array(obj,key):
    value=obj.get(key,[]) if isinstance(obj,dict) else []
    return value if isinstance(value,list) else []
def need(obj,fields,path,exact=True):
    if not isinstance(obj,dict):return [path+': expected object']
    errors=[]
    for k,t in fields.items():
        if k not in obj or not isinstance(obj[k],t):errors.append(path+'.'+k+': missing or wrong type')
    if exact:
        for k in set(obj)-set(fields):errors.append(path+'.'+k+': unexpected field')
    return errors
def strings(x):
    if isinstance(x,str):return [x]
    if isinstance(x,dict):return sum([strings(y) for y in x.values()],[])
    if isinstance(x,list):return sum([strings(y) for y in x],[])
    return []
def obs_schema(o,path):
    errors=need(o,dict(observation_id=str,dimension=str,scope=str,origin=str,related_record_ids=list,quotes=list,feature=str,scoring_relevance=str,limitation=str,next_check=str),path)
    if not isinstance(o,dict):return errors
    if o.get('scope') not in ['local','multiple_passages','whole_essay']:errors.append(path+': invalid scope')
    if o.get('origin') not in ['candidate_review','direct_text_review']:errors.append(path+': invalid origin')
    for key in ['quotes','related_record_ids']:
        if not all(isinstance(q,str) and q for q in array(o,key)):errors.append(path+'.'+key+': expected nonempty strings')
    return errors
def issue_schema(x,path):
    errors=need(x,dict(record_id=str,issue_type=str,candidate_excerpt=str,explanation=str),path)
    if isinstance(x,dict) and x.get('issue_type') not in ['observed_score_conflict','scope_overreach','unsupported_interpretation','source_role_error','conflicting_candidates']:errors.append(path+': invalid issue type')
    return errors
def a_top(v):
    errors=need(v,dict(schema_version=str,target_essay_id=str,observations=list,source_analysis_issues=list,insufficient_evidence=list),'$')
    if isinstance(v,dict):
        if v.get('schema_version')!='1.2':errors.append('schema_version != 1.2')
        if isinstance(v.get('observations'),list) and len(v['observations'])>3:errors.append('more than three observations')
    return errors
def b_schema(v):
    errors=need(v,dict(schema_version=str,rater_id=str,pattern_status=str,patterns=list,case_specific_observation_keys=list,representative_observation_key=(str,type(None)),rubric_comparison=dict,next_scoring_check=dict,insufficient_evidence=list,feedback_paragraph=str),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.2':errors.append('schema_version != 1.2')
    if v.get('pattern_status') not in ['supported','insufficient_evidence']:errors.append('invalid pattern_status')
    rc=v.get('rubric_comparison',{})
    errors+=need(rc,dict(observed_band_ref_id=(str,type(None)),comparison_band_ref_id=(str,type(None)),relationship=str,explanation=str),'$.rubric_comparison')
    if rc.get('relationship') not in ['consistent_with_rubric','possible_tension','indeterminate']:errors.append('invalid relationship')
    errors+=need(v.get('next_scoring_check'),dict(inspect=str,distinguish=str,retain_if=str,reconsider_if=str),'$.next_scoring_check')
    for i,pat in enumerate(array(v,'patterns')):
        errors+=need(pat,dict(statement=str,support=list,limitation=str),f'$.patterns[{i}]')
        for j,s in enumerate(array(pat,'support')):errors+=need(s,dict(observation_key=str,supports_how=str),f'$.patterns[{i}].support[{j}]')
    if len(array(v,'patterns'))>1:errors.append('more than one pattern')
    return errors
def structural(stage,v,payload):
    if 'target' not in payload:return b_schema(v)
    errors=a_top(v)
    if isinstance(v,dict):
        for i,o in enumerate(array(v,'observations')):errors+=obs_schema(o,f'$.observations[{i}]')
        for i,x in enumerate(array(v,'source_analysis_issues')):errors+=issue_schema(x,f'$.source_analysis_issues[{i}]')
    return errors

def gate_a(v,payload):
    top=a_top(v);eid=payload['target']['essay_id'];text=payload['target']['text']
    if not isinstance(v,dict) or v.get('target_essay_id')!=eid:top.append('target ID mismatch')
    records={r['record_id']:r for r in payload['accepted_records']}
    observations=array(v,'observations')
    ids=Counter(o.get('observation_id') for o in observations if isinstance(o,dict) and isinstance(o.get('observation_id'),str))
    audits=[];passed=[]
    for i,o in enumerate(observations):
        reasons=top+obs_schema(o,f'$.observations[{i}]');qchecks=[];spans=[]
        if isinstance(o,dict):
            if not isinstance(o.get('observation_id'),str) or not o.get('observation_id') or ids[o['observation_id']]!=1:reasons.append('missing/duplicate observation_id')
            if o.get('dimension') not in payload['dimension_names']:reasons.append('unknown dimension')
            if any(not isinstance(rid,str) or rid not in records for rid in array(o,'related_record_ids')):reasons.append('candidate does not belong to target')
            if o.get('origin')=='direct_text_review' and o.get('related_record_ids'):reasons.append('direct text review must have empty related_record_ids')
            if o.get('origin')=='candidate_review' and not o.get('related_record_ids'):reasons.append('candidate review has no candidate ID')
            for q in array(o,'quotes'):
                ok=isinstance(q,str) and bool(q) and q in text
                qchecks.append(dict(quote=q,exact=ok,all_start_offsets=([m.start() for m in re.finditer(re.escape(q),text)] if ok else [])))
                if not ok:reasons.append('quote not exact target substring')
            unique=list(dict.fromkeys(q for q in array(o,'quotes') if isinstance(q,str) and q and q in text))
            # Identical quotations count once. Nested/overlapping excerpts count as one location.
            for q in unique:
                start=text.index(q);end=start+len(q)
                if not any(start<b and end>a for a,b in spans):spans.append((start,end))
            if not unique:reasons.append('no usable quote')
            if o.get('scope') in ['multiple_passages','whole_essay'] and len(spans)<2:reasons.append('multiple/whole-essay scope without two distinct nonoverlapping excerpts')
        audits.append(dict(index=i,observation_id=o.get('observation_id') if isinstance(o,dict) else None,pass_=not reasons,reasons=reasons,quote_checks=qchecks,distinct_evidence_locations=len(spans),semantic_support_not_certified=True))
        if not reasons:passed.append(o)
    issues=[];ia=[]
    for i,x in enumerate(array(v,'source_analysis_issues')):
        reasons=top+issue_schema(x,f'$.source_analysis_issues[{i}]')
        if isinstance(x,dict):
            rid=x.get('record_id');excerpt=x.get('candidate_excerpt');rid=rid if isinstance(rid,str) else None
            if rid not in records:reasons.append('issue candidate does not belong to target')
            if not isinstance(excerpt,str) or not excerpt or not any(excerpt in s for s in strings(records.get(rid,{}))):reasons.append('issue excerpt not exact substring of candidate string value')
        ia.append(dict(index=i,pass_=not reasons,reasons=reasons))
        if not reasons:issues.append(x)
    return dict(top_errors=top,observation_checks=audits,issue_checks=ia,passed_observations=passed,passed_issues=issues)

def freeze():return {str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run_manifest.json').exists():return
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
    old=read(BASE/'run_manifest.json');shutil.copyfile(BF/'input.json',OUT/'fixed_input.json')
    fixed=read(OUT/'fixed_input.json');targets=['1868:1','4902:1'];source={s['essay_id']:s for s in fixed['source_essays']}
    assert [r['record_id'] for r in fixed['accepted_records']]==['1868_1__K1','1868_1__K2','4902_1__K1','4902_1__K2']
    mapping=[]
    for eid in targets:
        records=[]
        for i,record in enumerate(fixed['accepted_records']):
            if record['target_essay_id']!=eid:continue
            rid=record['record_id'];assert re.fullmatch(re.escape(eid.replace(':','_'))+r'__K[12]',rid)
            records.append(dict(record,record_id=rid));mapping.append(dict(source_index=i,source_record_id=record['record_id'],normalized_record_id=rid,target_essay_id=eid,transformation='identity: canonical actual ID already valid',source_record_sha256=sha_json(record)))
        assert len(records)==2
        e=source[eid];save(OUT/'prepared_3a'/eid.replace(':','_')/'input.json',dict(target={k:e[k] for k in ['essay_id','text']},observed_scores=dict(Overall=e.get('Overall'),Traits=e.get('Traits',{})),accepted_records=records,dimension_names=fixed['rubric']['structure']['holistic']+fixed['rubric']['structure']['analytic']))
    save(OUT/'record_id_mapping.json',mapping)
    for f in PROMPTS.values():assert f.read_bytes().decode('utf-8').count('{{INPUT_JSON}}')==1
    save(OUT/'run_manifest.json',dict(created_at=p.now(),comparison_commit=COMMIT,code_commit=COMMIT,baseline_path=str(BASE),baseline_files_sha256=freeze(),fixed_input_sha256=sha(OUT/'fixed_input.json'),prompts={k:dict(path=str(f),relative_path=str(f.relative_to(ROOT)),sha256=sha(f),same_name_locations=[str(x) for x in ROOT.rglob(f.name)]) for k,f in PROMPTS.items()},model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],seed=SEED,seed_policy='Use the saved Stage3 seed 925847335 independently for each of the two 3A calls and the 3B call.',sampling=read(BF/'sampling.json'),code_sha256_before=sha(__file__),differences=['One integration call -> two isolated per-target 3A requests + one gated 3B request, including zero-observation branch. This is a procedure comparison, not a prompt-text-only effect.','Same model snapshot, sampling, 5000 output-token budget per call, seed and chat template. New input partitioning and token lengths; 3B lacks raw candidates/history.','No Stage1/2 regeneration, additional system directive, guided output, repair, semantic human editing, or selection resampling.','Mechanical checks only govern handoff. Codex semantic assessment is reported separately.']))
def sha_json(x):
    import hashlib
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def handoff():
    fixed=read(OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']};observations=[];issues=[];limitations=['Only two previously used accepted targets, both Overall=3; candidate alternatives are not independent essays.','Passing source checks does not certify semantic support or rater weighting; local observations do not establish a whole-essay score.'];provenance=[];entries={};audits={}
    for eid in ['1868:1','4902:1']:
        folder=OUT/'stage3a'/eid.replace(':','_');payload=read(OUT/'prepared_3a'/eid.replace(':','_')/'input.json')
        if not (folder/'parsed.json').exists():
            audit=dict(top_errors=['strict JSON unavailable'],observation_checks=[],issue_checks=[],passed_observations=[],passed_issues=[])
        else:audit=gate_a(read(folder/'parsed.json'),payload)
        audits[eid]=audit;save(folder/'mechanical_checks.json',audit)
        for check in audit['observation_checks']:
            if not check['pass_']:save(OUT/'exclusions'/f'{eid.replace(":","_")}__{check["index"]}.json',dict(target_essay_id=eid,**check))
        if not audit['passed_observations']:limitations.append(f'{eid}: no mechanically usable observations.')
        for o in audit['passed_observations']:
            d=o['dimension'];s=sources[eid];score=s.get('Overall') if d=='Overall' else s.get('Traits',{}).get(d)
            key=eid+'::'+o['observation_id'];observations.append(dict(o,observation_key=key,target_essay_id=eid,observed_score=score))
            bands=sorted(float(b) for b,ds in fixed['rubric']['scores'].items() if d in ds)
            if score is None:limitations.append(f'{key}: observed score missing; no band inferred.');continue
            want=[float(score)]+([max(b for b in bands if b<score)] if any(b<score for b in bands) else [])+([min(b for b in bands if b>score)] if any(b>score for b in bands) else [])
            for band in want:
                b=str(int(band)) if band.is_integer() else str(band);desc=fixed['rubric']['scores'].get(b,{}).get(d)
                if desc is None:limitations.append(f'{key}: no official rubric entry at observed band {b}.');continue
                ref=d+':'+b;entries[ref]=dict(rubric_ref_id=ref,dimension=d,score_band=int(band) if band.is_integer() else band,descriptor=desc)
                provenance.append(dict(observation_key=key,rubric_ref_id=ref,source_file=str(BF/'input.json'),source_sha256=sha(BF/'input.json'),json_path=f'$.rubric.scores["{b}"]["{d}"]',dimension=d,score_band=entries[ref]['score_band'],descriptor=desc))
        for x in audit['passed_issues']:issues.append({k:x[k] for k in ['record_id','issue_type','explanation']})
        if any(not x['pass_'] for x in audit['issue_checks']):limitations.append(f'{eid}: some candidate-issue excerpts failed validation and were excluded; see external audit.')
        if any(not x['pass_'] for x in audit['observation_checks']):limitations.append(f'{eid}: some observations failed mechanical validation and were excluded; see external audit.')
        if (folder/'parsed.json').exists():limitations += [eid+': '+s for s in array(read(folder/'parsed.json'),'insufficient_evidence') if isinstance(s,str)]
    result=dict(rater_id=fixed['rater_id'],accepted_target_ids=['1868:1','4902:1'],accepted_record_count=len(fixed['accepted_records']),verified_observations=observations,rubric_entries=list(entries.values()),source_analysis_issues=issues,evidence_limitations=limitations)
    assert len({o['observation_key'] for o in observations})==len(observations)
    save(OUT/'handoff/input_3b.json',result);save(OUT/'handoff/rubric_provenance.json',provenance)
    save(OUT/'handoff/audit_summary.json',dict(generated_observations=sum(len(a['observation_checks']) for a in audits.values()),passed_observations=len(observations),excluded_observations=sum(sum(not x['pass_'] for x in a['observation_checks']) for a in audits.values()),issues_passed=len(issues),issues_excluded=sum(sum(not x['pass_'] for x in a['issue_checks']) for a in audits.values()),semantic_support_not_certified=True))
    return result

def audit_b(v,inp):
    checks=[]
    def ck(kind,ok,**detail):checks.append(dict(kind=kind,pass_=bool(ok),**detail))
    obs={o['observation_key']:o for o in inp['verified_observations']};refs={r['rubric_ref_id']:r for r in inp['rubric_entries']}
    ck('schema',not b_schema(v),errors=b_schema(v));ck('rater_id',v.get('rater_id')==inp['rater_id'])
    support=[]
    for pat in v.get('patterns',[]):
        for s in pat.get('support',[]):support.append(s.get('observation_key'));ck('support_key',s.get('observation_key') in obs,key=s.get('observation_key'))
    for k in v.get('case_specific_observation_keys',[]):ck('case_key',k in obs,key=k)
    rep=v.get('representative_observation_key');ck('representative_key',rep in obs if obs else rep is None,key=rep)
    if v.get('pattern_status')=='supported':
        ck('one_supported_pattern',len(v.get('patterns',[]))==1)
        targets={obs[k]['target_essay_id'] for k in support if k in obs};ck('independent_support',len(targets)>=2 and targets<=set(inp['accepted_target_ids']),targets=sorted(targets))
        ck('representative_in_support',rep in support)
    else:
        ck('abstention_empty_patterns',v.get('patterns')==[])
        ck('representative_in_case_keys',rep in v.get('case_specific_observation_keys',[]) if rep else not obs)
    rc=v.get('rubric_comparison',{});orid=rc.get('observed_band_ref_id');crid=rc.get('comparison_band_ref_id');representative=obs.get(rep)
    for role,rid in [('observed',orid),('comparison',crid)]:ck('rubric_ref_exists',rid in refs if rid is not None else True,role=role,ref=rid)
    if representative:
        expected=next((r['rubric_ref_id'] for r in refs.values() if r['dimension']==representative['dimension'] and r['score_band']==representative['observed_score']),None)
        ck('observed_band_identity',orid==expected,expected=expected,actual=orid)
        if crid in refs:ck('comparison_band_identity',refs[crid]['dimension']==representative['dimension'] and refs[crid]['score_band']!=representative['observed_score'])
        paragraph=v.get('feedback_paragraph','');ck('paragraph_representative_quote',any(q in paragraph for q in representative['quotes']))
        ck('paragraph_target_id',representative['target_essay_id'] in paragraph)
    else:ck('no_observations_no_refs',orid is None and crid is None)
    text=json.dumps(v,ensure_ascii=False)
    for eid in set(re.findall(r'\b\d+:\d+\b',text)):ck('output_target_role',eid in inp['accepted_target_ids'],target=eid)
    return dict(checks=checks,total=len(checks),passed=sum(x['pass_'] for x in checks),failed=[x for x in checks if not x['pass_']],semantic_support_not_certified=True)

def finalize():
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=freeze()==m['baseline_files_sha256'];m['prompts_unchanged']=all(sha(PROMPTS[k])==v['sha256'] for k,v in m['prompts'].items());assert m['baseline_unchanged'] and m['prompts_unchanged']
    m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')};m['last_checked_at']=p.now();m['actual_model_requests']=sum(1 for f in OUT.glob('stage3*/*/raw.txt'));save(OUT/'run_manifest.json',m)
def worker():
    prepare();p.OUT=OUT;p.PROMPTS.update(PROMPTS);p.seed=lambda stage,rid:SEED;p.legacy.structural=structural
    engine=p.Engine()
    engine.run([p.job(OUT/'stage3a'/eid.replace(':','_'),'a',3,eid,read(OUT/'prepared_3a'/eid.replace(':','_')/'input.json')) for eid in ['1868:1','4902:1']])
    inp=handoff();engine.run([p.job(OUT/'stage3b/rater_7','b',3,'rater_7',inp)])
    if (OUT/'stage3b/rater_7/parsed.json').exists():save(OUT/'stage3b/rater_7/mechanical_checks.json',audit_b(read(OUT/'stage3b/rater_7/parsed.json'),inp))
    finalize()

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','worker','launch','finalize']);args=a.parse_args()
    if args.phase=='launch':
        prepare();assert not (OUT/'process.json').exists(),'Already launched; inspect results rather than regenerate'
        with (OUT/'execution.log').open('ab',buffering=0) as log:
            proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));raise
