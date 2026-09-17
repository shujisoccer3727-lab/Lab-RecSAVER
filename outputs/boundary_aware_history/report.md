# Rec-SAVER AES: Boundary-aware History Prompt Ablation

## 実験条件

同じOverall Rubric・Correct-rater Raw History K=3・Target Essayの100件。Existingは保存済みraw_k3_with_rubricを再利用し、新規生成はBoundary-awareの100件のみ。

ユーザー承認により既存と同じJSONのreasoning / predicted_overallを使用。parserは変更していない。Reasoningは簡潔な採点根拠のみ。

```yaml
model:
  model_id: Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4
  quantization: gptq_marlin
  tensor_parallel_size: 1
  max_model_len: 8192
  gpu_memory_utilization: 0.9
generation:
  temperature: 0.2
  top_p: 0.8
  max_tokens: 384
target_seed: 20260814
history_seed: 20260814
GPU: NVIDIA RTX 6000 Ada Generation, 49140, 596.72
```

Target/historyは再samplingせず、同じ順序で10件ずつ処理した。生成seedは共通VLLMGeneratorの既定値0を使用。保存済みExistingと新規条件の乱数系列・バッチ構成が完全に対応することまでは保証しない（Existing実験はK=0/K=3を交互に生成）。単一実行の比較であり、反復実験による安定性は未検証。

## Performance

| condition | n | exact_accuracy | mae | rmse | qwk |
| --- | --- | --- | --- | --- | --- |
| Existing | 100 | 0.5600 | 0.4800 | 0.7483 | 0.2899 |
| Boundary-aware | 100 | 0.5500 | 0.4900 | 0.7550 | 0.3015 |

## Metric delta

Boundary-aware minus Existing。Accuracy/QWKは正、MAE/RMSEは負が改善。

| accuracy_delta | mae_delta | rmse_delta | qwk_delta |
| --- | --- | --- | --- |
| -0.0100 | 0.0100 | 0.0067 | 0.0116 |

## Paired comparison

同一targetの絶対誤差を比較。Mean/Median AE differenceはExisting minus Boundary-aware（正が改善）。

| improved_targets | unchanged_targets | worsened_targets | mean_ae_difference | median_ae_difference |
| --- | --- | --- | --- | --- |
| 4 | 91 | 5 | -0.0100 | 0.0000 |

## Prediction distribution

単位：%。

| score | Gold | Existing | Boundary-aware |
| --- | --- | --- | --- |
| 1 | 0.0000 | 0.0000 | 0.0000 |
| 2 | 18.0000 | 16.0000 | 17.0000 |
| 3 | 54.0000 | 79.0000 | 76.0000 |
| 4 | 25.0000 | 5.0000 | 7.0000 |
| 5 | 3.0000 | 0.0000 | 0.0000 |

## Score collapse

| condition | unique_predicted_scores | most_frequent_score | most_frequent_score_ratio |
| --- | --- | --- | --- |
| Existing | 3 | 3 | 0.7900 |
| Boundary-aware | 3 | 3 | 0.7600 |

## Score transitions

予測が変化した9件すべてをscore_transitions.csvに保存。

| transition | n |
| --- | --- |
| 2 -> 3 | 2 |
| 3 -> 2 | 3 |
| 3 -> 4 | 3 |
| 4 -> 3 | 1 |

| transition | n | toward_gold | away_from_gold | same_error |
| --- | --- | --- | --- | --- |
| 3 -> 2 | 3 | 1 | 2 | 0 |
| 3 -> 4 | 3 | 2 | 1 | 0 |

## Rater別傾向

探索的結果。better/same/worseはraterごとのMAEで判定し、各raterのnに注意する。

| criterion | boundary_better | same | boundary_worse |
| --- | --- | --- | --- |
| MAE (exploratory) | 2 | 16 | 3 |

