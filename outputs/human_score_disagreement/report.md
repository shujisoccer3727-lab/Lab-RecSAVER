# 人間採点者間の点差を対象とする探索実験

参照理由は実Overallを条件としてLLMが生成した説明であり、採点者本人の実際の思考を示すものではありません。自己検証通過は説明の正しさを保証しません。予測点差の縮小や理由の生成だけで、採点者バイアスの是正・人間採点者間の点差縮小・フィードバックの効果は結論できません。

## 対象・設定・既存実験との整合性

rawを再集計。有効Overallは整数1～5。対象はエッセイ本文×異なる採点者の順序なしペア。3点差7エッセイ・7ペア、2点差252エッセイ・252ペア（期待値15/215とは不一致。実測値を採用）。Filename重複10組は本文差分を確認し、空白・匿名化の版違いとして同一エッセイに統合。両者の入力は後方の匿名化済み本文に統一し、履歴ではすべての同一エッセイ版を除外。3名以上の採点があるエッセイは全体で10件。同一採点者の重複1組はOverall一致・Trait不一致を記録し、後方レコードを代表として使用。詳細は[data_audit.json](data_audit.json)、[抽出一覧](extracted_pairs.csv)を参照。

JIMAと同じQwen2.5-32B-Instruct-GPTQ-Int4、GPTQ Marlin、履歴K=3、本人の履歴をseed=20260814で抽出。英語の既存Overallルーブリック・既存3プロンプトを使用。対象本文・Filename・非欠損kaggle IDを全採点者の履歴候補から除外。対象の実Trait/実Overall/相手の点数は予測入力に含めない。自己検証は対象の実スコアを含めない。

予測・参照生成: temperature=.2, top_p=.8, max_tokens=384。自己検証: .2/.8/64。参照理由3枠、枠ごと最大5生成試行。スコア開示があれば除外・再生成し、文章の恣意的な削除はしない。検証のparse失敗は1回再試行、再構成スコアが実スコアと一致すれば採用。理由生成/検証seed=20260916はreasoning_eval_largeに一致。設定・履歴・プロンプト・元ファイルのhashが一致した既存出力を再利用。

GPUメモリ利用率: 0.5（既存 0.9）。モデル・生成条件の変更なし。

変更は点差による対象選択、別名も含む履歴除外、両者の比較レポート・未記入人手評価欄の追加。対象Traitが無効な場合は既存前処理に合わせ実験対象から外し、ペア一覧には失敗理由を残す。


## 集計

A/Bは採点者ID順で、高得点/低得点の順ではありません。処理成功は参照生成・検証の所定試行が完了した状態で、参照取得成功とは別です。

```
[
  {
    "gap": 3,
    "essays": 7,
    "pairs": 7,
    "processing_success": 7,
    "processing_failed": 0,
    "processing_pending": 0,
    "reference_both": 3,
    "reference_one": 3,
    "reference_neither": 1,
    "mae_a": 1.2857142857142858,
    "mae_b": 1.5714285714285714,
    "predicted_gap_mean": 0.14285714285714285,
    "predicted_gap_distribution": {
      "0.0": 6,
      "1.0": 1
    },
    "predicted_gap_smaller": 7,
    "signed_error_a_distribution": {
      "1.0": 5,
      "-2.0": 2
    },
    "signed_error_b_distribution": {
      "-2": 4,
      "1": 2,
      "-1": 1
    }
  },
  {
    "gap": 2,
    "essays": 252,
    "pairs": 252,
    "processing_success": 251,
    "processing_failed": 1,
    "processing_pending": 0,
    "reference_both": 140,
    "reference_one": 96,
    "reference_neither": 16,
    "mae_a": 0.848605577689243,
    "mae_b": 1.0515873015873016,
    "predicted_gap_mean": 0.2350597609561753,
    "predicted_gap_distribution": {
      "0.0": 192,
      "1.0": 59
    },
    "predicted_gap_smaller": 251,
    "signed_error_a_distribution": {
      "-1.0": 87,
      "1.0": 70,
      "0.0": 66,
      "-2.0": 25,
      "2.0": 3
    },
    "signed_error_b_distribution": {
      "1": 76,
      "-1": 73,
      "-2": 54,
      "0": 45,
      "2": 4
    }
  }
]
```


## 人が次に確認する点

