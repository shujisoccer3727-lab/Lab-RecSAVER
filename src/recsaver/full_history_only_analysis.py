"""既存2条件を読み取り専用で利用する全件Raw K=3比較。"""
from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd

from .config import project_path
from .full_prediction_analysis import distribution_entropy, metric_row, qwk, table
from .full_prediction_experiment import atomic_json, sha
from .full_history_only_experiment import CONDITION, REFERENCE, PREDICTIONS, output_path, read_records, require

CONDITIONS = ['k0', CONDITION, REFERENCE]
COMPARISONS = [('raw_history_effect', 'k0', CONDITION), ('rubric_effect_under_correct_history', CONDITION, REFERENCE)]


def bootstrap(config, common):
    """既存と同じtarget単位のpaired percentile bootstrapにAccuracy差を追加。"""
    gold = common['k0'].gold_overall.to_numpy(int)
    preds = {c:g.predicted_overall.to_numpy(int) for c,g in common.items()}
    rng = np.random.default_rng(config['bootstrap_seed'])
    samples = {(name,stat):[] for name,_,_ in COMPARISONS
               for stat in ('accuracy_delta','mae_delta','paired_ae_difference','qwk_delta')}

    def statistics(g, a, b):
        ae = np.mean(np.abs(b-g)-np.abs(a-g))
        return dict(accuracy_delta=np.mean(b==g)-np.mean(a==g), mae_delta=ae,
                    paired_ae_difference=-ae, qwk_delta=qwk(g,b)-qwk(g,a))

    for _ in range(config['bootstrap_repetitions']):
        idx = rng.integers(0,len(gold),len(gold))
        for name,a,b in COMPARISONS:
            for statistic,value in statistics(gold[idx],preds[a][idx],preds[b][idx]).items():
                samples[name,statistic].append(value)
    rows = []
    for name,a,b in COMPARISONS:
        for statistic,point in statistics(gold,preds[a],preds[b]).items():
            low,high = np.quantile(samples[name,statistic],[.025,.975])
            rows.append(dict(analysis=name,statistic=statistic,n=len(gold),point_estimate=point,
                ci_lower=low,ci_upper=high,confidence_level=.95,bootstrap_seed=config['bootstrap_seed'],
                bootstrap_repetitions=config['bootstrap_repetitions'],resampling_unit='target_id'))
    return pd.DataFrame(rows)


def same_essay_pairs(common):
    rows = []
    for condition,frame in common.items():
        pairs = []
        for _,group in frame.groupby('source_row_id'):
            for a,b in itertools.combinations(group.itertuples(),2):
                if a.rater_id == b.rater_id:
                    continue
                gd = int(np.sign(b.gold_overall-a.gold_overall))
                pdirection = int(np.sign(b.predicted_overall-a.predicted_overall))
                pairs.append((gd,pdirection))
        gd = np.array([p[0] for p in pairs])
        pred = np.array([p[1] for p in pairs])
        disagree, agree = gd!=0, gd==0
        reproduced = int(((pred==gd)&disagree).sum())
        rows.append(dict(condition=condition,same_essay_rater_pair_count=len(pairs),
            gold_disagreement_pair_count=int(disagree.sum()),gold_agreement_pair_count=int(agree.sum()),
            prediction_disagreement_pair_count=int((pred!=0).sum()),
            gold_disagreement_direction_reproduced_count=reproduced,
            gold_disagreement_direction_reproduced_rate=reproduced/disagree.sum() if disagree.any() else np.nan,
            prediction_disagreement_rate_among_gold_agreement=float(np.mean(pred[agree]!=0)) if agree.any() else np.nan))
    return pd.DataFrame(rows)


