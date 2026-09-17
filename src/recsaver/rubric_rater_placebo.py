"""Compare correct- and wrong-rater K=3 histories under the same Overall Rubric."""
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

ORDER=['k0','k0_with_rubric','wrong_rater_k3_with_rubric','correct_rater_k3_with_rubric']

def sources(config):
    rows=[json.loads(x) for x in project_path(config,config['source_rubric_predictions']).read_text(encoding='utf-8').splitlines() if x]
    meta=json.loads(project_path(config,config['source_rubric_metadata']).read_text(encoding='utf-8'))
    return meta,{(r['target_id'],r['condition']):r for r in rows}

def prepare(config,tokenizer):
    frame=load_valid_data(config);indexed=frame.set_index('target_id',drop=False);meta,prior=sources(config)
    assignments=pd.read_csv(project_path(config,config['history_assignment'])).set_index('target_id');rubric=project_path(config,config['rubric_path']).read_text(encoding='utf-8');template=project_path(config,config['prediction_prompt']).read_text(encoding='utf-8');items=[]
    for tid in meta['target_ids']:
        target=indexed.loc[tid];a=assignments.loc[tid];ids=[a[f'wrong_history_id_{i}'] for i in range(1,4)];history=indexed.loc[ids]
        if history.target_id.tolist()!=ids or history.rater_id.nunique()!=1 or history.rater_id.iloc[0]!=a.wrong_history_rater or a.wrong_history_rater==target.rater_id:raise ValueError(f'wrong history mismatch {tid}')
        if target.source_row_id in set(history.source_row_id):raise ValueError(f'target essay in history {tid}')
        prompt=template.format(overall_rubric=rubric,rating_history=format_history(history),target_essay=target.Text);tokens=len(tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
        if tokens+config['generation']['max_tokens']>config['model']['max_model_len']:raise ValueError(f'overflow {tid}')
        items.append({'target':target,'history':history,'wrong_rater':a.wrong_history_rater,'prompt':prompt,'prompt_tokens':tokens})
    return meta,prior,items

def summarize(records,out):
    valid=pd.DataFrame([r for r in records if r['parse_success']]);rows=[]
    for c in ORDER:
        g=valid[valid.condition==c];allr=[r for r in records if r['condition']==c];rows.append({'condition':c,'n':len(g),'exact_accuracy':g.exact_correct.mean(),'mae':g.absolute_error.mean(),'rmse':math.sqrt(g.squared_error.mean()),'qwk':quadratic_weighted_kappa(g.gold_overall,g.predicted_overall),'parse_success_rate':len(g)/len(allr),'mean_prompt_tokens':np.mean([r['prompt_tokens'] for r in allr]),'median_prompt_tokens':np.median([r['prompt_tokens'] for r in allr]),'p90_prompt_tokens':np.quantile([r['prompt_tokens'] for r in allr],.9),'mean_inference_time_seconds':np.mean([r['inference_time_seconds'] for r in allr]),'total_inference_time_seconds':sum(r['inference_time_seconds'] for r in allr),'parse_errors':sum(not r['parse_success'] for r in allr),'context_overflows':sum(not r['context_fit'] for r in allr)})
    summary=pd.DataFrame(rows);summary.to_csv(out/'rubric_rater_placebo_summary.csv',index=False);sm=summary.set_index('condition');pivot=valid.pivot(index='target_id',columns='condition',values='absolute_error');a='wrong_rater_k3_with_rubric';b='correct_rater_k3_with_rubric';d=pivot[a]-pivot[b]
    pd.DataFrame([{'from_condition':a,'to_condition':b,'improved_targets':int((d>0).sum()),'unchanged_targets':int((d==0).sum()),'worsened_targets':int((d<0).sum()),'mean_ae_difference':d.mean(),'median_ae_difference':d.median(),'accuracy_delta_correct_minus_wrong':sm.loc[b].exact_accuracy-sm.loc[a].exact_accuracy,'mae_delta_correct_minus_wrong':sm.loc[b].mae-sm.loc[a].mae,'rmse_delta_correct_minus_wrong':sm.loc[b].rmse-sm.loc[a].rmse,'qwk_delta_correct_minus_wrong':sm.loc[b].qwk-sm.loc[a].qwk}]).to_csv(out/'paired_comparison.csv',index=False)
    dist=[];gold=valid.drop_duplicates('target_id').gold_overall
    for label,values in [('gold',gold)]+[(c,valid[valid.condition==c].predicted_overall) for c in ORDER[1:]]:
        counts=values.value_counts().reindex(range(1,6),fill_value=0);dist.extend({'series':label,'score':s,'count':int(n),'rate':n/len(values)} for s,n in counts.items())
    pd.DataFrame(dist).to_csv(out/'prediction_distribution.csv',index=False);collapse=[]
    for c in ORDER[1:]:
        counts=valid[valid.condition==c].predicted_overall.value_counts();collapse.append({'condition':c,'unique_predicted_scores':len(counts),'most_frequent_score':int(counts.index[0]),'most_frequent_score_ratio':counts.iloc[0]/counts.sum()})
    pd.DataFrame(collapse).to_csv(out/'score_collapse_summary.csv',index=False)
    valid[valid.condition.isin([a,b])].groupby(['condition','rater_id']).agg(n=('target_id','size'),accuracy=('exact_correct','mean'),mae=('absolute_error','mean')).reset_index().to_csv(out/'rater_summary.csv',index=False)
    wrong=valid[valid.condition==a].set_index('target_id');correct=valid[valid.condition==b].set_index('target_id');changed=[]
    for tid in wrong.index:
        if wrong.loc[tid].predicted_overall!=correct.loc[tid].predicted_overall:changed.append({'target_id':str(tid),'gold':int(wrong.loc[tid].gold_overall),'wrong_prediction':int(wrong.loc[tid].predicted_overall),'correct_prediction':int(correct.loc[tid].predicted_overall),'wrong_error':int(wrong.loc[tid].absolute_error),'correct_error':int(correct.loc[tid].absolute_error),'wrong_rater':str(wrong.loc[tid].get('wrong_rater_id','')),'target_rater':str(wrong.loc[tid].rater_id)})
    pd.DataFrame(changed).to_csv(out/'changed_targets.csv',index=False);examples=[]
    for row in changed[:10]:
        tid=row['target_id'];examples.append({**row,'wrong_reasoning':wrong.loc[tid].prediction_reasoning,'correct_reasoning':correct.loc[tid].prediction_reasoning})
    (out/'reasoning_difference_examples.json').write_text(json.dumps(examples,indent=2),encoding='utf-8');return summary

def dry_run(config):
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True);_,_,items=prepare(config,tok);out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True);pd.DataFrame([{'target_id':x['target'].target_id,'target_rater':x['target'].rater_id,'wrong_rater':x['wrong_rater'],'history_count':len(x['history']),'prompt_tokens':x['prompt_tokens'],'context_fit':True} for x in items]).to_csv(out/'dry_run_conditions.csv',index=False);print(f"targets={len(items)} max_tokens={max(x['prompt_tokens'] for x in items)}")

