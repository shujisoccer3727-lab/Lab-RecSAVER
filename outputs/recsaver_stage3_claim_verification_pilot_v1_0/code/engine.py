"""Paired v1.1 validation; immutable raw responses, no repair/resampling."""
from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, os, subprocess, sys, time, traceback
from decimal import Decimal
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
OLD=ROOT/'outputs/recsaver_prompt_v1_0_initial_20261118'
sp=importlib.util.spec_from_file_location('legacy',OLD/'code/run.py');legacy=importlib.util.module_from_spec(sp);sp.loader.exec_module(legacy)
read,save,sha,now,csvsave=legacy.read,legacy.save,legacy.sha,legacy.now,legacy.csvsave
PROMPTS={'s1':ROOT/'prompts/en/recsaver_01_reference_rationale_v1_1.txt','s2':ROOT/'prompts/en/recsaver_02_overall_reconstruction_v1_1.txt','s2_old':ROOT/'prompts/en/recsaver_02_overall_reconstruction_v1_0.txt','s3':ROOT/'prompts/en/recsaver_03_integrated_feedback_v1_0.txt'}
def rel(p):return str(p.relative_to(ROOT)).replace('\\','/')
def freeze_files():return {rel(p):sha(p) for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
def cases():return read(OUT/'case_manifest.json')['development']
def ids(c):return legacy.ids(c)
def seed(stage,rid):return int(hashlib.sha256(f'20261118:stage{stage}:{rid}'.encode()).hexdigest()[:8],16)%(2**31)
def status(s,**kw):save(OUT/'status.json',dict(timestamp=now(),status=s,**kw));print(s,flush=True)
def prepare():
    if (OUT/'run_manifest.json').exists():
        m=read(OUT/'run_manifest.json');assert m['code_sha256']==sha(__file__)
        assert all(sha(PROMPTS[k])==v['sha256_before'] for k,v in m['prompts'].items());return
    OUT.mkdir(parents=True,exist_ok=True)
    old=read(OLD/'run_manifest.json')
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='078ae7e912a42e4f3c2f97b5ecd9ed752a583052'
    for p,h in old['prompt_sha256_before'].items():assert sha(ROOT/p)==h
    for n in ['case_manifest.json','rubric.json','score_specification.json']:save(OUT/n,read(OLD/n))
    for c in cases():
        assert len(c['history'])==3 and all(h['essay_id']!=c['target']['essay_id'] for h in c['history'])
        for rid in ids(c):assert read(OLD/'stage1'/rid/'input.json')==dict(rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),rater_id=c['rater_id'],history=c['history'],target=c['target'])
    duplicates={k:[rel(p) for p in ROOT.rglob(v.name) if '.git' not in p.parts] for k,v in PROMPTS.items()}
    m=dict(created_at=now(),comparison_commit='078ae7e912a42e4f3c2f97b5ecd9ed752a583052',baseline_path=str(OLD),baseline_files_sha256=freeze_files(),prompts={k:dict(path=str(p),relative_path=rel(p),sha256_before=sha(p),same_name_locations=duplicates[k]) for k,p in PROMPTS.items()},code_sha256=sha(__file__),model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],seed=old['seed'],seed_policy=old['seed_policy'],system_message=old['system_message'],chat=old['chat'],retries=old['retries'],differences=['Stage1 v1.1 and Stage2 v1.1 canonical text only; Stage3 v1.0 unchanged.','Same six record IDs, exact Stage1 payloads, 20261118 stage/record seeds, chat serialization, budgets and sampling as baseline.','New preflight rejects confirmed numerical target-band/range application as well as recoverable observed scores; full observed score copying checked.','Same-input diagnostics use paired old/new prompt, same payload and original stage2 candidate seed; kept out of main selection.','No guided decoding, task system message, repair or mismatch resampling. New call grouping may change GPU scheduling; stochastic independence and tokenwise determinism not guaranteed.'],preflight_policy='Strict JSON/schema/identity; all copied observed target scores present/equal; no confirmed direct/recoverable disclosure; no numerical target-band/range application. Codex semantic review recorded before Stage2.',stage3_policy='Only if at least two distinct accepted targets. k counts full records; source essays include all corresponding target/history.',notes='Single rater, three previously used targets all Overall=3; no general reconstruction performance or causal explanation claims.')
    save(OUT/'run_manifest.json',m);status('prepared')
