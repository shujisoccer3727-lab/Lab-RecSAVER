"""Evaluate Overall-rubric effects with and without correct-rater raw history."""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess, time
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yaml
from .config import load_config, project_path
from .data import load_valid_data
from .history import format_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .utils import write_jsonl


ORDER=['k0','k0_with_rubric','raw_k3','raw_k3_with_rubric']


def sources(config):
    meta=json.loads(project_path(config,config['source_metadata']).read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in project_path(config,config['source_predictions']).read_text(encoding='utf-8').splitlines() if x]
    return meta,{(r['target_id'],int(r['K'])):r for r in rows}


def prepare(config,tokenizer):
    frame=load_valid_data(config); indexed=frame.set_index('target_id',drop=False); meta,prior=sources(config)
    rubric_path=project_path(config,config['rubric_path']); rubric=rubric_path.read_text(encoding='utf-8')
    template=project_path(config,config['prediction_prompt']).read_text(encoding='utf-8'); items=[]
    for target_id in meta['target_ids']:
        target=indexed.loc[target_id]
        for k,condition in [(0,'k0_with_rubric'),(3,'raw_k3_with_rubric')]:
            old=prior[(target_id,k)]; ids=old['history_ids']; history=frame.set_index('target_id',drop=False).loc[ids] if ids else frame.iloc[:0]
            if history.target_id.tolist()!=ids or (k and not history.rater_id.eq(target.rater_id).all()): raise ValueError(f'history mismatch {target_id}')
            if target.source_row_id in set(history.source_row_id): raise ValueError(f'target in history {target_id}')
            prompt=template.format(overall_rubric=rubric,rating_history=format_history(history),target_essay=target.Text)
            tokens=len(tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
            fit=tokens+config['generation']['max_tokens']<=config['model']['max_model_len']
            if not fit: raise ValueError(f'context overflow {target_id} {condition}')
            items.append({'target':target,'history':history,'condition':condition,'prompt':prompt,'prompt_tokens':tokens,'context_fit':fit})
    return meta,prior,items


def summarize(records,out,order=None,comparisons=None,summary_filename='overall_rubric_summary.csv'):
    order = ORDER if order is None else order
    comparisons = [('k0','k0_with_rubric'),('raw_k3','raw_k3_with_rubric'),('k0_with_rubric','raw_k3_with_rubric')] if comparisons is None else comparisons
    valid=pd.DataFrame([r for r in records if r['parse_success']]); rows=[]
    for c in order:
        g=valid[valid.condition==c]; allr=[r for r in records if r['condition']==c]
        rows.append({'condition':c,'n':len(g),'exact_accuracy':g.exact_correct.mean(),'mae':g.absolute_error.mean(),'rmse':math.sqrt(g.squared_error.mean()),
          'qwk':quadratic_weighted_kappa(g.gold_overall,g.predicted_overall),'parse_success_rate':len(g)/len(allr),
          'mean_prompt_tokens':np.mean([r['prompt_tokens'] for r in allr]),'median_prompt_tokens':np.median([r['prompt_tokens'] for r in allr]),
          'p90_prompt_tokens':np.quantile([r['prompt_tokens'] for r in allr],.9),'mean_inference_time_seconds':np.mean([r['inference_time_seconds'] for r in allr]),
          'total_inference_time_seconds':sum(r['inference_time_seconds'] for r in allr),'parse_errors':sum(not r['parse_success'] for r in allr),
          'context_overflows':sum(not r['context_fit'] for r in allr)})
    summary=pd.DataFrame(rows);summary.to_csv(out/summary_filename,index=False); sm=summary.set_index('condition'); pivot=valid.pivot(index='target_id',columns='condition',values='absolute_error'); paired=[]
    for a,b in comparisons:
        d=pivot[a]-pivot[b];paired.append({'from_condition':a,'to_condition':b,'improved_targets':int((d>0).sum()),'unchanged_targets':int((d==0).sum()),'worsened_targets':int((d<0).sum()),
          'mean_ae_difference':d.mean(),'median_ae_difference':d.median(),'accuracy_delta':sm.loc[b].exact_accuracy-sm.loc[a].exact_accuracy,
          'mae_delta':sm.loc[b].mae-sm.loc[a].mae,'rmse_delta':sm.loc[b].rmse-sm.loc[a].rmse,'qwk_delta':sm.loc[b].qwk-sm.loc[a].qwk})
    pd.DataFrame(paired).to_csv(out/'paired_comparisons.csv',index=False)
    dist=[];gold=valid.drop_duplicates('target_id').gold_overall
    for label,values in [('gold',gold)]+[(c,valid[valid.condition==c].predicted_overall) for c in order]:
        counts=values.value_counts().reindex(range(1,6),fill_value=0);dist.extend({'series':label,'score':s,'count':int(n),'rate':n/len(values)} for s,n in counts.items())
    pd.DataFrame(dist).to_csv(out/'prediction_distribution.csv',index=False)
    collapse=[]
    for c in order:
        counts=valid[valid.condition==c].predicted_overall.value_counts();collapse.append({'condition':c,'unique_predicted_scores':len(counts),'most_frequent_score':int(counts.index[0]),'most_frequent_score_ratio':counts.iloc[0]/counts.sum()})
    pd.DataFrame(collapse).to_csv(out/'score_collapse_summary.csv',index=False)
    valid.groupby(['condition','rater_id']).agg(n=('target_id','size'),accuracy=('exact_correct','mean'),mae=('absolute_error','mean')).reset_index().to_csv(out/'rater_summary.csv',index=False)
    examples={c:valid[valid.condition==c][['target_id','gold_overall','predicted_overall','prediction_reasoning']].head(3).to_dict('records') for c in order}
    (out/'reasoning_examples.json').write_text(json.dumps(examples,indent=2),encoding='utf-8');return summary


def dry_run(config):
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True);_,_,items=prepare(config,tok);out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame([{'target_id':x['target'].target_id,'condition':x['condition'],'history_count':len(x['history']),'prompt_tokens':x['prompt_tokens'],'context_fit':x['context_fit']} for x in items]).to_csv(out/'dry_run_conditions.csv',index=False)
    print(f"conditions={len(items)} fit={sum(x['context_fit'] for x in items)} max_tokens={max(x['prompt_tokens'] for x in items)}")


