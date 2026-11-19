"""Frozen first validation. No prompt edits, output repair, or mismatch resampling."""
from pathlib import Path
import argparse, csv, hashlib, json, os, re, subprocess, sys, time, traceback
from datetime import datetime, timezone, timedelta
from decimal import Decimal

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[1]
TRAITS = ['Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']
NAMES = ['recsaver_01_reference_rationale_v1_0.txt','recsaver_02_overall_reconstruction_v1_0.txt','recsaver_03_integrated_feedback_v1_0.txt']
def now(): return datetime.now(timezone(timedelta(hours=9))).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def journal(p,v):
    with Path(p).open('a',encoding='utf-8') as f: f.write(json.dumps(v,ensure_ascii=False)+'\n')
def csvsave(p, rows, columns):
    with Path(p).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
def prompt_paths(): return [ROOT/'prompts/en'/n for n in NAMES]
def source(p): return str(p.relative_to(ROOT)).replace('\\','/')
def num(v): return int(Decimal(str(v)))
def essay(row):
    return dict(essay_id=f"{row['source_row_id']}:{row['rater_position']}",text=row['Text'],Overall=num(row['Overall']),Traits={t:num(row[t]) for t in TRAITS})

def prepare():
    if (OUT/'run_manifest.json').exists():
        m=read(OUT/'run_manifest.json')
        assert {source(p):sha(p) for p in prompt_paths()}==m['prompt_sha256_before']
        assert sha(__file__)==m['code_sha256'], 'Code changed: record a separate revision before execution'
        return
    cfg=read(ROOT/'configs/rater_feedback_development_v22.json')
    old=read(ROOT/'outputs/rater_feedback_pilot_v2/v2_2/inputs.json')
    with (ROOT/cfg['wide_path']).open(encoding='utf-8-sig',newline='') as f: wide=list(csv.DictReader(f))
    with (ROOT/cfg['raw_path']).open(encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f))
    index={f"{r['source_row_id']}:{r['rater_position']}":r for r in wide}
    checks=[]; cases=[]
    for item in old:
        if item['target_id'] not in cfg['target_ids']: continue
        all_ids=[item['target_id']]+[h['essay_id'] for h in item['history']]
        for eid in all_ids:
            row=index[eid]; r=raw[int(row['source_row_id'])]; pos=row['rater_position']
            assert row['rater_id']==r[f'Rater_{pos}']=='rater_7'
            assert row['Text']==r['Text']
            assert all(Decimal(row[t])==Decimal(r[f'{t}_{pos}']) for t in ['Overall']+TRAITS)
            old_e=item['target'] if eid==item['target_id'] else next(h for h in item['history'] if h['essay_id']==eid)
            assert old_e['text']==row['Text'] and old_e['overall']==num(row['Overall'])
            assert old_e['traits']=={t:num(row[t]) for t in TRAITS}
            checks.append(dict(essay_id=eid,raw_position=pos,rater_id=row['rater_id'],raw_wide_prior_input_equal=True))
        assert len(all_ids)==4 and len(set(all_ids))==4
        cases.append(dict(split='development',rater_id='rater_7',target=essay(index[item['target_id']]),history=[essay(index[e]) for e in all_ids[1:]],selection='Existing fixed development set v2.2; previously exposed; retain identical history IDs'))
    assert len(cases)==3
    # Reserve two additional essays; prior exposure is explicitly NOT assumed absent.
    excluded={e['essay_id'] for c in cases for e in [c['target']]+c['history']}
    reserved=[]
    for row in sorted(wide,key=lambda r:hashlib.sha256(('20261118:'+r['source_row_id']+':'+r['rater_position']).encode()).hexdigest()):
        eid=f"{row['source_row_id']}:{row['rater_position']}"
        if row['rater_id']!='rater_7' or eid in excluded: continue
        if not all(Decimal(row[t]) in range(1,6) for t in ['Overall']+TRAITS): continue
        reserved.append(dict(split='reserved_not_generated',rater_id='rater_7',essay_id=eid,prior_exposure='unknown; not certified unused final evaluation',selection='SHA256(20261118:row:position), excluding all development targets/history'))
        if len(reserved)==2: break
    save(OUT/'case_manifest.json',dict(frozen_at=now(),development=cases,reserved=reserved,notes=['Existing development set takes precedence over provisional 3x4 selection. One rater, all targets Overall=3; no broader score-coverage claim.','Reserved items excluded from every development input; historical exposure unknown, so no unused-final-set claim.']))
    save(OUT/'input_checks.json',checks)
    rubric=read(ROOT/cfg['rubric_path']);save(OUT/'rubric.json',rubric)
    spec=dict(valid_overall_values=[1,2,3,4,5],valid_trait_values=[1,2,3,4,5],increment=1,Overall='Holistic language proficiency judgment; use the supplied Overall rubric descriptors.',Traits={t:dict(descriptors={k:v[t] for k,v in rubric['scores'].items()}) for t in TRAITS},relationship='Overall is the original human holistic judgment. No arithmetic or weighted relationship to Traits is specified.',definition_sources=['rubrics/ellipse_rubric_structured.json','src/config.py','src/transform_data.py','README.md'])
    save(OUT/'score_specification.json',spec)
    files=[ROOT/cfg['raw_path'],ROOT/cfg['wide_path'],ROOT/cfg['rubric_path'],ROOT/'configs/rater_feedback_development_v22.json',ROOT/'outputs/rater_feedback_pilot_v2/v2_2/inputs.json',ROOT/'outputs/rater_feedback_pilot_v2/v2_2/assessment.md']
    try: git=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except Exception: git=None
    manifest=dict(created_at=now(),status='prepared',prompt_sha256_before={source(p):sha(p) for p in prompt_paths()},source_sha256={source(p):sha(p) for p in files},code_sha256=sha(__file__),git_commit=git,model=cfg['model'],generation=dict(temperature=0.2,top_p=0.8),max_tokens={'stage1':6500,'stage2':1200,'stage3':5000},seed=20261118,seed_policy='first 8 hex SHA256(20261118:stage:record_id) modulo 2**31; separate requests; stochastic independence not guaranteed',candidates_per_target=2,history_size=3,system_message=None,chat='one user message, tokenizer.apply_chat_template; rendered chat saved. No guided decoding, repair or extra instructions.',retries=dict(transport=1,model_format=0,context=0,score_mismatch=0),acceptance=['Stage1 and Stage2 valid JSON/schema/identity','status=estimated','reconstructed_overall in 1..5 integers','Decimal(str(prediction)) == Decimal(str(observed)); no rounding','no confirmed target-score disclosure in score_free_analysis'],important='Stage1 conditions on observed target Overall and Traits; retrospective explanation, not independent or faithful human reasoning.',max_tokens_reason='New English JSON templates contain extensive evidence fields; initial fixed budgets 6500/1200/5000, no output-driven extension or input truncation.',holdout='Reserved only, prior exposure unknown; never generated in this run.')
    save(OUT/'run_manifest.json',manifest)
    for s in ['stage1','stage2','stage3']: (OUT/s).mkdir(exist_ok=True)

