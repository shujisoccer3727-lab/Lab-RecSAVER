"""本実験集計を検証し、発表候補の未編集出力と元資料を保存する。"""
import json
import numpy as np
import pandas as pd
from src.recsaver import rater_tendency_grounded_pilot_v2 as rev
from src.recsaver.rater_tendency_grounded_review_v2 import quotes
from src.recsaver.history import format_history

rev.setup()
core, out = rev.core, rev.OUT
rows = core.records()
assert len(rows) == 1000
frame = core.previous.data()
targets = pd.read_csv(out / 'target_manifest.csv').set_index('target_id')
assert set(rows) == set(targets.index)
baseline = {r['target_id']:r for r in core.read(out / 'baseline_A.jsonl')}
valid = {t:r for t,r in rows.items() if r['parse_success']}
for tid,r in valid.items():
    assert core.parse(r['attempts'][-1]['raw'],r['history_ids'])['predicted_overall'] == r['predicted_overall']
for source,label in [(baseline,'A'),(valid,"A'")]:
    ids = sorted(valid)
    actual = core.previous.metrics(targets.loc[ids].gold_overall.to_numpy(),np.array([source[t]['predicted_overall'] for t in ids]))
    saved = pd.read_csv(out / 'prediction_summary.csv').set_index('Condition').loc[label]
    assert all(np.isclose(actual[k],saved[k]) for k in actual)
attempts = [a for r in rows.values() for a in r['attempts']]
tokens = [a['output_tokens'] for a in attempts]
audit = []
for tid,r in valid.items():
    tq = quotes(r['reasoning']['essay_evidence'])
    hq = quotes(r['rater_tendency']['description'])
    tm = [q for q in tq if q in str(frame.loc[tid,'Text'])]
    hm = [q for q in hq if any(q in str(frame.loc[h,'Text']) for h in r['history_ids'])]
    audit.append({'target_id':tid,'target_quotes_exact':len(tm),'history_quotes_exact':len(hm)})
audit = pd.DataFrame(audit)
audit.to_csv(out / 'full_quotation_audit.csv',index=False)
examples = ['# 発表用候補と照合資料',
            '選定はAIによる予備確認。独立した人手評価ではない。正解例を選んだ目的抽出であり、平均的な品質を代表しない。生成文は編集せず保存。日本語の紹介文は要約である。',
            '## 第一候補: 4816:2',
            '過去の2点・4点の事例と対象Essayの誤り／伝達可能な内容を結びつけ、3点を予測する出力形式の説明に向く。引用と記録スコアは元データで確認する。ただし「単純な文だから低い」という説明やRubricに近い傾向記述が残るため、完全に妥当な採点理由の成功例とは呼ばない。',
            '## 第二候補: 3453:1',
            'postivite、unsussecfulなどの本文中の綴りを挙げるため、Essay固有の証拠の提示を説明しやすい。ただしorganizationが弱いという指摘の具体性は不十分。',
            '## 問題例: 1637:1',
            '正しい英文they might have an accident due to the weatherを誤り扱いする。Goldと予測は一致しても理由の正しさは保証されないことを示す。']
for tid in ['4816:2','3453:1','1637:1']:
    r = rows[tid]
    examples.extend([f'## 元資料 {tid}',f'Gold={int(frame.loc[tid,"Overall"])} / A={baseline[tid]["predicted_overall"]} / A\'={r["predicted_overall"]}',
                     '### Target Essay',str(frame.loc[tid,'Text']), '### History K=3',format_history(frame.loc[r['history_ids']]),
                     '### Aの理由',baseline[tid]['reasoning'], '### A\'の未編集生成出力',
                     '```json\n'+json.dumps({k:r[k] for k in ['predicted_overall','rater_tendency','reasoning']},ensure_ascii=False,indent=2)+'\n```'])
(out / 'presentation_examples.md').write_text('\n\n'.join(examples),encoding='utf-8')
stats = {'attempted':1000,'valid':len(valid),'retry_total':sum(r.get('retry_count',0) for r in rows.values()),
         'length_finish_attempts':sum(a['finish_reason']=='length' for a in attempts),
         'output_tokens_min_median_max':[min(tokens),float(np.median(tokens)),max(tokens)],
         'targets_with_2_exact_target_quotes':int((audit.target_quotes_exact>=2).sum()),
         'targets_with_1_exact_history_quote':int((audit.history_quotes_exact>=1).sum())}