両者の実スコア条件付き参照理由をすべて比較し、着目点の違い、本文・履歴の裏付け、ルーブリック上の再確認点を記入してください。予測理由は実スコアなしの別出力です。人手評価は未実施です。役立ちそうかの選択肢は「役立ちそう／判断できない／役立ちにくい」です。実際の効果を調べるには、別途採点者による再確認・再採点が必要です。


## 再開・出力

`python -m src.recsaver.human_score_disagreement --stage all` で既存設定を検証して未処理から再開。journalは各試行でflush/fsync。変更された入力・コード・設定での混在を拒否します。reference_candidates.jsonl/self_verification_results.jsonlに生出力・入力・seed・失敗理由、prepared_targets.jsonlに履歴と予測入力、target_results.jsonlに対象別全結果、pair_results.jsonl/CSVにペア別結果を保存。理由指標はBLEU・ROUGE-1 F1・METEOR・BERTScore F1（roberta-large、17層、IDF/再スケールなし）。各参照と平均・最大を提示します。


[人手記入用CSV](human_review.csv) / [集計CSV](summary_by_gap.csv) / [対象別結果](target_results.jsonl)


## ケース別比較レポート

- [essay_06652__rater_10__rater_11](cases/essay_06652__rater_10__rater_11.md) — 3点差、実 5 / 2、参照理由 0 / 3
- [essay_06662__rater_10__rater_11](cases/essay_06662__rater_10__rater_11.md) — 3点差、実 5 / 2、参照理由 3 / 3
- [essay_06771__rater_12__rater_13](cases/essay_06771__rater_12__rater_13.md) — 3点差、実 2 / 5、参照理由 0 / 0
- [essay_06788__rater_12__rater_13](cases/essay_06788__rater_12__rater_13.md) — 3点差、実 2 / 5、参照理由 1 / 3
- [essay_07473__rater_18__rater_19](cases/essay_07473__rater_18__rater_19.md) — 3点差、実 2 / 5、参照理由 0 / 3
- [essay_08561__rater_2__rater_7](cases/essay_08561__rater_2__rater_7.md) — 3点差、実 2 / 5、参照理由 0 / 2
- [essay_08828__rater_11__rater_9](cases/essay_08828__rater_11__rater_9.md) — 3点差、実 2 / 5、参照理由 3 / 3
- [essay_00479__rater_4__rater_7](cases/essay_00479__rater_4__rater_7.md) — 2点差、実 4 / 2、参照理由 2 / 1
- [essay_00651__rater_23__rater_9](cases/essay_00651__rater_23__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_00817__rater_2__rater_7](cases/essay_00817__rater_2__rater_7.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_00820__rater_23__rater_9](cases/essay_00820__rater_23__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_01023__rater_11__rater_9](cases/essay_01023__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 3
- [essay_01164__rater_23__rater_9](cases/essay_01164__rater_23__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 3
- [essay_01179__rater_23__rater_9](cases/essay_01179__rater_23__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_01698__rater_13__rater_27](cases/essay_01698__rater_13__rater_27.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_02450__rater_11__rater_7](cases/essay_02450__rater_11__rater_7.md) — 2点差、実 1 / 3、参照理由 3 / 3
- [essay_02504__rater_11__rater_9](cases/essay_02504__rater_11__rater_9.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_02530__rater_11__rater_9](cases/essay_02530__rater_11__rater_9.md) — 2点差、実 3 / 1、参照理由 3 / 3
- [essay_03211__rater_7__rater_9](cases/essay_03211__rater_7__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_03241__rater_11__rater_23](cases/essay_03241__rater_11__rater_23.md) — 2点差、実 2 / 4、参照理由 3 / 0
- [essay_04537__rater_10__rater_11](cases/essay_04537__rater_10__rater_11.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_05082__rater_11__rater_5](cases/essay_05082__rater_11__rater_5.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_05090__rater_11__rater_9](cases/essay_05090__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_05245__rater_11__rater_6](cases/essay_05245__rater_11__rater_6.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_05489__rater_11__rater_9](cases/essay_05489__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_05594__rater_11__rater_6](cases/essay_05594__rater_11__rater_6.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_06504__rater_1__rater_2](cases/essay_06504__rater_1__rater_2.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_06529__rater_1__rater_2](cases/essay_06529__rater_1__rater_2.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_06531__rater_1__rater_2](cases/essay_06531__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 2 / 3
- [essay_06533__rater_1__rater_2](cases/essay_06533__rater_1__rater_2.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_06553__rater_1__rater_2](cases/essay_06553__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_06571__rater_1__rater_2](cases/essay_06571__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06572__rater_1__rater_2](cases/essay_06572__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 3 / 2
- [essay_06574__rater_1__rater_2](cases/essay_06574__rater_1__rater_2.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_06577__rater_1__rater_2](cases/essay_06577__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06592__rater_1__rater_2](cases/essay_06592__rater_1__rater_2.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_06611__rater_1__rater_2](cases/essay_06611__rater_1__rater_2.md) — 2点差、実 4 / 2、参照理由 3 / 3
- [essay_06622__rater_1__rater_5](cases/essay_06622__rater_1__rater_5.md) — 2点差、実 3 / 5、参照理由 1 / 3
- [essay_06627__rater_1__rater_5](cases/essay_06627__rater_1__rater_5.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_06634__rater_10__rater_11](cases/essay_06634__rater_10__rater_11.md) — 2点差、実 2 / 4、参照理由 2 / 3
- [essay_06640__rater_10__rater_11](cases/essay_06640__rater_10__rater_11.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_06645__rater_10__rater_11](cases/essay_06645__rater_10__rater_11.md) — 2点差、実 5 / 3、参照理由 0 / 2
- [essay_06651__rater_10__rater_11](cases/essay_06651__rater_10__rater_11.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_06654__rater_10__rater_11](cases/essay_06654__rater_10__rater_11.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_06657__rater_10__rater_11](cases/essay_06657__rater_10__rater_11.md) — 2点差、実 3 / 5、参照理由 0 / 3
- [essay_06664__rater_10__rater_11](cases/essay_06664__rater_10__rater_11.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06668__rater_10__rater_11](cases/essay_06668__rater_10__rater_11.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06671__rater_10__rater_11](cases/essay_06671__rater_10__rater_11.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06672__rater_10__rater_11](cases/essay_06672__rater_10__rater_11.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_06686__rater_10__rater_2](cases/essay_06686__rater_10__rater_2.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_06724__rater_12__rater_27](cases/essay_06724__rater_12__rater_27.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_06748__rater_12__rater_13](cases/essay_06748__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_06762__rater_12__rater_13](cases/essay_06762__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 2 / 0
- [essay_06763__rater_12__rater_13](cases/essay_06763__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 2 / 1
- [essay_06765__rater_12__rater_13](cases/essay_06765__rater_12__rater_13.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06766__rater_12__rater_13](cases/essay_06766__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_06770__rater_12__rater_13](cases/essay_06770__rater_12__rater_13.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06777__rater_12__rater_13](cases/essay_06777__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_06779__rater_12__rater_13](cases/essay_06779__rater_12__rater_13.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_06783__rater_12__rater_13](cases/essay_06783__rater_12__rater_13.md) — 2点差、実 2 / 4、参照理由 2 / 2
- [essay_06787__rater_12__rater_13](cases/essay_06787__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_06790__rater_12__rater_13](cases/essay_06790__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_06795__rater_12__rater_13](cases/essay_06795__rater_12__rater_13.md) — 2点差、実 2 / 4、参照理由 3 / 0
- [essay_06796__rater_12__rater_13](cases/essay_06796__rater_12__rater_13.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_06808__rater_12__rater_15](cases/essay_06808__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06810__rater_12__rater_22](cases/essay_06810__rater_12__rater_22.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06818__rater_12__rater_22](cases/essay_06818__rater_12__rater_22.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_06823__rater_12__rater_22](cases/essay_06823__rater_12__rater_22.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_06826__rater_12__rater_22](cases/essay_06826__rater_12__rater_22.md) — 2点差、実 5 / 3、参照理由 2 / 2
- [essay_06849__rater_12__rater_24](cases/essay_06849__rater_12__rater_24.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_06856__rater_13__rater_27](cases/essay_06856__rater_13__rater_27.md) — 2点差、実 4 / 2、参照理由 3 / 1
- [essay_06859__rater_13__rater_27](cases/essay_06859__rater_13__rater_27.md) — 2点差、実 4 / 2、参照理由 0 / 2
- [essay_06866__rater_13__rater_27](cases/essay_06866__rater_13__rater_27.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_06868__rater_13__rater_27](cases/essay_06868__rater_13__rater_27.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_06870__rater_13__rater_27](cases/essay_06870__rater_13__rater_27.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_06872__rater_13__rater_27](cases/essay_06872__rater_13__rater_27.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_06877__rater_13__rater_27](cases/essay_06877__rater_13__rater_27.md) — 2点差、実 5 / 3、参照理由 3 / 1
- [essay_06896__rater_13__rater_27](cases/essay_06896__rater_13__rater_27.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06928__rater_13__rater_14](cases/essay_06928__rater_13__rater_14.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_06934__rater_12__rater_15](cases/essay_06934__rater_12__rater_15.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_06939__rater_12__rater_15](cases/essay_06939__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_06944__rater_12__rater_15](cases/essay_06944__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 3 / 0
- [essay_06952__rater_12__rater_15](cases/essay_06952__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_06958__rater_12__rater_15](cases/essay_06958__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 2 / 3
- [essay_06966__rater_12__rater_15](cases/essay_06966__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_06974__rater_12__rater_15](cases/essay_06974__rater_12__rater_15.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07032__rater_15__rater_24](cases/essay_07032__rater_15__rater_24.md) — 2点差、実 3 / 1、参照理由 0 / 3
- [essay_07052__rater_17__rater_20](cases/essay_07052__rater_17__rater_20.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_07058__rater_12__rater_18](cases/essay_07058__rater_12__rater_18.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_07062__rater_12__rater_18](cases/essay_07062__rater_12__rater_18.md) — 2点差、実 2 / 4、参照理由 2 / 3
- [essay_07063__rater_12__rater_18](cases/essay_07063__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_07067__rater_12__rater_18](cases/essay_07067__rater_12__rater_18.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_07074__rater_12__rater_18](cases/essay_07074__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07080__rater_12__rater_18](cases/essay_07080__rater_12__rater_18.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_07087__rater_12__rater_18](cases/essay_07087__rater_12__rater_18.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_07093__rater_12__rater_18](cases/essay_07093__rater_12__rater_18.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_07095__rater_12__rater_18](cases/essay_07095__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07103__rater_12__rater_18](cases/essay_07103__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07104__rater_12__rater_18](cases/essay_07104__rater_12__rater_18.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07114__rater_12__rater_18](cases/essay_07114__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07115__rater_12__rater_18](cases/essay_07115__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07117__rater_12__rater_18](cases/essay_07117__rater_12__rater_18.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07120__rater_12__rater_18](cases/essay_07120__rater_12__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07135__rater_13__rater_18](cases/essay_07135__rater_13__rater_18.md) — 2点差、実 4 / 2、参照理由 2 / 2
- [essay_07139__rater_13__rater_18](cases/essay_07139__rater_13__rater_18.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_07140__rater_13__rater_18](cases/essay_07140__rater_13__rater_18.md) — 2点差、実 5 / 3、参照理由 0 / 0
- [essay_07141__rater_13__rater_18](cases/essay_07141__rater_13__rater_18.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_07142__rater_13__rater_18](cases/essay_07142__rater_13__rater_18.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_07144__rater_13__rater_18](cases/essay_07144__rater_13__rater_18.md) — 2点差、実 5 / 3、参照理由 0 / 2
- [essay_07157__rater_15__rater_18](cases/essay_07157__rater_15__rater_18.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07160__rater_15__rater_18](cases/essay_07160__rater_15__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07165__rater_15__rater_18](cases/essay_07165__rater_15__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07171__rater_15__rater_18](cases/essay_07171__rater_15__rater_18.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_07178__rater_15__rater_18](cases/essay_07178__rater_15__rater_18.md) — 2点差、実 4 / 2、参照理由 2 / 1
- [essay_07179__rater_15__rater_18](cases/essay_07179__rater_15__rater_18.md) — 2点差、実 3 / 1、参照理由 3 / 3
- [essay_07180__rater_15__rater_18](cases/essay_07180__rater_15__rater_18.md) — 2点差、実 4 / 2、参照理由 3 / 2
- [essay_07192__rater_15__rater_18](cases/essay_07192__rater_15__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07202__rater_15__rater_18](cases/essay_07202__rater_15__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07205__rater_16__rater_18](cases/essay_07205__rater_16__rater_18.md) — 2点差、実 3 / 5、参照理由 3 / 1
- [essay_07226__rater_18__rater_22](cases/essay_07226__rater_18__rater_22.md) — 2点差、実 5 / 3、参照理由 1 / 3
- [essay_07231__rater_18__rater_24](cases/essay_07231__rater_18__rater_24.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_07233__rater_18__rater_24](cases/essay_07233__rater_18__rater_24.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_07236__rater_19__rater_27](cases/essay_07236__rater_19__rater_27.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_07249__rater_19__rater_27](cases/essay_07249__rater_19__rater_27.md) — 2点差、実 5 / 3、参照理由 0 / 3
- [essay_07251__rater_19__rater_27](cases/essay_07251__rater_19__rater_27.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_07254__rater_19__rater_27](cases/essay_07254__rater_19__rater_27.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_07261__rater_12__rater_19](cases/essay_07261__rater_12__rater_19.md) — 2点差、実 2 / 4、参照理由 3 / 2
- [essay_07265__rater_12__rater_19](cases/essay_07265__rater_12__rater_19.md) — 2点差、実 3 / 5、参照理由 1 / 0
- [essay_07285__rater_13__rater_19](cases/essay_07285__rater_13__rater_19.md) — 2点差、実 2 / 4、参照理由 2 / 1
- [essay_07286__rater_15__rater_19](cases/essay_07286__rater_15__rater_19.md) — 2点差、実 3 / 1、参照理由 1 / 3
- [essay_07306__rater_15__rater_19](cases/essay_07306__rater_15__rater_19.md) — 2点差、実 4 / 2、参照理由 3 / 2
- [essay_07331__rater_16__rater_19](cases/essay_07331__rater_16__rater_19.md) — 2点差、実 2 / 4、参照理由 1 / 3
- [essay_07342__rater_16__rater_19](cases/essay_07342__rater_16__rater_19.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_07344__rater_16__rater_19](cases/essay_07344__rater_16__rater_19.md) — 2点差、実 2 / 4、参照理由 3 / 3
- [essay_07366__rater_16__rater_19](cases/essay_07366__rater_16__rater_19.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07375__rater_16__rater_19](cases/essay_07375__rater_16__rater_19.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07441__rater_18__rater_19](cases/essay_07441__rater_18__rater_19.md) — 2点差、実 5 / 3、参照理由 1 / 0
- [essay_07448__rater_18__rater_19](cases/essay_07448__rater_18__rater_19.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_07451__rater_18__rater_19](cases/essay_07451__rater_18__rater_19.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07459__rater_18__rater_19](cases/essay_07459__rater_18__rater_19.md) — 2点差、実 3 / 5、参照理由 3 / 1
- [essay_07472__rater_18__rater_19](cases/essay_07472__rater_18__rater_19.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07475__rater_18__rater_19](cases/essay_07475__rater_18__rater_19.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_07476__rater_18__rater_19](cases/essay_07476__rater_18__rater_19.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07495__rater_1__rater_2](cases/essay_07495__rater_1__rater_2.md) — 2点差、実 3 / 5、参照理由 2 / 2
- [essay_07496__rater_1__rater_2](cases/essay_07496__rater_1__rater_2.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07514__rater_2__rater_7](cases/essay_07514__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07521__rater_11__rater_21](cases/essay_07521__rater_11__rater_21.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07525__rater_11__rater_21](cases/essay_07525__rater_11__rater_21.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_07528__rater_11__rater_21](cases/essay_07528__rater_11__rater_21.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07551__rater_10__rater_23](cases/essay_07551__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07552__rater_10__rater_23](cases/essay_07552__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_07554__rater_10__rater_23](cases/essay_07554__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 2 / 2
- [essay_07555__rater_10__rater_23](cases/essay_07555__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07561__rater_10__rater_23](cases/essay_07561__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_07563__rater_10__rater_23](cases/essay_07563__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_07564__rater_10__rater_23](cases/essay_07564__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07566__rater_10__rater_23](cases/essay_07566__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 3 / 3
- [essay_07569__rater_10__rater_23](cases/essay_07569__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07571__rater_10__rater_23](cases/essay_07571__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_07576__rater_10__rater_23](cases/essay_07576__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_07577__rater_10__rater_23](cases/essay_07577__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 2 / 3
- [essay_07580__rater_10__rater_23](cases/essay_07580__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07584__rater_10__rater_23](cases/essay_07584__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_07588__rater_10__rater_23](cases/essay_07588__rater_10__rater_23.md) — 2点差、実 2 / 4、参照理由 2 / 1
- [essay_07590__rater_10__rater_23](cases/essay_07590__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07616__rater_10__rater_23](cases/essay_07616__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07635__rater_10__rater_23](cases/essay_07635__rater_10__rater_23.md) — 2点差、実 4 / 2、参照理由 3 / 1
- [essay_07638__rater_10__rater_23](cases/essay_07638__rater_10__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_07665__rater_2__rater_23](cases/essay_07665__rater_2__rater_23.md) — 2点差、実 3 / 1、参照理由 3 / 3
- [essay_07666__rater_2__rater_23](cases/essay_07666__rater_2__rater_23.md) — 2点差、実 3 / 5、参照理由 1 / 1
- [essay_07682__rater_2__rater_23](cases/essay_07682__rater_2__rater_23.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07687__rater_2__rater_23](cases/essay_07687__rater_2__rater_23.md) — 2点差、実 3 / 5、参照理由 3 / 2
- [essay_07711__rater_24__rater_27](cases/essay_07711__rater_24__rater_27.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_07758__rater_13__rater_26](cases/essay_07758__rater_13__rater_26.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_07759__rater_13__rater_26](cases/essay_07759__rater_13__rater_26.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_07782__rater_3__rater_4](cases/essay_07782__rater_3__rater_4.md) — 2点差、実 1 / 3、参照理由 3 / 3
- [essay_07808__rater_2__rater_4](cases/essay_07808__rater_2__rater_4.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_07809__rater_2__rater_4](cases/essay_07809__rater_2__rater_4.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_07833__rater_2__rater_4](cases/essay_07833__rater_2__rater_4.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_07850__rater_4__rater_7](cases/essay_07850__rater_4__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_07869__rater_1__rater_5](cases/essay_07869__rater_1__rater_5.md) — 2点差、実 2 / 4、参照理由 1 / 3
- [essay_07876__rater_1__rater_5](cases/essay_07876__rater_1__rater_5.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_07953__rater_27__rater_6](cases/essay_07953__rater_27__rater_6.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_07973__rater_27__rater_6](cases/essay_07973__rater_27__rater_6.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_07984__rater_27__rater_6](cases/essay_07984__rater_27__rater_6.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_08036__rater_1__rater_6](cases/essay_08036__rater_1__rater_6.md) — 2点差、実 5 / 3、参照理由 3 / 1
- [essay_08043__rater_1__rater_6](cases/essay_08043__rater_1__rater_6.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_08045__rater_1__rater_6](cases/essay_08045__rater_1__rater_6.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_08046__rater_1__rater_6](cases/essay_08046__rater_1__rater_6.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_08054__rater_1__rater_6](cases/essay_08054__rater_1__rater_6.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_08074__rater_1__rater_6](cases/essay_08074__rater_1__rater_6.md) — 2点差、実 4 / 2、参照理由 3 / 3
- [essay_08095__rater_1__rater_6](cases/essay_08095__rater_1__rater_6.md) — 2点差、実 2 / 4、参照理由 0 / 1
- [essay_08105__rater_1__rater_6](cases/essay_08105__rater_1__rater_6.md) — 2点差、実 3 / 5、参照理由 0 / 3
- [essay_08128__rater_11__rater_6](cases/essay_08128__rater_11__rater_6.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_08131__rater_11__rater_6](cases/essay_08131__rater_11__rater_6.md) — 2点差、実 1 / 3、参照理由 3 / 3
- [essay_08135__rater_11__rater_6](cases/essay_08135__rater_11__rater_6.md) — 2点差、実 1 / 3、参照理由 0 / 0
- [essay_08142__rater_11__rater_6](cases/essay_08142__rater_11__rater_6.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_08150__rater_11__rater_6](cases/essay_08150__rater_11__rater_6.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_08164__rater_11__rater_6](cases/essay_08164__rater_11__rater_6.md) — 2点差、実 1 / 3、参照理由 3 / 3
- [essay_08165__rater_11__rater_6](cases/essay_08165__rater_11__rater_6.md) — 2点差、実 2 / 4、参照理由 3 / 1
- [essay_08180__rater_2__rater_6](cases/essay_08180__rater_2__rater_6.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_08237__rater_2__rater_6](cases/essay_08237__rater_2__rater_6.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08278__rater_3__rater_6](cases/essay_08278__rater_3__rater_6.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_08286__rater_3__rater_6](cases/essay_08286__rater_3__rater_6.md) — 2点差、実 1 / 3、参照理由 3 / 1
- [essay_08289__rater_3__rater_6](cases/essay_08289__rater_3__rater_6.md) — 2点差、実 5 / 3、参照理由 2 / 1
- [essay_08303__rater_3__rater_6](cases/essay_08303__rater_3__rater_6.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_08314__rater_3__rater_6](cases/essay_08314__rater_3__rater_6.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_08373__rater_10__rater_7](cases/essay_08373__rater_10__rater_7.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_08377__rater_10__rater_7](cases/essay_08377__rater_10__rater_7.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_08380__rater_10__rater_7](cases/essay_08380__rater_10__rater_7.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_08386__rater_10__rater_7](cases/essay_08386__rater_10__rater_7.md) — 2点差、実 3 / 5、参照理由 1 / 2
- [essay_08421__rater_2__rater_7](cases/essay_08421__rater_2__rater_7.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_08466__rater_2__rater_7](cases/essay_08466__rater_2__rater_7.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_08479__rater_2__rater_7](cases/essay_08479__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08484__rater_2__rater_7](cases/essay_08484__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 1
- [essay_08493__rater_2__rater_7](cases/essay_08493__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 2 / 3
- [essay_08505__rater_2__rater_7](cases/essay_08505__rater_2__rater_7.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_08528__rater_2__rater_7](cases/essay_08528__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08562__rater_2__rater_7](cases/essay_08562__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08569__rater_2__rater_7](cases/essay_08569__rater_2__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08593__rater_21__rater_7](cases/essay_08593__rater_21__rater_7.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_08597__rater_21__rater_7](cases/essay_08597__rater_21__rater_7.md) — 2点差、実 3 / 5、参照理由 3 / 0
- [essay_08611__rater_23__rater_7](cases/essay_08611__rater_23__rater_7.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_08620__rater_23__rater_7](cases/essay_08620__rater_23__rater_7.md) — 2点差、実 5 / 3、参照理由 2 / 2
- [essay_08664__rater_4__rater_7](cases/essay_08664__rater_4__rater_7.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_08683__rater_4__rater_7](cases/essay_08683__rater_4__rater_7.md) — 2点差、実 4 / 2、参照理由 1 / 3
- [essay_08694__rater_4__rater_7](cases/essay_08694__rater_4__rater_7.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_08733__rater_7__rater_9](cases/essay_08733__rater_7__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_08738__rater_7__rater_9](cases/essay_08738__rater_7__rater_9.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_08743__rater_7__rater_9](cases/essay_08743__rater_7__rater_9.md) — 2点差、実 5 / 3、参照理由 0 / 3
- [essay_08744__rater_7__rater_9](cases/essay_08744__rater_7__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_08745__rater_7__rater_9](cases/essay_08745__rater_7__rater_9.md) — 2点差、実 5 / 3、参照理由 3 / 2
- [essay_08756__rater_11__rater_8](cases/essay_08756__rater_11__rater_8.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08765__rater_11__rater_8](cases/essay_08765__rater_11__rater_8.md) — 2点差、実 3 / 5、参照理由 3 / 3
- [essay_08768__rater_11__rater_8](cases/essay_08768__rater_11__rater_8.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_08787__rater_8__rater_9](cases/essay_08787__rater_8__rater_9.md) — 2点差、実 5 / 3、参照理由 0 / 3
- [essay_08804__rater_10__rater_9](cases/essay_08804__rater_10__rater_9.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_08810__rater_10__rater_9](cases/essay_08810__rater_10__rater_9.md) — 2点差、実 5 / 3、参照理由 3 / 3
- [essay_08813__rater_11__rater_9](cases/essay_08813__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 2
- [essay_08815__rater_11__rater_9](cases/essay_08815__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 0
- [essay_08816__rater_11__rater_9](cases/essay_08816__rater_11__rater_9.md) — 2点差、実 3 / 5、参照理由 0 / 3
- [essay_08822__rater_11__rater_9](cases/essay_08822__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_08830__rater_11__rater_9](cases/essay_08830__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_08831__rater_11__rater_9](cases/essay_08831__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 0
- [essay_08833__rater_11__rater_9](cases/essay_08833__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 3
- [essay_08839__rater_11__rater_9](cases/essay_08839__rater_11__rater_9.md) — 2点差、実 2 / 4、参照理由 3 / 3
- [essay_08840__rater_11__rater_9](cases/essay_08840__rater_11__rater_9.md) — 2点差、実 2 / 4、参照理由 0 / 2
- [essay_08843__rater_11__rater_9](cases/essay_08843__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 1 / 0
- [essay_08846__rater_11__rater_9](cases/essay_08846__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 2
- [essay_08847__rater_11__rater_9](cases/essay_08847__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 0
- [essay_08849__rater_11__rater_9](cases/essay_08849__rater_11__rater_9.md) — 2点差、実 2 / 4、参照理由 0 / 0
- [essay_08855__rater_11__rater_9](cases/essay_08855__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 3 / 2
- [essay_08864__rater_11__rater_9](cases/essay_08864__rater_11__rater_9.md) — 2点差、実 2 / 4、参照理由 0 / 3
- [essay_08870__rater_11__rater_9](cases/essay_08870__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 2
- [essay_08878__rater_11__rater_9](cases/essay_08878__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 3
- [essay_08881__rater_11__rater_9](cases/essay_08881__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 0 / 3
- [essay_08884__rater_11__rater_9](cases/essay_08884__rater_11__rater_9.md) — 2点差、実 4 / 2、参照理由 2 / 2
- [essay_08888__rater_23__rater_9](cases/essay_08888__rater_23__rater_9.md) — 2点差、実 4 / 2、参照理由 1 / 1
- [essay_08889__rater_23__rater_9](cases/essay_08889__rater_23__rater_9.md) — 2点差、実 5 / 3、参照理由 2 / 3
## 最終整合性確認

259ペアのレポート、517対象の処理、全938検証済み参照理由への指標計算を確認しました。

[最終監査](integrity_validation.json) / [採点者別予測誤差](prediction_error_by_rater.csv) / [スコア分布](prediction_score_distribution.csv) / [理由指標集計](reasoning_metrics_summary.csv)

最終監査・枠別の失敗理由も含めた一括再開は `bash scripts/run_human_score_disagreement.sh`。段階別に再開した場合は最後に `python scripts/validate_human_score_disagreement.py` を実行してください。

チャットの接続から独立して実行する場合は `bash scripts/start_human_disagreement_detached.sh`。tmuxセッション `recsaver-human-disagreement`、runner_exit_code.txt、run.logで稼働と終了コードを確認できます。

運用設定: 生成・検証のスケジューラバッチ数を既存reasoning_eval_largeの10から64へ変更しました。各リクエストの入力・モデル・サンプリングパラメータ・seedは維持しています。途中のメモリ確保量・バッチ数の変更とシリアライズ修正はmetadata.jsonの移行記録および各保存ログを参照してください。

seedの区別: 再利用予測はfull_prediction_experimentの基準seed=20260814と既存の条件別規則を保持しています。新規予測は追加実験のrequest_seed規則（基準seed=20260916、stage=prediction）、参照生成・自己検証はreasoning_eval_largeと同じrequest_seed規則（基準seed=20260916）です。新規予測のseed規則は既存全件予測と異なります。実際のリクエストseedは全試行に保存しています。再利用判定はモデルID・量子化・文脈長・入力・履歴・生成パラメータの一致を検証し、参照理由はseedも照合しています。GPU確保量とバッチ数は運用差として分離しており、異なるバッチ構成でのビット単位の再現は保証しません。

最終監査の本文照合で、匿名化の版が複数ある3ケース・4採点者側に参照入力の版不一致を検出しました。参照生成も予測・自己検証と同じ共通本文を使うよう修正し、該当対象の参照・検証・指標だけを再実行して再監査しました。旧30生成試行・11検証試行・11指標は削除せず隔離し、現行集計から除外しました。[修正・隔離の記録](reference_text_fix/migration.json)を参照してください。

raw行内での暫定3点差15件のうち8件は無効Overallを含み、有効は7件でした。raw行内の2点差258件のうち7件は無効Overallを含み、有効251件です。同一Filenameの版を対応づけた別行間の採点者ペアが1件加わり、2点差は252ペアとなりました。最大4点差の1件も無効Overallを含むため除外しています。
