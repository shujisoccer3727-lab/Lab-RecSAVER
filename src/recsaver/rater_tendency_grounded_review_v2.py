"""引用の機械的一致を内容評価と区別して記録し、v1/v2比較を保存。"""
import json
import re
import numpy as np
import pandas as pd
from . import rater_tendency_grounded_pilot_v2 as revision


def quotes(text):
    return [next(s for s in match if s) for match in re.findall(r'"([^"\n]+)"|“([^”\n]+)”|(?<!\w)\x27((?:[^\x27\n]|(?<=\w)\x27(?=\w))+)\x27(?!\w)', text)]


def main():
    revision.setup()
    core, out = revision.core, revision.OUT
    core.analyze()
    rows = core.records()
    assert len(rows) == 30, 'Wait for all pilot targets'
    old = {r['target_id']:r for r in core.read(revision.SOURCE / 'predictions.jsonl')}
    frame = core.previous.data()
    audit, details = [], []
    for tid, row in rows.items():
        if not row['parse_success']:
            continue
        target_quotes = quotes(row['reasoning']['essay_evidence'])
        history_quotes = quotes(row['rater_tendency']['description'])
        target_text = str(frame.loc[tid, 'Text'])
        history_texts = [str(frame.loc[h, 'Text']) for h in row['history_ids']]
        matched = [q for q in target_quotes if q in target_text]
        hmatched = [q for q in history_quotes if any(q in t for t in history_texts)]
        audit.append({'target_id':tid, 'target_quotes_detected':len(target_quotes),
                      'target_quotes_exact':len(matched), 'target_quotes_unmatched':json.dumps([q for q in target_quotes if q not in target_text]),
                      'history_quotes_detected':len(history_quotes), 'history_quotes_exact':len(hmatched),
                      'history_quotes_unmatched':json.dumps([q for q in history_quotes if q not in hmatched])})
        details.extend([f'## {tid}', '### v1', json.dumps({k:old[tid][k] for k in ['predicted_overall','rater_tendency','reasoning']}, ensure_ascii=False, indent=2),
                        '### v2', json.dumps({k:row[k] for k in ['predicted_overall','rater_tendency','reasoning']}, ensure_ascii=False, indent=2),
                        '### history recorded scores', json.dumps([{ 'id': h, 'overall':int(frame.loc[h,'Overall'])} for h in row['history_ids']]),
                        '本文・過去履歴・Rubric・全入出力はreasoning_review_examples.mdを参照。人手評価: 未実施。'])
    audit = pd.DataFrame(audit)
    audit.to_csv(out / 'quotation_audit.csv', index=False)
    (out / 'v1_v2_review.md').write_text('\n\n'.join(details), encoding='utf-8')
    ids = sorted(t for t,r in rows.items() if r['parse_success'] and old[t]['parse_success'])
    gold = frame.loc[ids,'Overall'].to_numpy()
    comparison = []
    baseline = {r['target_id']:r for r in core.read(out / 'baseline_A.jsonl')}
    for label, source in [('A',baseline),('A_prime_v1',old),('A_prime_grounded_v2',rows)]:
        comparison.append({'Condition':label,'N':len(ids), **core.previous.metrics(gold,np.array([source[t]['predicted_overall'] for t in ids]))})
    pd.DataFrame(comparison).to_csv(out / 'v1_v2_prediction_comparison.csv', index=False)
    attempts = [a for r in rows.values() for a in r['attempts']]
    tokens = [a['output_tokens'] for a in attempts]
    summary = f'''# Grounded v2 Pilot実測結果

実行30件、有効JSON/schema={sum(r['parse_success'] for r in rows.values())}/30。
max_tokens=768、temperature=.2、top_p=.8、K=3、max_model_len=8192、同じ30件・履歴・生成seedを維持。
実際のPrompt: prompts/en/rater_tendency_joint_prediction_grounded_v2.txt。
実装: src/recsaver/rater_tendency_grounded_pilot_v2.py setup/main、旧実装のrun/render/parseを再利用。
変更: 対象Essayから2つ以上の短い正確な引用、履歴本文の引用とID・記録Overallの対応、匿名化placeholderの中立扱い。

出力tokens min/median/max={min(tokens)}/{np.median(tokens):g}/{max(tokens)}。
length終了attempt数={sum(a['finish_reason']=='length' for a in attempts)}/{len(attempts)}。
retry数={sum(r.get('retry_count',0) for r in rows.values())}。

機械的引用検査: 対象本文に完全一致する引用が2つ以上={int((audit.target_quotes_exact>=2).sum())}/30。
履歴本文に完全一致する引用が1つ以上={int((audit.history_quotes_exact>=1).sum())}/30。
一致しない引用が含まれる対象数={int(((audit.target_quotes_detected>audit.target_quotes_exact)|(audit.history_quotes_detected>audit.history_quotes_exact)).sum())}/30。
引用記号で抽出して文字列一致を調べた値であり、根拠として適切か、採点傾向を裏付けるかの判定ではない。
全30件のv1/v2比較はv1_v2_review.md、全入力はreasoning_review_examples.md。
スコア比較はv1_v2_prediction_comparison.csv、対Aのpaired bootstrap CIはpaired_comparison.csv。
旧Prompt・旧予測はSHA256照合により保持確認済み。Gold不入力等の検査は継承し、入力部分も旧条件と同一。
構造評価と内容の正しさを区別する。人手評価は未実施。30件の結果を1,000件での有効性と解釈しない。
本実験は未実行。Pilot後の承認待ち。
'''
    (out / 'grounded_v2_report.md').write_text(summary, encoding='utf-8')
    comments = {
        '7497:1': '対象引用は具体化したが、descriptionで根拠不足としつつconnectionで傾向を推論する不整合が残る。',
        '6168:2': '対象の具体的引用はある。履歴IDとscoreを示す一方、履歴本文の直接引用はない。',
        '4163:2': '本文の2つの具体例に基づく説明へ変化。誤りの特定・通信への影響の説明はなお曖昧。',
        '8814:1': '前回のGeneric_Cityへの否定的言及は消え、具体的な本文例と長所も示す。履歴scoreとの整合性は要確認。',
        '1637:1': '文法的に成立するthey might have an accident due to the weatherを誤りとし、weather conditionsへの変更を要求する問題が残る。'}
    table = ['## 代表5例（AIによる予備確認。人手評価ではない）',
             '| target_id | Gold | A | v1 | v2 | 評価傾向 | 新しい採点理由 | 気になる点 |',
             '|---|---:|---:|---:|---:|---|---|---|']
    for tid, note in comments.items():
        r = rows[tid]
        if not r['parse_success']:
            continue
        table.append('| ' + ' | '.join(str(v).replace('|','／').replace('\n',' ') for v in
                    [tid, int(frame.loc[tid,'Overall']), baseline[tid]['predicted_overall'], old[tid]['predicted_overall'],
                     r['predicted_overall'], r['rater_tendency']['description'],
                     ' / '.join(r['reasoning'][k] for k in core.FIELDS), note]) + ' |')
    summary += '\n\n' + '\n'.join(table)
    summary += '''

## 判断と推奨

AccuracyはA=56.7%、v1=60.0%、v2=53.3%。同じ30件でv1より2件正解が少なく、既存Aより1件少ない。予測性能の改善は確認できない。
対象Essayの引用は増えた一方、履歴本文の直接引用要求は満たされず、採点者傾向の根拠の弱さと、正しい英文を誤りとする例が残る。
匿名化については8814:1で前回のGeneric_Cityへの否定的言及が消えた。全件で匿名化に中立になったとする人手検証は未実施。
引用の非一致数には提案された修正文や句読点の違いも含み得るため、捏造引用数と同一視しない。
推奨設定は現行比較の再現用としてtemperature=.2、top_p=.8、max_tokens=768、max_model_len=8192を維持。
今回の最大出力は480 tokensだが、512の十分性は未実測。出力を変更して性能を補正していない。
本実験への移行は保留を推奨。次は同一30件の人手確認、または履歴引用と根拠不足時の接続をさらに明確にする別版の検証。
'''
    (out / 'grounded_v2_report.md').write_text(summary, encoding='utf-8')
    for filename in ['pilot_report.md','report.md']:
        with (out / filename).open('a',encoding='utf-8') as stream:
            stream.write('\n\n' + summary)
    core.status('git_status_after')
    print(summary)
    print(pd.DataFrame(comparison).to_string(index=False))


if __name__ == '__main__':
    main()
