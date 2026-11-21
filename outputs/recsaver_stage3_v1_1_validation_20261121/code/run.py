"""One fixed-input Stage 3 request. CPU audit is independent of model imports."""
from pathlib import Path
import sys, json, hashlib, importlib.util, subprocess, shutil, os, re, argparse
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1]; ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_prompt_v1_2_value_mask_20261121'
BF=BASE/'stage3/rater_7'; F=OUT/'stage3/rater_7'
PROMPT=ROOT/'prompts/en/recsaver_03_integrated_feedback_v1_1.txt'
sp=importlib.util.spec_from_file_location('prior',ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
read,save,sha=p.read,p.save,p.sha
OLD_STRUCT=p.legacy.structural

def schema(stage,v,payload):
    if v.get('schema_version')=='1.0':return OLD_STRUCT(stage,v,payload)
    errors=[]
    def need(obj, fields, path):
        if not isinstance(obj,dict):errors.append(path+': expected object');return False
        for k,t in fields.items():
            if k not in obj or not isinstance(obj[k],t):errors.append(path+'.'+k+': missing/type')
        return True
    if v.get('schema_version')!='1.1':errors.append('unknown schema_version')
    need(v,dict(schema_version=str,rater_id=str,evidence_scope=dict,patterns=list,case_specific_observations=list,source_analysis_issues=list,feedback_paragraph=str,insufficient_evidence=list),'$')
    need(v.get('evidence_scope'),dict(accepted_record_count=int,distinct_target_essay_count=int,target_essay_ids=list,coverage_and_selection_limitations=list),'$.evidence_scope')
    for i,x in enumerate(v.get('patterns',[])):
        path=f'$.patterns[{i}]'
        need(x,dict(pattern_id=str,pattern_statement=str,dimensions=list,supporting_cases=list,counterexamples_and_scope=list,representative_decision=dict,rubric_comparison=dict,next_scoring_check=dict,limitations=list),path)
        for c in x.get('supporting_cases',[]):need(c,dict(target_essay_id=str,reference_record_ids=list,quotes=list,observed_relevant_scores=dict,evaluative_connection=str),path+'.supporting_cases')
        for c in x.get('counterexamples_and_scope',[]):need(c,dict(target_essay_id=str,observation=str),path+'.counterexamples')
        need(x.get('representative_decision'),dict(target_essay_id=str,quotes=list,observable_feature=str,inferred_rater_treatment=str,observed_relevant_scores=dict,selection_reason=str),path+'.representative')
        rc=x.get('rubric_comparison',{})
        need(rc,dict(dimension=str,observed_essay_id=str,observed_score=(int,float,type(None)),rubric_quote=(str,type(None)),rubric_refs=list,criterion_interpretation=str,relationship=str,comparison=str,uncertainty=str),path+'.rubric_comparison')
        for r in rc.get('rubric_refs',[]):
            need(r,dict(dimension=str,score_band=(int,float),role=str,quote=str),path+'.rubric_refs')
            if r.get('role') not in ['observed_band','comparison_band']:errors.append(path+': invalid rubric ref role')
        need(x.get('next_scoring_check'),dict(inspect=str,distinguish=str,retain_or_reconsider=str),path+'.next_scoring_check')
    for i,c in enumerate(v.get('case_specific_observations',[])):
        need(c,dict(target_essay_id=str,quotes=list,dimension=str,observed_score=(int,float,type(None)),observation=str,scoring_implication=str,uncertainty=str),f'$.case_specific_observations[{i}]')
    return errors

def freeze():return {str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}

def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run_manifest.json').exists():return
    old=read(BASE/'run_manifest.json');payload=read(BF/'input.json')
    assert [r['record_id'] for r in payload['accepted_records']]==['1868_1__K1','1868_1__K2','4902_1__K1','4902_1__K2']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert commit=='d5eee9a20dfd066496ffb84f60271a830e501ba0'
    text=PROMPT.read_bytes().decode('utf-8');assert text.count('{{INPUT_JSON}}')==1
    m=dict(created_at=p.now(),comparison_commit=commit,code_commit=commit,baseline_path=str(BASE),baseline_files_sha256=freeze(),prompt=dict(path=str(PROMPT),windows_path='C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/'+str(PROMPT.relative_to(ROOT)),sha256=sha(PROMPT),same_name_locations=[str(f) for f in ROOT.rglob(PROMPT.name)]),model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],sampling=read(BF/'sampling.json'),fixed_input_sha256=sha(BF/'input.json'),code_sha256=sha(__file__),differences=['Only Stage3 prompt v1.0 -> v1.1; schema-aware validation added.','Exact saved input, ordered records, model snapshot, sampling, seed, chat template retained. No Stage1/2 execution.','One new generation; no additional system instructions, guided decoding, output repair or format retry. Model scheduling may preclude tokenwise determinism.'])
    save(OUT/'run_manifest.json',m)

def worker():
    prepare();p.OUT=OUT;p.PROMPTS['s3']=PROMPT;p.legacy.structural=schema
    engine=p.Engine();engine.run([p.job(F,'s3',3,'rater_7',read(BF/'input.json'))])
    assert sha(F/'input.json')==sha(BF/'input.json')
    assert read(F/'sampling.json')==read(BF/'sampling.json')
    audit()

