"""Analysis and reporting for the full-scale four-condition prediction experiment."""
from __future__ import annotations

import argparse
import itertools
import json
import math

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .full_prediction_experiment import FILES, atomic_json, input_fingerprint, recover_jsonl


COMPARISONS = [
    ('rubric_effect','k0','k0_overall_rubric'),
    ('generic_history_effect','k0_overall_rubric','wrong_k3_overall_rubric'),
    ('correct_history_effect','k0_overall_rubric','correct_k3_overall_rubric'),
    ('personalization_effect','wrong_k3_overall_rubric','correct_k3_overall_rubric'),
]


def qwk(gold, predicted):
    gold=np.asarray(gold,dtype=int)-1; predicted=np.asarray(predicted,dtype=int)-1; n=5
    observed=np.bincount(gold*n+predicted,minlength=n*n).reshape(n,n)
    expected=np.outer(np.bincount(gold,minlength=n),np.bincount(predicted,minlength=n))/len(gold)
    weights=np.fromfunction(lambda i,j:((i-j)/(n-1))**2,(n,n))
    denominator=(weights*expected).sum()
    return float(1-(weights*observed).sum()/denominator) if denominator else float('nan')


def metric_row(condition, rows, scope):
    valid=rows[rows.parse_success].copy()
    return {'scope':scope,'condition':condition,'attempted_n':len(rows),'n':len(valid),
            'accuracy':valid.exact_correct.mean(),'mae':valid.absolute_error.mean(),
            'rmse':math.sqrt(valid.squared_error.mean()),'qwk':qwk(valid.gold_overall,valid.predicted_overall),
            'parse_success_rate':len(valid)/len(rows),'retry_count':int(rows.retry_count.sum()),
            'context_overflow':int((~rows.context_fit).sum()),'mean_prompt_tokens':rows.prompt_tokens.mean(),
            'median_prompt_tokens':rows.prompt_tokens.median(),'p90_prompt_tokens':rows.prompt_tokens.quantile(.9),
            'mean_inference_time_seconds':rows.inference_time_seconds.mean(),
            'total_inference_time_seconds':rows.inference_time_seconds.sum()}


def distribution_entropy(values):
    p=values.value_counts(normalize=True).reindex(range(1,6),fill_value=0).to_numpy(float)
    return float(-(p[p>0]*np.log2(p[p>0])).sum())


def bootstrap(config, common):
    if any(condition not in common for condition in config['conditions']):
        return pd.DataFrame()
    ids=sorted(set.intersection(*[set(common[c].target_id) for c in config['conditions']]))
    frames={c:common[c].set_index('target_id').loc[ids] for c in config['conditions']}
    gold=frames[config['conditions'][0]].gold_overall.to_numpy(int); preds={c:frames[c].predicted_overall.to_numpy(int) for c in frames}
    rng=np.random.default_rng(config['bootstrap_seed']); reps=config['bootstrap_repetitions']; samples={}
    for condition in config['conditions']:
        samples[(condition,'accuracy')]=[]; samples[(condition,'mae')]=[]
    for name,a,b in COMPARISONS:
        samples[(name,'qwk_delta')]=[]; samples[(name,'paired_ae_difference')]=[]
    for _ in range(reps):
        idx=rng.integers(0,len(ids),len(ids)); g=gold[idx]
        for condition in config['conditions']:
            p=preds[condition][idx]
            samples[(condition,'accuracy')].append(float(np.mean(p==g)))
            samples[(condition,'mae')].append(float(np.mean(np.abs(p-g))))
        for name,a,b in COMPARISONS:
            pa,pb=preds[a][idx],preds[b][idx]
            samples[(name,'qwk_delta')].append(qwk(g,pb)-qwk(g,pa))
            samples[(name,'paired_ae_difference')].append(float(np.mean(np.abs(pa-g)-np.abs(pb-g))))
    rows=[]
    for (analysis,statistic),values in samples.items():
        if statistic=='accuracy': point=np.mean(preds[analysis]==gold)
        elif statistic=='mae': point=np.mean(np.abs(preds[analysis]-gold))
        else:
            _,a,b=next(x for x in COMPARISONS if x[0]==analysis)
            point=qwk(gold,preds[b])-qwk(gold,preds[a]) if statistic=='qwk_delta' else np.mean(np.abs(preds[a]-gold)-np.abs(preds[b]-gold))
        low,high=np.quantile(values,[.025,.975])
        rows.append({'analysis':analysis,'statistic':statistic,'n':len(ids),'point_estimate':point,
                     'ci_lower':low,'ci_upper':high,'confidence_level':.95,'bootstrap_repetitions':reps,
                     'bootstrap_seed':config['bootstrap_seed'],'resampling_unit':'target_id'})
    return pd.DataFrame(rows)


