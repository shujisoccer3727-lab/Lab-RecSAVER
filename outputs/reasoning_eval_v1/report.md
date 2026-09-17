# Rec-SAVER AES: Reasoning Evaluation V1

## Experiment setup

Correct-rater K=3 + Overall Rubric + Existing Promptの保存済みPrediction Reasoningを固定。新規Prediction生成は0件。ReferenceとSelf-verificationのみ新規生成。

```json
{
  "model": {
    "model_id": "Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4",
    "quantization": "gptq_marlin",
    "tensor_parallel_size": 1,
    "max_model_len": 8192,
    "gpu_memory_utilization": 0.9
  },
  "generation": {
    "reference": {
      "temperature": 0.2,
      "top_p": 0.8,
      "max_tokens": 384
    },
    "verification": {
      "temperature": 0.2,
      "top_p": 0.8,
      "max_tokens": 64
    }
  },
  "seed": 20260814,
  "GPU": "NVIDIA RTX 6000 Ada Generation, 49140 MiB, 596.72"
}
```

Referenceは3候補枠。各枠は初回を含め最大5 attempt（追加retryは最大4）。Goldまたは他のnumeric scoreを採点文脈で明示した候補は不採用として再生成する。Score不一致のSelf-verificationは再試行せず、parse失敗だけ最大1回retry。

## Prediction source

outputs/overall_rubric_ablation/overall_rubric_predictions.jsonl

| condition | n | exact_accuracy | mae | rmse | qwk |
| --- | --- | --- | --- | --- | --- |
| raw_k3_with_rubric | 100 | 0.5600 | 0.4800 | 0.7483 | 0.2899 |

## Reference generation

| total_generated_attempts | gold_leakage_count | gold_leakage_rate | other_score_disclosures | retry_attempts | leakage_free_candidates | initial_leakage_free_candidates | retry_recovered_candidates | targets_recovered_from_zero_initial_free | targets_short_of_three |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 821 | 586 | 0.7138 | 5 | 521 | 234 | 111 | 123 | 22 | 39 |

## Self-verification

| candidates_submitted | verification_attempts | verified_candidates | verification_pass_rate |
| --- | --- | --- | --- |
| 234 | 234 | 212 | 0.9060 |

## Coverage

| targets_total | completed_targets | targets_with_verified_reference | coverage_rate | mean_verified_refs_per_target | median_verified_refs_per_target |
| --- | --- | --- | --- | --- | --- |
| 100 | 100 | 84 | 0.8400 | 2.1200 | 3.0000 |

| verified_reference_count | targets |
| --- | --- |
| 0 | 16 |
| 1 | 8 |
| 2 | 24 |
| 3 | 52 |

Gold score別の補助集計：

| gold_overall | n | completed_targets | targets_with_reference | mean_verified_refs | coverage_rate |
| --- | --- | --- | --- | --- | --- |
| 2 | 18 | 18 | 9 | 1.2778 | 0.5000 |
| 3 | 54 | 54 | 48 | 2.3333 | 0.8889 |
| 4 | 25 | 25 | 24 | 2.1600 | 0.9600 |
| 5 | 3 | 3 | 3 | 3.0000 | 1.0000 |

未完了targetがある場合、coverageは未完了を含む設定target数を分母とする。Reasoning metricsは完了かつverified referenceが1件以上あるtargetのみで計算。未coverage targetは0点に置換せずNaNを保存。

## Reasoning quality

| metric | aggregation | n | macro_mean |
| --- | --- | --- | --- |
| bleu | max | 84 | 0.2202 |
| bleu | mean | 84 | 0.1939 |
| rouge1_f1 | max | 84 | 0.5565 |
| rouge1_f1 | mean | 84 | 0.5315 |
| meteor | max | 84 | 0.4003 |
| meteor | mean | 84 | 0.3665 |
| bertscore_f1 | max | 84 | 0.9113 |
| bertscore_f1 | mean | 84 | 0.9065 |

各referenceとのscoreをreasoning_metrics_by_reference.csvに保存。max/meanはtarget内referenceに対する集約、その後のmacro_meanは対象target間の平均。どちらを主要指標にするかは未決定。