def build(stage,rid,payload):
    p=prompt_paths()[stage-1]; template=p.read_bytes().decode('utf-8')
    assert template.count('{{INPUT_JSON}}')==1
    rendered=template.replace('{{INPUT_JSON}}',json.dumps(payload,ensure_ascii=False,allow_nan=False))
    folder=OUT/f'stage{stage}'/rid;folder.mkdir(parents=True,exist_ok=True)
    save(folder/'input.json',payload);save(folder/'messages.json',[dict(role='user',content=rendered)])
    save(folder/'prompt_integrity.json',dict(template=source(p),sha256=sha(p),only_input_placeholder_replaced=True,rendered_sha256=hashlib.sha256(rendered.encode()).hexdigest()))
    return folder

def no_dupes(pairs):
    d={}
    for k,v in pairs:
        if k in d: raise ValueError('duplicate JSON key: '+k)
        d[k]=v
    return d

def structural(stage,value,payload):
    # Required keys and container types follow the literal JSON example in each canonical prompt.
    template=prompt_paths()[stage-1].read_text(encoding='utf-8')
    start=template.index('{\n',template.index('OUTPUT FORMAT'))
    example=json.JSONDecoder().raw_decode(template[start:])[0]
    errors=[]
    def walk(x,ex,path):
        if isinstance(ex,dict):
            if not isinstance(x,dict): errors.append(path+': expected object');return
            for k,e in ex.items():
                if k not in x: errors.append(path+'/'+k+': missing')
                else: walk(x[k],e,path+'/'+k)
        elif isinstance(ex,list):
            if not isinstance(x,list): errors.append(path+': expected array')
            elif ex:
                for i,v in enumerate(x): walk(v,ex[0],path+f'/{i}')
        elif isinstance(ex,str):
            if x is None and path.endswith('/rubric_quote'): return
            if not isinstance(x,str): errors.append(path+': expected string')
        elif ex is None:
            if x is not None and (isinstance(x,bool) or not isinstance(x,(int,float))): errors.append(path+': expected numeric/null score')
        elif isinstance(ex,int):
            if isinstance(x,bool) or not isinstance(x,int): errors.append(path+': expected integer')
    walk(value,example,'')
    if not isinstance(value,dict): return errors
    if value.get('schema_version')!='1.0': errors.append('schema_version')
    if value.get('rater_id')!=payload['rater_id']: errors.append('rater_id mismatch')
    if stage<3 and value.get('target_essay_id')!=payload['target']['essay_id']: errors.append('target ID mismatch')
    if stage==1:
        for h in value.get('score_free_analysis',{}).get('history_patterns',[]):
            if h.get('status') not in ['recurring_in_supplied_history','single_case_hypothesis']: errors.append('history pattern status')
    if stage==2:
        status=value.get('status');v=value.get('reconstructed_overall')
        if status not in ['estimated','insufficient_information','contaminated_input']: errors.append('invalid status')
        if status=='estimated' and (isinstance(v,bool) or v not in [1,2,3,4,5]): errors.append('invalid estimate')
        if status!='estimated' and v is not None: errors.append('non-estimated value must be null')
    return errors

