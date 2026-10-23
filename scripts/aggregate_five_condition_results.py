"""既存JSONLのみを用いた5条件共通N集計。推論依存を一切importしない。"""
from pathlib import Path
import ast
import hashlib
import itertools
import json
import platform
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/full_prediction_main_results'
LABELS = dict(k0='K=0', raw_k3='Correct Raw K=3', k0_rubric='K=0 + Overall Rubric',
              wrong_k3_rubric='Wrong K=3 + Overall Rubric', correct_k3_rubric='Correct K=3 + Overall Rubric')
PAIRS = [('A','k0','raw_k3'), ('B','k0','k0_rubric'), ('C','k0_rubric','wrong_k3_rubric'),
         ('D','k0_rubric','correct_k3_rubric'), ('E','wrong_k3_rubric','correct_k3_rubric'),
         ('F','raw_k3','correct_k3_rubric')]
CONDITIONS = dict(k0='k0', raw_k3='correct_k3_no_rubric', k0_rubric='k0_overall_rubric',
                  wrong_k3_rubric='wrong_k3_overall_rubric', correct_k3_rubric='correct_k3_overall_rubric')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def reuse_functions(path, names, namespace):
    # 既存関数のASTをそのまま再利用。親moduleの推論関連importは実行しない。
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)


def read_rows(path, fields):
    with path.open(encoding='utf-8') as f:
        return pd.DataFrame([{k: r.get(k) for k in fields} for line in f if line.strip()
                             for r in [json.loads(line)]])


def score_valid(values):
    return values.map(lambda v: not isinstance(v, bool) and isinstance(v, (int, float))
                      and pd.notna(v) and v in (1,2,3,4,5))


def interpretation_notes():
    # 本データの検算済み結果に対する解釈。数値の詳細は直前の各表に示す。
    return [
        'Raw History（A）はQWKを改善し、その95% CIはゼロを跨がない。一方、AccuracyとMAEのCIはゼロを含むため、これらの改善を明確とは判断しない。',
        'Rubric単独（B）はAccuracyとMAEを改善するが、QWKは低下する。Score 3集中が強まるため、Accuracyだけでは性能を評価できない。Wrong履歴追加（C）はQWKを改善する一方、AccuracyとMAEを悪化させる。',
        '本人履歴＋Rubricは5条件中でAccuracy/QWKが最高、MAE/RMSEが最低である。EではAccuracy・MAE・QWKの改善方向に95% CIがゼロを跨がず、同一Rubric下で本人履歴の追加価値を支持する。ただしこのCIはtarget単位bootstrapに基づく。',
        'FでもAccuracy・MAE・QWKのCIは改善方向でゼロを跨がないが、Prompt指示文の差を含む関連的な改善であり、Rubricだけの因果効果とは解釈しない。',
        'History条件でも予測はScore 3に強く集中している。Correct＋RubricのGold分布とのTV距離はWrong＋Rubricより小さくないため、Correctの改善を分布拡大だけで説明することはできない。',
        'Correct＋Rubricのsame-essay方向再現率はWrong＋Rubricより高いが、Raw Historyより低い。Gold不一致の方向再現は限定的で、Gold一致pairにも予測不一致が生じる。集計指標の改善は個別採点者差の十分な再現を保証しない。',
    ]


