"""Pilotの実測値とAIによる予備確認を追記。人手評価は代替しない。"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.recsaver import rater_tendency_joint_mvp_1000 as ex

out = Path(__file__).resolve().parent
ex.analyze()
rows = ex.records()
pilot = pd.read_csv(out / 'pilot_targets.csv')
assert len(rows) == 30 and set(rows) == set(pilot.target_id)
frame = ex.previous.data()
manifests = {r['target_id']:r for r in ex.read(out / 'target_history_manifest.jsonl')}
baseline = {r['target_id']:r for r in ex.read(out / 'baseline_A.jsonl')}
attempts = [a for r in rows.values() for a in r['attempts']]
tokens = [a['output_tokens'] for a in attempts]
valid = [r for r in rows.values() if r['parse_success']]
# Negative schema checks: fabricated citation and bool score must be rejected.
sample = valid[0]
value = {k:sample[k] for k in ('predicted_overall','rater_tendency','reasoning')}
for invalid in [dict(value, predicted_overall=True), dict(value, rater_tendency=dict(value['rater_tendency'], supporting_history_ids=['invented']))]:
    try:
        ex.parse(json.dumps(invalid), sample['history_ids'])
    except AssertionError:
        pass
    else:
        raise AssertionError('Invalid schema was accepted')
references = ex.read(ex.ROOT / 'outputs/reasoning_eval_v1/verified_reference_pool.jsonl')
overlap = [r for r in references if r['target_id'] in manifests]
matching = [r for r in overlap if r['history_ids'] == manifests[r['target_id']]['correct_history_ids']]
notes = {
    '7497:1': '傾向とEssay evidenceがRubricの一般的表現に近く、固有の本文根拠が弱い。',
    '6168:2': '未知の対象Traitを3–4程度と推測して説明している。Gold入力ではないが、根拠としての妥当性に注意。',
    '4163:2': '具体的な単語を挙げる比較的具体的な例。ただし綴りの誤りをgrammar等と混同していないか要確認。',
    '8814:1': 'Generic_Cityという匿名化表記を不自然さとして扱っており、匿名化処理への誤反応が疑われる。',
    '1637:1': '引用した英文をinaccuraciesと呼ぶが、引用自体がどの誤りを示すのか不明確。'}
table = ['| target_id | Gold | A | A\' | 生成された評価傾向 | 新しい採点理由 | 気になる点 |',
         '|---|---:|---:|---:|---|---|---|']
for tid, note in notes.items():
    r = rows[tid]
    text = ' / '.join(r['reasoning'][k] for k in ex.FIELDS)
    table.append('| ' + ' | '.join(str(x).replace('|','／').replace('\n',' ') for x in
                 [tid, int(frame.loc[tid,'Overall']), baseline[tid]['predicted_overall'], r['predicted_overall'],
                  r['rater_tendency']['description'], text, note]) + ' |')
summary = f'''## Pilot完了時の確認

30件実行、schema有効 {len(valid)}/30。出力token min/median/max={min(tokens)}/{np.median(tokens):g}/{max(tokens)}。
length終了={sum(a['finish_reason']=='length' for a in attempts)}/{len(attempts)} attempts。
retry総数={sum(r.get('retry_count',0) for r in rows.values())}。
不正な履歴ID・bool型scoreの拒否もCPUチェック済み。

生成されたA'のscore分布: {dict(pd.Series([r['predicted_overall'] for r in valid]).value_counts().sort_index())}。
「insufficient evidence」の文言は不確実性の留保としても使われるため、その出現率を「傾向推定を断念した率」と同一視できない。

### 推奨と停止点

現行Promptのまま1,000件へ進むことは推奨しない。下記のAI予備確認では一般的なRubric表現の反復、具体的根拠の弱さ、匿名化表記への反応が見られる。
Prompt改訂候補は、履歴の具体的な対照例と記録済みscoreの対応を求め、本文から短い引用で根拠を示し、匿名化placeholderを言語誤りに数えないと明記すること。
改訂版は別ファイル・別出力先で30件を再実行し、現行の失敗例も保持して比較する。
今回のmax_tokens=768は切断検査の実測に基づいて検討する。512は未検証であり確定設定とはしない。
入力K=3・temperature=.2・top_p=.8・max_model_len=8192は維持する。
ここで停止。本実験の最終Promptは未確定、承認前にfullを実行しない。

### 代表5例（AIによる予備確認。人手評価ではない）

''' + '\n'.join(table) + f'''

### Rec-SAVER参照の照合

既存verified_reference_poolとのtarget重複は {len({r['target_id'] for r in overlap})} 件、そのうちhistory IDsが順序も含め一致するtargetは {len({r['target_id'] for r in matching})} 件。
参照の生成元はoutputs/overall_rubric_ablationであり、対象と履歴の一致だけで全面再利用可能とは断定できない。Rubric/本文/参照生成条件のhash照合を追加して採否を判断する。
既存評価値の転記は行っていない。新規比較時はreasoningの3要素のみ文章化し、tendencyを含むJSON全体は比較しない。
追加所要時間は未実測。新規参照が必要な対象数と検証retry数を確定し、小規模実測後に見積もる。
'''
for name in ['pilot_report.md','report.md','reasoning_review_examples.md']:
    with (out / name).open('a', encoding='utf-8') as stream:
        stream.write('\n\n' + summary)
ex.status('git_status_after')
print(summary.split('### 代表5例')[0])
print((out / 'prediction_summary.csv').read_text())