class Engine:
    def __init__(self):
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',VLLM_USE_V1='0',VLLM_ENABLE_V1_ENGINE='0')
        import vllm,torch,transformers
        from transformers import AutoTokenizer
        from huggingface_hub import snapshot_download
        self.m=read(OUT/'run_manifest.json');cfg=self.m['model']
        model_path=snapshot_download(cfg['model_id'],local_files_only=True)
        self.tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
        self.path=model_path;self.llm=None
        save(OUT/'environment.json',dict(timestamp=now(),python=sys.version,vllm=vllm.__version__,torch=torch.__version__,transformers=transformers.__version__,model_id=cfg['model_id'],local_snapshot=model_path,cuda=torch.cuda.is_available(),gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None))
    def run(self,stage,jobs,dry=False):
        from vllm import LLM, SamplingParams
        pending=[]
        for rid,payload in jobs:
            folder=build(stage,rid,payload)
            if (folder/'result.json').exists() or (folder/'error.json').exists(): continue
            messages=read(folder/'messages.json')
            chat=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            (folder/'rendered_chat.txt').write_text(chat,encoding='utf-8')
            count=len(self.tokenizer.encode(chat,add_special_tokens=False));budget=self.m['max_tokens'][f'stage{stage}']
            save(folder/'context_check.json',dict(prompt_tokens=count,max_tokens=budget,max_model_len=self.m['model']['max_model_len'],fits=count+budget<=self.m['model']['max_model_len'],input_truncated=False))
            if count+budget>self.m['model']['max_model_len']:
                save(folder/'error.json',dict(kind='context_capacity',message='Input retained; generation not attempted'));continue
            seed=int(hashlib.sha256(f'20261118:stage{stage}:{rid}'.encode()).hexdigest()[:8],16)%(2**31)
            params=dict(**self.m['generation'],max_tokens=budget,seed=seed)
            save(folder/'sampling.json',params)
            pending.append((rid,payload,folder,chat,params))
        if dry or not pending: return
        if self.llm is None:
            cfg=dict(self.m['model']);cfg.pop('model_id')
            opts=cfg.pop('runtime_options',{})
            self.llm=LLM(model=self.path,trust_remote_code=True,**cfg,**opts)
        prompts=[x[3] for x in pending];params=[SamplingParams(**x[4]) for x in pending]
        for attempt in range(2):
            started=now()
            try:
                outputs=self.llm.generate(prompts,params,use_tqdm=True)
                break
            except (ConnectionError,TimeoutError) as ex:
                journal(OUT/'execution_events.jsonl',dict(stage=stage,attempt=attempt,started=started,error=repr(ex),kind='transport'))
                if attempt: raise
            except Exception as ex:
                journal(OUT/'execution_events.jsonl',dict(stage=stage,attempt=attempt,started=started,error=traceback.format_exc(),kind='runtime_not_retried'))
                raise
        for (rid,payload,folder,_,params),output in zip(pending,outputs):
            item=output.outputs[0];text=item.text
            (folder/'raw.txt').write_text(text,encoding='utf-8')
            save(folder/'generation.json',dict(started=started,finished=now(),seed=params['seed'],attempt=attempt,finish_reason=item.finish_reason,stop_reason=item.stop_reason,prompt_tokens=len(output.prompt_token_ids),output_tokens=len(item.token_ids),raw_sha256=sha(folder/'raw.txt')))
            try:
                value=json.loads(text,object_pairs_hook=no_dupes,parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
                save(folder/'parsed.json',value)
                errors=structural(stage,value,payload)
                save(folder/'result.json',dict(json_valid=True,schema_valid=not errors,errors=errors,truncated=item.finish_reason=='length'))
            except Exception as ex:
                save(folder/'result.json',dict(json_valid=False,schema_valid=False,errors=[str(ex)],truncated=item.finish_reason=='length'))

def ok(folder): return (folder/'result.json').exists() and read(folder/'result.json')['schema_valid']
def base(c): return dict(rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),rater_id=c['rater_id'],history=c['history'])
def ids(c): return [c['target']['essay_id'].replace(':','_')+f'__K{i}' for i in [1,2]]

