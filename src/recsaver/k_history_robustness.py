"""既存100 targetを固定し、K=3/5を複数history seedで比較する。"""
from __future__ import annotations
import argparse, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd
from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .prompts import render
from .utils import read_jsonl, write_jsonl, experiment_metadata


def fixed_targets(config, frame):
    meta=json.loads((project_path(config,config['base_pilot_dir'])/'experiment_metadata.json').read_text(encoding='utf-8'))
    indexed=frame.set_index('target_id',drop=False)
    targets=indexed.loc[meta['target_ids']].copy()
    assert targets.target_id.tolist()==meta['target_ids']
    return targets


def prepare_seed(config, frame, targets, seed, tokenizer):
    rows=[]
    for _,target in targets.iterrows():
        pool=sample_history(frame,target,5,seed,'random')
        for k in (3,5):
            history=pool.iloc[:k]; ids=history.target_id.tolist()
            assert target.target_id not in ids
            assert pool.iloc[:3].target_id.tolist()==pool.iloc[:5].target_id.tolist()[:3]
            prompt=render('zero_shot_prediction.txt',history,target)
            n=len(tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
            assert n+config['generation']['prediction']['max_tokens']<=config['model']['max_model_len']
            rows.append({'seed':seed,'K':k,'target':target,'history':history,'prompt':prompt,'prompt_tokens':n})
    return rows


def reuse_base(config):
    base=read_jsonl(project_path(config,config['base_pilot_dir'])/'k_history_predictions.jsonl')
    return [{**r,'seed':20260814,'reused_from_base_pilot':True} for r in base if r['K'] in (3,5)]


def aggregate(config, records):
    out=project_path(config,config['output_dir']); valid=pd.DataFrame([r for r in records if r['parse_success']])
    summaries=[]
    for (seed,k),g in valid.groupby(['seed','K']):
        summaries.append({'seed':seed,'K':k,'n':len(g),'accuracy':g.exact_correct.mean(),'mae':g.absolute_error.mean(),
          'rmse':math.sqrt(g.squared_error.mean()),'qwk':quadratic_weighted_kappa(g.gold_overall,g.predicted_overall),
          'parse_success_rate':len(g)/100,'mean_prompt_tokens':g.prompt_tokens.mean(),
          'mean_inference_time_seconds':g.inference_time_seconds.mean()})
    summary=pd.DataFrame(summaries).sort_values(['seed','K']); summary.to_csv(out/'k3_k5_seed_summary.csv',index=False)
    paired=[]
    for seed,g in valid.groupby('seed'):
        p=g.pivot(index='target_id',columns='K',values='absolute_error'); delta=p[5]-p[3]
        paired.append({'seed':seed,'improved_k5':int((delta<0).sum()),'unchanged':int((delta==0).sum()),
          'worsened_k5':int((delta>0).sum()),'mean_delta_ae_k5_minus_k3':delta.mean(),
          'median_delta_ae_k5_minus_k3':delta.median(),'paired_targets':delta.notna().sum()})
    pd.DataFrame(paired).to_csv(out/'k3_k5_seed_paired_comparison.csv',index=False)
    agg=summary.groupby('K').agg(accuracy_mean=('accuracy','mean'),accuracy_std=('accuracy','std'),
      mae_mean=('mae','mean'),mae_std=('mae','std'),qwk_mean=('qwk','mean'),qwk_std=('qwk','std'),
      prompt_tokens_mean=('mean_prompt_tokens','mean'),inference_time_mean=('mean_inference_time_seconds','mean')).reset_index()
    agg.to_csv(out/'k3_k5_seed_aggregate.csv',index=False); return summary,agg


def run(config):
    out=project_path(config,config['output_dir']); out.mkdir(parents=True,exist_ok=True)
    records=reuse_base(config) if config.get('reuse_base_seed') else []
    existing=read_jsonl(out/'k3_k5_seed_predictions.jsonl'); records.extend(existing)
    completed={(r['seed'],r['K'],r['target_id']) for r in records}
    pending_seeds=[s for s in config['history_seeds'] if s!=20260814]
    if pending_seeds:
        generator=VLLMGenerator(config); frame=load_valid_data(config); targets=fixed_targets(config,frame)
        for seed in pending_seeds:
            prepared=prepare_seed(config,frame,targets,seed,generator.tokenizer)
            for k in (3,5):
                items=[x for x in prepared if x['K']==k and (seed,k,x['target']['target_id']) not in completed]
                batch=int(config['experiment']['batch_size'])
                for offset in range(0,len(items),batch):
                    chunk=items[offset:offset+batch]; started=time.perf_counter()
                    outputs=generator.generate([x['prompt'] for x in chunk],config['generation']['prediction'])
                    elapsed=time.perf_counter()-started
                    for item,raws in zip(chunk,outputs):
                        raw=raws[0]; error=None
                        try: parsed=parse_prediction(raw,True)
                        except Exception as exc: parsed={'predicted_overall':None,'reasoning':''}; error=f'{type(exc).__name__}: {exc}'
                        t=item['target']; pred=parsed['predicted_overall']; gold=int(t['Overall'])
                        records.append({'seed':seed,'K':k,'target_id':t['target_id'],'source_row_id':int(t['source_row_id']),
                          'rater_id':t['rater_id'],'gold_overall':gold,'predicted_overall':pred,
                          'exact_correct':pred==gold if pred else None,'absolute_error':abs(pred-gold) if pred else None,
                          'squared_error':(pred-gold)**2 if pred else None,'prediction_reasoning':parsed['reasoning'],
                          'history_ids':item['history'].target_id.tolist(),'prompt_tokens':item['prompt_tokens'],
                          'parse_success':pred is not None,'parse_error':error,'retry_count':0,
                          'inference_time_seconds':elapsed/len(chunk),'raw_model_output':raw,'prompt':item['prompt'],
                          'reused_from_base_pilot':False})
                    write_jsonl(out/'k3_k5_seed_predictions.jsonl',[r for r in records if r['seed']!=20260814])
    all_records=reuse_base(config)+read_jsonl(out/'k3_k5_seed_predictions.jsonl')
    write_jsonl(out/'k3_k5_seed_predictions_all.jsonl',all_records)
    (out/'experiment_metadata.json').write_text(json.dumps({**experiment_metadata(config),'history_seeds':config['history_seeds']},indent=2),encoding='utf-8')
    return aggregate(config,all_records)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--config',default='configs/k_history_robustness.yaml'); a=p.parse_args()
    print(run(load_config(a.config))[0].to_string(index=False))
if __name__=='__main__': main()
