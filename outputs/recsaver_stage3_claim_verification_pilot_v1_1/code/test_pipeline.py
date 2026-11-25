"""CPU format/identity, dependency and guided-decoding compilation tests."""
import sys,os
sys.dont_write_bytecode=True
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
from copy import deepcopy
import pipeline as p
from jsonschema import Draft7Validator

checks=[]
def ck(name,ok):
    assert ok,name
    checks.append(dict(name=name,pass_=True,synthetic_fixture_not_a_model_result=True))
for g in p.groups():
    payload=p.read(p.OUT/'groups'/g['group_id']/'input_3c.json')
    value=dict(verdicts=[dict(claim_id=c['claim_id'],verdict='supported',reason='Synthetic CPU test reason.') for c in payload['claims']])
    ck(g['group_id']+' normal accepted',not p.validate(value,payload))
    Draft7Validator.check_schema(p.schema_for(payload));Draft7Validator(p.schema_for(payload)).validate(value)
    mutations=[]
    w=deepcopy(value);w['verdicts'].pop();mutations.append(('missing',w))
    w=deepcopy(value);w['verdicts'][1]=deepcopy(w['verdicts'][0]);mutations.append(('duplicate',w))
    w=deepcopy(value);w['verdicts'][0]['claim_id']='UNKNOWN';mutations.append(('unknown',w))
    w=deepcopy(value);w['verdicts'][0]['verdict']='probably';mutations.append(('undefined label',w))
    w=deepcopy(value);w['verdicts'][0]['extra']='not permitted';mutations.append(('extra field',w))
    for name,mutant in mutations:ck(g['group_id']+' rejects '+name,bool(p.validate(mutant,payload)))
    try:p.strict_parse('```json\n'+p.json.dumps(value)+'\n```');fence_accepted=True
    except ValueError:fence_accepted=False
    ck(g['group_id']+' strict code fence rejection',not fence_accepted)
    ck(g['group_id']+' input contains claims only',set(payload)=={'claims'} and all(set(c)=={'claim_id','claim','evidence'} for c in payload['claims']))
    banned=['upstream_interpretation','display_candidate','code_verdict','expected_verdict','scoring_relevance','claim_checks']
    ck(g['group_id']+' no upstream/review leakage',all(k not in p.json.dumps(payload) for k in banned))
code=p.read(p.OUT/'code_verdicts.json')
ck('K01 actual start supported',code['known']['K01']['verdict']=='supported')
ck('K05 actual end contradicted',code['known']['K05']['verdict']=='contradicted' and code['known']['K05']['actual_quote_boundary']==610 and code['known']['K05']['required_source_boundary']==765)
claim=next(c for g in p.groups() for c in g['claims'] if c['claim_id']=='K05')
ck('missing position is insufficient',p.code_position(claim,[])['verdict']=='insufficient')

# Compile the actual per-request JSON constraints on the CPU, with the same
# tokenizer and installed vLLM guidance backend. No LLM is instantiated.
from transformers import AutoTokenizer
from vllm.sampling_params import GuidedDecodingParams
from vllm.model_executor.guided_decoding.outlines_decoding import get_local_outlines_guided_decoding_logits_processor
oldenv=p.read(p.BASE/'environment.json');tokenizer=AutoTokenizer.from_pretrained(oldenv['model_snapshot'],local_files_only=True)
compiled=[]
for g in p.groups():
    payload=p.read(p.OUT/'groups'/g['group_id']/'input_3c.json')
    params=GuidedDecodingParams(json=p.schema_for(payload),backend='outlines')
    processor=get_local_outlines_guided_decoding_logits_processor(params,tokenizer)
    ck(g['group_id']+' JSON guide compiled on CPU',processor is not None)
    compiled.append(dict(group_id=g['group_id'],processor_class=type(processor).__name__,backend='outlines'))
p.save(p.OUT/'pre_gpu_tests.json',dict(all_passed=True,total=len(checks),checks=checks,guided_json_cpu_compilation=compiled,model_requests=0))
print('CPU checks passed:',len(checks),'; all four JSON guides compiled; no model requests.')