| rater_id | Boundary-aware n | Existing n | Boundary-aware accuracy | Existing accuracy | Boundary-aware mae | Existing mae |
| --- | --- | --- | --- | --- | --- | --- |
| rater_1 | 4.0000 | 4.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| rater_10 | 9.0000 | 9.0000 | 0.3333 | 0.3333 | 0.7778 | 0.6667 |
| rater_11 | 9.0000 | 9.0000 | 0.4444 | 0.5556 | 0.5556 | 0.4444 |
| rater_12 | 7.0000 | 7.0000 | 0.5714 | 0.7143 | 0.4286 | 0.2857 |
| rater_13 | 7.0000 | 7.0000 | 0.4286 | 0.4286 | 0.5714 | 0.5714 |
| rater_15 | 6.0000 | 6.0000 | 0.3333 | 0.3333 | 0.6667 | 0.6667 |
| rater_18 | 7.0000 | 7.0000 | 0.4286 | 0.4286 | 0.5714 | 0.5714 |
| rater_19 | 3.0000 | 3.0000 | 0.6667 | 0.3333 | 0.3333 | 0.6667 |
| rater_2 | 10.0000 | 10.0000 | 0.8000 | 0.8000 | 0.2000 | 0.2000 |
| rater_21 | 4.0000 | 4.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 |
| rater_22 | 2.0000 | 2.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| rater_23 | 5.0000 | 5.0000 | 0.6000 | 0.6000 | 0.4000 | 0.4000 |
| rater_24 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| rater_27 | 2.0000 | 2.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| rater_3 | 2.0000 | 2.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| rater_4 | 3.0000 | 3.0000 | 0.3333 | 0.3333 | 1.0000 | 1.0000 |
| rater_5 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 |
| rater_6 | 4.0000 | 4.0000 | 0.5000 | 0.5000 | 0.7500 | 0.7500 |
| rater_7 | 10.0000 | 10.0000 | 0.5000 | 0.6000 | 0.6000 | 0.6000 |
| rater_8 | 2.0000 | 2.0000 | 0.0000 | 0.0000 | 1.0000 | 1.0000 |
| rater_9 | 2.0000 | 2.0000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 |

## Boundary-aware Reasoning examples

変化したtargetから3→2と3→4を各最大5件、残りはtarget順で補完。代表性を保証する抽出ではない。以下は保存された簡潔な説明の原文。

### 1881:2 / rater rater_24 / Gold 2 / 3 -> 2

**Existing:** The essay demonstrates limited facility in the use of language, with frequent errors in grammar, syntax, and usage. The organization is generally controlled, but there are instances where connections between ideas are absent or unsuccessful. The communication is impeded by language inaccuracies in some cases, which aligns with the characteristics of a Score 3 essay according to the rubric.

**Boundary-aware:** The essay demonstrates inconsistent facility in sentence formation, word choice, and mechanics. There are frequent errors in grammar, syntax, and usage, which impede communication in many instances. The organization is partially developed but often missing or unsuccessful, aligning more closely with a Score 2 than a Score 3.

### 2016:1 / rater rater_7 / Gold 3 / 3 -> 2

**Existing:** The essay demonstrates limited facility in the use of language, with frequent errors in grammar, syntax, and usage. The organization is generally controlled, but there are instances where connections are absent or unsuccessful. The communication is impeded by language inaccuracies in some cases, which aligns with the rubric for a score of 3.

**Boundary-aware:** The essay demonstrates inconsistent facility in sentence formation, word choice, and mechanics, with frequent grammatical errors and awkward phrasing. The organization is partially developed but often unsuccessful, and communication is impeded in many instances by language inaccuracies. This aligns more closely with a Score 2 than a Score 3, as the language inaccuracies and organizational issues are more severe than in the historical examples rated as 3.

### 3076:1 / rater rater_18 / Gold 3 / 3 -> 2

**Existing:** The essay demonstrates limited facility in the use of language, with inconsistent sentence formation, word choice, and mechanics. The organization is partially developed but sometimes missing or unsuccessful. There are errors in grammar and syntax, and usage issues that impede communication in some cases. This aligns with the rubric for a score of 3.

**Boundary-aware:** The essay demonstrates inconsistent facility in sentence formation, word choice, and mechanics. The organization is partially developed but often missing or unsuccessful. Communication is impeded in many instances by language inaccuracies, which aligns more closely with a Score 2 than a Score 3. Compared to the historical examples, this essay shows more significant language inaccuracies and less coherent organization.

### 2840:1 / rater rater_19 / Gold 4 / 3 -> 4

**Existing:** The target essay demonstrates a limited range of vocabulary and occasional errors in grammar and syntax, which aligns with the rubric for a score of 3. The essay is generally organized, but there are instances where the connection between ideas is not always clear. The writer's argument is understandable, but the language inaccuracies and occasional structural issues impede communication in some cases.

**Boundary-aware:** The essay demonstrates a range of vocabulary and syntactic variety, with controlled organization and accuracy in grammar and conventions, aligning with the Score 4 criteria. While there are occasional inaccuracies, they rarely impede communication. Comparing with the historical examples, this essay shows more syntactic variety and fewer language inaccuracies than the Score 3 essays, supporting a Score 4.

### 2993:2 / rater rater_12 / Gold 3 / 3 -> 4

