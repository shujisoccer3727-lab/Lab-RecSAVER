"""Predict Overall from a target-independent natural-language rater profile."""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yaml
from .config import load_config, project_path
from .data import load_valid_data
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .utils import write_jsonl


def write_metadata(config, out, target_ids):
    try:
        gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip()
    except Exception: gpu='unknown'
    pp=project_path(config,config['profile_prompt']); predp=project_path(config,config['prediction_prompt'])
    metadata={'experiment_name':config['experiment_name'],'timestamp':datetime.now(timezone.utc).isoformat(),
      'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),
      'model':config['model'],'prompt_language':'en','profile_prompt':config['profile_prompt'],
      'profile_prompt_sha256':hashlib.sha256(pp.read_bytes()).hexdigest(),'prediction_prompt':config['prediction_prompt'],
      'prediction_prompt_sha256':hashlib.sha256(predp.read_bytes()).hexdigest(),'profile_generation_seed':config['profile_generation_seed'],
      'target_seed':config['seed'],'generation':config['generation'],'target_ids':target_ids,'gpu':gpu}
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')


def prepare(config, tokenizer):
    frame=load_valid_data(config); meta=json.loads(project_path(config,config['source_metadata']).read_text(encoding='utf-8'))
    profiles={r['rater_id']:r for r in [json.loads(x) for x in (project_path(config,config['output_dir'])/'profiles.jsonl').read_text(encoding='utf-8').splitlines() if x]}
    targets=frame.set_index('target_id',drop=False).loc[meta['target_ids']]; template=project_path(config,config['prediction_prompt']).read_text(encoding='utf-8')
    assignments=pd.read_csv(project_path(config,config['output_dir'])/'profile_history_assignment.csv')
    items=[]
    for _,target in targets.iterrows():
        profile=profiles[target.rater_id]; history_sources=set(assignments[assignments.rater_id==target.rater_id].source_row_id)
        if target.source_row_id in history_sources: raise ValueError(f"target in profile history: {target.target_id}")
        prompt=template.format(profile=profile['profile_text'],target_essay=target.Text)
        tokens=len(tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
        if tokens+config['generation']['prediction']['max_tokens']>config['model']['max_model_len']: raise ValueError('context overflow')
        items.append({'target':target,'profile':profile,'prompt':prompt,'prompt_tokens':tokens})
    return items


def summarize(records,outdir):
    valid=pd.DataFrame([r for r in records if r['parse_success']]); order=['k0','raw_history_k3','rater_profile']; rows=[]
    for condition in order:
        g=valid[valid.condition==condition]; allr=[r for r in records if r['condition']==condition]
        rows.append({'condition':condition,'n':len(g),'exact_accuracy':g.exact_correct.mean(),'mae':g.absolute_error.mean(),
          'rmse':math.sqrt(g.squared_error.mean()),'qwk':quadratic_weighted_kappa(g.gold_overall,g.predicted_overall),
          'parse_success_rate':len(g)/len(allr),'mean_prompt_tokens':np.mean([r['prompt_tokens'] for r in allr]),
          'mean_inference_time_seconds':np.mean([r['inference_time_seconds'] for r in allr]),
          'total_inference_time_seconds':sum(r['inference_time_seconds'] for r in allr),
          'parse_errors':sum(not r['parse_success'] for r in allr),'context_overflows':sum(not r['context_fit'] for r in allr)})
    summary=pd.DataFrame(rows); summary.to_csv(outdir/'profile_prediction_summary.csv',index=False)
    pivot=valid.pivot(index='target_id',columns='condition',values='absolute_error'); paired=[]
    for start in ['raw_history_k3','k0']:
        d=pivot[start]-pivot.rater_profile; paired.append({'from_condition':start,'to_condition':'rater_profile',
          'improved_targets':int((d>0).sum()),'unchanged_targets':int((d==0).sum()),'worsened_targets':int((d<0).sum()),
          'mean_ae_difference':d.mean(),'median_ae_difference':d.median(),'paired_targets':int(d.notna().sum())})
    pd.DataFrame(paired).to_csv(outdir/'paired_comparison.csv',index=False)
    dist=[]; gold=valid.drop_duplicates('target_id').gold_overall
    for label,values in [('gold',gold)]+[(c,valid[valid.condition==c].predicted_overall) for c in order]:
        counts=values.value_counts().reindex(range(1,6),fill_value=0)
        dist.extend({'series':label,'score':s,'count':int(n),'rate':n/len(values)} for s,n in counts.items())
    pd.DataFrame(dist).to_csv(outdir/'prediction_distribution.csv',index=False)
    valid.groupby(['condition','rater_id']).agg(n=('target_id','size'),accuracy=('exact_correct','mean'),mae=('absolute_error','mean')).reset_index().to_csv(outdir/'rater_summary.csv',index=False)
    return summary


def dry_run(config):
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True); items=prepare(config,tok)
    out=project_path(config,config['output_dir']); pd.DataFrame([{'target_id':x['target'].target_id,'rater_id':x['target'].rater_id,
      'profile_rater_id':x['profile']['rater_id'],'prompt_tokens':x['prompt_tokens'],'context_fit':True,'raw_history_in_prompt':'[History ' in x['prompt']} for x in items]).to_csv(out/'prediction_dry_run.csv',index=False)
    print(f"targets={len(items)} max_prompt_tokens={max(x['prompt_tokens'] for x in items)}")


