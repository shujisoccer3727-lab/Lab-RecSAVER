"""A pre-GPU assembly fixtures; B fixed 3B; C 3A x2 -> gated handoff -> 3B."""
from pathlib import Path
import sys,json,importlib.util,subprocess,shutil,traceback
from copy import deepcopy
sys.dont_write_bytecode=True
from assembly import assemble
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1]
BASE=ROOT/'outputs/recsaver_stage3_v1_3_validation_20261121';COMMIT='c55e45c4da14cef2475e53d72e5f5cd5a9314b5a'
sp=importlib.util.spec_from_file_location('pipeline13',BASE/'code/run.py');prev=importlib.util.module_from_spec(sp);sp.loader.exec_module(prev)
GATE13=prev.gate_a;A_SCHEMA13=prev.a_schema;B_SCHEMA13=prev.b_schema
p=prev.p;read,save,sha=prev.read,prev.save,prev.sha
PROMPTS={k:ROOT/'prompts/en'/n for k,n in [('a','recsaver_03a_case_evidence_review_v1_4.txt'),('b','recsaver_03b_integrated_feedback_v1_4.txt')]}
TARGETS=['1868:1','4902:1'];SEED=925847335

def project_b(v,paragraph=None):
    c=deepcopy(v);c['schema_version']='1.3';c.pop('representative_quote_index',None);c['rubric_comparison'].pop('comparison_direction',None)
    template=c.pop('feedback_paragraph_template');c['feedback_paragraph']=template if paragraph is None else paragraph
    return c
def a_schema(v):
    if not isinstance(v,dict):return A_SCHEMA13(v)
    c=deepcopy(v);c['schema_version']='1.3';errors=A_SCHEMA13(c)
    if v.get('schema_version')!='1.4':errors.append('schema_version !=1.4')
    return errors
