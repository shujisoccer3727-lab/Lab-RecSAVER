"""Stratified 1,000-target scale-up of the fixed Reasoning Evaluation V1 method."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import subprocess
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml

from .config import load_config, project_path
from .data import load_valid_data
from .history import format_history
from .reasoning_eval_v1 import (
    atomic_json, generate, sha, summarize as summarize_v1, token_count, verification_prompt,
)
from .utils import read_jsonl


METRICS = ['bleu', 'rouge1_f1', 'meteor', 'bertscore_f1']
AGGREGATIONS = ['mean', 'max']


def stable_rank(seed, target_id):
    return hashlib.sha256(f'{seed}:{target_id}'.encode()).hexdigest()


def proportional_allocation(frame, total):
    """Hamilton allocation over Gold x rater strata with stable tie-breaking."""
    sizes=frame.groupby(['gold_overall','rater_id'],sort=True).size().rename('population_n').reset_index()
    sizes['quota']=sizes.population_n*total/len(frame)
    sizes['sample_n']=np.floor(sizes.quota).astype(int)
    remaining=total-int(sizes.sample_n.sum())
    sizes['remainder']=sizes.quota-sizes.sample_n
    order=sizes.sort_values(['remainder','gold_overall','rater_id'],ascending=[False,True,True]).index
    for index in order[:remaining]:
        sizes.loc[index,'sample_n']+=1
    if int(sizes.sample_n.sum()) != total or (sizes.sample_n > sizes.population_n).any():
        raise AssertionError('invalid proportional allocation')
    return sizes


def sample_predictions(config, predictions):
    frame=pd.DataFrame(predictions).copy()
    frame=frame[frame.parse_success].sort_values('target_id').reset_index(drop=True)
    if config['num_targets'] > len(frame):
        raise ValueError('num_targets exceeds available predictions')
    allocation=proportional_allocation(frame,config['num_targets'])
    alloc={(int(r.gold_overall),r.rater_id):int(r.sample_n) for r in allocation.itertuples()}
    frame['sampling_stratum']=frame.apply(lambda r:f"gold_{int(r.gold_overall)}__{r.rater_id}",axis=1)
    frame['sampling_rank']=frame.target_id.map(lambda tid:stable_rank(config['sample_seed'],tid))
    frame['selected']=False
    for (gold,rater),part in frame.groupby(['gold_overall','rater_id'],sort=True):
        chosen=part.sort_values(['sampling_rank','target_id']).head(alloc[(int(gold),rater)]).index
        frame.loc[chosen,'selected']=True
    sizes=frame.groupby(['gold_overall','rater_id']).size().to_dict()
    frame['sampling_probability']=frame.apply(
        lambda r:alloc[(int(r.gold_overall),r.rater_id)]/sizes[(r.gold_overall,r.rater_id)],axis=1)
    selected=frame[frame.selected].sort_values(['gold_overall','rater_id','sampling_rank','target_id']).copy()
    if len(selected)!=config['num_targets'] or selected.target_id.nunique()!=len(selected):
        raise AssertionError('sampling did not produce exactly 1,000 unique targets')
    if set(range(1,6)).difference(selected.gold_overall):
        raise AssertionError('a populated Gold score was omitted')
    return frame,selected,allocation


def prepare(config,tokenizer):
    source_md=json.loads(project_path(config,config['source_metadata']).read_text(encoding='utf-8'))
    predictions=[r for r in read_jsonl(project_path(config,config['source_predictions']))
                 if r['condition']==config['prediction_condition']]
    common_ids={r['target_id'] for r in read_jsonl(project_path(config,config['population_filter_predictions']))
                if r['parse_success']}
    predictions=[r for r in predictions if r['target_id'] in common_ids]
    if len(predictions)!=17728:
        raise ValueError(f'expected 17,728 common-comparison predictions, found {len(predictions)}')
    if not predictions or any(not r['parse_success'] for r in predictions):
        raise ValueError('prediction source is empty or contains parse failures')
    if config['model']!=source_md['model']:
        raise ValueError('model differs from full prediction experiment')
    reference_generation=config['generation']['reference']
    if reference_generation!=source_md['generation_config']:
        raise ValueError('reference generation settings differ from V1/full prediction settings')
    if sha(project_path(config,config['rubric_path']))!=source_md['rubric_sha256']:
        raise ValueError('rubric hash differs')
    expected_prompt_hash=source_md['source_sha256']['rubric_prompt']
    if sha(project_path(config,config['prediction_prompt']))!=expected_prompt_hash:
        raise ValueError('prediction prompt hash differs')
    audit,selected,_=sample_predictions(config,predictions)
    data=load_valid_data(config).set_index('target_id',drop=False)
    manifest={r['target_id']:r for r in read_jsonl(project_path(config,config['source_manifest']))}
    rubric=project_path(config,config['rubric_path']).read_text(encoding='utf-8')
    prediction_template=project_path(config,config['prediction_prompt']).read_text(encoding='utf-8')
    reference_template=project_path(config,config['reference_prompt']).read_text(encoding='utf-8')
    verify_template=project_path(config,config['self_verification_prompt']).read_text(encoding='utf-8')
    if '{gold_overall}' in verify_template or '{predicted_overall}' in verify_template:
        raise ValueError('Self-verification template contains a score field')
    items=[]; dry=[]
    for prediction in selected.to_dict('records'):
        tid=prediction['target_id']; target=data.loc[tid]
        history_ids=prediction['history_ids']; history=data.loc[history_ids]
        manifest_row=manifest[tid]
        expected_prompt=prediction_template.format(overall_rubric=rubric,rating_history=format_history(history),
                                                   target_essay=target.Text)
        checks={
            'prediction_exists':True,
            'correct_prediction_condition':prediction['condition']==config['prediction_condition'],
            'target_id_valid':tid in data.index,
            'target_rater_valid':prediction['rater_id']==target.rater_id,
            'gold_valid':int(prediction['gold_overall']) in range(1,6) and int(prediction['gold_overall'])==int(target.Overall),
            'history_size_valid':len(history_ids)==config['history_size'],
            'history_matches_manifest':history_ids==manifest_row['correct_history_ids'],
            'history_rater_matches':bool(history.rater_id.eq(target.rater_id).all()),
            'target_source_excluded':int(target.source_row_id) not in set(history.source_row_id.astype(int)),
            'prediction_prompt_exact':prediction['prompt']==expected_prompt,
            'overall_rubric_only':True,
            'target_gold_not_prediction_input':True,
            'target_traits_not_prediction_input':True,
            'verification_gold_field_absent':True,
        }
        if not all(checks.values()):
            raise ValueError(f'structural audit failed for {tid}: {checks}')
        item=dict(target_id=tid,target_rater=target.rater_id,gold_overall=int(target.Overall),
                  history_ids=history_ids,history_text=format_history(history),rubric=rubric,essay=target.Text,
                  prediction=prediction)
        item['reference_prompt']=reference_template.format(overall_rubric=rubric,rating_history=item['history_text'],
                                                           target_essay=item['essay'],gold_overall=item['gold_overall'])
        item['reference_prompt_tokens']=token_count(tokenizer,item['reference_prompt'])
        item['verification_base_tokens']=token_count(tokenizer,verification_prompt(verify_template,item,''))
        reference_fit=item['reference_prompt_tokens']+reference_generation['max_tokens']<=config['model']['max_model_len']
        verification_fit=(item['verification_base_tokens']+reference_generation['max_tokens']+16+
                          config['generation']['verification']['max_tokens']<=config['model']['max_model_len'])
        if not reference_fit or not verification_fit:
            raise ValueError(f'context overflow before inference: {tid}')
        items.append(item)
        dry.append(dict(target_id=tid,target_rater=target.rater_id,gold_overall=int(target.Overall),
                        predicted_overall=int(prediction['predicted_overall']),history_ids=json.dumps(history_ids),
                        **checks,reference_prompt_tokens=item['reference_prompt_tokens'],
                        verification_base_tokens=item['verification_base_tokens'],reference_context_fit=reference_fit,
                        verification_context_fit=verification_fit))
    if len(items)!=config['num_targets']:
        raise AssertionError('prepared target count mismatch')
    return items,verify_template,audit,selected,pd.DataFrame(dry)


def initialize(config,items,audit,selected,dry):
    out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    paths={k:config[k] for k in ['source_metadata','source_predictions','population_filter_predictions','source_manifest','rubric_path',
                                 'prediction_prompt','reference_prompt','self_verification_prompt']}
    paths.update(parser='src/recsaver/parsing.py',leakage_detector='src/recsaver/reference_audit.py',
                 dataset=config['data']['processed_path'])
    hashes={k:sha(project_path(config,p)) for k,p in paths.items()}
    clean={k:v for k,v in config.items() if not k.startswith('_')}
    fingerprint=hashlib.sha256(json.dumps({'config':clean,'hashes':hashes},sort_keys=True).encode()).hexdigest()
    metadata_path=out/'metadata.json'
    if metadata_path.exists():
        md=json.loads(metadata_path.read_text(encoding='utf-8'))
        if md['fingerprint']!=fingerprint or md['target_ids']!=[i['target_id'] for i in items]:
            raise ValueError('resume config, input, or sampled targets changed')
    else:
        try:
            gpu=subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'],
                               capture_output=True,text=True,check=True).stdout.strip()
        except Exception:
            gpu='unknown'
        md=dict(experiment_name=config['experiment_name'],timestamp=datetime.now(timezone.utc).isoformat(),
                git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),
                model=config['model'],quantization=config['model']['quantization'],GPU=gpu,generation_config=config['generation'],
                sample_seed=config['sample_seed'],bootstrap_seed=config['bootstrap_seed'],target_count=len(items),
                target_ids=[i['target_id'] for i in items],history_ids={i['target_id']:i['history_ids'] for i in items},
                prediction_condition=config['prediction_condition'],prediction_inference_count=0,source_paths=paths,
                source_sha256=hashes,fingerprint=fingerprint,resume=config['resume'],skip_completed=config['skip_completed'],
                seed_policy='SHA256(sample seed, stage, target ID, candidate slot, attempt); resume-stable',status='validated',
                packages={name:importlib.metadata.version(name) for name in ['vllm','torch','transformers','nltk','bert-score']})
        atomic_json(metadata_path,md)
    (out/'resolved_config.yaml').write_text(yaml.safe_dump(clean,sort_keys=False),encoding='utf-8')
    selected[['target_id','rater_id','gold_overall','predicted_overall','exact_correct','absolute_error',
              'sampling_stratum','sampling_probability']].rename(columns={'rater_id':'target_rater',
              'exact_correct':'prediction_correct'}).to_csv(out/'sampled_targets.csv',index=False)
    audit[['target_id','rater_id','gold_overall','predicted_overall','exact_correct','sampling_stratum','selected',
           'sampling_probability']].rename(columns={'rater_id':'target_rater','exact_correct':'prediction_correct'}).to_csv(
               out/'sampling_audit.csv',index=False)
    pop=audit.groupby('gold_overall').size();sample=selected.groupby('gold_overall').size()
    pd.DataFrame([{'gold_score':score,'population_n':int(pop.get(score,0)),'population_proportion':pop.get(score,0)/len(audit),
                   'sample_n':int(sample.get(score,0)),'sample_proportion':sample.get(score,0)/len(selected)}
                  for score in range(1,6)]).to_csv(out/'population_vs_sample_distribution.csv',index=False)
    dry.to_csv(out/'dry_validation.csv',index=False)
    return out


def summarize_large(config,items,references,verifications,out):
    accepted={(r['target_id'],r['candidate_index']) for r in references if r['accepted_as_leakage_free']}
    attempt_counts={}
    for r in references:
        key=(r['target_id'],r['candidate_index']);attempt_counts[key]=attempt_counts.get(key,0)+1
    latest={(v['target_id'],v['candidate_index']):v for v in verifications}
    completed_ids=[];covered_ids=set()
    for item in items:
        tid=item['target_id'];slots=[(tid,n) for n in range(1,config['num_reference_candidates']+1)]
        reference_done=all(key in accepted or attempt_counts.get(key,0)>=config['max_reference_retries'] for key in slots)
        accepted_slots=[key for key in slots if key in accepted]
        verification_done=all(key in latest and (latest[key]['parse_success'] or
                              latest[key]['attempt_index']>=1+config['max_verification_parse_retries']) for key in accepted_slots)
        if reference_done and verification_done:
            completed_ids.append(tid)
        if any(key in latest and latest[key]['verified'] for key in accepted_slots):
            covered_ids.add(tid)
    all_references_done=all(
        (item['target_id'],slot) in accepted or attempt_counts.get((item['target_id'],slot),0)>=config['max_reference_retries']
        for item in items for slot in range(1,config['num_reference_candidates']+1))
    all_complete=len(completed_ids)==len(items)
    interval=250
    full_summary=(not references and not verifications) or all_complete or (
        not all_references_done and len(references)>0 and len(references)%interval<config['batch_size']) or (
        all_references_done and not verifications) or (
        all_references_done and verifications and len(verifications)%interval<config['batch_size'])
    if full_summary:
        summarize_v1(config,items,references,verifications,out)
    md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
    elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(md['timestamp'])).total_seconds()
    done=len(completed_ids);remaining=(elapsed/done*(len(items)-done)) if done else None
    atomic_json(out/'progress.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),selected_targets=len(items),
                completed_targets=done,completed_target_ids=completed_ids,
                covered_targets_so_far=len(covered_ids),reference_attempts=len(references),
                leakage_count=sum(r['leaked'] for r in references),
                verified_reference_count=sum(v['verified'] for v in latest.values()),verification_attempts=len(verifications),
                elapsed_seconds=elapsed,estimated_remaining_seconds=remaining))


def failure_analysis(summary,references):
    rows=[]
    for target in summary[summary.verified_count==0].itertuples():
        attempts=[r for r in references if r['target_id']==target.target_id]
        if attempts and all(not r['parse_success'] for r in attempts):
            category='C_generation_or_parse_failure'
        elif target.leakage_free_count==0:
            category='A_no_leakage_free_candidate'
        elif target.verified_count==0:
            category='B_none_passed_self_verification'
        else:
            category='D_other'
        rows.append({'target_id':target.target_id,'category':category})
    details=pd.DataFrame(rows)
    if details.empty:
        return pd.DataFrame(columns=['category','count','percentage'])
    result=details.groupby('category').size().rename('count').reset_index()
    result['percentage']=result['count']/len(details)
    return result


def bootstrap_tables(config,by_target):
    covered=by_target[by_target.verified_reference_count>0].copy();rng=np.random.default_rng(config['bootstrap_seed'])
    reps=config['bootstrap_repetitions'];rows=[]
    for metric in METRICS:
        for agg in AGGREGATIONS:
            column=f'{metric}_{agg}';values=covered[column].to_numpy(float)
            estimates=[np.mean(values[rng.integers(0,len(values),len(values))]) for _ in range(reps)]
            lo,hi=np.quantile(estimates,[.025,.975])
            rows.append({'analysis':'overall','metric':metric,'aggregation':agg,'group':'covered','n':len(values),
                         'estimate':values.mean(),'ci_lower':lo,'ci_upper':hi})
            groups={str(label):part[column].to_numpy(float) for label,part in covered.groupby('prediction_correct')}
            if 'True' in groups and 'False' in groups:
                correct,incorrect=groups['True'],groups['False'];diffs=[]
                for _ in range(reps):
                    a=correct[rng.integers(0,len(correct),len(correct))]
                    b=incorrect[rng.integers(0,len(incorrect),len(incorrect))]
                    diffs.append(a.mean()-b.mean())
                lo,hi=np.quantile(diffs,[.025,.975])
                rows.append({'analysis':'prediction_correctness_difference','metric':metric,'aggregation':agg,
                             'group':'correct_minus_incorrect','n':len(values),'estimate':correct.mean()-incorrect.mean(),
                             'ci_lower':lo,'ci_upper':hi})
    return pd.DataFrame(rows).assign(confidence_level=.95,bootstrap_repetitions=reps,
                                     bootstrap_seed=config['bootstrap_seed'],resampling_unit='target_id')


def analyze(config):
    out=project_path(config,config['output_dir'])
    from .reasoning_eval_metrics import evaluate
    evaluate(config)
    sampled=pd.read_csv(out/'sampled_targets.csv');summary=pd.read_csv(out/'target_reference_summary.csv')
    refs=read_jsonl(out/'reference_candidates.jsonl');verifications=read_jsonl(out/'self_verification_results.jsonl')
    pool=read_jsonl(out/'verified_reference_pool.jsonl');by_target=pd.read_csv(out/'reasoning_metrics_by_target.csv')
    if len(summary)!=config['num_targets'] or not summary.completed.all():
        raise ValueError('generation is incomplete')
    gold=sampled.set_index('target_id').gold_overall.to_dict();rater=sampled.set_index('target_id').target_rater.to_dict()
    latest={(v['target_id'],v['candidate_index']):v for v in verifications}
    coverage_rows=[]
    for key,filename in [('gold','coverage_by_gold.csv'),('rater','coverage_by_rater.csv')]:
        labels=gold if key=='gold' else rater;rows=[]
        for label,part in summary.assign(label=summary.target_id.map(labels)).groupby('label'):
            tids=set(part.target_id);attempts=[x for x in refs if x['target_id'] in tids]
            accepted=[x for x in attempts if x['accepted_as_leakage_free']]
            checks=[latest[(x['target_id'],x['candidate_index'])] for x in accepted if (x['target_id'],x['candidate_index']) in latest]
            rows.append({f'{key}_overall' if key=='gold' else 'target_rater':label,'target_n':len(part),
                         'covered_n':int((part.verified_count>0).sum()),'coverage_rate':float((part.verified_count>0).mean()),
                         'mean_verified_refs':part.verified_count.mean(),'generated_attempts':len(attempts),
                         'leakage_rate':sum(x['leaked'] for x in attempts)/len(attempts) if attempts else np.nan,
                         'self_verification_pass_rate':sum(x['verified'] for x in checks)/len(checks) if checks else np.nan})
        frame=pd.DataFrame(rows);frame.to_csv(out/filename,index=False);coverage_rows.append(frame)
    failures=failure_analysis(summary,refs);failures.to_csv(out/'uncovered_failure_analysis.csv',index=False)
    columns=[f'{m}_{a}' for m in METRICS for a in AGGREGATIONS]
    covered=by_target[by_target.verified_reference_count>0]
    metric_summary=[]
    boot=bootstrap_tables(config,by_target);boot.to_csv(out/'bootstrap_ci.csv',index=False)
    for metric in METRICS:
        for agg in AGGREGATIONS:
            values=covered[f'{metric}_{agg}'];ci=boot[(boot.analysis=='overall')&(boot.metric==metric)&(boot.aggregation==agg)].iloc[0]
            metric_summary.append({'metric':metric,'aggregation':agg,'n':len(values),'mean':values.mean(),
                                   'median':values.median(),'sd':values.std(ddof=1),'ci_lower':ci.ci_lower,'ci_upper':ci.ci_upper})
    pd.DataFrame(metric_summary).to_csv(out/'reasoning_metrics_summary.csv',index=False)
    correctness=[]
    for label,part in by_target.groupby('prediction_correct'):
        valid=part[part.verified_reference_count>0]
        correctness.append({'prediction_correct':label,'selected_n':len(part),'covered_n':len(valid),
                            'coverage_rate':len(valid)/len(part),**valid[columns].mean().to_dict()})
    diff_rows=boot[boot.analysis=='prediction_correctness_difference']
    for row in diff_rows.itertuples():
        correctness.append({'prediction_correct':'correct_minus_incorrect','selected_n':len(by_target),
                            'covered_n':len(covered),'coverage_rate':np.nan,'metric':row.metric,
                            'aggregation':row.aggregation,'difference':row.estimate,
                            'ci_lower':row.ci_lower,'ci_upper':row.ci_upper})
    pd.DataFrame(correctness).to_csv(out/'prediction_correctness_comparison.csv',index=False)
    by_target['score_error_group']=by_target.absolute_score_error.map(lambda x:'0' if x==0 else '1' if x==1 else '>=2')
    score_rows=[]
    for label,part in by_target.groupby('score_error_group',sort=False):
        valid=part[part.verified_reference_count>0]
        score_rows.append({'score_error_group':label,'selected_n':len(part),'covered_n':len(valid),
                           'coverage_rate':len(valid)/len(part),**valid[columns].mean().to_dict()})
    pd.DataFrame(score_rows).to_csv(out/'score_error_comparison.csv',index=False)
    gold_rows=[]
    for label,part in by_target.groupby('gold_overall'):
        valid=part[part.verified_reference_count>0]
        gold_rows.append({'gold_overall':label,'selected_n':len(part),'covered_n':len(valid),
                          'coverage_rate':len(valid)/len(part),**valid[columns].mean().to_dict()})
    pd.DataFrame(gold_rows).to_csv(out/'gold_score_reasoning_summary.csv',index=False)
    bias=[]
    for scope,part in [('selected',by_target),('covered',covered)]:
        for score,count in part.gold_overall.value_counts().sort_index().items():
            bias.append({'dimension':'gold_overall','level':score,'scope':scope,'n':count,'proportion':count/len(part)})
        for rid,count in part.target_rater.value_counts().sort_index().items():
            bias.append({'dimension':'target_rater','level':rid,'scope':scope,'n':count,'proportion':count/len(part)})
        bias.extend([{'dimension':'prediction_correct_rate','level':'overall','scope':scope,'n':len(part),
                      'proportion':part.prediction_correct.mean()},
                     {'dimension':'mean_absolute_prediction_error','level':'overall','scope':scope,'n':len(part),
                      'proportion':part.absolute_score_error.mean()}])
    pd.DataFrame(bias).to_csv(out/'coverage_bias_analysis.csv',index=False)
    warnings=pd.read_csv(out/'quality_warnings.csv')
    md=json.loads((out/'metadata.json').read_text(encoding='utf-8'));metric_md=json.loads((out/'metric_metadata.json').read_text())
    generation_seconds=md['reference_gpu_seconds'];verification_seconds=md['verification_gpu_seconds']
    total=generation_seconds+verification_seconds+metric_md['metric_seconds']
    runtime=pd.DataFrame([{'reference_generation_seconds':generation_seconds,'self_verification_seconds':verification_seconds,
                           'reasoning_metric_seconds':metric_md['metric_seconds'],'total_measured_seconds':total,
                           'seconds_per_target':total/config['num_targets'],
                           'estimated_seconds_for_17728':total/config['num_targets']*17728,
                           'estimated_hours_for_17728':total/config['num_targets']*17728/3600}])
    runtime.to_csv(out/'runtime_summary.csv',index=False)
    coverage=pd.DataFrame([{'target_count':len(summary),'covered_targets':int((summary.verified_count>0).sum()),
                            'uncovered_targets':int((summary.verified_count==0).sum()),
                            'coverage_rate':float((summary.verified_count>0).mean()),
                            'mean_verified_refs':summary.verified_count.mean(),'median_verified_refs':summary.verified_count.median()}])
    distribution=pd.DataFrame([{'verified_reference_count':n,'targets':int((summary.verified_count==n).sum())} for n in range(4)])
    attempts=pd.DataFrame([{'generated_attempts':len(refs),'leaked_attempts':sum(x['leaked'] for x in refs),
                            'leakage_rate':sum(x['leaked'] for x in refs)/len(refs),'retry_attempts':sum(x['attempt_index']>1 for x in refs),
                            'leakage_free_candidates':sum(x['accepted_as_leakage_free'] for x in refs)}])
    verified=pd.DataFrame([{'candidate_n':len(latest),'verification_attempts':len(verifications),'verified_n':len(pool),
                            'pass_rate':len(pool)/len(latest)}])
    diversity=pd.read_csv(out/'reference_diversity.csv')
    def table(frame):
        def fmt(x): return f'{x:.4f}' if isinstance(x,float) else str(x).replace('|','\\|')
        return '\n'.join(['| '+' | '.join(map(str,frame.columns))+' |','| '+' | '.join(['---']*len(frame.columns))+' |']+
                         ['| '+' | '.join(fmt(x) for x in row)+' |' for row in frame.itertuples(index=False,name=None)])
    lines=['# Rec-SAVER AES: Reasoning Evaluation Large-scale (1,000 targets)','## Sampling',
           table(pd.read_csv(out/'population_vs_sample_distribution.csv')),
           'Gold Overall × target raterの比例配分と固定hash rankで1,000件を決定した。Predictionは再生成していない。',
           '## Reference generation',table(attempts),'## Self-verification',table(verified),
           '## Coverage',table(coverage),table(distribution),'### Coverage by Gold',table(coverage_rows[0]),
           '### Coverage by rater',table(coverage_rows[1]),'## Failure analysis',table(failures),
           '## Reasoning metrics',table(pd.DataFrame(metric_summary)),
           '## Prediction correctness relationship',table(pd.DataFrame(correctness)),
           'Correct/Incorrect差は探索的関連であり因果を示さない。bootstrap CIと各groupのcoverageを併記した。',
           '## Score-error relationship',table(pd.DataFrame(score_rows)),
           '## Gold-score-specific metrics',table(pd.DataFrame(gold_rows)),
           '## Coverage bias','詳細はcoverage_bias_analysis.csv。selectedとcoveredのGold・rater分布、prediction correctness、absolute errorを比較した。',
           '## Reference diversity',table(pd.DataFrame([{'target_n':diversity.target_id.nunique(),'pair_n':len(diversity),
               'mean_lexical_jaccard':diversity.lexical_jaccard.mean(),'median_lexical_jaccard':diversity.lexical_jaccard.median(),
               'mean_bertscore_similarity':diversity.bertscore_similarity.mean() if 'bertscore_similarity' in diversity else np.nan}])) ,
           '## Quality warnings',table(pd.DataFrame([{'warning_count':len(warnings),'warning_rate_per_attempt':len(warnings)/len(refs)}])),
           '## Runtime',table(runtime),
           '## Interpretation rule','Coverageは、漏洩のないSelf-verified Referenceを1件以上持ちReasoning類似度評価に含められる割合である。Prediction accuracyや人間の実思考との一致を意味しない。',
           '## Recommendation',('1,000件がparse/context errorなく完了し、外挿時間が運用可能なら全件化は技術的に実行可能。'
                                'この判断は計算可能性とpipeline安定性だけに基づき、研究手法の変更や全件実行を自動的には行わない。')]
    (out/'report.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    md.update(status='completed',analysis_timestamp=datetime.now(timezone.utc).isoformat(),quality_warning_count=len(warnings),
              runtime_summary=runtime.iloc[0].to_dict())
    atomic_json(out/'metadata.json',md)


def validate_complete(config):
    out=project_path(config,config['output_dir']);md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
    for key,path in md['source_paths'].items():
        if sha(project_path(config,path))!=md['source_sha256'][key]:
            raise ValueError(f'source changed: {key}')
    summary=pd.read_csv(out/'target_reference_summary.csv')
    if len(summary)!=config['num_targets'] or not summary.completed.all():
        raise ValueError('not all sampled targets completed')
    if len(set(md['target_ids']))!=config['num_targets']:
        raise ValueError('duplicate sampled target')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='configs/reasoning_eval_large.yaml')
    parser.add_argument('--stage',choices=['validate','generate','evaluate'],default='validate');parser.add_argument('--limit',type=int)
    args=parser.parse_args();config=load_config(args.config)
    out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    from filelock import FileLock
    with FileLock(str(out/'.run.lock'),timeout=0):
        if args.stage=='evaluate':
            validate_complete(config);analyze(config);return
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True)
        items,template,audit,selected,dry=prepare(config,tokenizer)
        out=initialize(config,items,audit,selected,dry)
        summarize_large(config,items,[],[],out) if not (out/'reference_candidates.jsonl').exists() else None
        print(f'Structural validation: {len(items)} targets passed',flush=True)
        if args.stage=='generate':
            generate(config,items,template,out,args.limit,summarize_fn=summarize_large)


if __name__=='__main__':
    main()