def table(frame):
    def cell(value):
        if isinstance(value,float): return f'{value:.4f}'
        return str(value).replace('|','\\|')
    return '\n'.join(['| '+' | '.join(map(str,frame.columns))+' |','| '+' | '.join(['---']*len(frame.columns))+' |']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None)])


def pilot_comparison(out, full_paired):
    """Compare full-scale deltas with the fixed 100-target pilot when available."""
    pilot_path=out.parent/'rubric_rater_placebo'/'rubric_rater_placebo_summary.csv'
    if not pilot_path.exists():
        return pd.DataFrame()
    pilot=pd.read_csv(pilot_path).set_index('condition')
    pairs={
        'rubric_effect':('k0','k0_with_rubric'),
        'generic_history_effect':('k0_with_rubric','wrong_rater_k3_with_rubric'),
        'correct_history_effect':('k0_with_rubric','correct_rater_k3_with_rubric'),
        'personalization_effect':('wrong_rater_k3_with_rubric','correct_rater_k3_with_rubric'),
    }
    full=full_paired.set_index('comparison')
    rows=[]
    for name,(a,b) in pairs.items():
        rows.append({
            'comparison':name,
            'pilot_accuracy_delta':pilot.loc[b,'exact_accuracy']-pilot.loc[a,'exact_accuracy'],
            'full_accuracy_delta':full.loc[name,'accuracy_delta'],
            'pilot_mae_delta':pilot.loc[b,'mae']-pilot.loc[a,'mae'],
            'full_mae_delta':full.loc[name,'mae_delta'],
            'pilot_rmse_delta':pilot.loc[b,'rmse']-pilot.loc[a,'rmse'],
            'full_rmse_delta':full.loc[name,'rmse_delta'],
            'pilot_qwk_delta':pilot.loc[b,'qwk']-pilot.loc[a,'qwk'],
            'full_qwk_delta':full.loc[name,'qwk_delta'],
        })
    frame=pd.DataFrame(rows)
    frame.to_csv(out/'pilot_full_comparison.csv',index=False)
    return frame