def b_schema(v):
    expected=dict(schema_version=str,rater_id=str,pattern_status=str,patterns=list,case_specific_observation_keys=list,representative_observation_key=(str,type(None)),representative_quote_index=(int,type(None)),rubric_comparison=dict,next_scoring_check=dict,insufficient_evidence=list,feedback_paragraph_template=str)
    errors=prev.base.need(v,expected,'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.4':errors.append('schema_version !=1.4')
    if isinstance(v.get('representative_quote_index'),bool):errors.append('bool is not a quote index')
    rc=v.get('rubric_comparison',{})
    errors+=prev.base.need(rc,dict(observed_band_ref_id=(str,type(None)),comparison_band_ref_id=(str,type(None)),comparison_direction=str,relationship=str,explanation=str),'$.rubric_comparison')
    if isinstance(rc,dict) and rc.get('comparison_direction') not in ['higher','lower','none']:errors.append('invalid comparison_direction')
    if not errors:errors+=B_SCHEMA13(project_b(v))
    return errors
def structural(stage,v,payload):return a_schema(v) if 'evidence_spans' in payload else b_schema(v)
def gate_a(v,payload):
    c=deepcopy(v)
    if isinstance(c,dict):c['schema_version']='1.3'
    result=GATE13(c,payload)
    if not isinstance(v,dict) or v.get('schema_version')!='1.4':
        result['top_errors'].append('schema_version !=1.4');result['passed_observations']=[];result['passed_issues']=[]
        for k in ['observation_checks','issue_checks']:
            for x in result[k]:x['pass_']=False;x['reasons'].append('schema_version !=1.4')
    return result

def assembly_tests():
    inp=read(BASE/'stage3b_pipeline/rater_7/input.json');old=read(BASE/'stage3b_pipeline/rater_7/parsed.json');key=old['representative_observation_key'];cases=[]
    def test(name,value,expect):
        got=assemble(value,inp);assert got['pass_']==expect,(name,got)
        cases.append(dict(name=name,validation_fixture=True,derived_from_saved_v1_3=True,added_fields_not_generated_by_old_model=['representative_quote_index','feedback_paragraph_template placeholder'],input=value,assembly=got,expected_pass=expect,test_passed=True))
        return got
    value=dict(representative_observation_key=key,representative_quote_index=0,feedback_paragraph_template='Please review the cited feature. [REPRESENTATIVE_EVIDENCE] Check other passages.')
    got=test('saved representative, synthetic index/placeholder',value,True)
    o=next(o for o in inp['verified_observations'] if o['observation_key']==key);assert got['exact_quote']==o['quotes'][0] and got['target_essay_id']==o['target_essay_id']
    v=dict(value,representative_observation_key='4902:1::O1');got=test('4902 exact opening-quote whitespace',v,True);assert '" To be yourself' in got['exact_quote']
    test('no representative',dict(representative_observation_key=None,representative_quote_index=None,feedback_paragraph_template='Gather source evidence before review.'),True)
    for index in [-1,999,True,0.5,None]:test('invalid quote index '+str(index),dict(value,representative_quote_index=index),False)
    test('unknown observation key',dict(value,representative_observation_key='unknown'),False)
    test('missing placeholder',dict(value,feedback_paragraph_template='No slot.'),False)
    test('duplicate placeholders',dict(value,feedback_paragraph_template='[REPRESENTATIVE_EVIDENCE] [REPRESENTATIVE_EVIDENCE]'),False)
    test('no representative but placeholder',dict(value,representative_observation_key=None,representative_quote_index=None),False)
    test('appended punctuation',dict(value,feedback_paragraph_template='[REPRESENTATIVE_EVIDENCE].'),False)
    test('surrounding quotes',dict(value,feedback_paragraph_template='“ [REPRESENTATIVE_EVIDENCE] ”'),False)
    test('second quote selected exactly, no fallback',dict(value,representative_quote_index=1),True)
    save(OUT/'A_display_tests.json',dict(timestamp=p.now(),before_gpu=True,actual_model_calls=0,total=len(cases),passed=len(cases),cases=cases,not_counted_as_old_model_success=True))
    print('Pre-GPU display tests passed:',len(cases),flush=True)

def freeze():return {str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts}
def prepare():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'run_manifest.json').exists():return
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
    shutil.copyfile(BASE/'fixed_input.json',OUT/'fixed_input.json');(OUT/'fixed_source').mkdir(exist_ok=True);shutil.copyfile(BASE/'fixed_input.json',OUT/'fixed_source/input.json')
    for eid in TARGETS:
        f=eid.replace(':','_');(OUT/'prepared_3a'/f).mkdir(parents=True,exist_ok=True);shutil.copyfile(BASE/'prepared_3a'/f/'input.json',OUT/'prepared_3a'/f/'input.json')
        (OUT/'evidence_spans').mkdir(exist_ok=True);shutil.copyfile(BASE/'evidence_spans'/f'{f}.json',OUT/'evidence_spans'/f'{f}.json')
    shutil.copyfile(BASE/'stage3b_pipeline/rater_7/input.json',OUT/'fixed_3b_input.json');m=read(BASE/'run_manifest.json')
    for f in PROMPTS.values():assert f.read_bytes().decode('utf-8').count('{{INPUT_JSON}}')==1
    save(OUT/'run_manifest.json',dict(created_at=p.now(),comparison_commit=COMMIT,code_commit=COMMIT,baseline_path=str(BASE),baseline_files_sha256=freeze(),fixed_input_sha256=sha(OUT/'fixed_input.json'),fixed_3b_input_sha256=sha(OUT/'fixed_3b_input.json'),span_catalogs={eid:dict(source=str(BASE/'evidence_spans'/f'{eid.replace(":","_")}.json'),sha256=sha(OUT/'evidence_spans'/f'{eid.replace(":","_")}.json')) for eid in TARGETS},prompts={k:dict(path=str(f),windows_path=str(f).replace('/mnt/c/','C:/'),sha256=sha(f),same_name_locations=[str(x) for x in ROOT.rglob(f.name)]) for k,f in PROMPTS.items()},model=m['model'],generation=m['generation'],max_tokens=m['max_tokens'],sampling=m['sampling'],seed=SEED,seed_policy='925847335 independently for each request, unchanged from saved Stage3.',system_message=m['system_message'],chat=m['chat'],code_sha256_before=sha(__file__),planned_requests=dict(A_display=0,B_fixed_3b=1,C_3a=2,C_pipeline_3b=1),differences=['A is deterministic code with explicit synthetic indices/placeholders, not an old or new model success.','B retains exact v1.3 pipeline input; only new 3B prompt/output schema and deterministic display step differ.','C retains old 3A payloads and exact span tables but changes 3A prompt; new gate/handoff -> 3B v1.4.','Same cached model/sampling/seed/chat and 5000-token budget per request; 4 requests; no Stage1/2, masking, acceptance rerun, repair or resampling.']))
def configure():
    prev.OUT=OUT;prev.BASE=BASE;prev.PROMPTS=PROMPTS;prev.gate_a=gate_a;prev.b_schema=b_schema;prev.configure()
