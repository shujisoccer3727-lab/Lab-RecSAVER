"""実呼出し前のA/B生成入力を確定保存する。モデル出力は作らない。"""
import json
import shutil
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,sha,digest,now,generation_payload


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    items=load(out/'inputs.json');rubric=load(out/'rubric.json');conditions=load(out/'conditions.json')
    template=(ROOT/cfg['prompt_dir']/'generate.txt').read_text(encoding='utf-8')
    manifest=[]
    for condition in cfg['conditions']:
        for item in items:
            p=generation_payload(item,condition,rubric,conditions)
            filename=item['target_id'].replace(':','_')+'.json'
            path=out/'conditions'/condition/'generation_inputs'/filename
            save(path,p)
            prompt=template+json.dumps(p,ensure_ascii=False,separators=(',',':'))
            for k in range(1,cfg['candidates_per_target']+1):
                seed=int(digest(f"{cfg['seed']}:generate:{item['target_id']}|K{k}:0")[:8],16)
                manifest.append(dict(condition=condition,target_id=item['target_id'],rater_id=item['rater_id'],candidate_index=k,history_ids=[h['essay_id'] for h in item['history']],input_path=str(path.relative_to(out)),input_sha256=sha(path),prompt_sha256=digest(prompt),seed=seed))
    save(out/'generation_input_manifest.json',dict(timestamp=now(),model_calls_made=0,candidate_inputs=manifest))
    for name in ['prepare_feedback_v2_inputs.py','run_feedback_v2_when_ready.py']:
        source=ROOT/'scripts'/name
        shutil.copy2(source,out/'code'/name)
    save(out/'auxiliary_code_manifest.json',{name:sha(out/'code'/name) for name in ['prepare_feedback_v2_inputs.py','run_feedback_v2_when_ready.py']})
    print(f'Saved {len(manifest)} candidate entries / {len(items)*len(cfg["conditions"])} distinct A/B generation inputs',flush=True)


if __name__=='__main__':
    main()