**Existing:** The essay demonstrates a limited facility in the use of language, with occasional syntactic variety and a range of vocabulary, but there are noticeable errors in grammar and syntax that impede communication. The organization is generally controlled, but there are instances where the connection between ideas is absent or unsuccessful. The essay provides a mix of positive and negative points about technology, but the language inaccuracies and occasional structural issues suggest a score of 3 according to the rubric.

**Boundary-aware:** The essay demonstrates facility in the use of language with syntactic variety and a range of words and phrases. The organization is generally controlled, and while there are occasional language inaccuracies, they rarely impede communication. This aligns with the rubric for Score 4. The historical examples, particularly the essays with Overall scores of 4, show similar levels of language facility and organization, with occasional inaccuracies that do not significantly hinder understanding.

### 8415:1 / rater rater_7 / Gold 5 / 3 -> 4

**Existing:** The essay demonstrates a range of vocabulary and syntactic variety, but there are occasional errors in grammar and syntax that impede communication. The organization is generally controlled, but there are some instances where the connection between ideas is not as clear as it could be. Based on the rubric, this essay aligns most closely with a score of 3, as it shows facility limited to the use of common structures and generic vocabulary with some errors in grammar and usage that impede communication in some cases.

**Boundary-aware:** The target essay demonstrates facility in the use of language with syntactic variety and a range of words and phrases. The organization is generally controlled, and while there are some errors in grammar and conventions, they rarely impede communication. This aligns more closely with a Score 4 than a Score 3, where communication is more frequently impeded by language inaccuracies. Comparing with the historical examples, the target essay shows a higher level of syntactic variety and fewer errors that impede communication.

### 2615:2 / rater rater_11 / Gold 2 / 2 -> 3

**Existing:** The essay demonstrates inconsistent facility in sentence formation, word choice, and mechanics. The organization is partially developed but often missing or unsuccessful. There are frequent errors in grammar, syntax, and usage, which impede communication in many instances. The essay does not meet the criteria for a score of 3, as the language inaccuracies are more frequent and impactful. Therefore, the predicted overall score is 2.

**Boundary-aware:** The essay demonstrates limited facility in sentence formation, word choice, and mechanics, with frequent errors in grammar and syntax. The organization is partially developed but sometimes missing or unsuccessful. Communication is impeded in many instances by language inaccuracies, which aligns more closely with a Score 3 than a Score 4. Compared to the historical examples, this essay has similar issues with grammar and syntax, and the organization is not as controlled as in the Score 4 example (ID=5269:2).

### 4718:2 / rater rater_10 / Gold 5 / 4 -> 3

**Existing:** The target essay demonstrates a range of vocabulary and syntactic variety, with controlled organization and generally accurate grammar and conventions. While there are occasional inaccuracies, they do not significantly impede communication. This aligns with the rubric for a score of 4, which indicates facility in the use of language with syntactic variety and range of words and phrases, controlled organization, and accuracy in grammar and conventions with occasional language inaccuracies that rarely impede communication.

**Boundary-aware:** The essay demonstrates a reasonable level of language facility, with some syntactic variety and range of vocabulary, but there are noticeable errors in grammar and syntax that occasionally impede communication. The organization is generally controlled, though some connections are weak. This aligns more closely with a Score 3 than a Score 4, where the language would be more accurate and controlled. Compared to the Score 4 essay in History 3, this essay has more errors and less syntactic variety. It also shows more control and fewer errors than the Score 2 essay in History 2.

### 4869:1 / rater rater_18 / Gold 3 / 2 -> 3

**Existing:** The essay demonstrates limited facility in sentence formation, word choice, and mechanics. There are frequent errors in grammar, syntax, and usage, which impede communication in many instances. The organization is partially developed but may be missing or unsuccessful. The essay's content and structure suggest a score of 2 according to the rubric.

**Boundary-aware:** The essay demonstrates a reasonable level of language facility, with some syntactic variety and range of vocabulary. The organization is generally controlled, though there are occasional lapses in coherence and some errors in grammar and syntax. While communication is impeded at times, it is not as frequently as in the examples scored as 2. The essay does not reach the level of a score 4 due to the presence of errors and less controlled language use.

## History utilization簡易監査

Keyword-based heuristicであり正式評価ではない。rater/example等への言及は具体的な履歴比較を保証せず、暗黙の比較は検出できない。隣接比較は対比語に加えて明示的な隣接score番号2つを要求するため、取りこぼしがある。

| heuristic | count | n | rate |
| --- | --- | --- | --- |
| history_explicitly_referenced | 74 | 100 | 0.7400 |
| rubric_explicitly_referenced | 12 | 100 | 0.1200 |
| neighboring_score_comparison_present | 33 | 100 | 0.3300 |

## Leakage checks