def analyze(config, allow_partial=False):
    out=project_path(config,config['output_dir']); manifest=recover_jsonl(out/'target_manifest.jsonl')
    records={}; expected={c:sum(r['condition_available'][c] for r in manifest) for c in config['conditions']}
    for condition in config['conditions']:
        rows=recover_jsonl(out/FILES[condition])
        if rows:
            frame=pd.DataFrame(rows); records[condition]=frame
            if len(frame)!=frame.target_id.nunique(): raise ValueError(f'duplicate target: {condition}')
        if not allow_partial and len(rows)!=expected[condition]:
            raise ValueError(f'incomplete {condition}: {len(rows)}/{expected[condition]}')
    if not records: return
    summary=pd.DataFrame([metric_row(c,g,'all_available') for c,g in records.items()])
    summary.to_csv(out/'full_prediction_summary.csv',index=False)
    if len(records)<len(config['conditions']):
        return
    valid={c:g[g.parse_success].copy() for c,g in records.items()}
    common_ids=sorted(set.intersection(*[set(g.target_id) for g in valid.values()]))
    common={c:g.set_index('target_id').loc[common_ids].reset_index() for c,g in valid.items()}
    common_summary=pd.DataFrame([metric_row(c,g,'common_targets') for c,g in common.items()])
    common_summary.to_csv(out/'common_target_summary.csv',index=False)
    paired=[]
    for name,a,b in COMPARISONS:
        left=common[a].set_index('target_id');right=common[b].set_index('target_id');delta=left.absolute_error-right.absolute_error
        paired.append({'comparison':name,'from_condition':a,'to_condition':b,'paired_n':len(delta),
                       'improved':int((delta>0).sum()),'unchanged':int((delta==0).sum()),'worsened':int((delta<0).sum()),
                       'mean_ae_difference':delta.mean(),'median_ae_difference':delta.median(),
                       'accuracy_delta':right.exact_correct.mean()-left.exact_correct.mean(),
                       'mae_delta':right.absolute_error.mean()-left.absolute_error.mean(),
                       'rmse_delta':math.sqrt(right.squared_error.mean())-math.sqrt(left.squared_error.mean()),
                       'qwk_delta':qwk(right.gold_overall,right.predicted_overall)-qwk(left.gold_overall,left.predicted_overall)})
    paired_frame=pd.DataFrame(paired);paired_frame.to_csv(out/'paired_comparisons.csv',index=False)
    dist=[]; gold=common[config['conditions'][0]].gold_overall
    for label,values in [('gold',gold)]+[(c,common[c].predicted_overall) for c in config['conditions']]:
        counts=values.value_counts().reindex(range(1,6),fill_value=0)
        dist.extend({'series':label,'score':int(score),'count':int(n),'rate':n/len(values)} for score,n in counts.items())
    pd.DataFrame(dist).to_csv(out/'prediction_distribution.csv',index=False)
    gold_p=gold.value_counts(normalize=True).reindex(range(1,6),fill_value=0)
    collapse=[]
    for condition in config['conditions']:
        values=common[condition].predicted_overall; counts=values.value_counts(); pred_p=values.value_counts(normalize=True).reindex(range(1,6),fill_value=0)
        collapse.append({'condition':condition,'unique_predicted_scores':len(counts),'most_frequent_score':int(counts.index[0]),
                         'most_frequent_score_ratio':counts.iloc[0]/len(values),'entropy_bits':distribution_entropy(values),
                         'total_variation_distance_from_gold':.5*np.abs(pred_p-gold_p).sum()})
    pd.DataFrame(collapse).to_csv(out/'score_collapse_summary.csv',index=False)
    rater=[]
    for condition,g in common.items():
        for rater_id,part in g.groupby('rater_id'):
            rater.append({'condition':condition,'rater_id':rater_id,'n':len(part),'accuracy':part.exact_correct.mean(),
                          'mae':part.absolute_error.mean(),'mean_prediction':part.predicted_overall.mean(),
                          'mean_gold':part.gold_overall.mean(),'calibration_gap':part.predicted_overall.mean()-part.gold_overall.mean()})
    rater_frame=pd.DataFrame(rater);rater_frame.to_csv(out/'rater_summary.csv',index=False)
    pivot=rater_frame.pivot(index='rater_id',columns='condition',values='mae')
    delta=pivot.correct_k3_overall_rubric-pivot.wrong_k3_overall_rubric
    gap_pivot=rater_frame.pivot(index='rater_id',columns='condition',values='calibration_gap')
    gap_delta=gap_pivot.correct_k3_overall_rubric.abs()-gap_pivot.wrong_k3_overall_rubric.abs()
    rater_comparison=pd.DataFrame({
        'rater_id':delta.index,
        'wrong_mae':pivot.wrong_k3_overall_rubric,
        'correct_mae':pivot.correct_k3_overall_rubric,
        'mae_gain_wrong_minus_correct':-delta,
        'wrong_calibration_gap':gap_pivot.wrong_k3_overall_rubric,
        'correct_calibration_gap':gap_pivot.correct_k3_overall_rubric,
        'absolute_calibration_gap_gain':-gap_delta,
    }).reset_index(drop=True)
    rater_comparison.to_csv(out/'rater_correct_wrong_details.csv',index=False)
    rater_summary=pd.DataFrame([
        {'criterion':'MAE','correct_better':int((delta<0).sum()),'same':int((delta==0).sum()),
         'correct_worse':int((delta>0).sum()),'rater_count':len(delta),
         'wrong_mean_value':pivot.wrong_k3_overall_rubric.mean(),
         'correct_mean_value':pivot.correct_k3_overall_rubric.mean()},
        {'criterion':'absolute_calibration_gap','correct_better':int((gap_delta<0).sum()),
         'same':int((gap_delta==0).sum()),'correct_worse':int((gap_delta>0).sum()),
         'rater_count':len(gap_delta),'wrong_mean_value':gap_pivot.wrong_k3_overall_rubric.abs().mean(),
         'correct_mean_value':gap_pivot.correct_k3_overall_rubric.abs().mean()},
    ])
    rater_summary.to_csv(out/'rater_correct_wrong_summary.csv',index=False)
    gold_rows=[]
    for condition,g in common.items():
        for gold_score,part in g.groupby('gold_overall'):
            counts=part.predicted_overall.value_counts().reindex(range(1,6),fill_value=0)
            for score,n in counts.items():
                gold_rows.append({'condition':condition,'gold_overall':int(gold_score),'n':len(part),
                                  'accuracy':part.exact_correct.mean(),'mae':part.absolute_error.mean(),
                                  'predicted_score':int(score),'prediction_count':int(n),'prediction_rate':n/len(part)})
    pd.DataFrame(gold_rows).to_csv(out/'gold_score_summary.csv',index=False)
    correct=common['correct_k3_overall_rubric']; pairs=[]
    for source_id,group in correct.groupby('source_row_id'):
        for (_,a),(_,b) in itertools.combinations(group.iterrows(),2):
            gd=int(np.sign(b.gold_overall-a.gold_overall));pdirection=int(np.sign(b.predicted_overall-a.predicted_overall))
            pairs.append({'source_row_id':int(source_id),'target_id_a':a.target_id,'target_id_b':b.target_id,
                          'rater_a':a.rater_id,'rater_b':b.rater_id,'gold_a':int(a.gold_overall),'gold_b':int(b.gold_overall),
                          'prediction_a':int(a.predicted_overall),'prediction_b':int(b.predicted_overall),
                          'gold_disagreement':gd!=0,'prediction_disagreement':pdirection!=0,
                          'gold_direction_reproduced':pdirection==gd if gd!=0 else None})
    pair_frame=pd.DataFrame(pairs); pair_frame.to_csv(out/'same_essay_pair_details.csv',index=False)
    disagreement=pair_frame[pair_frame.gold_disagreement]
    prediction_disagreement_on_gold=int(disagreement.prediction_disagreement.sum())
    direction_reproduced=int(disagreement.gold_direction_reproduced.sum())
    agreement=pair_frame[~pair_frame.gold_disagreement]
    prediction_disagreement_on_agreement=int(agreement.prediction_disagreement.sum())
    pair_summary=pd.DataFrame([{
        'same_essay_rater_pair_count':len(pair_frame),
        'gold_disagreement_pair_count':len(disagreement),
        'gold_agreement_pair_count':len(agreement),
        'prediction_disagreement_pair_count':int(pair_frame.prediction_disagreement.sum()),
        'prediction_disagreement_among_gold_disagreement':prediction_disagreement_on_gold,
        'prediction_differentiation_rate_among_gold_disagreement':prediction_disagreement_on_gold/len(disagreement),
        'prediction_disagreement_among_gold_agreement':prediction_disagreement_on_agreement,
        'prediction_disagreement_rate_among_gold_agreement':prediction_disagreement_on_agreement/len(agreement),
        'gold_disagreement_direction_reproduced_count':direction_reproduced,
        'gold_disagreement_direction_reproduced_rate':direction_reproduced/len(disagreement),
        'direction_accuracy_when_prediction_differs':direction_reproduced/prediction_disagreement_on_gold,
    }])
    pair_summary.to_csv(out/'same_essay_pair_analysis.csv',index=False)
    ci=bootstrap(config,common);ci.to_csv(out/'bootstrap_ci.csv',index=False)
    pilot_frame=pilot_comparison(out,paired_frame)
    metadata_path=out/'metadata.json';metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata.setdefault('completion_timestamp',pd.Timestamp.now(tz='UTC').isoformat())
    metadata.update(status='completed',
                    condition_counts={c:len(records[c]) for c in config['conditions']},common_target_count=len(common_ids),
                    parse_errors={c:int((~records[c].parse_success).sum()) for c in config['conditions']},
                    context_overflows={c:int((~records[c].context_fit).sum()) for c in config['conditions']},
                    retry_counts={c:int(records[c].retry_count.sum()) for c in config['conditions']},
                    inference_seconds={c:float(records[c].inference_time_seconds.sum()) for c in config['conditions']})
    atomic_json(metadata_path,metadata)
    gold_compact=pd.DataFrame(gold_rows).drop_duplicates(['condition','gold_overall'])[
        ['condition','gold_overall','n','accuracy','mae']]
    total_inference_hours=sum(metadata['inference_seconds'].values())/3600
    elapsed_hours=(pd.Timestamp(metadata['completion_timestamp'])-pd.Timestamp(metadata['timestamp'])).total_seconds()/3600
    report_lines=['# Rec-SAVER AES: Full-scale Prediction Experiment',
                  '## Executive summary',
                  ('共通17,728 targetでは、Correct-rater K=3 + Overall Rubricが4条件中で最高のAccuracy '
                   f"({common_summary.set_index('condition').loc['correct_k3_overall_rubric','accuracy']:.4f})とQWK "
                   f"({common_summary.set_index('condition').loc['correct_k3_overall_rubric','qwk']:.4f})、最低のMAE "
                   f"({common_summary.set_index('condition').loc['correct_k3_overall_rubric','mae']:.4f})とRMSE "
                   f"({common_summary.set_index('condition').loc['correct_k3_overall_rubric','rmse']:.4f})を得た。"
                   'Wrong-rater履歴に対して全主要指標が改善し、paired AEとQWKの差はbootstrap 95% CIでゼロを跨がない。'
                   'したがって、履歴の一般的なfew-shot効果だけでなく、採点者本人の履歴に追加価値があるというRQ3を支持する。'),
                  ('一方、Overall Rubric単体はK=0よりAccuracy、MAE、RMSEをわずかに改善したが、Score 3予測を'
                   '85.59%から93.91%へ集中させ、QWKを0.2650から0.1782へ低下させた。'
                   'Accuracy/MAEだけではこの退化を捉えられず、順序的一致と分布を併記する必要がある。'),
                  '## Dataset',table(pd.read_csv(out/'dataset_audit.csv')),
                  '主比較は4条件すべてでparse成功した共通target集合。条件単独の全利用可能sampleと共通集合の両方を保存した。',
                  '## Performance: all available',table(summary),'## Performance: common targets',table(common_summary),
                  '## Main paired comparisons','AE differenceはfrom minus to（正が改善）。',table(paired_frame),
                  '## Bootstrap 95% CI','target_idを単位に2,000回percentile bootstrap。QWK deltaはto minus from。',table(ci),
                  'すべての比較でQWK差とpaired AE differenceの95% CIはゼロを跨がない。ただし、同一source essayを複数raterが評価したtarget間の依存と、generation/history drawの不確実性はこのbootstrapに含まれない。',
                  '## Prediction distribution',table(pd.DataFrame(dist)),'## Score collapse',table(pd.DataFrame(collapse)),
                  ('HistoryはScore 3集中を約79%まで緩和し、Score 4を約7%まで回復させたが、GoldのScore 4比率26.17%には遠い。'
                   'CorrectとWrongの分布距離はほぼ同等で、Correctの改善は単なる分布拡大だけでは説明できない。'),
                  '## Gold score performance',table(gold_compact),
                  ('Correct条件はWrong条件に対してGold 1〜5のすべてでMAEを改善した。ただしGold 1のAccuracyは0.168対0.224で低い。'
                   'Gold 1は125件、Gold 5は535件と少なく、両端の推定は慎重に扱う。'
                   '最大の残存誤差は高得点側で、Correct条件でもGold 4の83.66%を3、Gold 5の64.67%を3と予測した。'),
                  '## Rater analysis',table(rater_summary),
                  ('Correct履歴はWrong履歴よりMAEが19/27 raterで低く、1名で同じ、7名で高い。rater別の絶対calibration gapは17/27名で縮小し、'
                   f"27名の単純平均は{gap_pivot.wrong_k3_overall_rubric.abs().mean():.4f}から"
                   f"{gap_pivot.correct_k3_overall_rubric.abs().mean():.4f}へ低下した。"
                   'raterごとのNは27〜1,602と不均衡であり、この集計は探索的である。calibration_gapはmean prediction − mean Goldで、因果的なbias correctionを意味しない。'),
                  '## Same-essay pair analysis',table(pair_summary),
                  ('Goldが異なる4,163組のうち、Correct条件が異なる予測を出したのは999組（24.00%）。Gold差の方向を再現したのは全Gold不一致組の'
                   '614組（14.75%）であり、予測が異なった組に限定すると61.46%だった。Goldが同じ4,689組でも1,101組（23.48%）で予測が異なり、'
                   'Gold不一致組の差別化率24.00%とほぼ同じだった。本人履歴は集計指標を改善したが、同一essayに対する個別rater差を選択的に再現する力は限定的である。'),
                  '## Pilotとの比較',table(pilot_frame) if not pilot_frame.empty else 'Pilot outputが見つからなかった。',
                  ('100-target Pilotで見られたRubricのMAE/RMSE改善とQWK低下、Wrong履歴の分布拡大とQWK改善は全件版でも再現した。'
                   'PilotでCorrect対WrongがAccuracy/MAEのみCorrect優位、RMSE/QWKは混在していた点は、全件版で4指標すべてCorrect優位に収束した。'),
                  '## Interpretation by research question',
                  ('**RQ1 — Rubric effect:** 部分的に支持。K=0からRubric追加でAccuracy +0.0054、MAE −0.0107、RMSE −0.0143だが、'
                   'QWK −0.0868。RubricはGold 3の識別を強めた一方、Gold 2への3判定を大幅に増やし、高得点側もほぼ3に留めた。'),
                  ('**RQ2 — History effect:** Correct履歴では全主要指標がRubric単体より改善した。Wrong履歴はQWKと分布を改善したが、'
                   'Accuracy/MAE/RMSEを悪化させた。Historyの価値は指標と履歴の本人一致に依存する。'),
                  ('**RQ3 — Personalization effect:** 支持。CorrectはWrongに対してAccuracy +0.0178、MAE −0.0242、RMSE −0.0249、QWK +0.0378。'
                   'paired AEは2,290件で改善、1,872件で悪化し、平均改善0.0242。95% CIはpaired AE [0.0166, 0.0310]、QWK差 [0.0244, 0.0506]。'
                   'ただし同一essay pair分析ではrater差の再現率が低く、個別化を完全に捉えたとは言えない。'),
                  '## Parse/context errors',table(pd.DataFrame([{'condition':c,'parse_errors':metadata['parse_errors'][c],
                       'retry_count':metadata['retry_counts'][c],'context_overflows':metadata['context_overflows'][c]} for c in config['conditions']])),
                  '## Runtime',table(pd.DataFrame([{'condition':c,'inference_seconds':metadata['inference_seconds'][c],
                       'inference_hours':metadata['inference_seconds'][c]/3600} for c in config['conditions']])),
                  f'条件別inference時間の合計は{total_inference_hours:.2f}時間、metadata上の開始から完了までは{elapsed_hours:.2f}時間。',
                  '## Disk outputs','Correct K=3 JSONLはtarget_id、rater_id、gold_overall、predicted_overall、prediction_reasoning、history_idsを各行に持ち、後続Reasoning Evaluationから直接参照可能。']
    (out/'report.md').write_text('\n\n'.join(report_lines)+'\n',encoding='utf-8')
    print(common_summary.to_string(index=False),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--config',default='configs/full_prediction_experiment.yaml')
    parser.add_argument('--allow-partial',action='store_true');args=parser.parse_args();analyze(load_config(args.config),args.allow_partial)


if __name__=='__main__':main()