def leak_scan(value):
    hits=[]
    patterns=[r'\b(?:overall|cohesion|syntax|vocabulary|phraseology|grammar|conventions|score|band|level)\s*(?:score\s*)?(?:is|of|was|=|:|at|assigned|rated)?\s*(?:[1-5](?:\.\d+)?|one|two|three|four|five)\b',r'\b(?:observed|assigned|target).{0,60}\b(?:[1-5]|one|two|three|four|five)\b',r'\b(?:average|sum|weight|deduct|subtract|plus|minus)\w*\b']
    def walk(v,path):
        if isinstance(v,dict):
            for k,x in v.items():
                if k not in ['quotes','relevant_observed_history_scores']: walk(x,path+'/'+k)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,path+f'/{i}')
        elif isinstance(v,str):
            for rule in patterns:
                if re.search(rule,v,re.I): hits.append(dict(path=path,rule=rule,text=v))
    walk(value,'/score_free_analysis')
    return hits

def stage12(engine,dry=False):
    cases=read(OUT/'case_manifest.json')['development']
    engine.run(1,[(rid,dict(**base(c),target=c['target'])) for c in cases for rid in ids(c)],dry)
    jobs=[]
    for c in cases:
        for rid in ids(c):
            f=OUT/'stage1'/rid
            if not ok(f):continue
            a=read(f/'parsed.json')['score_free_analysis']
            save(f/'leak_scan.json',dict(rules='Heuristic prose matching; exclude exact quotes and explicitly labeled history score objects. Suspicions require semantic review; no rewriting.',suspicions=leak_scan(a),confirmed_leak=None))
            payload=dict(**base(c),target={k:c['target'][k] for k in ['essay_id','text']},reference_analysis=a)
            assert set(payload['target'])=={'essay_id','text'}
            assert 'observed_score_alignment' not in payload
            jobs.append((rid,payload))
    engine.run(2,jobs,dry)