全100件で保存済みExisting Promptを元データから再構成し完全一致を確認。両条件のRubricヘッダー以降の全入力部分も一致。TargetブロックはEssay本文のみで、Gold Overall/Target Trait scoresを挿入していない。

target/history ID・順序・history size=3・history rater=target raterを検証。targetのsource rowと同じessay本文を履歴から排除していることを確認。Overall RubricのSHA-256も既存metadataと一致。Full Rubric、Key Terms、Profile、Wrong Historyの追加なし。

## Context / parse errors

Context overflow: 0。最大prompt 4445 + 384 = 4829 <= 8192。切り詰めなし。Parse errors: 0。再推論0件。

## 実行時間

生成処理合計: 228.38秒。dry run・model初期化を含む計測区間: 275.43秒（集計・レポート作成は含まない）。

## 再現性と成果物

metadata.jsonに実行時刻、git commit、GPU、seed、全target/history ID、Rubric/両Prompt/parser/既存予測のSHA-256、generation設定を保存。resolved_config.yamlとdry_run_conditions.csvを併記。

実行: `python -m src.recsaver.boundary_aware_history`。レポート再作成のみ: `python -m src.recsaver.boundary_aware_history --report-only`。既存予測がある状態の推論再実行は拒否する。

## 結果の解釈と次段階

今回の100件では、Boundary-awareの明確な優位性は確認できなかった。Accuracyは1 percentage point低下、MAEは0.01増加、RMSEは0.0067増加し、QWKのみ0.0116改善した。予測一致は91/100件で、変更9件のうち改善4件・悪化5件だった。

提示された分類ではPattern Dに近い小差・混合の結果と解釈する。ただし統計的同等性を検定したわけではない。Score 3への集中が少し緩む一方でAccuracy/MAE/RMSEが悪化するという、Pattern Cの軽微な傾向もある。Pattern Aのような複数主要指標の改善はなく、Historyを境界として比較させるinstructionがcalibrationを改善したとは結論できない。

Score 3比率は79%から76%へ3 percentage points低下したが、Goldの54%よりまだ22 points高い。使用スコアは両条件とも2/3/4の3種類で、Score 5は依然0%。3→2はGold方向1件・逆方向2件、3→4はGold方向2件・逆方向1件と相殺している。さらに2→3が2件（改善1・悪化1）、4→3が1件（悪化）あり、全体で絶対誤差が1点増加した。

Rater別MAEでは改善2・同じ16・悪化3。改善raterはrater_19（n=3）とrater_24（n=1）で、ともに小標本。rater_7はMAEが同じでもAccuracyが0.60→0.50と低下しており、MAEによるsameを全指標の不変と解釈しない。

本結果を次段階へ進む根拠として十分に有望とは判断せず、Wrong-rater条件は実行していない。今回の結論は固定100件・単一生成実行の範囲に限定する。

## Reasoningの目視確認メモ（探索的）

予測変化が9件のみだったため、reasoning_examples.jsonと本レポートには変更全9件のExisting / Boundary-aware説明を保存した。正式なReasoning評価ではない。

- 1881:2（Gold 2、3→2、改善）：ExistingはScore 3記述への適合を説明。Boundary-awareはScore 2と3を明示比較したが、履歴の具体的参照はない。
- 2016:1（Gold 3、3→2、悪化）：Boundary-awareは過去のScore 3例より言語・構成の問題が大きいと説明。履歴比較の言及があっても正解につながるとは限らない。
- 2840:1（Gold 4、3→4、改善）：Boundary-awareは過去のScore 3例に対して構文の多様さと誤りの少なさを比較し、4を選択した。
- 2615:2（Gold 2、2→3、悪化）：Boundary-awareはHistory ID=5269:2を挙げ、主に3対4を比較している。元の予測である2との境界説明は不足している。
- 4718:2（Gold 5、4→3、悪化）：Boundary-awareはHistory 3のScore 4、History 2のScore 2の間として3を説明したが、Goldからは離れた。

隣接スコアや履歴を比較する表現は確認できるが、Rubricに沿った一般的な言語・構成の説明が多く、具体的なEssayの箇所を示す説明は乏しい。履歴への言及や出力された説明だけから、実際の内部的な履歴活用やScore 3を機械的に選んだかどうかは判定できない。

自動監査はhistory言及74%、rubric明示言及12%、隣接比較検出33%。rubricという語がない説明でもRubricの表現を使っている場合があり、12%はRubric利用率ではない。1881:2の「Score 2 than a Score 3」は実際には比較表現だが、今回の保守的heuristicは単独のthanを対比語に含めないため見逃す。33%も実際の比較率とは区別する。

