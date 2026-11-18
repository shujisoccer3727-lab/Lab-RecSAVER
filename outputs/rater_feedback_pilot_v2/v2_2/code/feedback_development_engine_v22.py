"""v1.6 Engineの別コピー。変更はschema供給先のみ。既存成果物は変更しない。"""
import json
import subprocess
import time
from .rater_feedback_pilot_v2 import ROOT, now, digest, load, save, append, parse_json

from .feedback_payload_compaction import intern_payload

class Engine:
    """既存VLLMGeneratorを使い、各入力ごとのseedを保ったバッチを追加。"""
    def __init__(self,cfg,out):
        self.cfg,self.out=cfg,out;self.generator=None
        from transformers import AutoTokenizer
        self.tokenizer=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True,trust_remote_code=True)

    def path(self,stage,key):
        return self.out/'stages'/stage/(key.replace(':','_').replace('|','__')+'.json')

    def batch(self,stage,jobs):
        if not jobs:
            return {}
        template=(ROOT/self.cfg['prompt_dir']/f'{stage}.txt').read_text(encoding='utf-8')
        completed={};pending=[]
        for key,payload,validator in jobs:
            encoded=intern_payload(payload) if stage in ['merge','integrate','compare','text'] else payload
            if encoded is not payload:
                name=key.replace(':','_').replace('|','__')+'.json'
                save(self.out/'stage_inputs_expanded'/stage/name,payload)
                save(self.out/'stage_inputs'/stage/name,encoded)
                append(self.out/'compaction_checks.jsonl',dict(stage=stage,key=key,lossless_roundtrip=True,
                    original_characters=len(json.dumps(payload,ensure_ascii=False)),serialized_characters=len(json.dumps(encoded,ensure_ascii=False))))
            prompt=template+json.dumps(encoded,ensure_ascii=False,separators=(',',':'))
            schema=None
            if stage in self.cfg.get('guided_stages',[]):
                from .feedback_development_schema_v21 import output_schema
                schema=output_schema(stage,payload)
                prompt='OUTPUT_JSON_SCHEMA:\n'+json.dumps(schema,ensure_ascii=False,separators=(',',':'))+'\n'+prompt
            fp=digest(prompt+json.dumps(dict(model=self.cfg['model'],generation=self.cfg['generation'],max_tokens=self.cfg['max_tokens'][stage],version=self.cfg['version']),sort_keys=True))
            path=self.path(stage,key)
            if path.exists():
                prior=load(path);assert prior['fingerprint']==fp, f'Fingerprint changed: {stage}/{key}; use new run version'
                completed[key]=prior['result'];continue
            pending.append(dict(key=key,payload=payload,validator=validator,prompt=prompt,fingerprint=fp,schema=schema))
        for offset in range(0,len(pending),self.cfg['batch_size']):
            current=pending[offset:offset+self.cfg['batch_size']]
            for attempt in range(self.cfg['format_retries']+1):
                if not current:
                    break
                prompts=[];params=[];records=[];valid=[]
                for j in current:
                    prompt=j['prompt']+ ('\n前の出力の検査エラー: '+j['error']+'\nJSON全体を修正してください。候補の得点不一致を修正する再生成ではありません。' if 'error' in j else '')
                    ids=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True)
                    # 条件ラベルだけseedから外す。同じtarget/candidateはA/Bで対にする。
                    paired=j['key'].split('|',1)[-1]
                    seed=int(digest(f"{self.cfg['seed']}:{stage}:{paired}:{attempt}")[:8],16)
                    p=dict(self.cfg['generation'],max_tokens=self.cfg['max_tokens'][stage],seed=seed)
                    record=dict(timestamp=now(),stage=stage,key=j['key'],attempt=attempt,model=self.cfg['model'],sampling_parameters=p,prompt=prompt,prompt_tokens=len(ids),fingerprint=j['fingerprint'])
                    if j['schema'] is not None:
                        record['output_json_schema']=j['schema']
                        record['guided_backend']=self.cfg.get('guided_backend','outlines')
                    fit=len(ids)+p['max_tokens']<=self.cfg['model']['max_model_len']
                    append(self.out/'context_checks.jsonl',dict(stage=stage,key=j['key'],prompt_tokens=len(ids),max_tokens=p['max_tokens'],fits=fit,truncated=False))
                    if not fit:
                        record.update(status='failed',error='Context overflow; nothing truncated; no call made')
                        append(self.out/'calls.jsonl',record)
                        save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=None,error=record['error']))
                        completed[j['key']]=None;continue
                    prompts.append(self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True))
                    params.append(p);records.append(record);valid.append(j)
                if not valid:
                    break
                if self.generator is None:
                    free=subprocess.run(['nvidia-smi','--query-gpu=memory.free,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
                    free_mib,total_mib=map(int,free.stdout.strip().splitlines()[0].split(','))
                    required=int(total_mib*self.cfg['model']['gpu_memory_utilization'])+1024
                    append(self.out/'gpu_checks.jsonl',dict(timestamp=now(),free_mib=free_mib,total_mib=total_mib,required_mib=required))
                    assert free_mib>=required,'GPU busy: do not stop other jobs'
                    from .model import VLLMGenerator
                    self.generator=VLLMGenerator(self.cfg)
                from vllm import SamplingParams
                from vllm.sampling_params import GuidedDecodingParams
                import torch
                # 長いprefillで増えた未使用キャッシュを解放。モデル・KV・入力は保持。
                torch.cuda.empty_cache()
                start=time.monotonic()
                sampling=[SamplingParams(n=1,**p,**({'guided_decoding':GuidedDecodingParams(json=j['schema'],backend=self.cfg.get('guided_backend','outlines'))} if j['schema'] is not None else {})) for p,j in zip(params,valid)]
                try:
                    outputs=self.generator.llm.generate(prompts,sampling,use_tqdm=False)
                except BaseException as exc:
                    for record in records:
                        record.update(status='runtime_failed',error=f'{type(exc).__name__}: {exc}',elapsed_batch_seconds=time.monotonic()-start)
                        append(self.out/'calls.jsonl',record)
                    raise
                retry=[]
                for j,record,output in zip(valid,records,outputs):
                    record.update(raw_output=output.outputs[0].text,elapsed_batch_seconds=time.monotonic()-start,
                                  output_tokens=len(output.outputs[0].token_ids),finish_reason=output.outputs[0].finish_reason)
                    try:
                        result=j['validator'](parse_json(record['raw_output']))
                        record['status']='ok';completed[j['key']]=result
                        save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=result,timestamp=now()))
                    except Exception as exc:
                        record.update(status='failed',error=f'{type(exc).__name__}: {exc}')
                        j['error']=record['error'];retry.append(j)
                        if attempt==self.cfg['format_retries']:
                            completed[j['key']]=None
                            save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=None,error=record['error']))
                    append(self.out/'calls.jsonl',record)
                print(stage, f'{offset+len(valid)}/{len(pending)}', 'retry',len(retry),flush=True)
                current=retry
        return completed