def decisions():
    reviews=read(OUT/'leak_review.json') if (OUT/'leak_review.json').exists() else {}
    rows=[]
    for c in read(OUT/'case_manifest.json')['development']:
        for rid in ids(c):
            f1=OUT/'stage1'/rid; f2=OUT/'stage2'/rid
            p2=read(f2/'parsed.json') if (f2/'parsed.json').exists() else {}
            valid=ok(f2) and p2.get('status')=='estimated'
            match=bool(valid and Decimal(str(p2['reconstructed_overall']))==Decimal(str(c['target']['Overall'])))
            review=reviews.get(rid,{})
            confirmed=review.get('confirmed_leak')
            rejected=[]
            if not ok(f1): rejected.append('stage1_invalid_or_not_run')
            if not valid: rejected.append('stage2_invalid_or_no_estimate')
            elif not match: rejected.append('overall_mismatch')
            if confirmed is True:rejected.append('confirmed_leak')
            if confirmed is None:rejected.append('leak_review_pending')
            row=dict(candidate_id=rid,rater_id=c['rater_id'],essay_id=c['target']['essay_id'],observed_overall=c['target']['Overall'],stage1_valid=ok(f1),stage2_executed=(f2/'raw.txt').exists(),valid_estimate=valid,reconstructed_overall=p2.get('reconstructed_overall'),match=match,confirmed_leak=confirmed,accepted=not rejected,rejection_reasons=';'.join(rejected),content_review='pending')
            rows.append(row);save(f2/'external_decision.json',row)
    csvsave(OUT/'candidate_results.csv',rows,list(rows[0]))
    essays=[dict(rater_id=c['rater_id'],essay_id=c['target']['essay_id'],observed_overall=c['target']['Overall'],candidate_count=2,accepted_count=sum(r['accepted'] for r in rows if r['essay_id']==c['target']['essay_id'])) for c in read(OUT/'case_manifest.json')['development']]
    csvsave(OUT/'essay_results.csv',essays,list(essays[0]))
    save(OUT/'summary.json',dict(planned_candidates=len(rows),generated_candidates=sum((OUT/'stage1'/r['candidate_id']/'raw.txt').exists() for r in rows),stage1_valid=sum(r['stage1_valid'] for r in rows),stage2_executed=sum(r['stage2_executed'] for r in rows),valid_estimates=sum(r['valid_estimate'] for r in rows),matches=sum(r['match'] for r in rows),accepted_records=sum(r['accepted'] for r in rows),distinct_accepted_targets=sum(e['accepted_count']>0 for e in essays),rows=rows))
    return rows

def stage3(engine,dry=False):
    rows=decisions();cases=read(OUT/'case_manifest.json')['development'];records=[];sources={}
    for r in rows:
        if not r['accepted']:continue
        c=next(c for c in cases if c['target']['essay_id']==r['essay_id'])
        records.append(dict(record_id=r['candidate_id'],**read(OUT/'stage1'/r['candidate_id']/'parsed.json')))
        for e in [c['target']]+c['history']: sources[e['essay_id']]=e
    if not records:
        save(OUT/'stage3/skip.json',dict(reason='No accepted records; no synthesis'));return
    payload=dict(rater_id='rater_7',rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),accepted_records=records,source_essays=list(sources.values()),selection_metadata=dict(generated_candidate_count=6,accepted_record_count=len(records),distinct_target_essay_count=len({r['target_essay_id'] for r in records}),observed_overall_coverage=[3],scope='Previously used fixed development set, one rater and three Overall=3 essays. Reconstruction selection does not establish content correctness.',excluded_records=[r for r in rows if not r['accepted']] ))
    engine.run(3,[('rater_7',payload)],dry)

def finalize():
    m=read(OUT/'run_manifest.json');m['prompt_sha256_after']={source(p):sha(p) for p in prompt_paths()};m['prompt_unchanged']=m['prompt_sha256_after']==m['prompt_sha256_before'];m['last_checked_at']=now();save(OUT/'run_manifest.json',m)
    assert m['prompt_unchanged']

def main():
    a=argparse.ArgumentParser();a.add_argument('--phase',choices=['prepare','stage12','stage3','summarize'],default='prepare');a.add_argument('--dry-run',action='store_true');args=a.parse_args()
    prepare()
    try:
        if args.phase in ['stage12','stage3']:
            engine=Engine()
            if args.phase=='stage12':stage12(engine,args.dry_run)
            else:stage3(engine,args.dry_run)
        if args.phase=='summarize':decisions()
    except Exception:
        journal(OUT/'execution_events.jsonl',dict(time=now(),phase=args.phase,exception=traceback.format_exc()));raise
    finally:finalize()
if __name__=='__main__':main()