def handoff():
    configure();return prev.handoff()
def process_b(folder,payload):
    if not (folder/'parsed.json').exists():save(folder/'assembly_result.json',dict(pass_=False,errors=['strict JSON unavailable'],feedback_paragraph=None));return
    value=read(folder/'parsed.json');shutil.copyfile(folder/'parsed.json',folder/'parsed_template.json')
    assembly=assemble(value,payload);save(folder/'assembly_result.json',assembly)
    if assembly['pass_']:(folder/'assembled_feedback.txt').write_text(assembly['feedback_paragraph'],encoding='utf-8')
    if b_schema(value):save(folder/'mechanical_checks.json',dict(schema_errors=b_schema(value),assembly=assembly,total=0,passed=0,failed=['schema invalid']));return
    projected=project_b(value,assembly['feedback_paragraph'] if assembly['pass_'] else value['feedback_paragraph_template'])
    saved_schema=prev.base.b_schema;prev.base.b_schema=B_SCHEMA13
    try:checks=prev.base.audit_b(projected,payload)['checks']
    finally:prev.base.b_schema=saved_schema
    rep=value.get('representative_observation_key')
    if rep is None:
        checks=[c for c in checks if c['kind'] not in ['representative_key','representative_in_case_keys']]
        checks.append(dict(kind='no_representative_fields',pass_=value['representative_quote_index'] is None))
    checks.append(dict(kind='assembly',pass_=assembly['pass_'],errors=assembly['errors']))
    obs={o['observation_key']:o for o in payload['verified_observations']};refs={r['rubric_ref_id']:r for r in payload['rubric_entries']};rc=value['rubric_comparison'];cr=refs.get(rc['comparison_band_ref_id']);o=obs.get(rep);expected='none'
    if cr and o and isinstance(o.get('observed_score'),(int,float)):
        expected='higher' if cr['score_band']>o['observed_score'] else 'lower' if cr['score_band']<o['observed_score'] else 'invalid_equal_band'
    checks.append(dict(kind='comparison_direction',pass_=rc['comparison_direction']==expected,actual=rc['comparison_direction'],expected=expected))
    save(folder/'mechanical_checks.json',dict(checks=checks,total=len(checks),passed=sum(c['pass_'] for c in checks),failed=[c for c in checks if not c['pass_']],semantic_direction_alignment_requires_review=True))
def finalize():
    m=read(OUT/'run_manifest.json');m['baseline_unchanged']=freeze()==m['baseline_files_sha256'];m['prompts_unchanged']=all(sha(PROMPTS[k])==v['sha256'] for k,v in m['prompts'].items());assert m['baseline_unchanged'] and m['prompts_unchanged']
    m['implementation_files_sha256']={str(f.relative_to(OUT)):sha(f) for f in (OUT/'code').glob('*.py')};m['actual_requests']=sum(1 for f in OUT.glob('stage3*/*/raw.txt'));m['last_checked_at']=p.now();save(OUT/'run_manifest.json',m)
def worker():
    prepare();assert read(OUT/'A_display_tests.json')['before_gpu'];p.OUT=OUT;p.PROMPTS.update(PROMPTS);p.seed=lambda stage,rid:SEED;p.legacy.structural=structural
    engine=p.Engine();jobs=[p.job(OUT/'stage3a'/e.replace(':','_'),'a',3,e,read(OUT/'prepared_3a'/e.replace(':','_')/'input.json')) for e in TARGETS];jobs.append(p.job(OUT/'stage3b_fixed/rater_7','b',3,'rater_7',read(OUT/'fixed_3b_input.json')))
    engine.run(jobs);inp=handoff();engine.run([p.job(OUT/'stage3b_pipeline/rater_7','b',3,'rater_7',inp)])
    process_b(OUT/'stage3b_fixed/rater_7',read(OUT/'fixed_3b_input.json'));process_b(OUT/'stage3b_pipeline/rater_7',inp);finalize()
if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('phase',choices=['prepare','assembly_tests','worker','launch','finalize']);args=a.parse_args()
    if args.phase=='launch':
        prepare();assembly_tests();assert not (OUT/'process.json').exists()
        with (OUT/'execution.log').open('ab',buffering=0) as log:proc=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'worker'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        save(OUT/'process.json',dict(pid=proc.pid,started=p.now()));print(proc.pid)
    else:
        try:globals()[args.phase]()
        except BaseException:save(OUT/'execution_error.json',dict(traceback=traceback.format_exc()));raise
