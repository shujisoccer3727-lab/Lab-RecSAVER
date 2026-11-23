"""Fixed three-request v1.6 prompt baseline (v1.5 contract): text-only 3A, isolated score audit, structured 3B."""
from pathlib import Path
import sys,json,re,subprocess,shutil,importlib.util,traceback,hashlib
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_v1_5_baseline_20261122';COMMIT='bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac'
sp=importlib.util.spec_from_file_location('engine11',ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py');p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
read,save,sha=p.read,p.save,p.sha
PROMPTS={k:ROOT/'prompts/en'/n for k,n in [('a','recsaver_03a_case_evidence_review_v1_6.txt'),('b','recsaver_03b_integrated_feedback_v1_6.txt')]}
TARGETS=['1868:1','4902:1'];SEED=925847335

def array(x,k):return x.get(k,[]) if isinstance(x,dict) and isinstance(x.get(k,[]),list) else []
def need(x,fields,path):
    if not isinstance(x,dict):return [path+': expected object']
    errors=[path+'.'+k+': missing/type' for k,t in fields.items() if k not in x or not isinstance(x[k],t)]
    errors += [path+'.'+k+': unexpected field' for k in set(x)-set(fields)]
    return errors
def obs_schema(o,path):return need(o,dict(observation_id=str,dimension=str,evidence_span_ids=list,feature=str,scoring_relevance=str,limitation=str,next_check=str),path)
def a_schema(v):
    errors=need(v,dict(schema_version=str,target_essay_id=str,observations=list,insufficient_evidence=list),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.5':errors.append('schema_version !=1.5')
    if len(array(v,'observations'))>2:errors.append('more than two observations')
    for i,o in enumerate(array(v,'observations')):errors+=obs_schema(o,f'$.observations[{i}]')
    return errors
def b_schema(v):
    errors=need(v,dict(schema_version=str,rater_id=str,pattern_status=str,pattern=(dict,type(None)),pattern_limit=str,representative_observation_key=(str,type(None)),quote_indices=list,textual_finding=(str,type(None)),evidence_limit=(str,type(None)),rubric_review=dict,next_check=dict),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.5':errors.append('schema_version !=1.5')
    if v.get('pattern_status') not in ['supported','insufficient_evidence']:errors.append('invalid pattern_status')
    errors+=need(v.get('rubric_review'),dict(observed_band_ref_id=(str,type(None)),comparison_band_ref_id=(str,type(None)),band_assessment=str),'$.rubric_review')
    if isinstance(v.get('rubric_review'),dict) and v['rubric_review'].get('band_assessment') not in ['indeterminate','possible_tension']:errors.append('invalid band assessment')
    errors+=need(v.get('next_check'),dict(inspect=str,distinguish=str,reconsider_if=(str,type(None))),'$.next_check')
    if isinstance(v.get('pattern'),dict):
        errors+=need(v['pattern'],dict(statement=str,support=list),'$.pattern')
        for s in array(v['pattern'],'support'):errors+=need(s,dict(observation_key=str,supports_how=str),'$.pattern.support')
    return errors
def structural(stage,v,payload):return a_schema(v) if 'target_text' in payload else b_schema(v)

def gate_a(v,payload):
    top=need(v,dict(schema_version=str,target_essay_id=str,observations=list,insufficient_evidence=list),'$')
    if not isinstance(v,dict) or v.get('schema_version')!='1.5' or v.get('target_essay_id')!=payload['target_essay_id']:top.append('version/target mismatch')
    if len(array(v,'observations'))>2:top.append('more than two observations')
    catalog={s['span_id']:s for s in payload['evidence_spans']};counts={};passed=[];checks=[]
    for o in array(v,'observations'):
        oid=o.get('observation_id') if isinstance(o,dict) else None
        if isinstance(oid,str):counts[oid]=counts.get(oid,0)+1
    for i,o in enumerate(array(v,'observations')):
        reasons=top+obs_schema(o,f'observations[{i}]');selected=[]
        if isinstance(o,dict):
            oid=o.get('observation_id');ids=array(o,'evidence_span_ids')
            if not isinstance(oid,str) or not oid or counts.get(oid,0)!=1:reasons.append('observation ID missing/duplicated')
            if o.get('dimension') not in payload['dimension_names']:reasons.append('unknown dimension')
            if not ids:reasons.append('no selected spans')
            if any(not isinstance(s,str) or s not in catalog for s in ids):reasons.append('unknown/other-target span ID')
            if len(set(s for s in ids if isinstance(s,str)))!=len(ids):reasons.append('duplicate/invalid span ID')
            selected=[catalog[s] for s in ids if isinstance(s,str) and s in catalog]
        quotes=[payload['target_text'][s['start']:s['end']] for s in selected]
        if any(q!=s['text'] for q,s in zip(quotes,selected)):reasons.append('catalog/source mismatch')
        checks.append(dict(index=i,pass_=not reasons,reasons=reasons,source_spans=selected,reconstructed_quotes=quotes,semantic_support_not_certified=True))
        if not reasons:passed.append(dict(o,quotes=quotes))
    return dict(top_errors=top,checks=checks,passed_observations=passed)

def sentence(text):
    text=text.strip()
    return text if re.search(r'[.!?]["”\x27]?$',text) else text+'.'
def quoted_sentence(prefix,quote):
    # Inspect terminal punctuation without changing even one character inside quote.
    return prefix+'“'+quote+'”'+('' if re.search(r'[.!?]["”\x27]?\s*$',quote) else '.')
def review_and_render(v,payload):
    errors=b_schema(v);checks=[]
    def ck(kind,ok,**details):checks.append(dict(kind=kind,pass_=bool(ok),**details))
    if errors:return dict(pass_=False,schema_errors=errors,checks=[],feedback_paragraph=None)
    obs={o['observation_key']:o for o in payload['verified_observations']};refs={e['rubric_ref_id']:e for e in payload['rubric_entries']};key=v['representative_observation_key'];rep=obs.get(key);indices=v['quote_indices'];rr=v['rubric_review'];nc=v['next_check']
    ck('rater',v['rater_id']==payload['rater_id']);ck('representative_key',key is None or key in obs)
    valid_indices=all(isinstance(i,int) and not isinstance(i,bool) and rep is not None and 0<=i<len(rep['quotes']) for i in indices)
    ck('indices',valid_indices and len(set(i for i in indices if isinstance(i,int)))==len(indices) and (bool(indices) if key is not None else indices==[]))
    ck('representative_fields',all(isinstance(v[k],str) and bool(v[k]) for k in ['textual_finding','evidence_limit']) if key is not None else v['textual_finding'] is None and v['evidence_limit'] is None)
    if v['pattern_status']=='insufficient_evidence':ck('abstention',v['pattern'] is None and bool(v['pattern_limit']))
    else:
        support=array(v.get('pattern'),'support');keys=[s.get('observation_key') for s in support];targets={obs[k]['target_essay_id'] for k in keys if isinstance(k,str) and k in obs}
        ck('supported_pattern_keys',all(isinstance(k,str) and k in obs for k in keys) and key in keys)
        ck('independent_support',len(targets)>=2 and targets<=set(payload['accepted_target_ids']))
    observed=refs.get(rr['observed_band_ref_id']);comparison=refs.get(rr['comparison_band_ref_id']);direction='none'
    expected=next((r['rubric_ref_id'] for r in refs.values() if rep and r['dimension']==rep['dimension'] and r['score_band']==rep['observed_score']),None)
    ck('observed_reference',rr['observed_band_ref_id']==expected)
    ck('comparison_exists',rr['comparison_band_ref_id'] is None or comparison is not None)
    if comparison and rep:
        bands=sorted({e['score_band'] for e in refs.values() if e['dimension']==rep['dimension']});score=rep['observed_score'];neighbors=[]
        if score is not None:
            if any(b<score for b in bands):neighbors.append(max(b for b in bands if b<score))
            if any(b>score for b in bands):neighbors.append(min(b for b in bands if b>score))
        ck('same_dimension_adjacent_band',comparison['dimension']==rep['dimension'] and comparison['score_band'] in neighbors)
        direction='higher' if score is not None and comparison['score_band']>score else 'lower'
        ck('comparison_condition',isinstance(nc['reconsider_if'],str) and bool(nc['reconsider_if']))
    elif rr['comparison_band_ref_id'] is None:ck('no_comparison_condition',nc['reconsider_if'] is None)
    if key is None:ck('no_representative_refs',observed is None and comparison is None and rr['band_assessment']=='indeterminate')
    ok=all(c['pass_'] for c in checks)
    result=dict(pass_=ok,schema_errors=[],checks=checks,comparison_direction=direction,feedback_paragraph=None,selected_evidence=[],semantic_support_not_certified=True)
    if not ok:return result
    parts=[sentence('A scoring pattern cannot be established from these cases. '+v['pattern_limit']) if v['pattern_status']=='insufficient_evidence' else sentence(v['pattern']['statement'])]
    if rep:
        for i in indices:
            q=rep['quotes'][i];parts.append(quoted_sentence(f'In essay {rep["target_essay_id"]}, the relevant excerpt is ',q));result['selected_evidence'].append(dict(observation_key=key,quote_index=i,target_essay_id=rep['target_essay_id'],exact_quote=q))
        parts.append(sentence(v['textual_finding']))
        score=rep['observed_score'];parts.append(f'The recorded {rep["dimension"]} score is {score}.' if score is not None else f'The recorded {rep["dimension"]} score is unavailable.')
        if observed:parts.append(quoted_sentence(f'The official descriptor for {observed["rubric_ref_id"]} is ',observed['descriptor']))
        parts.append('This evidence alone does not establish whether that band is appropriate.' if rr['band_assessment']=='indeterminate' else 'This evidence suggests a possible tension to review; it does not establish a corrected score.')
        parts.append(sentence(v['evidence_limit']))
    parts += [sentence('Next inspect: '+nc['inspect']),sentence('Check: '+nc['distinguish'])]
    if comparison:
        parts.append(quoted_sentence(f'The {direction} comparison band {comparison["rubric_ref_id"]} is described as ',comparison['descriptor']))
        parts.append(sentence(f'For review toward that {direction} band, reconsider if '+nc['reconsider_if']))
    result['feedback_paragraph']=' '.join(parts);return result

def score_audit():
    fixed=read(OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']};rows=[]
    def walk(x,path='$'):
        if isinstance(x,str):yield path,x
        elif isinstance(x,dict):
            for k,y in x.items():yield from walk(y,path+'.'+k)
        elif isinstance(x,list):
            for i,y in enumerate(x):yield from walk(y,path+f'[{i}]')
    for record in fixed['accepted_records']:
        src=sources[record['target_essay_id']]
        for path,text in walk(record):
            # Only an explicit collective claim identifies all dimensions; no nearby-Trait inference.
            matches=list(re.finditer(r'(?:observed\s+)?scores?\s+of\s+([1-5](?:\.0)?)\s+for\s+both\s+Overall\s+and\s+(?:all\s+)?Traits',text,re.I))
            for match in matches:
                claimed=float(match.group(1));scores=dict(Overall=src.get('Overall'),**src.get('Traits',{}));conflicts=[dict(dimension=d,claimed_score=claimed,observed_score=s) for d,s in scores.items() if s is not None and s!=claimed]
                rows.append(dict(record_id=record['record_id'],json_path=path,exact_candidate_text=text,classification='explicit_collective_score_claim',score_conflicts=conflicts))
            if not matches and re.search(r'\bscore of [1-5]\b',text,re.I):rows.append(dict(record_id=record['record_id'],json_path=path,exact_candidate_text=text,classification='unattributed_score_reference_not_assigned_to_traits',score_conflicts=[]))
    save(OUT/'isolated_candidate_score_audit.json',dict(method='Deterministic explicit collective-claim regression checks, not a comprehensive semantic auditor.',sent_to_3B=False,rows=rows))

def pre_gpu_tests():
    old=read(BASE/'handoff/input_3b.json');key='4902:1::O1';v=dict(schema_version='1.5',rater_id='rater_7',pattern_status='insufficient_evidence',pattern=None,pattern_limit='No comparable evidence of feature weighting.',representative_observation_key=key,quote_indices=[1],textual_finding='The passage states a reason for agreement.',evidence_limit='Only this local relation is shown.',rubric_review=dict(observed_band_ref_id='Cohesion:2',comparison_band_ref_id=None,band_assessment='indeterminate'),next_check=dict(inspect='A following explanation of the same claim.',distinguish='Whether the relation is stated explicitly.',reconsider_if=None))
    results=[]
    def test(name,value,payload,expected):
        got=review_and_render(value,payload);assert got['pass_']==expected,(name,got);results.append(dict(name=name,validation_fixture=True,input=value,result=got,expected_pass=expected,test_passed=True));return got
    got=test('saved quote, synthetic v1.5 decisions',v,old,True);q=old['verified_observations'][1]['quotes'][1];assert got['selected_evidence'][0]['exact_quote']==q and '”.' not in got['feedback_paragraph']
    w=json.loads(json.dumps(v));w['quote_indices']=[0];got=test('4902 original opening space',w,old,True);assert '" To be yourself' in got['selected_evidence'][0]['exact_quote']
    for ix in [[-1],[999],[True],[0.5],[],[0,0]]:
        w=json.loads(json.dumps(v));w['quote_indices']=ix;test('invalid indices '+str(ix),w,old,False)
    w=json.loads(json.dumps(v));w['representative_observation_key']='unknown';test('unknown key',w,old,False)
    w=json.loads(json.dumps(v));w.update(representative_observation_key=None,quote_indices=[],textual_finding=None,evidence_limit=None);w['rubric_review']['observed_band_ref_id']=None;test('no representative',w,old,True)
    w=json.loads(json.dumps(v));w['rubric_review'].update(comparison_band_ref_id='Cohesion:4');w['next_check']['reconsider_if']='Devices connect ideas appropriately.';test('nonadjacent band',w,old,False)
    save(OUT/'pre_gpu_tests.json',dict(timestamp=p.now(),before_gpu=True,actual_model_calls=0,synthetic_decision_fields_not_old_model_success=True,total=len(results),passed=len(results),cases=results));print('Pre-GPU tests passed:',len(results),flush=True)

def freeze():return {str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run_manifest.json').exists():return
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
    shutil.copyfile(BASE/'fixed_input.json',OUT/'fixed_input.json');fixed=read(OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']}
    for eid in TARGETS:
        n=eid.replace(':','_');(OUT/'evidence_spans').mkdir(exist_ok=True);shutil.copyfile(BASE/'evidence_spans'/f'{n}.json',OUT/'evidence_spans'/f'{n}.json');e=sources[eid]
        save(OUT/'prepared_3a'/n/'input.json',dict(target_essay_id=eid,target_text=e['text'],evidence_spans=read(OUT/'evidence_spans'/f'{n}.json'),dimension_names=fixed['rubric']['structure']['holistic']+fixed['rubric']['structure']['analytic']))
    old=read(BASE/'run_manifest.json')
    for f in PROMPTS.values():assert f.read_bytes().decode('utf-8').count('{{INPUT_JSON}}')==1
    save(OUT/'run_manifest.json',dict(created_at=p.now(),comparison_commit=COMMIT,code_commit=COMMIT,baseline_path=str(BASE),baseline_files_sha256=freeze(),fixed_input_sha256=sha(OUT/'fixed_input.json'),prompts={k:dict(path=str(f),windows_path=str(f).replace('/mnt/c/','C:/'),sha256=sha(f),same_name_locations=[str(x) for x in ROOT.rglob(f.name)]) for k,f in PROMPTS.items()},span_catalogs={eid:dict(source=str(BASE/'evidence_spans'/f'{eid.replace(":","_")}.json'),sha256=sha(OUT/'evidence_spans'/f'{eid.replace(":","_")}.json')) for eid in TARGETS},model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],sampling=old['sampling'],seed=SEED,system_message=old['system_message'],chat=old['chat'],code_sha256_before=sha(__file__),planned_requests=dict(stage3a=2,stage3b=1,optional_fixed_3b=0),differences=['Only the specified local-evidence/passage-role English additions in the two v1.6 canonical prompts; output contract remains 1.5.', 'Output path and comparison source updated to v1.5 commit bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac; runner, handoff and renderer reused.', 'No position metadata added to 3B; no candidate-audit prose supplied; no self-verification or SLM revision stage.']))
    score_audit()
def handoff():
    fixed=read(OUT/'fixed_input.json');sources={s['essay_id']:s for s in fixed['source_essays']};observations=[];entries={};provenance=[];limits=['Two fixed development targets, both Overall=3; mechanical provenance does not establish scoring causation or band validity.'];summary=[]
    for eid in TARGETS:
        f=OUT/'stage3a'/eid.replace(':','_');payload=read(OUT/'prepared_3a'/eid.replace(':','_')/'input.json');gate=gate_a(read(f/'parsed.json'),payload) if (f/'parsed.json').exists() else dict(top_errors=['strict JSON unavailable'],checks=[],passed_observations=[]);save(f/'mechanical_checks.json',gate)
        if not gate['passed_observations']:limits.append(eid+': no source-checked observations.')
        for check in gate['checks']:
            if not check['pass_']:save(OUT/'exclusions'/f'{eid.replace(":","_")}__{check["index"]}.json',check)
        for o in gate['passed_observations']:
            d=o['dimension'];src=sources[eid];score=src.get('Overall') if d=='Overall' else src.get('Traits',{}).get(d);key=eid+'::'+o['observation_id'];observations.append(dict(o,observation_key=key,target_essay_id=eid,observed_score=score))
            if score is None:limits.append(key+': observed score unavailable.');continue
            bands=sorted(float(b) for b,ds in fixed['rubric']['scores'].items() if d in ds);chosen=[float(score)]+([max(b for b in bands if b<score)] if any(b<score for b in bands) else [])+([min(b for b in bands if b>score)] if any(b>score for b in bands) else [])
            for band in chosen:
                bs=str(int(band)) if band.is_integer() else str(band);descriptor=fixed['rubric']['scores'].get(bs,{}).get(d)
                if descriptor is None:continue
                ref=d+':'+bs;entries[ref]=dict(rubric_ref_id=ref,dimension=d,score_band=int(band) if band.is_integer() else band,descriptor=descriptor);provenance.append(dict(observation_key=key,source_file=str(BASE/'fixed_input.json'),source_sha256=sha(BASE/'fixed_input.json'),json_path=f'$.rubric.scores["{bs}"]["{d}"]',**entries[ref]))
        summary.append(dict(target_essay_id=eid,generated=len(gate['checks']),passed=len(gate['passed_observations'])))
    inp=dict(rater_id=fixed['rater_id'],accepted_target_ids=TARGETS,verified_observations=observations,rubric_entries=list(entries.values()),evidence_limitations=limits)
    save(OUT/'handoff/input_3b.json',inp);save(OUT/'handoff/rubric_provenance.json',provenance);save(OUT/'handoff/summary.json',summary);return inp
def finalize():
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=freeze()==m['baseline_files_sha256'];m['prompts_unchanged']=all(sha(PROMPTS[k])==v['sha256'] for k,v in m['prompts'].items());assert m['baseline_unchanged'] and m['prompts_unchanged'];m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')};m['actual_requests']=sum(1 for f in OUT.glob('stage3*/*/raw.txt'));m['last_checked_at']=p.now();save(OUT/'run_manifest.json',m)
def worker():
    prepare();assert read(OUT/'pre_gpu_tests.json')['before_gpu'];p.OUT=OUT;p.PROMPTS.update(PROMPTS);p.seed=lambda stage,rid:SEED;p.legacy.structural=structural;engine=p.Engine()
    engine.run([p.job(OUT/'stage3a'/eid.replace(':','_'),'a',3,eid,read(OUT/'prepared_3a'/eid.replace(':','_')/'input.json')) for eid in TARGETS]);inp=handoff();f=OUT/'stage3b/rater_7';engine.run([p.job(f,'b',3,'rater_7',inp)])
    if (f/'parsed.json').exists():
        result=review_and_render(read(f/'parsed.json'),inp);save(f/'render_result.json',result)
        if result['pass_']:(f/'feedback_paragraph.txt').write_text(result['feedback_paragraph'],encoding='utf-8')
    finalize()
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','pre_gpu_tests','worker','launch','finalize']);args=ap.parse_args()
    if args.phase=='launch':
        prepare();pre_gpu_tests();assert not (OUT/'process.json').exists()
        with (OUT/'execution.log').open('ab',buffering=0) as log:proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));raise
