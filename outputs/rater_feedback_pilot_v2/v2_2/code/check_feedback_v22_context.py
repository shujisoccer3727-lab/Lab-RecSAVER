"""失敗した実payloadを参照化し、切り捨てなしの入力長をCPUで測る。"""
import json
from src.recsaver import rater_feedback_development_v21 as p
from src.recsaver.feedback_payload_compaction import intern_payload,expand_interned
from src.recsaver.feedback_development_schema_v21 import output_schema


def main():
    from transformers import AutoTokenizer
    cfg=p.load(p.CONFIG);old=p.ROOT/cfg['output_dir'];tok=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True)
    rows=[]
    for stage in ['merge','integrate','compare','text']:
        for path in (old/'stage_inputs'/stage).glob('*three*.json' if stage not in ['merge'] else '*.json'):
            raw=p.load(path);data=intern_payload(raw);assert expand_interned(data)==raw
            prompt='OUTPUT_JSON_SCHEMA:\n'+json.dumps(output_schema(stage,raw),ensure_ascii=False,separators=(',',':'))+'\n'+(p.ROOT/cfg['prompt_dir']/f'{stage}.txt').read_text(encoding='utf-8')+json.dumps(data,ensure_ascii=False,separators=(',',':'))
            count=len(tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
            rows.append(dict(stage=stage,file=path.name,prompt_tokens=count,max_tokens=cfg['max_tokens'][stage],fits=count+cfg['max_tokens'][stage]<=cfg['model']['max_model_len'],lossless=True))
    p.save(old/'compaction_preflight_v22.json',rows)
    print(json.dumps(rows,indent=2));assert all(r['fits'] for r in rows)


if __name__=='__main__':main()