BLEUは既存MVPのsentence BLEU-4（全n-gram次数でadd-one smoothing）、ROUGE-1は既存の単語multiset F1を再利用。どちらも小文字化regex word tokenを使う。METEORにも同じtokenを渡し、NLTK既定stemmer/WordNetを使用。

BERTScoreはroberta-largeの17層、IDFなし、baseline rescalingなし、slow tokenizer。モデルrevisionと実装version、hashをmetric_metadata.jsonに保存。BERTScoreの入力上限も検査し、黙示的な切り詰めを行わない。

実装参照：[BERTScore公式](https://github.com/Tiiiger/bert_score)、[NLTK METEOR API](https://www.nltk.org/api/nltk.translate.meteor_score.html)。

## Correct vs Incorrect prediction

| prediction_correct | targets_total | targets_evaluated | coverage_rate | bleu_max | bleu_mean | rouge1_f1_max | rouge1_f1_mean | meteor_max | meteor_mean | bertscore_f1_max | bertscore_f1_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| False | 44 | 36 | 0.8182 | 0.1461 | 0.1328 | 0.5017 | 0.4813 | 0.3476 | 0.3211 | 0.8969 | 0.8938 |
| True | 56 | 48 | 0.8571 | 0.2758 | 0.2397 | 0.5975 | 0.5692 | 0.4398 | 0.4005 | 0.9221 | 0.9161 |

## Score-error analysis

| score_error_group | targets_total | targets_evaluated | coverage_rate | bleu_max | bleu_mean | rouge1_f1_max | rouge1_f1_mean | meteor_max | meteor_mean | bertscore_f1_max | bertscore_f1_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 56 | 48 | 0.8571 | 0.2758 | 0.2397 | 0.5975 | 0.5692 | 0.4398 | 0.4005 | 0.9221 | 0.9161 |
| 1 | 40 | 32 | 0.8000 | 0.1509 | 0.1375 | 0.5072 | 0.4870 | 0.3532 | 0.3262 | 0.8981 | 0.8950 |
| >=2 | 4 | 4 | 1.0000 | 0.1071 | 0.0950 | 0.4572 | 0.4362 | 0.3026 | 0.2802 | 0.8872 | 0.8845 |

探索的比較であり、因果関係を意味しない。Coverageと各groupのnが異なる場合の選択効果にも注意する。

## Reference diversity

| targets_with_multiple_refs | reference_pairs | mean_lexical_jaccard | median_lexical_jaccard | exact_duplicate_pairs | pairs_jaccard_ge_09 |
| --- | --- | --- | --- | --- | --- |
| 76 | 180 | 0.5721 | 0.5443 | 4 | 15 |

Jaccardは語集合の重なりであり、意味的な多様性を保証しない。類似度の高いreferenceによるmax集約の上昇もあり得るため、reference数と両集約を併記する。

## Quality warnings

属性推測のkeyword warning: 0件。検出0件でもhallucinationが存在しない保証ではない。

## Parse/context errors

| reference_parse_errors | verification_parse_errors | context_errors | max_reference_prompt_plus_budget | max_verification_prompt_plus_budget |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 4721 | 4495 |

Goldを入力するのはReference生成のみ。Self-verification PromptはGold引数を受け取らないrendererで作り、保存済み全verificationをGoldなしで再構成して一致を検査。履歴・Rubricに含まれる数字は既存の入力として維持している。

## GPU inference time

Reference生成: 1884.91秒。Self-verification: 438.87秒。合計: 2323.78秒（モデル初期化を除く、3-target dry run分を含む）。Metric処理: 10.63秒（BERTScoreモデル初期化を含む）。

## 解釈上の限界

Verifiedはモデルが条件付き生成した説明からGoldを再構成できたという自己整合性であり、人間によるGold Reasoningではない。同じモデルがReference生成・検証を担い、両段階が同じRubricとEssayを参照するため、共通の表現・判断傾向が一致を高める可能性がある。Reasoning metricはこの参照poolへの類似度であり、事実性・履歴忠実性・採点妥当性を単独で保証しない。

## 再開と再現

reference_candidates.jsonlとself_verification_results.jsonlはattemptごとにappend/fsyncする正本。config・入力hashが同じ場合のみ再開し、採用済み候補と検証済み候補をskip。末尾の不完全JSONは退避して復旧する。バッチ途中で未保存だったrequestのみ同じseedで再実行可能。完了済みtargetを再生成しない。

3-target確認: `python -m src.recsaver.reasoning_eval_v1 --stage generate --limit 3`。続いて`--stage evaluate`。100-target再開: `--stage generate`、続いて`--stage evaluate`。レポート/整合性検査: `python -m src.recsaver.reasoning_eval_report --require-complete`。

configのnum_targetsは固定source manifestのprefix数として変更できる。将来のdataset全件への拡張は別の固定prediction manifestと別output_dirを使う。今回は既存100件のみ。

## 実測結果の解釈

固定100-target V1の生成・検証・評価処理は完了した。Predictionは再生成せず、既存Accuracy 0.56、MAE 0.48、RMSE 0.7483、QWK 0.2899の出力をそのまま評価した。Reference生成・Self-verificationは2026-09-12に完了し、保存済み結果のmetric計算と最終確認は2026-09-14に実施した。

Verified Referenceを確保できたのは84/100 target（84%）、計212件。平均2.12件、中央値3件で、0/1/2/3件のtarget数は16/8/24/52だった。未coverageの16件は、漏洩なし候補を1件も確保できなかった11件と、候補は確保できたが検証を通過しなかった5件に分かれる。

生成821 attempt中、Goldの直接明示は586件（71.38%）と多かった。初回300 attemptから採用できた111候補に、追加521 attemptによる123候補が加わり、漏洩なし候補234件を確保した。初回に漏洩なし候補が0件だったtargetのうち22件で、retryにより1件以上を確保した。3候補を揃えられたのは61 target、上限到達時に不足が残ったのは39 target。他score明示5件はGold明示との重複4件を含むため、除外attempt総数は587件である。

漏洩なし候補のSelf-verification通過率は212/234 = 90.60%。スコア明示を除外しても定量評価は84件で成立しており、提示された分類ではPattern Bの「retryによる回復」に対応する。ただし全targetをカバーできておらず、運用上のReference生成コストと不足が残る。単一実行のため、反復実験における安定性までは確認していない。

特にGold score別coverageは、Gold 2が9/18（50%）、Gold 3が48/54（88.89%）、Gold 4が24/25（96%）、Gold 5が3/3（100%）だった。84件の平均metricを無条件に100件全体へ一般化しない。Gold 5はn=3の小標本である。

正解群48件と不正解群36件では、BLEU・ROUGE-1・METEOR・BERTScoreのtarget内max/meanのすべてで正解群が高かった。例えばtarget内meanの群平均は、BERTScore 0.9161対0.8938、ROUGE-1 0.5692対0.4813、METEOR 0.4005対0.3211。Pattern Dに対応する探索的な正の関連が見られる。ただし因果関係や統計的有意差を示した結果ではなく、Gold-conditioned referenceと共通モデル・Rubricによる評価設計の影響を受ける可能性がある。

Score error別にも、error 0 → 1 → 2以上で全metricのmax/meanが順に低下した。BERTScoreのtarget内meanは0.9161 → 0.8950 → 0.8845。ただし評価件数は48 → 32 → 4件であり、特にerror 2以上の結果は小標本の探索的結果として扱う。

Verified Referenceが複数ある76 target、180ペアのlexical Jaccardは平均0.5721、中央値0.5443。完全一致は4ペア、Jaccard 0.9以上は15ペアだった。同一文のみのpoolではない一方、語彙的に非常に近いReferenceもあり、意味的な多様性は別途確認が必要である。

採点者のpersonality/background等に関するkeyword warningは0件だった。これは属性hallucinationが存在しない証明ではない。Parse/context errorはいずれも0件。保存済み全Self-verification PromptをGold引数なしで再構成して一致を確認し、元prediction・Rubric・parser・dataset等のSHA-256も一致した。未処理の生成requestはない。

結論として、Reasoning Evaluation V1は実装・100-target実行を完了し、84 targetを4指標で評価できた。一方で、漏洩率の高さとGold 2のcoverage不足が改善課題として残る。Verified Referenceは人間のGold Reasoningではなく、モデルの自己整合性で選別した参照説明として扱う。