def render(key,payload):
    text=PROMPTS[key].read_bytes().decode('utf-8');assert text.count('{{INPUT_JSON}}')==1
    return text.replace('{{INPUT_JSON}}',json.dumps(payload,ensure_ascii=False,allow_nan=False))
def valid(f):return (f/'result.json').exists() and read(f/'result.json')['schema_valid']
def job(folder,key,stage,rid,payload):return dict(folder=folder,key=key,stage=stage,rid=rid,payload=payload)

class Engine:
    def __init__(self):
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',VLLM_USE_V1='0',VLLM_ENABLE_V1_ENGINE='0')
        import vllm,torch,transformers
        from transformers import AutoTokenizer
        from huggingface_hub import snapshot_download
        self.m=read(OUT/'run_manifest.json');self.path=snapshot_download(self.m['model']['model_id'],local_files_only=True)
        self.tokenizer=AutoTokenizer.from_pretrained(self.path,local_files_only=True);self.llm=None
        save(OUT/'environment.json',dict(timestamp=now(),python=sys.version,vllm=vllm.__version__,torch=torch.__version__,transformers=transformers.__version__,model_snapshot=self.path,gpu=torch.cuda.get_device_name(0)))
    def run(self,jobs):
        from vllm import LLM,SamplingParams
        pending=[]
        for j in jobs:
            f=j['folder'];f.mkdir(parents=True,exist_ok=True)
            if (f/'result.json').exists() or (f/'error.json').exists():continue
            assert not (f/'raw.txt').exists(),'Unclassified existing raw output: inspect before resume'
            payload=j['payload'];messages=[dict(role='user',content=render(j['key'],payload))]
            chat=self.tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            tokens=len(self.tokenizer.encode(chat,add_special_tokens=False));budget=self.m['max_tokens'][f'stage{j["stage"]}']
            params=dict(**self.m['generation'],max_tokens=budget,seed=seed(j['stage'],j['rid']))
            save(f/'input.json',payload);save(f/'messages.json',messages);save(f/'sampling.json',params)
            (f/'rendered_chat.txt').write_text(chat,encoding='utf-8')
            save(f/'integrity.json',dict(prompt_path=str(PROMPTS[j['key']]),prompt_sha256=sha(PROMPTS[j['key']]),input_sha256=sha(f/'input.json'),prompt_tokens=tokens,max_tokens=budget,context_limit=32768,input_truncated=False,only_placeholder_replaced=True))
            if tokens+budget>32768:save(f/'error.json',dict(kind='context_capacity',prompt_tokens=tokens,max_tokens=budget));continue
            pending.append((j,chat,params))
        if not pending:return
        if self.llm is None:
            cfg=dict(self.m['model']);cfg.pop('model_id');opts=cfg.pop('runtime_options',{})
            self.llm=LLM(model=self.path,trust_remote_code=True,**cfg,**opts)
        for attempt in range(1):
            started=now()
            try:
                outputs=self.llm.generate([v[1] for v in pending],[SamplingParams(**v[2]) for v in pending],use_tqdm=True);break
            except (ConnectionError,TimeoutError):
                legacy.journal(OUT/'events.jsonl',dict(time=now(),kind='transport',attempt=attempt,error=traceback.format_exc()))
                if attempt:raise
        for (j,_,params),output in zip(pending,outputs):
            f=j['folder'];item=output.outputs[0];text=item.text
            (f/'raw.txt').write_text(text,encoding='utf-8')
            save(f/'generation.json',dict(started=started,finished=now(),attempt=attempt,seed=params['seed'],finish_reason=item.finish_reason,prompt_tokens=len(output.prompt_token_ids),output_tokens=len(item.token_ids),raw_sha256=sha(f/'raw.txt')))
            try:
                value=json.loads(text,object_pairs_hook=legacy.no_dupes,parse_constant=lambda s:(_ for _ in ()).throw(ValueError(s)))
                save(f/'parsed.json',value);errors=legacy.structural(j['stage'],value,j['payload'])
                result=dict(json_valid=True,schema_valid=not errors,errors=errors,truncated=item.finish_reason=='length')
            except Exception as ex:result=dict(json_valid=False,schema_valid=False,errors=[str(ex)],truncated=item.finish_reason=='length')
            save(f/'result.json',result)
            # Diagnostic extraction never replaces raw/parsed/result and never affects selection.
            if j['folder'].is_relative_to(OUT/'stage2_diagnostics'):
                inner=text.strip();change='none'
                if inner.startswith('```') and inner.endswith('```'):
                    inner=inner.split('\n',1)[1].rsplit('```',1)[0].strip();change='strip one enclosing Markdown fence for diagnosis only'
                try:diagnostic=json.loads(inner,object_pairs_hook=legacy.no_dupes)
                except Exception:diagnostic=None
                save(f/'diagnostic_reading.json',dict(transformation=change,strict_json_pass=result['json_valid'],value=diagnostic,excluded_from_main_acceptance=True))