def audit_value(v,payload):
    checks=[]
    def ck(path,kind,ok,**detail):checks.append(dict(path=path,kind=kind,pass_=bool(ok),**detail))
    records={r['record_id']:r['target_essay_id'] for r in payload['accepted_records']};targets=set(records.values());sources={e['essay_id']:e for e in payload['source_essays']}
    def score(e,d):
        s=sources.get(e,{})
        return s.get('Overall') if d=='Overall' else s.get('Traits',{}).get(d)
    scope=v.get('evidence_scope',{})
    for k,w in [('accepted_record_count',len(records)),('distinct_target_essay_count',len(targets))]:ck('$.evidence_scope.'+k,'count',scope.get(k)==w,actual=scope.get(k),expected=w)
    ck('$.evidence_scope.target_essay_ids','target_set',set(scope.get('target_essay_ids',[]))==targets and len(scope.get('target_essay_ids',[]))==len(targets))
    def walk(obj,path='$',context=None):
        if isinstance(obj,dict):
            eid=obj.get('target_essay_id',context)
            if 'target_essay_id' in obj:ck(path+'.target_essay_id','accepted_target_role',eid in targets,actual=eid)
            for rid in obj.get('reference_record_ids',[]):ck(path+'.reference_record_ids','candidate_target_mapping',records.get(rid)==eid,candidate=rid,target=eid)
            for i,q in enumerate(obj.get('quotes',[])):ck(path+f'.quotes[{i}]','source_quote_exact',isinstance(q,str) and bool(q) and q in sources.get(eid,{}).get('text',''),target=eid,quote=q)
            if isinstance(obj.get('observed_relevant_scores'),dict):
                scores=obj['observed_relevant_scores'];flat={k:x for k,x in scores.items() if k!='Traits'};flat.update(scores.get('Traits',{}))
                for d,x in flat.items():ck(path+'.observed_relevant_scores.'+d,'observed_score',x==score(eid,d) and not isinstance(x,bool),actual=x,expected=score(eid,d),target=eid)
            if 'observed_score' in obj and 'target_essay_id' in obj:ck(path+'.observed_score','observed_score',obj['observed_score']==score(eid,obj.get('dimension')),actual=obj['observed_score'],expected=score(eid,obj.get('dimension')))
            for k,x in obj.items():walk(x,path+'.'+k,eid)
        elif isinstance(obj,list):
            for i,x in enumerate(obj):walk(x,path+f'[{i}]',context)
    walk(v)
    for i,pat in enumerate(v.get('patterns',[])):
        path=f'$.patterns[{i}].rubric_comparison';rc=pat.get('rubric_comparison',{});rep=pat.get('representative_decision',{}).get('target_essay_id');dim=rc.get('dimension');refs=rc.get('rubric_refs',[])
        if v.get('schema_version')=='1.1':
            ck(path+'.observed_essay_id','representative_identity',rc.get('observed_essay_id')==rep)
            ck(path+'.observed_score','observed_score',rc.get('observed_score')==score(rep,dim),expected=score(rep,dim),actual=rc.get('observed_score'))
            ck(path+'.rubric_quote','first_ref_consistency',rc.get('rubric_quote')==(refs[0].get('quote') if refs else None))
            for j,r in enumerate(refs):
                band=r.get('score_band');rd=r.get('dimension');q=r.get('quote');desc=payload['rubric']['scores'].get(str(band),{}).get(rd,'')
                ck(path+f'.rubric_refs[{j}]','rubric_dimension_band_quote',bool(q) and q in desc,dimension=rd,band=band,quote=q)
                ck(path+f'.rubric_refs[{j}].dimension','rubric_dimension',rd==dim)
                ck(path+f'.rubric_refs[{j}].role','rubric_band_role',band==score(rep,dim) if r.get('role')=='observed_band' else band!=score(rep,dim),role=r.get('role'),observed=score(rep,dim),band=band)
            if rc.get('relationship')=='consistent_with_rubric':ck(path,'observed_band_cited',any(r.get('role')=='observed_band' for r in refs))
        else:
            q=rc.get('rubric_quote');locations=[dict(band=b,dimension=d) for b,ds in payload['rubric']['scores'].items() for d,t in ds.items() if q and q in t]
            ck(path+'.rubric_quote','legacy_quote_located',bool(locations),locations=locations,ambiguous=len(locations)>1)
            claims=re.findall(r'(?:Overall score of|Overall)\s+(\d)',rc.get('comparison','')+' '+rc.get('criterion_interpretation',''))
            if claims:ck(path+'.comparison','legacy_claimed_band_matches_quote',any(x['dimension']==dim and x['band'] in claims for x in locations),claimed_bands=claims,locations=locations)
    return dict(schema_version=v.get('schema_version'),schema_errors=schema(3,v,payload),checks=checks,total=len(checks),passed=sum(c['pass_'] for c in checks),failed=[c for c in checks if not c['pass_']])

def audit():
    prepare();payload=read(BF/'input.json')
    for label,folder in [('v1_0',BF),('v1_1',F)]:
        if (folder/'parsed.json').exists():save(OUT/f'{label}_checks.json',audit_value(read(folder/'parsed.json'),payload))
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=freeze()==m['baseline_files_sha256'];m['prompt_unchanged']=sha(PROMPT)==m['prompt']['sha256'];m['code_sha256_after']=sha(__file__);m['last_checked_at']=p.now();save(OUT/'run_manifest.json',m)
    assert m['baseline_unchanged'] and m['prompt_unchanged']

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','worker','audit','launch']);args=a.parse_args()
    if args.phase=='launch':
        prepare()
        with (OUT/'execution.log').open('ab') as log:
            proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'worker'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=p.now()));print(proc.pid)
    else:globals()[args.phase]()
