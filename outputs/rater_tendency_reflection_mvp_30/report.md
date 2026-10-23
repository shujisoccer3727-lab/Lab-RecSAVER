# ルーブリック比較・振り返り情報のPrompt拡張MVP

同じ固定30件でgrounded v2と比較。変更はPrompt本文と出力先だけ。
既存のrun/render/parse/VLLMGenerator、JSON構造、モデル、入力K=3、Overallと6 Traits、履歴ID、Rubric、対象Essay、Gold除外を維持。
temperature=.2、top_p=.8、max_tokens=768、max_model_len=8192、generation seedも同じ。
生成された1つのJSONのtendency_connectionにRubricとの関係、scoring_explanationに建設的な振り返りを求めた。
別スコア・別LLM・Profile事前生成・追加推論ステージはなし。既存と同じJSON失敗時retry上限1のみ維持。

## 実行結果

```json
{
  "attempted": 30,
  "schema_valid": 30,
  "retries": 0,
  "length_finish_attempts": 0,
  "output_tokens_min_median_max": [
    364,
    428.5,
    531
  ],
  "score_changes_vs_grounded_v2": 1,
  "wording_presence_counts": {
    "rubric_mention": 11,
    "reflection_wording": 30,
    "no_discrepancy_wording": 0,
    "bias_or_fairness_wording_for_review": 0
  }
}
```

grounded_v2_comparison.csv:
```
Condition,N,Accuracy,MAE,RMSE,QWK
grounded_v2,30,0.5333333333333333,0.5,0.752772652709081,0.13559322033898236
reflection,30,0.5666666666666667,0.4666666666666667,0.7302967433402214,0.2131147540983641

```

## 読み方

reflection_structure_checks.csvは表現の有無の機械検査であり、内容の正しさや有用性を保証しない。
全30件の比較と人手評価欄はreview_all_30.md。人手評価は未実施。
小規模な同一対象での出力変更の影響を確認したもので、採点者の真の思考過程や偏り、振り返りによる改善を実証しない。

## 根拠と再現

Prompt: prompts/en/rater_tendency_joint_prediction_reflection_mvp.txt。
実装: rater_tendency_reflection_mvp.setup/main（既存core.runを呼ぶ）。
integrity_audit.csvは全30件の入力部分同一性とGold改変不変性。experiment_config.jsonのSHA256を実行後も確認。
既存Prompt・Config・Predictionは上書きせず、比較に既存結果を再利用。
再開: python -m src.recsaver.rater_tendency_reflection_mvp launch。


## 内容の予備確認と限界

AIによる予備確認であり、人手評価ではない。全30件に再確認や長所の考慮を促す文が出力された。
8814:1では誤りが実際に意思伝達を妨げるかと、論証・語彙の長所を確認するよう促す。
ただし、30件で繰り返される「誤りが意思伝達を妨げるか確認する」という助言は一般的になりやすく、個々のEssayに特有の振り返りとして十分かは未検証。
reasoningでrubricという語を含むのは11件。語の不在は比較内容の不在を直ちには意味しないが、具体的な基準との対応の説明は弱い例がある。
「no clear discrepancy」等を明示する出力は0件。Promptに制約を書いたことと、出力がその制約を満たしたことは区別する。
過去履歴に見られた事実と、そこから推定した採点者固有の傾向の区別も依然として弱い例がある。
全30件のrater_tendency.uncertaintyには根拠不足の留保があるが、その一方でdescriptionやconnectionでは傾向を断定する出力もあり、説明内部の整合性に確認が必要。
biased/unfair等の単語はreasoning内では0件。機械検出だけで全ての不適切な断定がないとは結論しない。
今回、別Rubric-only scoreや比較LLMは導入しておらず、正規スキーマの予測スコアは1つのみ。
全30件で再試行0回のため、各対象はLLM生成1回で終了した。
旧版よりAccuracyが1件分上がったが、30件の探索的な結果であり改善の証明ではない。
次の段階に進む前に、全30件の人手確認でRubric比較の具体性、差異なし／不明の明示、建設性、誤指摘の有無を確認することを推奨。
1,000件への拡大やPrompt再修正は今回実施していない。
原文・和訳の例はreflection_examples_bilingual.md。入力・モデル・生成設定は変更していないが、Promptが異なるため予測値まで不変とは限らない。


予測変更対象:

```json
[
  {
    "target_id": "8355:1",
    "grounded_v2": 3,
    "reflection": 4
  }
]
```