def stage1(engine):
    status('stage1_running')
    engine.run([job(OUT/'stage1'/rid,'s1',1,rid,read(OLD/'stage1'/rid/'input.json')) for c in cases() for rid in ids(c)])
    status('waiting_for_preflight_review')
def build_stage2(c,rid):
    value=read(OUT/'stage1'/rid/'parsed.json')
    payload=dict(rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),rater_id=c['rater_id'],history=c['history'],target={k:c['target'][k] for k in ['essay_id','text']},reference_analysis=value['score_free_analysis'])
    assert set(payload['target'])=={'essay_id','text'} and 'observed_score_alignment' not in payload
    return payload
def after_review(engine):
    review=read(OUT/'preflight_review.json');main=[]
    for c in cases():
        for rid in ids(c):
            r=review['candidates'][rid];assert isinstance(r['pass'],bool)
            if r['pass']:
                assert valid(OUT/'stage1'/rid) and not r['direct_or_recoverable_disclosure'] and not r['numbered_target_band_or_range']
                main.append(job(OUT/'stage2'/rid,'s2',2,rid,build_stage2(c,rid)))
            else:save(OUT/'preflight_rejections'/f'{rid}.json',r)
    control=review['diagnostic_control'];controlid=control['candidate_id']
    if control['source']=='v1.1_candidate':
        c=next(c for c in cases() if controlid in ids(c));cp=build_stage2(c,controlid)
    else:cp=read(OUT/control['input_path'])
    tests={'A':('1514_1__K1',read(OLD/'stage2/1514_1__K1/input.json')),'B':('4902_1__K2',read(OLD/'stage2/4902_1__K2/input.json')),'C':(controlid,cp)}
    save(OUT/'diagnostic_selection.json',dict(control=control,tests={k:dict(seed_record_id=v[0],input_json=v[1]) for k,v in tests.items()}))
    status('stage2_diagnostics_running')
    engine.run([job(OUT/'stage2_diagnostics'/k/ver,pkey,2,rid,payload) for k,(rid,payload) in tests.items() for ver,pkey in [('v1_0','s2_old'),('v1_1','s2')]])
    status('stage2_main_running',preflight_pass=len(main));engine.run(main)
    rows=[];accepted=[];sources={}
    for c in cases():
        for rid in ids(c):
            pf=review['candidates'][rid];f=OUT/'stage2'/rid
            v=read(f/'parsed.json') if (f/'parsed.json').exists() else {}
            estimate=valid(f) and v.get('status')=='estimated' and not isinstance(v.get('reconstructed_overall'),bool) and v.get('reconstructed_overall') in [1,2,3,4,5]
            match=bool(estimate and Decimal(str(v['reconstructed_overall']))==Decimal(str(c['target']['Overall'])))
            accept=bool(pf['pass'] and match);reasons=[]
            if not pf['pass']:reasons+=pf['rejection_reasons']
            elif not valid(f):reasons.append('stage2_invalid_or_not_executed')
            elif not estimate:reasons.append('stage2_'+v.get('status','no_status'))
            elif not match:reasons.append('overall_mismatch')
            row=dict(candidate_id=rid,rater_id=c['rater_id'],essay_id=c['target']['essay_id'],observed_overall=c['target']['Overall'],stage1_strict_json=read(OUT/'stage1'/rid/'result.json')['json_valid'],preflight_pass=pf['pass'],stage2_executed=(f/'raw.txt').exists(),stage2_strict_json=(read(f/'result.json')['json_valid'] if (f/'result.json').exists() else False),valid_estimate=estimate,reconstructed_overall=v.get('reconstructed_overall'),match=match,accepted=accept,rejection_reasons=';'.join(reasons))
            rows.append(row);save(OUT/'external_decisions'/f'{rid}.json',row)
            if accept:
                accepted.append(dict(record_id=rid,**read(OUT/'stage1'/rid/'parsed.json')))
                for e in [c['target']]+c['history']:sources[e['essay_id']]=e
    csvsave(OUT/'candidate_results.csv',rows,list(rows[0]))
    essays=[dict(rater_id=c['rater_id'],essay_id=c['target']['essay_id'],observed_overall=c['target']['Overall'],candidates=2,preflight_pass=sum(r['preflight_pass'] for r in rows if r['essay_id']==c['target']['essay_id']),accepted=sum(r['accepted'] for r in rows if r['essay_id']==c['target']['essay_id'])) for c in cases()]
    csvsave(OUT/'essay_results.csv',essays,list(essays[0]))
    unique={r['target_essay_id'] for r in accepted}
    summary=dict(generated_candidates=6,preflight_pass=sum(r['preflight_pass'] for r in rows),stage2_executed=sum(r['stage2_executed'] for r in rows),stage2_strict_json=sum(r['stage2_strict_json'] for r in rows),valid_estimates=sum(r['valid_estimate'] for r in rows),matches=sum(r['match'] for r in rows),accepted_candidates=len(accepted),distinct_accepted_essays=len(unique))
    save(OUT/'summary.json',summary)
    if len(unique)<2:save(OUT/'stage3/skip.json',dict(reason='Fewer than two distinct accepted targets',accepted_records=len(accepted),distinct_targets=len(unique)))
    else:
        payload=dict(rater_id='rater_7',rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),accepted_records=accepted,source_essays=list(sources.values()),selection_metadata=dict(**summary,scope='First Stage3 evaluation; three previously used development targets all Overall=3. Candidate alternatives are not independent essays.',excluded_candidates=[r for r in rows if not r['accepted']]))
        status('stage3_running');engine.run([job(OUT/'stage3/rater_7','s3',3,'rater_7',payload)])
    finalize();status('generation_completed_pending_content_review',summary=summary)
def finalize():
    m=read(OUT/'run_manifest.json')
    for k,v in m['prompts'].items():v['sha256_after']=sha(PROMPTS[k]);assert v['sha256_after']==v['sha256_before']
    m['baseline_unchanged']=m['baseline_files_sha256']==freeze_files();assert m['baseline_unchanged']
    m['last_checked_at']=now();save(OUT/'run_manifest.json',m)
def main():
    a=argparse.ArgumentParser();a.add_argument('--phase',choices=['prepare','worker'],default='prepare');args=a.parse_args();prepare()
    if args.phase=='worker':
        try:
            engine=Engine();stage1(engine)
            while not (OUT/'preflight_review.json').exists():time.sleep(1)
            after_review(engine)
        except BaseException:
            status('execution_failed',traceback=traceback.format_exc());raise
        finally:finalize()
if __name__=='__main__':main()
