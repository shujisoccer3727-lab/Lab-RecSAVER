"""未生成4候補の入力・seedと全3答案の入力長を事前確認する。推論しない。"""
import importlib.metadata
import json
import platform
from transformers import AutoTokenizer
from src.recsaver.rater_feedback_development_v21 import ROOT,CONFIG,load,save,now,generation_payload,output_schema
from src.recsaver.rater_feedback_pilot_v2 import digest


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir']
    tokenizer=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True,trust_remote_code=True)
    rubric=load(out/'rubric.json');catalog=load(out/'conditions.json');checks=[];pending=[]
    template=(ROOT/cfg['prompt_dir']/'generate.txt').read_text(encoding='utf-8')
    for item in load(out/'inputs.json'):
        payload=generation_payload(item,'B',rubric,catalog)
        prompt='OUTPUT_JSON_SCHEMA:\n'+json.dumps(output_schema('generate',payload),ensure_ascii=False,separators=(',',':'))+'\n'+template+json.dumps(payload,ensure_ascii=False,separators=(',',':'))
        tokens=len(tokenizer.apply_chat_template([dict(role='user',content=prompt)],tokenize=True,add_generation_prompt=True))
        fits=tokens+cfg['max_tokens']['generate']<=cfg['model']['max_model_len'];assert fits
        checks.append(dict(target_id=item['target_id'],prompt_tokens=tokens,max_tokens=cfg['max_tokens']['generate'],fits=True,truncated=False))
        for k in [1,2]:
            key=f"B|{item['target_id']}|K{k}"
            cache=out/'stages/generate'/(key.replace(':','_').replace('|','__')+'.json')
            if cache.exists(): continue
            path=out/'pending_inputs'/f"{item['target_id'].replace(':','_')}.json"
            save(path,payload)
            seed=int(digest(f"{cfg['seed']}:generate:{item['target_id']}|K{k}:0")[:8],16)
            pending.append(dict(key=key,input_path=path.relative_to(out).as_posix(),sampling_parameters=dict(cfg['generation'],max_tokens=cfg['max_tokens']['generate'],seed=seed)))
    save(out/'preflight_all_three.json',dict(timestamp=now(),model_called=False,checks=checks))
    save(out/'pending_generation_jobs.json',dict(timestamp=now(),status='prepared_not_executed',jobs=pending,
        resume_command='python -m src.recsaver.rater_feedback_development_v21 three'))
    save(out/'environment.json',dict(timestamp=now(),python=platform.python_version(),
        packages={name:importlib.metadata.version(name) for name in ['vllm','torch','transformers','outlines']},library_changes=False))
    print(dict(checked_targets=len(checks),pending_candidates=len(pending),model_called=False))


if __name__=='__main__':main()