def analyze(config):
    out = output_path(config)
    source = project_path(config,config['target_source'])
    metadata = json.loads((out/'metadata.json').read_text(encoding='utf-8'))
    for name,value in metadata['reference_file_sha256'].items():
        require(sha(source/name) == value, f'Reference changed: {name}')
    manifest = read_records(source/'target_manifest.jsonl')
    ids = [r['target_id'] for r in manifest]
    paths = {'k0':source/'predictions_k0.jsonl',CONDITION:out/PREDICTIONS,REFERENCE:source/'predictions_correct_k3_rubric.jsonl'}
    records = {}
    for condition,path in paths.items():
        rows = read_records(path)
        require([r['target_id'] for r in rows] == ids, f'Incomplete/order mismatch: {condition} ({len(rows)}/{len(ids)})')
        for row,target in zip(rows,manifest):
            require(row['condition'] == condition and row['gold_overall'] == target['gold_overall']
                    and row['rater_id'] == target['target_rater'] and row['source_row_id'] == target['source_row_id'], 'Analysis identity mismatch')
            pred = row['predicted_overall']
            require(row['parse_success'] == (pred is not None), 'Inconsistent parse status')
            if pred is not None:
                require(pred in range(1,6), 'Invalid prediction')
                row.update(exact_correct=pred==row['gold_overall'],absolute_error=abs(pred-row['gold_overall']),squared_error=(pred-row['gold_overall'])**2)
        records[condition] = pd.DataFrame(rows)
    valid = {c:g[g.parse_success].copy() for c,g in records.items()}
    common_set = set.intersection(*[set(g.target_id) for g in valid.values()])
    common_ids = [tid for tid in ids if tid in common_set]
    require(bool(common_ids), 'No common successful targets')
    common = {c:g.set_index('target_id').loc[common_ids].reset_index() for c,g in valid.items()}
    summaries = pd.DataFrame([metric_row(c,g,'all_available') for c,g in records.items()])
    summary = pd.DataFrame([metric_row(c,g,'common_targets') for c,g in common.items()])
    summaries[summaries.condition==CONDITION].to_csv(out/'full_history_only_summary.csv',index=False)
    summaries.to_csv(out/'all_available_summary.csv',index=False)
    summary.to_csv(out/'comparison_summary.csv',index=False)
    pd.DataFrame({'target_id':common_ids}).to_csv(out/'common_target_ids.csv',index=False)
    paired = []
    for name,a,b in COMPARISONS:
        left,right = common[a],common[b]
        delta = left.absolute_error-right.absolute_error
        paired.append(dict(comparison=name,from_condition=a,to_condition=b,paired_n=len(delta),
            improved=int((delta>0).sum()),unchanged=int((delta==0).sum()),worsened=int((delta<0).sum()),
            mean_ae_difference=delta.mean(),median_ae_difference=delta.median(),
            accuracy_delta=right.exact_correct.mean()-left.exact_correct.mean(),
            mae_delta=right.absolute_error.mean()-left.absolute_error.mean(),
            qwk_delta=qwk(right.gold_overall,right.predicted_overall)-qwk(left.gold_overall,left.predicted_overall)))
    paired = pd.DataFrame(paired)
    paired.to_csv(out/'paired_comparisons.csv',index=False)
    ci = bootstrap(config,common)
    ci.to_csv(out/'bootstrap_ci.csv',index=False)
    dist,collapse = [],[]
    gold = common['k0'].gold_overall
    gold_p = gold.value_counts(normalize=True).reindex(range(1,6),fill_value=0)
    for label,values in [('gold',gold)]+[(c,g.predicted_overall) for c,g in common.items()]:
        counts = values.value_counts().reindex(range(1,6),fill_value=0)
        dist.extend(dict(series=label,score=int(s),count=int(n),rate=n/len(values),percent=100*n/len(values)) for s,n in counts.items())
        if label != 'gold':
            collapse.append(dict(condition=label,unique_predicted_scores=values.nunique(),
                most_frequent_score=int(counts.idxmax()),most_frequent_score_ratio=counts.max()/len(values),
                entropy_bits=distribution_entropy(values),total_variation_distance_from_gold=.5*np.abs(counts/len(values)-gold_p).sum()))
    dist,collapse = pd.DataFrame(dist),pd.DataFrame(collapse)
    dist.to_csv(out/'prediction_distribution.csv',index=False)
    collapse.to_csv(out/'score_collapse_summary.csv',index=False)
    raters,gold_rows = [],[]
    for condition,g in common.items():
        for rater,part in g.groupby('rater_id'):
            raters.append(dict(condition=condition,rater_id=rater,n=len(part),accuracy=part.exact_correct.mean(),
                mae=part.absolute_error.mean(),mean_prediction=part.predicted_overall.mean(),mean_gold=part.gold_overall.mean(),
                calibration_gap=part.predicted_overall.mean()-part.gold_overall.mean()))
        for score in range(1,6):
            part = g[g.gold_overall==score]
            for predicted,n in part.predicted_overall.value_counts().reindex(range(1,6),fill_value=0).items():
                gold_rows.append(dict(condition=condition,gold_overall=score,n=len(part),accuracy=part.exact_correct.mean(),
                    mae=part.absolute_error.mean(),predicted_score=int(predicted),prediction_count=int(n),
                    prediction_rate=n/len(part) if len(part) else np.nan))
    raters,gold_rows = pd.DataFrame(raters),pd.DataFrame(gold_rows)
    raters.to_csv(out/'rater_summary.csv',index=False)
    gold_rows.to_csv(out/'gold_score_summary.csv',index=False)
    calibration = []
    gap = raters.pivot(index='rater_id',columns='condition',values='calibration_gap').abs()
    for name,a,b in COMPARISONS:
        delta = gap[a]-gap[b]
        calibration.append(dict(comparison=name,rater_count=len(delta),improved=int((delta>0).sum()),
            unchanged=int((delta==0).sum()),worsened=int((delta<0).sum()),
            from_mean_absolute_gap=gap[a].mean(),to_mean_absolute_gap=gap[b].mean()))
    calibration = pd.DataFrame(calibration)
    calibration.to_csv(out/'calibration_summary.csv',index=False)
    pairs = same_essay_pairs(common)
    pairs.to_csv(out/'same_essay_pair_analysis.csv',index=False)
    raw = summaries.set_index('condition').loc[CONDITION]
    pilot = pd.DataFrame([dict(scope='pilot (user supplied)',n=100,accuracy=.53,mae=.54,rmse=.8246,qwk=.1536),
                          dict(scope='full-scale (all valid)',**{k:raw[k] for k in ('n','accuracy','mae','rmse','qwk')})])
    pilot.to_csv(out/'pilot_full_comparison.csv',index=False)
    interpretation = []
    for r in paired.itertuples():
        interpretation.append(f'{r.comparison}: Accuracy差={r.accuracy_delta:+.4f}, MAE差={r.mae_delta:+.4f}, QWK差={r.qwk_delta:+.4f}。')
    lines = ['# Full-scale Correct Raw History K=3 without Rubric',
        '## Experiment setup',
        '既存の固定target・固定Historyを再利用。モデル・生成設定・parserは既存実験と同一。新規推論はRubricなしの1条件のみ。',
        f"Model: {config['model']}; generation: {config['generation']}; seed: {config['generation_seed']}。",
        '指定されたRaw用PromptとRubric用Promptは指示文も異なるため、Rubric本文だけを除去した厳密な比較ではない。Prompt tuningは行っていない。',
        'seedは既存の条件名依存の生成方針を使用し、新条件名により個々の乱数drawは異なる。',
        '## Dataset / audit',table(pd.read_csv(out/'dataset_audit.csv')),
        '## Performance',f'主比較は3条件でparse成功した共通{len(common_ids):,}件。各条件独自Nも以下に示す。',
        table(summary[['condition','n','accuracy','mae','rmse','qwk']]),table(summaries[['condition','attempted_n','n','accuracy','mae','rmse','qwk']]),
        '## Raw History effect',table(paired.iloc[:1]),
        '## Rubric effect under Correct History',table(paired.iloc[1:]),
        'AE differenceはfrom − to（正が改善）。Accuracy/QWK/MAE deltaはto − from。',
        '## Bootstrap CI',table(ci),
        '固定seedのtarget単位paired percentile bootstrap。既存分析と同様に同一essay内の相関、History/生成drawの変動は区間に含まない。',
        '## Prediction distribution',table(dist),'## Score collapse',table(collapse),
        '## Gold-score analysis',table(gold_rows.drop_duplicates(['condition','gold_overall'])[['condition','gold_overall','n','accuracy','mae']]),
        'Gold 2/4に対する予測内訳：',table(gold_rows[gold_rows.gold_overall.isin([2,4])]),
        '## Rater-level analysis',table(raters),'## Calibration analysis',table(calibration),
        'Calibration gapはmean prediction − mean Gold。採点者別の記述的・探索的比較であり、採点者間のNや作文構成は異なる。',
        '## Same-essay pair analysis',table(pairs),'## Pilot vs full-scale',table(pilot),
        'Pilotと全件ではsampling条件が異なるため、記述的比較のみであり統計検定は行わない。',
        '## Parse/context audit',table(summaries[['condition','attempted_n','n','parse_success_rate','retry_count','context_overflow','mean_prompt_tokens','median_prompt_tokens','p90_prompt_tokens']]),
        '## Runtime',table(summaries[['condition','mean_inference_time_seconds','total_inference_time_seconds']]),
        '既存2条件の時間は保存済み記録から転載。新規実験の時間は実測生成時間（retryを含む、batch時間をtargetへ等分）。',
        '## Interpretation',*interpretation,
        '指標間の一致・不一致と95% CIを併読し、期待したPatternに結果を当てはめない。上記Prompt指示文と条件別乱数drawの差にも留意する。']
    (out/'report.md').write_text('\n\n'.join(lines)+'\n',encoding='utf-8')
    metadata.update(status='completed',completion_timestamp=pd.Timestamp.now(tz='UTC').isoformat(),common_target_count=len(common_ids),
        parse_errors={c:int((~g.parse_success).sum()) for c,g in records.items()},
        condition_counts={c:len(g) for c,g in records.items()},bootstrap_seed=config['bootstrap_seed'],bootstrap_repetitions=config['bootstrap_repetitions'])
    atomic_json(out/'metadata.json',metadata)
    print(summary[['condition','n','accuracy','mae','rmse','qwk']].to_string(index=False),flush=True)
