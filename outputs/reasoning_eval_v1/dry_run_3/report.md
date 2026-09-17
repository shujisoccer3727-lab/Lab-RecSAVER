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

| total_generated_attempts | gold_leakage_count | gold_leakage_rate | other_score_disclosures | retry_attempts | leakage_free_candidates | targets_short_of_three |
| --- | --- | --- | --- | --- | --- | --- |
| 35 | 31 | 0.8857 | 0 | 26 | 4 | 2 |

## Self-verification

| candidates_submitted | verification_attempts | verified_candidates | verification_pass_rate |
| --- | --- | --- | --- |
| 4 | 4 | 3 | 0.7500 |

## Coverage

| targets_total | completed_targets | targets_with_verified_reference | coverage_rate | mean_verified_refs_per_target | median_verified_refs_per_target |
| --- | --- | --- | --- | --- | --- |
| 100 | 3 | 1 | 0.0100 | 0.0300 | 0.0000 |

| verified_reference_count | targets |
| --- | --- |
| 0 | 99 |
| 1 | 0 |
| 2 | 0 |
| 3 | 1 |

未完了targetがある場合、coverageは未完了を含む設定target数を分母とする。Reasoning metricsは完了かつverified referenceが1件以上あるtargetのみで計算。未coverage targetは0点に置換せずNaNを保存。

## Reasoning quality

| metric | aggregation | n | macro_mean |
| --- | --- | --- | --- |
| bleu | max | 1 | 0.3215 |
| bleu | mean | 1 | 0.2624 |
| rouge1_f1 | max | 1 | 0.6475 |
| rouge1_f1 | mean | 1 | 0.5934 |
| meteor | max | 1 | 0.4942 |
| meteor | mean | 1 | 0.4270 |
| bertscore_f1 | max | 1 | 0.9265 |
| bertscore_f1 | mean | 1 | 0.9210 |

各referenceとのscoreをreasoning_metrics_by_reference.csvに保存。max/meanはtarget内referenceに対する集約、その後のmacro_meanは対象target間の平均。どちらを主要指標にするかは未決定。

BLEUは既存MVPのsentence BLEU-4（全n-gram次数でadd-one smoothing）、ROUGE-1は既存の単語multiset F1を再利用。どちらも小文字化regex word tokenを使う。METEORにも同じtokenを渡し、NLTK既定stemmer/WordNetを使用。

BERTScoreはroberta-largeの17層、IDFなし、baseline rescalingなし、slow tokenizer。モデルrevisionと実装version、hashをmetric_metadata.jsonに保存。BERTScoreの入力上限も検査し、黙示的な切り詰めを行わない。

実装参照：[BERTScore公式](https://github.com/Tiiiger/bert_score)、[NLTK METEOR API](https://www.nltk.org/api/nltk.translate.meteor_score.html)。

## Correct vs Incorrect prediction

| prediction_correct | targets_total | targets_evaluated | coverage_rate | bleu_max | bleu_mean | rouge1_f1_max | rouge1_f1_mean | meteor_max | meteor_mean | bertscore_f1_max | bertscore_f1_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| True | 3 | 1 | 0.3333 | 0.3215 | 0.2624 | 0.6475 | 0.5934 | 0.4942 | 0.4270 | 0.9265 | 0.9210 |

## Score-error analysis

| score_error_group | targets_total | targets_evaluated | coverage_rate | bleu_max | bleu_mean | rouge1_f1_max | rouge1_f1_mean | meteor_max | meteor_mean | bertscore_f1_max | bertscore_f1_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 3 | 1 | 0.3333 | 0.3215 | 0.2624 | 0.6475 | 0.5934 | 0.4942 | 0.4270 | 0.9265 | 0.9210 |

探索的比較であり、因果関係を意味しない。Coverageと各groupのnが異なる場合の選択効果にも注意する。

## Reference diversity

| targets_with_multiple_refs | reference_pairs | mean_lexical_jaccard | median_lexical_jaccard | exact_duplicate_pairs | pairs_jaccard_ge_09 |
| --- | --- | --- | --- | --- | --- |
| 1 | 3 | 0.4505 | 0.3717 | 0 | 0 |

Jaccardは語集合の重なりであり、意味的な多様性を保証しない。類似度の高いreferenceによるmax集約の上昇もあり得るため、reference数と両集約を併記する。

## Quality warnings

属性推測のkeyword warning: 0件。検出0件でもhallucinationが存在しない保証ではない。

## Parse/context errors

| reference_parse_errors | verification_parse_errors | context_errors |
| --- | --- | --- |
| 0 | 0 | 0 |

Goldを入力するのはReference生成のみ。Self-verification PromptはGold引数を受け取らないrendererで作り、保存済み全verificationをGoldなしで再構成して一致を検査。履歴・Rubricに含まれる数字は既存の入力として維持している。

## GPU inference time

Reference生成: 60.31秒。Self-verification: 5.04秒。合計: 65.35秒（モデル初期化を除く、3-target dry run分を含む）。Metric処理: 6.86秒（BERTScoreモデル初期化を含む）。

## 解釈上の限界

Verifiedはモデルが条件付き生成した説明からGoldを再構成できたという自己整合性であり、人間によるGold Reasoningではない。同じモデルがReference生成・検証を担い、両段階が同じRubricとEssayを参照するため、共通の表現・判断傾向が一致を高める可能性がある。Reasoning metricはこの参照poolへの類似度であり、事実性・履歴忠実性・採点妥当性を単独で保証しない。

## 再開と再現

reference_candidates.jsonlとself_verification_results.jsonlはattemptごとにappend/fsyncする正本。config・入力hashが同じ場合のみ再開し、採用済み候補と検証済み候補をskip。末尾の不完全JSONは退避して復旧する。バッチ途中で未保存だったrequestのみ同じseedで再実行可能。完了済みtargetを再生成しない。

3-target確認: `python -m src.recsaver.reasoning_eval_v1 --stage generate --limit 3`。続いて`--stage evaluate`。100-target再開: `--stage generate`、続いて`--stage evaluate`。レポート/整合性検査: `python -m src.recsaver.reasoning_eval_report --require-complete`。

configのnum_targetsは固定source manifestのprefix数として変更できる。将来のdataset全件への拡張は別の固定prediction manifestと別output_dirを使う。今回は既存100件のみ。