def main():
    if OUT.exists():
        raise FileExistsError(f'既存outputの上書き禁止: {OUT}')
    source = ROOT/'outputs/full_prediction_experiment'
    raw = ROOT/'outputs/full_history_only_experiment'
    paths = {c: source/f'predictions_{c}.jsonl' for c in LABELS}
    paths['raw_k3'] = raw/'predictions_correct_k3_no_rubric.jsonl'
    manifest_path = source/'target_manifest.jsonl'
    pilot_path = ROOT/'outputs/rubric_rater_placebo/rubric_rater_placebo_summary.csv'
    raw_pilot_path = raw/'pilot_full_comparison.csv'
    code1 = ROOT/'src/recsaver/full_prediction_analysis.py'
    code2 = ROOT/'src/recsaver/full_history_only_analysis.py'
    config_path = raw/'resolved_config.yaml'
    inputs = list(paths.values())+[manifest_path, pilot_path, raw_pilot_path, code1, code2, config_path]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    ns = dict(np=np, pd=pd, itertools=itertools, COMPARISONS=PAIRS)
    reuse_functions(code1, ['qwk','distribution_entropy','table'], ns)
    reuse_functions(code2, ['bootstrap','same_essay_pairs'], ns)
    qwk, table = ns['qwk'], ns['table']
    config = {}
    for line in config_path.read_text().splitlines():
        if line.startswith(('bootstrap_seed:', 'bootstrap_repetitions:')):
            k,v = line.split(':'); config[k] = int(v)
    manifest = read_rows(manifest_path, ['target_id','source_row_id','target_rater','gold_overall'])
    assert not manifest.target_id.duplicated().any()
    assert not manifest.duplicated(['source_row_id','target_rater']).any()
    reference = manifest.set_index('target_id')
    frames, integrity, errors = {}, [], []
    for c,path in paths.items():
        f = read_rows(path, ['target_id','source_row_id','rater_id','condition','gold_overall','predicted_overall','parse_success'])
        duplicate = int(f.target_id.duplicated().sum())
        pair_duplicate = int(f.duplicated(['source_row_id','rater_id']).sum())
        f['prediction_valid'] = score_valid(f.predicted_overall)
        f['gold_valid'] = score_valid(f.gold_overall)
        f['valid'] = f.parse_success.eq(True) & f.prediction_valid & f.gold_valid
        identity_errors = 0
        gold_errors = 0
        for r in f.itertuples():
            if r.target_id not in reference.index:
                identity_errors += 1
                continue
            m = reference.loc[r.target_id]
            identity_errors += int(r.source_row_id != m.source_row_id or r.rater_id != m.target_rater
                                   or r.condition != CONDITIONS[c])
            gold_errors += int(pd.notna(r.gold_overall) and pd.notna(m.gold_overall) and r.gold_overall != m.gold_overall)
        integrity.append(dict(condition=c, original_rows=len(f), unique_target_keys=f.target_id.nunique(),
                              duplicate_target_keys=duplicate, duplicate_essay_rater_keys=pair_duplicate,
                              parse_success_rows=int(f.parse_success.eq(True).sum()),
                              missing_prediction_rows=int(f.predicted_overall.isna().sum()),
                              invalid_predicted_overall_rows=int((~f.prediction_valid & f.predicted_overall.notna()).sum()),
                              gold_available_rows=int(f.gold_overall.notna().sum()), valid_gold_rows=int(f.gold_valid.sum()),
                              valid_predictions=int(f.valid.sum()), gold_mismatch_rows=gold_errors,
                              identity_mismatch_rows=identity_errors))
        if duplicate or pair_duplicate or identity_errors or gold_errors:
            errors.append(c)
        frames[c] = f.set_index('target_id')
    print('INTEGRITY CHECK', json.dumps(integrity), flush=True)
    if errors:
        raise ValueError(f'集計前監査で停止: {errors}; Gold不一致・重複・identityを上記参照')
    common_set = set.intersection(*[set(f.index[f.valid]) for f in frames.values()])
    ids = [tid for tid in manifest.target_id if tid in common_set]
    assert ids
    audit = manifest.rename(columns={'target_id':'target_key'}).copy()
    audit['target_id'] = audit.target_key
    reasons = {tid: [] for tid in audit.target_key}
    for c,f in frames.items():
        audit[f'available_{c}'] = audit.target_key.isin(f.index[f.valid])
        for tid in audit.target_key:
            if tid not in f.index:
                reasons[tid].append(c+':missing_target')
            else:
                r = f.loc[tid]
                for fail,label in [(not r.parse_success == True,'parse_failure'),
                                   (pd.isna(r.predicted_overall),'missing_prediction'),
                                   (pd.notna(r.predicted_overall) and not r.prediction_valid,'invalid_prediction'),
                                   (not r.gold_valid,'invalid_or_missing_gold')]:
                    if fail: reasons[tid].append(c+':'+label)
    audit['included_in_common_set'] = audit.target_key.isin(common_set)
    audit['exclusion_reason'] = audit.target_key.map(lambda t: ';'.join(reasons[t]))
    common = {c: f.loc[ids].reset_index() for c,f in frames.items()}
    gold = common['k0'].gold_overall.to_numpy(int)
    for f in common.values():
        assert np.array_equal(f.gold_overall, gold)
    def metrics(c, f):
        p = f.predicted_overall.to_numpy(int); g = f.gold_overall.to_numpy(int)
        return dict(Condition=LABELS[c], N=len(g), Accuracy=float(np.mean(p==g)),
                    MAE=float(np.mean(abs(p-g))), RMSE=float(np.sqrt(np.mean((p-g)**2))), QWK=qwk(g,p))
    main_table = pd.DataFrame([metrics(c,f) for c,f in common.items()])
    by_c = dict(zip(LABELS, main_table.to_dict('records')))
    paired = []
    for name,a,b in PAIRS:
        delta = abs(common[a].predicted_overall.to_numpy()-gold)-abs(common[b].predicted_overall.to_numpy()-gold)
        paired.append(dict(comparison=name, from_condition=LABELS[a], to_condition=LABELS[b], N=len(ids),
                           **{m.lower()+'_delta':by_c[b][m]-by_c[a][m] for m in ['Accuracy','MAE','RMSE','QWK']},
                           improved=int((delta>0).sum()), unchanged=int((delta==0).sum()), worsened=int((delta<0).sum()),
                           mean_paired_ae_difference=float(delta.mean()), median_paired_ae_difference=float(np.median(delta))))
    print(f'Gold一致・重複なし。共通N={len(ids)}。Bootstrap開始 {config}', flush=True)
    ci = ns['bootstrap'](config, common)
    dist, collapse, gold_rows, gold_dist, raters = [], [], [], [], []
    gold_p = pd.Series(gold).value_counts(normalize=True).reindex(range(1,6),fill_value=0)
    for c,values in [('Gold',pd.Series(gold))]+[(c,f.predicted_overall) for c,f in common.items()]:
        counts = values.value_counts().reindex(range(1,6),fill_value=0)
        dist.extend(dict(Condition=LABELS.get(c,c), score=s, count=int(n), proportion=n/len(ids)) for s,n in counts.items())
        if c == 'Gold': continue
        collapse.append(dict(Condition=LABELS[c], most_frequent_score=int(counts.idxmax()),
                             most_frequent_score_ratio=counts.max()/len(ids), score_3_ratio=counts[3]/len(ids),
                             unique_predicted_scores=values.nunique(), prediction_entropy_bits=ns['distribution_entropy'](values),
                             total_variation_distance_from_gold=float(.5*abs(counts/len(ids)-gold_p).sum())))
        f = common[c]
        for s in range(1,6):
            part = f[f.gold_overall==s]
            gold_rows.append(dict(Condition=LABELS[c], gold_overall=s, N=len(part),
                                  Accuracy=(part.predicted_overall==s).mean(), MAE=abs(part.predicted_overall-s).mean()))
            gold_dist.extend(dict(Condition=LABELS[c], gold_overall=s, predicted_score=p, count=int(n),
                                  proportion=n/len(part) if len(part) else np.nan)
                             for p,n in part.predicted_overall.value_counts().reindex(range(1,6),fill_value=0).items())
        for r,part in f.groupby('rater_id'):
            raters.append(dict(Condition=LABELS[c], target_rater=r, N=len(part),
                               Accuracy=(part.predicted_overall==part.gold_overall).mean(),
                               MAE=abs(part.predicted_overall-part.gold_overall).mean(), mean_prediction=part.predicted_overall.mean(),
                               mean_gold=part.gold_overall.mean(), calibration_gap=part.predicted_overall.mean()-part.gold_overall.mean()))
    pairs = ns['same_essay_pairs'](common)
    pilot_source = pd.read_csv(pilot_path).set_index('condition')
    pilot_map = dict(k0='k0', k0_rubric='k0_with_rubric', wrong_k3_rubric='wrong_rater_k3_with_rubric', correct_k3_rubric='correct_rater_k3_with_rubric')
    pilot = []
    for c in LABELS:
        if c == 'raw_k3':
            r = pd.read_csv(raw_pilot_path).query("scope == 'pilot (user supplied)'").iloc[0]
            provenance = str(raw_pilot_path.relative_to(ROOT))+'; user supplied; rounded existing values'
        else:
            r = pilot_source.loc[pilot_map[c]].rename({'exact_accuracy':'accuracy'})
            provenance = str(pilot_path.relative_to(ROOT))
        pilot.append(dict(scope='Pilot', Condition=LABELS[c], N=int(r['n']), Accuracy=r.accuracy, MAE=r.mae,
                          RMSE=r.rmse, QWK=r.qwk, provenance=provenance))
        pilot.append(dict(scope='Full-scale common N', **by_c[c], provenance='main_5condition_results.csv'))
    integrity_df = pd.DataFrame(integrity)
    integrity_df['missing_from_5condition_intersection'] = integrity_df.valid_predictions-len(ids)
    integrity_df['common_N'] = len(ids)
    targets = manifest.set_index('target_id').loc[ids].reset_index()
    targets.insert(0,'target_key', targets.target_id)
    for c,f in common.items(): targets['prediction_'+c] = f.predicted_overall.to_numpy(int)
    outputs = {'intersection_audit':audit, 'common_targets':targets, 'integrity_audit':integrity_df,
               'main_5condition_results':main_table, 'paired_comparisons':pd.DataFrame(paired), 'bootstrap_ci':ci,
               'prediction_distribution_common':pd.DataFrame(dist), 'score_collapse_summary':pd.DataFrame(collapse),
               'gold_score_summary':pd.DataFrame(gold_rows), 'gold_score_prediction_distribution':pd.DataFrame(gold_dist),
               'rater_summary':pd.DataFrame(raters), 'same_essay_pair_analysis':pairs, 'pilot_full_comparison':pd.DataFrame(pilot)}
    assert all(digest(ROOT/p)==h for p,h in hashes.items()), 'Input changed during analysis'
    assert len(outputs['rater_summary']) == 5*manifest.target_rater.nunique()
    OUT.mkdir()
    for name,f in outputs.items(): f.to_csv(OUT/(name+'.csv'), index=False)
    lines = ['# Full-scale Prediction Main Results：5条件共通N',
             '## Common target construction',
             f'共通N = {len(ids):,}。manifestの{len(manifest):,} target中、除外{len(manifest)-len(ids)}件。Gold不一致0件、重複key 0件。',
             'target_idを使用し、manifestのsource_row_id（essay）×target_raterとの一対一対応を全条件で検証した。'
             '保存済みparse_successがtrue、predictionとGoldが整数1〜5のtargetだけを共通集合に採用。raw出力の再parseは行わない。',
             'Valid predictionsはparse成功・prediction有効・Gold有効の件数。Missing from intersectionは各条件Valid N − Common N。',
             table(integrity_df), '除外targetと理由：', table(audit[~audit.included_in_common_set]),
             '## Main 5-condition results', table(main_table),
             '## Paired comparisons', '差の向き：Accuracy/MAE/RMSE/QWK deltaはto − from。paired AE differenceはfrom − to（正が改善）。improved/worsenedは絶対誤差の減少/増加。', table(outputs['paired_comparisons']),
             '## Bootstrap CI', f'既存full_history_only_analysis.bootstrapを関数本体の変更なしで再利用し、比較リストのみA〜Fに指定。seed={config["bootstrap_seed"]}、{config["bootstrap_repetitions"]}回、target単位paired percentile 95% CI。',
             '同じdrawで全条件を再標本化。これはCI計算用の再標本化であり、実験target/historyの再選択ではない。同一essay内の依存、生成・History drawの不確実性は含めず、多重比較補正は行っていない。', table(ci),
             '## Prediction distribution', table(outputs['prediction_distribution_common']),
             '## Score collapse', 'entropyはlog2（bits）。TV距離はGoldとの比率差の絶対値合計の1/2。', table(outputs['score_collapse_summary']),
             '## Gold-score analysis', table(outputs['gold_score_summary']), '全Gold別予測分布はgold_score_prediction_distribution.csvに保存。',
             '## Rater-level analysis', 'calibration gap = mean prediction − mean Gold。採点者別の記述統計であり、平均差だけでbiasとは断定しない。', table(outputs['rater_summary']),
             '## Same-essay analysis', '既存same_essay_pairs関数を再利用。common set内の同一source_row_id・異なるraterの非順序pairを対象とする。方向再現率の分母はGold不一致pair全体（予測同点も不正解）。Gold一致時の予測不一致率の分母はGold一致pair全体。', table(pairs),
             '## Pilot vs Full-scale', 'Pilotは既存値をそのまま転載。Raw K3は既存CSVのuser supplied値（丸め済み）。samplingが異なるため、研究経緯を示す記述的併記のみで、Pilot対Full-scaleの統計比較は行わない。', table(outputs['pilot_full_comparison']),
             '## Interpretation notes',
             '以下は上記の事実に対する解釈である。AはRaw History追加の比較、BはRubric単独追加、Cはwrong-rater履歴追加、Dは本人履歴追加、Eは同一Rubric下の比較的クリーンなpersonalization比較、FはCorrect History下のRubric-associated improvementである。',
             'FではPrompt指示文にも差があるため、Rubricだけの純粋な因果効果とは断定できない。',
             '## Reproducibility', '既存入力のSHA-256、環境、bootstrap設定をmetadata.jsonに保存。GPU推論・model loading・予測再生成・retry・parser/Prompt変更・history/実験targetのresampling・dataset変更・既存output上書き・git commit/pushは実施していない。']
    # データから解釈の数値を構築し、過去reportの結論は転記しない。
    notes = []
    for p in paired:
        notes.append(f'比較{p["comparison"]}: Accuracy差 {p["accuracy_delta"]:+.6f}、MAE差 {p["mae_delta"]:+.6f}、QWK差 {p["qwk_delta"]:+.6f}。指標別の方向と上記CIを併読する。')
    notes.extend(interpretation_notes())
    lines[lines.index('## Reproducibility'):lines.index('## Reproducibility')] = notes
    (OUT/'report.md').write_text('\n\n'.join(lines)+'\n', encoding='utf-8')
    metadata = dict(common_target_count=len(ids), manifest_target_count=len(manifest), excluded_target_count=len(manifest)-len(ids),
                    gold_mismatch_count=0, duplicate_key_count=0, condition_audit=integrity,
                    input_sha256=hashes, inputs_unchanged=True, script_sha256=digest(Path(__file__)),
                    bootstrap=config, bootstrap_implementation='full_history_only_analysis.bootstrap (unchanged AST function; A-F comparisons)',
                    target_order='manifest order', target_identity='target_id, verified one-to-one with source_row_id x target_rater',
                    inference_performed=False, python=sys.version, executable=sys.executable, platform=platform.platform(),
                    numpy=np.__version__, pandas=pd.__version__, created_utc=pd.Timestamp.now(tz='UTC').isoformat())
    (OUT/'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(main_table.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