core.save(out / 'full_validation_summary.json',stats)
sections = [
('実験目的','採点者本人の履歴から評価傾向と対象Essay固有の理由を同時に生成する初期的検証。'),
("AとA'の入力・出力の違い",'入力は同じ本人履歴K=3（本文・Overall・6 Traits）、Overall rubric、Target Essay。出力のみ評価傾向と3要素の理由に拡張。Profile生成なし。'),
('Pilotの結果','旧A\'30件Accuracy=60.0%、grounded v2の同じ30件=53.3%。匿名化指示と具体的引用を追加したv2で本実験を承認。Pilot出力30件を再利用。'),
('最終Promptと生成設定','prompts/en/rater_tendency_joint_prediction_grounded_v2.txt。Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、temperature=.2、top_p=.8、max_tokens=768（Aは384）、max_model_len=8192、K=3。設定とSHA256はexperiment_config.json。'),
('共通1,000件のOverall予測性能','2026-10-19 15:17–18:43 JSTに本実験完了。試行1,000件、有効995件。共通有効995件で比較。prediction_summary.csv:\n\n'+(out/'prediction_summary.csv').read_text()),
("AとA'の統計的比較",'2,000 paired percentile bootstrap、seed=20260914、target単位。Accuracy差−0.50ポイントのCIは−2.51～+1.41ポイント。QWK差−0.0818、95%CI[−0.1180,−0.0437]。この対象集合のbootstrapではQWK低下のCIが0を含まない。改善は確認できず、同一rater内の相関を扱うcluster bootstrapではない。詳細paired_comparison.csv。'),
('予測Overall分布','995件のA: [6,125,803,61,0]、A\': [1,72,855,67,0]（1～5順）。A\'は3点への集中が強い。prediction_distribution.csv。'),
('新しい採点理由の出力例','presentation_examples.mdに候補4816:2、3453:1、問題例1637:1の未編集出力とEssay・履歴・Aを保存。目的抽出であり全体の代表性は主張しない。'),
('評価傾向と履歴との整合性','reasoning_structure_summary.csvは構造の有無のみ。全995有効出力が留保文言を含むが、推定断念率とは異なる。引用の機械的照合はfull_quotation_audit.csv。統計: '+json.dumps(stats,ensure_ascii=False)+'。人手評価は未実施。'),
('Rec-SAVER評価の再利用可能性','既存verified_reference_poolとのtarget/history一致は先行照合で2対象のみ。Rubric・本文・参照生成条件の追加照合が必要。既存評価値は転記せず、再計算も未実施。Essay固有reasoningのみ比較し、rater_tendencyは別評価。追加時間は未実測。'),
('Integrity audit','1,000件の既存A再利用・同一履歴・Essay重複排除・Gold改変不変性はintegrity_audit.csv。入力SHA256を再検証、1,000 unique targetsと995有効予測・保存済み指標を再計算照合した。5件はretry後もJSONDecodeError（excluded_targets.csv）。出力の切断は0、retry合計10。'),
('主張できること・現時点で主張できないこと','評価傾向とEssay固有理由の構造化出力は995件で得られた。Overall性能の改善は得られずQWKは低下。引用の一致は正しい解釈や採点者固有性を証明しない。真の判断理由の再現、予測への因果的寄与、採点者間ばらつきの低減は検証していない。'),
('次の研究課題','人手によるTendency Grounding / Essay Grounding / Tendency Connection / Score Consistencyの確認。誤ったエラー指摘、Rubric言い換え、3点集中を分析。設定を変更する追試は既存結果を保持して実施する。')]
report = out / 'report.md'
archive = out / 'report_pre_finalization.md'
if not archive.exists():
    archive.write_bytes(report.read_bytes())
report.write_text('\n\n'.join(f'## {i}. {title}\n\n{body}' for i,(title,body) in enumerate(sections,1)),encoding='utf-8')
core.status('git_status_after')
print(json.dumps(stats,indent=2))
for tid in ['4816:2','3453:1']:
    print(tid, frame.loc[tid,'rater_id'])
    print(format_history(frame.loc[rows[tid]['history_ids']])[:15000])
