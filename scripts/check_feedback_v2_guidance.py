"""既存バックエンドでQwenのJSONを最終トークンまで制約できるかCPU確認。"""
import json
import time
from pathlib import Path
from transformers import AutoTokenizer
import torch
from vllm.model_executor.guided_decoding import get_local_guided_decoding_logits_processor
from vllm.sampling_params import GuidedDecodingParams
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now
from src.recsaver.feedback_output_schema import output_schema


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    calls=[json.loads(s) for s in (ROOT/'outputs/rater_feedback_pilot_v2/v1_3/calls.jsonl').read_text(encoding='utf-8').splitlines()]
    tok=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True)
    torch.set_num_threads(2)
    examples=dict(merge=dict(groups=[],differences=[],unknowns=''),integrate=dict(patterns=[],unknowns=''),compare=dict(relationships=[]),text={k:'確認。' for k in ['criterion_intro','tendency','examples_intro','relationship','next_checks','limits']})
    checks=[]
    for stage in cfg['guided_stages']:
        c=next(c for c in calls if c['stage']==stage);payload=json.loads(c['prompt'].split('INPUT_JSON:')[1])
        schema=output_schema(stage,payload);start=time.monotonic()
        processor=get_local_guided_decoding_logits_processor(GuidedDecodingParams(json=schema,backend=cfg['guided_backend']),tok,None)
        text=json.dumps(examples[stage],ensure_ascii=False,separators=(',',':'))
        ids=tok.encode(text,add_special_tokens=False);past=[]
        for token in ids:
            scores=processor(past,torch.zeros(152064))
            assert torch.isfinite(scores[token]),f'{stage} blocked a valid JSON token'
            past.append(token)
        scores=processor(past,torch.zeros(152064))
        assert torch.isfinite(scores[tok.eos_token_id]),f'{stage} did not allow EOS after complete JSON'
        checks.append(dict(stage=stage,complete_json_and_eos_passed=True,tokens=len(ids),elapsed_seconds=time.monotonic()-start))
        print(stage,'complete JSON and EOS passed',flush=True)
    save(out/'guided_backend_checks.json',dict(timestamp=now(),backend=cfg['guided_backend'],model_called=False,checks=checks))


if __name__=='__main__': main()