def run(config):
    gen=VLLMGenerator(config);meta,prior,items=prepare(config,gen.tokenizer);out=project_path(config,config['output_dir']);records=[]
    mapping=[('k0','k0'),('k0_with_rubric','k0_with_rubric'),('raw_k3_with_rubric','correct_rater_k3_with_rubric')]
    for tid in meta['target_ids']:
        for src,dst in mapping:r=dict(prior[(tid,src)]);r['condition']=dst;r['reused']=True;records.append(r)
    for off in range(0,len(items),config['batch_size']):
        chunk=items[off:off+config['batch_size']];start=time.perf_counter();outputs=gen.generate([x['prompt'] for x in chunk],config['generation']);per=(time.perf_counter()-start)/len(chunk)
        for item,vals in zip(chunk,outputs):
            raw=vals[0];attempts=[raw];error=None
            try:parsed=parse_prediction(raw,True)
            except Exception as exc:
                error=str(exc);raw=gen.generate([item['prompt']],config['generation'])[0][0];attempts.append(raw)
                try:parsed=parse_prediction(raw,True);error=None
                except Exception as exc2:parsed={'predicted_overall':None,'reasoning':''};error=str(exc2)
            t=item['target'];pred=parsed['predicted_overall'];gold=int(t.Overall);records.append({'target_id':t.target_id,'source_row_id':int(t.source_row_id),'rater_id':t.rater_id,'condition':'wrong_rater_k3_with_rubric','K':3,'wrong_rater_id':item['wrong_rater'],'gold_overall':gold,'predicted_overall':pred,'exact_correct':pred==gold if pred else None,'absolute_error':abs(pred-gold) if pred else None,'squared_error':(pred-gold)**2 if pred else None,'prediction_reasoning':parsed['reasoning'],'history_ids':item['history'].target_id.tolist(),'history_rater_ids':item['history'].rater_id.tolist(),'prompt_tokens':item['prompt_tokens'],'output_tokens':len(gen.tokenizer.encode(raw,add_special_tokens=False)),'context_fit':True,'parse_success':pred is not None,'retry_count':len(attempts)-1,'parse_error':error,'inference_time_seconds':per,'raw_model_output':raw,'raw_model_output_attempts':attempts,'prompt':item['prompt'],'reused':False})
        write_jsonl(out/'rubric_rater_placebo_predictions.jsonl',records)
    rubric=project_path(config,config['rubric_path']);prompt=project_path(config,config['prediction_prompt']);assign=pd.read_csv(project_path(config,config['history_assignment']));md={'experiment_name':config['experiment_name'],'timestamp':datetime.now(timezone.utc).isoformat(),'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),'model':config['model'],'target_seed':config['seed'],'history_seed':config['seed'],'wrong_rater_seed':config['wrong_rater_seed'],'target_ids':meta['target_ids'],'correct_history_ids':{tid:prior[(tid,'raw_k3_with_rubric')]['history_ids'] for tid in meta['target_ids']},'wrong_history_ids':{r.target_id:[r[f'wrong_history_id_{i}'] for i in range(1,4)] for _,r in assign.iterrows()},'rubric_path':config['rubric_path'],'rubric_sha256':hashlib.sha256(rubric.read_bytes()).hexdigest(),'prompt_path':config['prediction_prompt'],'prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),'generation_config':config['generation']}
    try:md['GPU']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True).stdout.strip()
    except Exception:md['GPU']='unknown'
    (out/'metadata.json').write_text(json.dumps(md,indent=2),encoding='utf-8');(out/'resolved_config.yaml').write_text(yaml.safe_dump({k:v for k,v in config.items() if k!='_root'},sort_keys=False),encoding='utf-8');return summarize(records,out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default='configs/rubric_rater_placebo.yaml');p.add_argument('--dry-run',action='store_true');p.add_argument('--summarize-only',action='store_true');a=p.parse_args();c=load_config(a.config)
    if a.dry_run:dry_run(c)
    elif a.summarize_only:
        out=project_path(c,c['output_dir']);rows=[json.loads(x) for x in (out/'rubric_rater_placebo_predictions.jsonl').read_text(encoding='utf-8').splitlines() if x];print(summarize(rows,out).to_string(index=False))
    else:print(run(c).to_string(index=False))
if __name__=='__main__':main()
