"""新schemaを既存outlinesでCPU検査。環境更新・モデル生成はしない。"""
import json
import time
from transformers import AutoTokenizer
import torch
from vllm.model_executor.guided_decoding import get_local_guided_decoding_logits_processor
from vllm.sampling_params import GuidedDecodingParams
from src.recsaver.rater_feedback_development import ROOT, CONFIG, load, save, now, generation_payload
from src.recsaver.feedback_development_schema import output_schema


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir'];item=load(out/'inputs.json')[0]
    cid='1514:1/K1/C1';sid=item['target']['spans'][0]['span_id']
    claim=dict(claim_id='C1',scope='target',essay_id=item['target_id'],aspect='Grammar',
        judgment_type='presence',feature='検査例',evaluation='判断保留',span_ids=[sid],direction='unclear',
        overall_relation='不明',trait_relation='不明',limits='検査例')
    payloads=dict(generate=generation_payload(item,'B',load(out/'rubric.json'),load(out/'conditions.json')),
        ground=dict(claims=[claim],essays=[item['target']]),merge=dict(claims=[dict(id=cid)]),
        integrate=dict(essays=[dict(target_id=item['target_id'],eligible_claims=[dict(id=cid)])]),
        compare=dict(target=item['target'],claims=[dict(id=cid)],condition_catalog=load(out/'conditions.json')),
        text=dict(claims={cid:{}},issues={'I':{}},conditions={'Grammar.S3.C01':{}}))
    examples=dict(generate=dict(rationale='検査例',claims=[claim],unexplained='不明'),
        ground=dict(reviews=[dict(claim_id='C1',verdict='insufficient',atomic=True,
            feature_supported=False,evaluation_supported=False,explanation='検査例',added_span_ids=[],counter_span_ids=[])]),
        merge=dict(groups=[],differences=[],unknowns='検査例'),
        integrate=dict(common_features=[],judgment_patterns=[],unknowns='不明'),compare=dict(relationships=[]),
        text=dict(sentences=[dict(element=i,text='検査例',claim_ids=[cid],issue_ids=['I'],condition_ids=['Grammar.S3.C01']) for i in range(1,6)],limits='検査例'))
    tok=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True)
    torch.set_num_threads(2);checks=[]
    for stage,payload in payloads.items():
        schema=output_schema(stage,payload);start=time.monotonic()
        processor=get_local_guided_decoding_logits_processor(GuidedDecodingParams(json=schema,backend='outlines'),tok,None)
        tokens=tok.encode(json.dumps(examples[stage],ensure_ascii=False,separators=(',',':')),add_special_tokens=False)
        past=[]
        for token in tokens:
            scores=processor(past,torch.zeros(152064));assert torch.isfinite(scores[token]),stage
            past.append(token)
        assert torch.isfinite(processor(past,torch.zeros(152064))[tok.eos_token_id]),stage
        checks.append(dict(stage=stage,complete_json_and_eos_passed=True,elapsed_seconds=time.monotonic()-start))
        print(stage,'JSON+EOS passed',flush=True)
    save(out/'guided_backend_checks.json',dict(timestamp=now(),backend='outlines',model_called=False,checks=checks))


if __name__=='__main__': main()
