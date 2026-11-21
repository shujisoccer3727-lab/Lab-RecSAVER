"""v1.2 target-value masking; replay diagnostics and new candidates kept separate."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,os,subprocess,sys,time,traceback
from decimal import Decimal
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];BASE=ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120'
sp=importlib.util.spec_from_file_location('prior',BASE/'code/run.py');p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
from masking import mask_analysis
read,save,sha,now,csvsave=p.read,p.save,p.sha,p.now,p.csvsave
PROMPTS={'s1':ROOT/'prompts/en/recsaver_01_reference_rationale_v1_2.txt','s2':ROOT/'prompts/en/recsaver_02_overall_reconstruction_v1_1.txt','s3':ROOT/'prompts/en/recsaver_03_integrated_feedback_v1_0.txt'}
p.OUT=OUT;p.PROMPTS=PROMPTS
def rel(x):return str(x.relative_to(ROOT)).replace('\\','/')
def frozen():return {rel(x):sha(x) for x in BASE.rglob('*') if x.is_file() and '__pycache__' not in x.parts}
def cases():return read(OUT/'case_manifest.json')['development']
def status(s,**kw):save(OUT/'status.json',dict(time=now(),status=s,**kw));print(s,flush=True)
def prepare():
    if (OUT/'run_manifest.json').exists():
        m=read(OUT/'run_manifest.json');assert m['code_sha256']==sha(__file__);assert m['masking_sha256']==sha(OUT/'code/masking.py');return
    OUT.mkdir(parents=True,exist_ok=True)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert commit=='c52617a669149b895c412165591d71257e4c0e8c'
    old=read(BASE/'run_manifest.json')
    for name in ['case_manifest.json','rubric.json','score_specification.json']:save(OUT/name,read(BASE/name))
    m=dict(created_at=now(),comparison_commit=commit,baseline=str(BASE),baseline_files_sha256=frozen(),prompts={k:dict(path=str(v),sha256_before=sha(v),same_name_locations=[rel(x) for x in (ROOT/'prompts').rglob(v.name)]) for k,v in PROMPTS.items() if v.exists()},missing_prompts=[str(v) for v in PROMPTS.values() if not v.exists()],code_sha256=sha(__file__),masking_sha256=sha(OUT/'code/masking.py'),model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],seed=old['seed'],seed_policy=old['seed_policy'],system_message=old['system_message'],chat=old['chat'],retries=old['retries'],changes=['Stage1 v1.2 canonical prompt; Stage2 v1.1 and Stage3 v1.0 unchanged.','Value-only masking of a deep-copied score_free_analysis. No clause deletion. Audit and original scores withheld from Stage2.','History-ID validation, score equivalence/calculation/named-band/ambiguous-role quarantine before reconstruction.','Replay of saved v1.1 candidates and A/B/C diagnostics separated from new six-candidate main run.'],prompt_conflict='Stage1 v1.2 OUTPUT SEPARATION allows explicit scores for later masking, but final paragraph still says to move explicit target band comparisons to observed_score_alignment. Preserved without alteration; cannot isolate this instruction interaction.',acceptance='Strict JSON/schema/ID; mask/input check pass; Stage2 estimated and valid Overall exactly equal to observed; content quality separately inspected.',stage3='At least two distinct accepted targets; use full UNMASKED Stage1 records and observed source scores.',notes='Single rater, three development targets all Overall=3. No independent human evaluation, general performance claim, repair prompts, guided decoding or new model download.')
    save(OUT/'run_manifest.json',m);status('prepared')
def apply_record(folder,record,inp):
    folder.mkdir(parents=True,exist_ok=True);before=copy.deepcopy(record['score_free_analysis'])
    save(folder/'original_record.json',record);save(folder/'original_analysis.json',before)
    result=mask_analysis(before,inp['history'],inp['target'])
    assert before==record['score_free_analysis']
    save(folder/'masked_analysis.json',result['masked_analysis']);save(folder/'mask_audit.json',result['audit'])
    return result
def replay():
    for c in cases():
        for rid in p.ids(c):apply_record(OUT/'saved_v1_1_masks'/rid,read(BASE/'stage1'/rid/'parsed.json'),read(BASE/'stage1'/rid/'input.json'))
    for test in ['A','B','C']:
        inp=read(BASE/'stage2_diagnostics'/test/'v1_1/input.json')
        c=next(c for c in cases() if c['target']['essay_id']==inp['target']['essay_id'])
        f=OUT/'diagnostic_masks'/test
        result=apply_record(f,dict(score_free_analysis=inp['reference_analysis']),dict(history=inp['history'],target=c['target']))
        masked=copy.deepcopy(inp);masked['reference_analysis']=result['masked_analysis'];save(f/'input.json',masked)
    status('saved_replay_masked')
def finalize():
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=m['baseline_files_sha256']==frozen();assert m['baseline_unchanged']
    for k,x in m['prompts'].items():x['sha256_after']=sha(PROMPTS[k]);assert x['sha256_before']==x['sha256_after']
    m['last_checked_at']=now();save(OUT/'run_manifest.json',m)
def stage2payload(c,masked):return dict(rater_id=c['rater_id'],rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),history=c['history'],target={k:c['target'][k] for k in ['essay_id','text']},reference_analysis=masked)
def worker():
    engine=p.Engine()
    status('waiting_for_replay_review')
    while not (OUT/'replay_review.json').exists():time.sleep(1)
    review=read(OUT/'replay_review.json');jobs=[]
    for test,verdict in review['diagnostics'].items():
        if verdict['pass']:
            inp=read(OUT/'diagnostic_masks'/test/'input.json');rid='1514_1__K1' if test in ['A','C'] else '4902_1__K2'
            jobs.append(p.job(OUT/'stage2_diagnostics'/test/'masked','s2',2,rid,inp))
    status('masked_diagnostics_running');engine.run(jobs)
    if not PROMPTS['s1'].exists():status('generation_unavailable_missing_canonical_stage1');finalize();return
    status('stage1_v1_2_running')
    engine.run([p.job(OUT/'stage1'/rid,'s1',1,rid,read(BASE/'stage1'/rid/'input.json')) for c in cases() for rid in p.ids(c)])
    for c in cases():
        for rid in p.ids(c):
            f=OUT/'stage1'/rid
            if p.valid(f):apply_record(OUT/'masks'/rid,read(f/'parsed.json'),read(f/'input.json'))
    status('waiting_for_main_mask_review')
    while not (OUT/'main_mask_review.json').exists():time.sleep(1)
    verdicts=read(OUT/'main_mask_review.json')['candidates'];jobs=[]
    for c in cases():
        for rid in p.ids(c):
            v=verdicts[rid]
            if v['pass']:
                assert p.valid(OUT/'stage1'/rid) and read(OUT/'masks'/rid/'mask_audit.json')['automatic_pass']
                payload=stage2payload(c,read(OUT/'masks'/rid/'masked_analysis.json'))
                assert set(payload['target'])=={'essay_id','text'} and set(payload)=={'rater_id','rubric','score_specification','history','target','reference_analysis'}
                jobs.append(p.job(OUT/'stage2'/rid,'s2',2,rid,payload))
            else:save(OUT/'preflight_rejections'/f'{rid}.json',v)
    status('main_stage2_running',passed=len(jobs));engine.run(jobs)
    rows=[];accepted=[];sources={}
    for c in cases():
        for rid in p.ids(c):
            f=OUT/'stage2'/rid;v=read(f/'parsed.json') if (f/'parsed.json').exists() else {}
            valid=p.valid(f) and v.get('status')=='estimated' and not isinstance(v.get('reconstructed_overall'),bool) and v.get('reconstructed_overall') in [1,2,3,4,5]
            match=bool(valid and Decimal(str(v['reconstructed_overall']))==Decimal(str(c['target']['Overall'])))
            verdict=verdicts[rid];accept=bool(verdict['pass'] and match)
            audit=read(OUT/'masks'/rid/'mask_audit.json') if (OUT/'masks'/rid/'mask_audit.json').exists() else {}
            reasons=verdict['reasons'] if not verdict['pass'] else [] if accept else ['stage2_invalid_or_abstained' if not valid else 'overall_mismatch']
            row=dict(candidate_id=rid,essay_id=c['target']['essay_id'],rater_id=c['rater_id'],observed_overall=c['target']['Overall'],stage1_valid=p.valid(OUT/'stage1'/rid),mask_applied=bool(audit.get('changes')),mask_values=audit.get('value_replacements',0),mask_changed_fields=audit.get('changed_fields',0),mask_input_pass=verdict['pass'],stage2_executed=(f/'raw.txt').exists(),stage2_strict_json=read(f/'result.json')['json_valid'] if (f/'result.json').exists() else False,valid_estimate=valid,reconstructed_overall=v.get('reconstructed_overall'),match=match,accepted=accept,reasons=';'.join(reasons))
            rows.append(row);save(OUT/'external_decisions'/f'{rid}.json',row)
            if accept:
                accepted.append(dict(record_id=rid,**read(OUT/'stage1'/rid/'parsed.json')))
                for e in [c['target']]+c['history']:sources[e['essay_id']]=e
    csvsave(OUT/'candidate_results.csv',rows,list(rows[0]));essays=[]
    for c in cases():
        rr=[v for v in rows if v['essay_id']==c['target']['essay_id']]
        essays.append(dict(essay_id=c['target']['essay_id'],candidate_count=2,input_pass=sum(v['mask_input_pass'] for v in rr),accepted=sum(v['accepted'] for v in rr)))
    csvsave(OUT/'essay_results.csv',essays,list(essays[0]));unique={v['target_essay_id'] for v in accepted}
    summary=dict(generated_candidates=sum((OUT/'stage1'/v['candidate_id']/'raw.txt').exists() for v in rows),mask_applied_candidates=sum(v['mask_applied'] for v in rows),mask_value_count=sum(v['mask_values'] for v in rows),mask_changed_fields=sum(v['mask_changed_fields'] for v in rows),input_pass=sum(v['mask_input_pass'] for v in rows),stage2_executed=sum(v['stage2_executed'] for v in rows),stage2_strict_json=sum(v['stage2_strict_json'] for v in rows),valid_estimates=sum(v['valid_estimate'] for v in rows),matches=sum(v['match'] for v in rows),accepted_records=len(accepted),distinct_accepted_targets=len(unique))
    save(OUT/'summary.json',summary)
    if len(unique)<2:save(OUT/'stage3/skip.json',dict(reason='Fewer than two distinct accepted targets',accepted_records=len(accepted),distinct_targets=len(unique)))
    else:
        payload=dict(rater_id='rater_7',rubric=read(OUT/'rubric.json'),score_specification=read(OUT/'score_specification.json'),accepted_records=accepted,source_essays=list(sources.values()),selection_metadata=dict(**summary,scope='First integration evaluation using original unmasked rationales after masked reconstruction; three previously used targets, all Overall=3.'))
        status('stage3_running');engine.run([p.job(OUT/'stage3/rater_7','s3',3,'rater_7',payload)])
    finalize();status('generation_completed_pending_review',summary=summary)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','worker'],default='prepare');a=ap.parse_args();prepare()
    if a.phase=='prepare':replay();finalize()
    else:
        try:worker()
        except BaseException:status('failed',traceback=traceback.format_exc());raise
        finally:finalize()
if __name__=='__main__':main()
