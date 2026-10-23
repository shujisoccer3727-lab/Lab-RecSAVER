## 1. 実験目的

採点者本人の履歴から評価傾向と対象Essay固有の理由を同時に生成する初期的検証。

## 2. AとA'の入力・出力の違い

入力は同じ本人履歴K=3（本文・Overall・6 Traits）、Overall rubric、Target Essay。出力のみ評価傾向と3要素の理由に拡張。Profile生成なし。

## 3. Pilotの結果

旧A'30件Accuracy=60.0%、grounded v2の同じ30件=53.3%。匿名化指示と具体的引用を追加したv2で本実験を承認。Pilot出力30件を再利用。

## 4. 最終Promptと生成設定

prompts/en/rater_tendency_joint_prediction_grounded_v2.txt。Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、temperature=.2、top_p=.8、max_tokens=768（Aは384）、max_model_len=8192、K=3。設定とSHA256はexperiment_config.json。

## 5. 共通1,000件のOverall予測性能

2026-10-19 15:17–18:43 JSTに本実験完了。試行1,000件、有効995件。共通有効995件で比較。prediction_summary.csv:

Condition,N,Accuracy,MAE,RMSE,QWK
A,995,0.5376884422110553,0.4844221105527638,0.7270785487692523,0.35112771887366767
A',995,0.5326633165829145,0.4894472361809045,0.7305260718882952,0.2693162472357936


## 6. AとA'の統計的比較

2,000 paired percentile bootstrap、seed=20260914、target単位。Accuracy差−0.50ポイントのCIは−2.51～+1.41ポイント。QWK差−0.0818、95%CI[−0.1180,−0.0437]。この対象集合のbootstrapではQWK低下のCIが0を含まない。改善は確認できず、同一rater内の相関を扱うcluster bootstrapではない。詳細paired_comparison.csv。

## 7. 予測Overall分布

995件のA: [6,125,803,61,0]、A': [1,72,855,67,0]（1～5順）。A'は3点への集中が強い。prediction_distribution.csv。

## 8. 新しい採点理由の出力例

presentation_examples.mdに候補4816:2、3453:1、問題例1637:1の未編集出力とEssay・履歴・Aを保存。目的抽出であり全体の代表性は主張しない。

## 9. 評価傾向と履歴との整合性

reasoning_structure_summary.csvは構造の有無のみ。全995有効出力が留保文言を含むが、推定断念率とは異なる。引用の機械的照合はfull_quotation_audit.csv。統計: {"attempted": 1000, "valid": 995, "retry_total": 10, "length_finish_attempts": 0, "output_tokens_min_median_max": [289, 403.0, 724], "targets_with_2_exact_target_quotes": 653, "targets_with_1_exact_history_quote": 20}。人手評価は未実施。

## 10. Rec-SAVER評価の再利用可能性

既存verified_reference_poolとのtarget/history一致は先行照合で2対象のみ。Rubric・本文・参照生成条件の追加照合が必要。既存評価値は転記せず、再計算も未実施。Essay固有reasoningのみ比較し、rater_tendencyは別評価。追加時間は未実測。

## 11. Integrity audit

1,000件の既存A再利用・同一履歴・Essay重複排除・Gold改変不変性はintegrity_audit.csv。入力SHA256を再検証、1,000 unique targetsと995有効予測・保存済み指標を再計算照合した。5件はretry後もJSONDecodeError（excluded_targets.csv）。出力の切断は0、retry合計10。

## 12. 主張できること・現時点で主張できないこと

評価傾向とEssay固有理由の構造化出力は995件で得られた。Overall性能の改善は得られずQWKは低下。引用の一致は正しい解釈や採点者固有性を証明しない。真の判断理由の再現、予測への因果的寄与、採点者間ばらつきの低減は検証していない。

## 13. 次の研究課題

人手によるTendency Grounding / Essay Grounding / Tendency Connection / Score Consistencyの確認。誤ったエラー指摘、Rubric言い換え、3点集中を分析。設定を変更する追試は既存結果を保持して実施する。