def run(config):
    gen=VLLMGenerator(config);meta,prior,items=prepare(config,gen.tokenizer);out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True);records=[]
    for tid in meta['target_ids']:
        for k,c in [(0,'k0'),(3,'raw_k3')]: row=dict(prior[(tid,k)]);row['condition']=c;row['reused']=True;records.append(row)
    for off in range(0,len(items),config['batch_size']):
        chunk=items[off:off+config['batch_size']];start=time.perf_counter();outputs=gen.generate([x['prompt'] for x in chunk],config['generation']);per=(time.perf_counter()-start)/len(chunk)
        for item,vals in zip(chunk,outputs):
            raw=vals[0];attempts=[raw];error=None
            try: parsed=parse_prediction(raw,True)
            except Exception as exc:
                error=str(exc);raw=gen.generate([item['prompt']],config['generation'])[0][0];attempts.append(raw)
                try:parsed=parse_prediction(raw,True);error=None
                except Exception as exc2:parsed={'predicted_overall':None,'reasoning':''};error=str(exc2)
            t=item['target'];pred=parsed['predicted_overall'];gold=int(t.Overall);records.append({'target_id':t.target_id,'source_row_id':int(t.source_row_id),'rater_id':t.rater_id,'condition':item['condition'],'K':len(item['history']),
              'gold_overall':gold,'predicted_overall':pred,'exact_correct':pred==gold if pred else None,'absolute_error':abs(pred-gold) if pred else None,'squared_error':(pred-gold)**2 if pred else None,'prediction_reasoning':parsed['reasoning'],
              'history_ids':item['history'].target_id.tolist(),'history_rater_ids':item['history'].rater_id.tolist(),'prompt_tokens':item['prompt_tokens'],'output_tokens':len(gen.tokenizer.encode(raw,add_special_tokens=False)),
              'context_fit':True,'parse_success':pred is not None,'retry_count':len(attempts)-1,'parse_error':error,'inference_time_seconds':per,'raw_model_output':raw,'raw_model_output_attempts':attempts,'prompt':item['prompt'],'reused':False})
        write_jsonl(out/'overall_rubric_predictions.jsonl',records)
    rubric=project_path(config,config['rubric_path']);prompt=project_path(config,config['prediction_prompt'])
    md={'experiment_name':config['experiment_name'],'timestamp':datetime.now(timezone.utc).isoformat(),'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),'model':config['model'],
      'temperature':config['generation']['temperature'],'top_p':config['generation']['top_p'],'max_tokens':config['generation']['max_tokens'],'target_seed':config['seed'],'history_seed':config['seed'],'target_ids':meta['target_ids'],
      'history_ids':{tid:prior[(tid,3)]['history_ids'] for tid in meta['target_ids']},'rubric_path':config['rubric_path'],'rubric_sha256':hashlib.sha256(rubric.read_bytes()).hexdigest(),
      'prediction_prompt_path':config['prediction_prompt'],'prediction_prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),'generation_config':config['generation']}
    try:md['GPU']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip()
    except Exception:md['GPU']='unknown'
    (out/'metadata.json').write_text(json.dumps(md,indent=2),encoding='utf-8');(out/'resolved_config.yaml').write_text(yaml.safe_dump({k:v for k,v in config.items() if k!='_root'},sort_keys=False),encoding='utf-8');return summarize(records,out)


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='configs/overall_rubric_ablation.yaml');p.add_argument('--dry-run',action='store_true');a=p.parse_args();c=load_config(a.config)
    if a.dry_run:dry_run(c)
    else:print(run(c).to_string(index=False))
if __name__=='__main__':main()