def run(config):
    gen=VLLMGenerator(config); items=prepare(config,gen.tokenizer); out=project_path(config,config['output_dir'])
    prior=[json.loads(x) for x in project_path(config,config['source_predictions']).read_text(encoding='utf-8').splitlines() if x]
    records=[]
    for row in prior:
        row=dict(row); row['condition']='k0' if row['K']==0 else 'raw_history_k3'; row['reused']=True; records.append(row)
    for off in range(0,len(items),config['batch_size']):
        chunk=items[off:off+config['batch_size']]; started=time.perf_counter(); outputs=gen.generate([x['prompt'] for x in chunk],config['generation']['prediction']); per=(time.perf_counter()-started)/len(chunk)
        for item,values in zip(chunk,outputs):
            raw=values[0]; attempts=[raw]; error=None
            try: parsed=parse_prediction(raw,True)
            except Exception as exc:
                error=f'{type(exc).__name__}: {exc}'; raw=gen.generate([item['prompt']],config['generation']['prediction'])[0][0]; attempts.append(raw)
                try: parsed=parse_prediction(raw,True); error=None
                except Exception as exc2: parsed={'predicted_overall':None,'reasoning':''}; error=f'{type(exc2).__name__}: {exc2}'
            t=item['target']; pred=parsed['predicted_overall']; gold=int(t.Overall)
            records.append({'target_id':t.target_id,'source_row_id':int(t.source_row_id),'rater_id':t.rater_id,'condition':'rater_profile','gold_overall':gold,
              'predicted_overall':pred,'exact_correct':pred==gold if pred else None,'absolute_error':abs(pred-gold) if pred else None,'squared_error':(pred-gold)**2 if pred else None,
              'prediction_reasoning':parsed['reasoning'],'profile_rater_id':item['profile']['rater_id'],'profile_history_ids':item['profile']['profile_history_ids'],
              'prompt_tokens':item['prompt_tokens'],'output_tokens':len(gen.tokenizer.encode(raw,add_special_tokens=False)),'context_fit':True,'parse_success':pred is not None,
              'retry_count':len(attempts)-1,'parse_error':error,'inference_time_seconds':per,'raw_model_output':raw,'raw_model_output_attempts':attempts,'prompt':item['prompt'],'reused':False})
        write_jsonl(out/'profile_predictions.jsonl',records)
    write_metadata(config,out,[x['target'].target_id for x in items])
    return summarize(records,out)


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='configs/rater_profile.yaml');p.add_argument('--dry-run',action='store_true');p.add_argument('--metadata-only',action='store_true');a=p.parse_args();c=load_config(a.config)
    if a.dry_run: dry_run(c)
    elif a.metadata_only:
        meta=json.loads(project_path(c,c['source_metadata']).read_text(encoding='utf-8'));write_metadata(c,project_path(c,c['output_dir']),meta['target_ids'])
    else: print(run(c).to_string(index=False))
if __name__=='__main__':main()
