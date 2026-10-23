"""Read saved results only; publish complete tables and unedited output examples."""
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def records(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def table(frame):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    return '| ' + ' | '.join(map(cell, frame.columns)) + ' |\n| ' + ' | '.join(['---'] * len(frame.columns)) + ' |\n' + ''.join(
        '| ' + ' | '.join(map(cell, row)) + ' |\n' for row in frame.itertuples(index=False, name=None))


def main():
    summary = pd.read_csv(OUT / 'condition_summary.csv')
    main = summary.loc[summary.scope.eq('common_all_seven')].copy()
    assert len(main) == 7 and main.N.eq(1000).all()
    conditions = main.condition.tolist()
    predictions = {c: records(OUT / 'predictions' / (c + '.jsonl')) for c in conditions}
    target_frame = pd.read_csv(OUT / 'common_targets_1000.csv')
    ids = target_frame.target_id.tolist()
    gold = target_frame.set_index('target_id').gold_overall.to_dict()
    profiles = {r['rater_id']: r for r in records(OUT / 'profiles/rater_profiles.jsonl')}
    essays = pd.read_csv(ROOT / 'data/processed/rater_essay_wide.csv', low_memory=False)
    essays['target_id'] = essays.source_row_id.astype(str) + ':' + essays.rater_position.astype(str)
    essays = essays.set_index('target_id', drop=False)
    by_id = {}
    for c, rows in predictions.items():
        assert len(rows) == 1000 and len({r['target_id'] for r in rows}) == 1000
        assert {r['target_id'] for r in rows} == set(ids)
        assert all(r['parse_success'] and r['gold_overall'] == gold[r['target_id']] for r in rows)
        by_id[c] = {r['target_id']: r for r in rows}
    # Stable selection; not chosen for good performance.
    first = ids[0]
    different = next(t for t in ids if len({by_id[c][t]['predicted_overall'] for c in conditions}) > 1)
    examples = []
    md = ['# 同一Essayに対する各手法の実出力\n',
          '選択規則：固定manifest先頭のtargetと、条件間の予測が異なる最初のtarget。性能が良いtargetを選ぶ規則ではない。英文は保存済み出力そのまま。\n']
    for tid in dict.fromkeys([first, different]):
        target = essays.loc[tid]
        md += [f'## Target {tid}; rater={target.rater_id}; Gold Overall={gold[tid]}\n',
               '### Essay本文\n', str(target.Text) + '\n']
        for c in conditions:
            row = by_id[c][tid]
            value = {key: row[key] for key in ['predicted_overall', 'rater_tendency', 'reasoning', 'used_profile_tendencies'] if key in row}
            md += [f'### {c}\n', '```json\n' + json.dumps(value, ensure_ascii=False, indent=2) + '\n```\n']
            examples.append({'target_id': tid, 'target_rater': target.rater_id, 'gold_overall': gold[tid],
                             'condition': c, **value})
        for rater in [target.rater_id, by_id[conditions[-1]][tid]['profile_rater']]:
            md += [f'### 使用Profile: {rater}\n', '```json\n' + json.dumps(profiles[rater]['profile'], ensure_ascii=False, indent=2) + '\n```\n']
    (OUT / 'prediction_output_examples.md').write_text('\n'.join(md), encoding='utf-8')
    (OUT / 'prediction_output_examples.json').write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding='utf-8')
    similarity = pd.read_csv(OUT / 'profiles/profile_similarity.csv')
    stability = pd.read_csv(OUT / 'profiles/joint_profile_stability.csv')
    pair_n = stability.N * (stability.N - 1) / 2
    strings = [json.dumps(p['profile'], sort_keys=True, ensure_ascii=False) for p in profiles.values()]
    diagnostic = {
        'profile_n': len(profiles), 'distinct_exact_profiles': len(set(strings)),
        'between_rater_profile_tfidf': {'pairs': len(similarity), 'mean': float(similarity.tfidf_cosine.mean()),
            'min': float(similarity.tfidf_cosine.min()), 'max': float(similarity.tfidf_cosine.max())},
        'joint_within_rater_tfidf': {'raters_with_at_least_2_targets': len(stability), 'pairs': int(pair_n.sum()),
            'pair_weighted_mean': float(np.average(stability.mean_within_rater_cosine, weights=pair_n)),
            'rater_mean_range': [float(stability.mean_within_rater_cosine.min()), float(stability.mean_within_rater_cosine.max())]},
        'profile_history_score_counts': {r: {str(int(k)): int(v) for k, v in essays.loc[p['history_ids'], 'Overall'].value_counts().sort_index().items()}
                                        for r, p in profiles.items()},
        'example_selection': {'manifest_first': first, 'first_disagreement': different},
        'gold_distribution': {str(int(k)): int(v) for k, v in target_frame.gold_overall.value_counts().sort_index().items()},
    }
    (OUT / 'profile_analysis_summary.json').write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding='utf-8')
    citations = []
    for rater, record in profiles.items():
        for reference in sorted(set(re.findall(r'\b\d+:[12]\b', json.dumps(record['profile'])))):
            citations.append({'rater_id': rater, 'cited_history_id': reference,
                'in_selected_history': reference in record['history_ids'],
                'actual_overall': int(essays.loc[reference, 'Overall']) if reference in essays.index else None})
    pd.DataFrame(citations, columns=['rater_id', 'cited_history_id', 'in_selected_history', 'actual_overall']).to_csv(OUT / 'profiles/profile_citation_audit.csv', index=False)
    review = ['# Profile grounding補足：限定的な目視照合、正解Profileの判定ではない\n',
              '選択：rater_1 / rater_10 / rater_11（ID順の先頭3名）。全20件の本文はprofile_examples_for_manual_review.md参照。'
              '履歴の単純なスコア頻度と生成記述の整合、Grammar/Vocabularyへの断定に対する具体的な反例候補を示す。\n']
    for rater in ['rater_1', 'rater_10', 'rater_11']:
        p = profiles[rater]
        review += [f'## {rater}\n', 'Observed Overall counts: ' + json.dumps(diagnostic['profile_history_score_counts'][rater]) + '\n',
            'Overall claim: ' + p['profile']['overall_scoring_tendency'] + '\n',
            'Grammar claim: ' + p['profile']['evaluation_aspects']['grammar'] + '\n',
            'Vocabulary claim: ' + p['profile']['evaluation_aspects']['vocabulary'] + '\n']
        high = essays.loc[p['history_ids']].query('Overall >= 4')
        for h in high.head(2).itertuples():
            review += [f'### 高得点でも誤りを含み得る例: {h.target_id}; Overall={int(h.Overall)}\n', str(h.Text)[:1800] + '\n']
    review += ['## 明確な記述上の不整合\nrater_1 Profileは「2と4が多く、3は少ない」と述べるが、実履歴20件は2=7、3=7、4=6件。'
               'この頻度の説明は履歴と整合しない。profileのPrediction utilityが正でも、個々の記述が正しいことを意味しない。'
               '同ProfileはPhraseologyを重視すると述べつつ、uncertaintiesではPhraseologyの基準は根拠不足としており、記述間の緊張もある。\n',
               '## 限界\n採点者間で共通Essayを統制していない20件から「このraterだけがGrammarを重視する」とは判定できない。'
               '文法誤りが残る高得点例は、単純な「誤りが少ないほど高い」という言い換えへの反例候補になる。'
               'Profile内にhistory IDや引用がない記述では根拠との対応を自動検証できない。因果的な重み・真の方針とは解釈しない。\n']
    (OUT / 'profiles/profile_grounding_observations.md').write_text('\n'.join(review), encoding='utf-8')
    base = (OUT / 'report.md').read_text(encoding='utf-8')
    marker = '\n## 最終結果の解釈と出力例\n'
    base = base.split(marker)[0]
    base = base.replace('## 現在の指標（available_onlyは7条件比較に使用不可）', '## 全条件の最終指標（主比較はcommon_all_seven）')
    base = base.replace('未実行条件の分布は未取得。', '全条件の分布を取得済み。')
    base = base.replace('全7条件共通結果が揃うまではTrait-free本人履歴の優位性、Joint Profileの影響、Two-stage Profile utilityは判断できない。',
                        '全7条件の同一1,000 targetで最終比較を行った。具体的な解釈は以下に示す。')
    concise = main[['condition', 'N', 'Accuracy', 'MAE', 'RMSE', 'QWK']].copy()
    for k in ['Accuracy', 'MAE', 'RMSE', 'QWK']:
        concise[k] = concise[k].map(lambda x: f'{x:.4f}')
    distribution = pd.read_csv(OUT / 'prediction_distribution.csv').query('scope == "common_all_seven"')
    dist = distribution.pivot(index='condition', columns='score', values='count').reindex(conditions)
    dist.columns = [f'Score {c} count' for c in dist.columns]
    dist['Score 3 %'] = distribution.query('score == 3').set_index('condition').percentage
    ci = pd.read_csv(OUT / 'paired_bootstrap_ci.csv')
    compact_ci = []
    for (left, right), group in ci.groupby(['left', 'right'], sort=False):
        row = {'差の向き': left + ' − ' + right}
        for k in ['Accuracy', 'MAE', 'RMSE', 'QWK']:
            r = group.loc[group.metric.eq(k)].iloc[0]
            multiplier = 100 if k == 'Accuracy' else 1
            row[k + (' (pp)' if k == 'Accuracy' else '')] = f'{r.difference * multiplier:+.3f} [{r.ci_lower * multiplier:+.3f}, {r.ci_upper * multiplier:+.3f}]'
        compact_ci.append(row)
    append = [marker, table(concise), '\n### 主要6比較：差と95% paired bootstrap CI\n', table(pd.DataFrame(compact_ci)),
        '\nAccuracyはpercentage points、MAE/RMSEはscore単位、QWKは係数差。個別95% CIであり、多重比較補正なし。\n',
        '1. **Trait除去（B本人−A）**：Accuracy −4.0pp、MAE +0.064。QWK差のCIは0を含む。Aより同等とは言えない。共通Trait定義をBに追加しており、純粋なTrait除去だけの差ではない。\n',
        '2. **Trait-free本人−他者履歴**：Accuracy +3.1pp、MAE −0.038、RMSE −0.033。これらの個別CIは0を含まない。QWK +0.036のCIは0を含む。本人履歴固有の予測情報が残る可能性を支持する。\n',
        '3. **Trait-free本人−履歴なし**：Accuracy −4.1pp、MAE +0.057、RMSE +0.058だがQWK +0.159。履歴の追加価値を全指標で支持する結果ではない。履歴なしはScore 3が93.5%に集中する。共通Trait定義の有無も異なる。\n',
        '4. **Joint−Direct本人**：Accuracy −1.6pp、MAE +0.008、RMSE −0.005はCIが0を含む。QWK −0.0448のCIは0を含まない。Jointでの改善は確認できず、QWKは低下した。\n',
        '5. **本人−他者Profile**：Accuracy +3.0pp、MAE −0.036、RMSE −0.033、QWK +0.0836。4指標の個別CIはすべて0を含まず、Profileの採点者固有の予測utilityを支持する。真の方針の同定ではない。\n',
        '6. **本人Profile−Direct本人**：Accuracy +5.7pp、MAE −0.083、RMSE −0.089は改善。QWK +0.0282のCIは0を含む。ProfileはK=20、DirectはK=3であり、圧縮・言語化そのものの効果と履歴件数の効果を切り分けられない。\n',
        '\n### 予測分布（N=1,000なので各count÷10が%）\n', table(dist.reset_index()),
        '\nGold distribution: ' + json.dumps(diagnostic['gold_distribution']) + '\n',
        'D本人はB本人よりScore 3が71.0%→80.5%へ増えるが、QWKは0.3327→0.3609で、点推定では「MAE改善とQWK低下」の組合せではない。ただしQWK差のCIは0を含む。'
        'D本人と他者では本人の方がScore 3集中が低く、QWKも高い。全条件でScore 5予測が0件、DはScore 1も0件で、両端scoreの予測不足が残る。\n',
        '\n### Profile多様性・Joint安定性\n',
        json.dumps({k: v for k, v in diagnostic.items() if k in ['profile_n', 'distinct_exact_profiles', 'between_rater_profile_tfidf', 'joint_within_rater_tfidf']}, ensure_ascii=False, indent=2),
        '\n27 Profileに完全一致はないが、TF-IDFは表層的語彙類似度であり、generic rubric paraphraseでないことの証明にはならない。'
        'Profileのschemaキーも類似度計算に含む。同rater内のJoint傾向の類似度は低いが、targetごとにK=3履歴も異なるためtarget依存と履歴依存を分離できない。1件しかないrater_25はwithin-rater評価不能。\n',
        '\n### 実際の出力例\n同一targetの全7条件の英文JSONとEssay全文は[prediction_output_examples.md](prediction_output_examples.md)に保存。'
        f'先頭target={first}（Gold={gold[first]}）は全7条件が3と予測し不正解だった。これは改善例だけを選ばないための固定規則による例。\n',
        'Profileの3例と根拠・反例候補は[profile_grounding_observations.md](profiles/profile_grounding_observations.md)、全20履歴は[manual review](profiles/profile_examples_for_manual_review.md)。'
        '出力はモデルが述べた説明であり、説明の忠実性・妥当性のGoldはない。\n',
        '**実際に見つかったgrounding問題**：rater_1の「2と4が多く3は少ない」という説明は、実際の20件（2=7、3=7、4=6）と不整合。'
        'Profileは予測に有用でも、文章の事実性が保証されるわけではない。例を除外・再生成して改善はしていない。\n',
        f'Profile内で明示されたhistory IDは{len(citations)}参照、選択履歴外のIDは{sum(not c["in_selected_history"] for c in citations)}参照。'
        'IDの実在・履歴内包含の検査であり、Traitの重要性や引用したEssayの解釈が正しいことを保証しない。\n']
    for rater in ['rater_1', 'rater_10', 'rater_15']:
        append += [f'\n#### Profile例：{rater}\n', '```json\n' + json.dumps(profiles[rater]['profile'], ensure_ascii=False, indent=2) + '\n```\n']
    append += ['\n### Gitと保存状態\n実験前から3 tracked filesがmodified。途中のsnapshotでは.gitignoreもmodifiedとして現れたが、最終確認では現れていない。'
               '本実験の編集操作では.gitignoreを変更・復元していない。git_status_before.txtは出力先ディレクトリ作成直後の記録である。'
               '今回の編集対象は新規experiment script、4つの新規prompt、今回専用outputディレクトリ内のファイル。\n']
    (OUT / 'report.md').write_text(base + '\n'.join(append), encoding='utf-8')
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
