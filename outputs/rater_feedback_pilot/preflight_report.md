# 採点者フィードバック予備検証：入力と実行準備

確認日時: 2026-11-14T12:48:05.903553+09:00

## 実行状況

入力監査・選択・プロンプト保存・引用照合コードのテストは完了。Qwenの追加ロードは既存LLMサービスのGPU占有と競合したため中断。フィードバック生成は未完了。

既存ローカルサービスの認証情報をプロセス情報から取得する試行は、自動承認審査で拒否され、実行されていない。ユーザーはサービス再利用を承認せず、Qwen用GPUが空くまで実生成を保留するよう指定した。認証取得用の未実行スクリプトは削除した。

## 確認できたこと

- 自己検証済みプール: 2056行。全件の本文・採点者ID・観測Overall・当時の自己検証入力一致を確認。
- 通常のPrediction Reasoning、後続のtendency明示生成、未検証候補は入力に使用していない。
- 採点者IDはrawのRater_1／Rater_2の値。対象IDは0始まりの論理source行番号とrater_positionから復元。
- 対象本文と当時の3件の履歴は別フィールドで保存。引用は対象本文に限定して照合。
- 参照推論はOverallについて、観測Overallを与えて生成した事後的説明。自己検証は得点再構成であり、本文による説明の正しさを保証しない。
- 元DOCXは不在。保存済みOverall原文・構造化JSON・当時の保存プロンプトを完全一致で照合。DOCXとの真正性は独立検証できない。
- 生成候補ログ不在で自己検証プロンプトから来歴確認した採用済み候補: 19行。

## 選択

seed=20261113。SHA256(seed:rater:ID), then SHA256(seed:essay:target_id); unique text_id_kaggle else Filename else exact Text hash; smallest numeric candidate_index then attempt_index within verified pool; no outcome-based replacement。結果による差し替えなし。代表性を持つ標本ではない。

|採点者|利用可能ユニーク答案|選択答案|観測Overall分布|
|---|---:|---:|---|
|rater_7|59|10|{2: 1, 3: 6, 4: 2, 5: 1}|
|rater_17|7|7|{2: 1, 3: 3, 4: 2, 5: 1}|
|rater_4|24|10|{2: 1, 3: 7, 4: 2}|

全採点者の利用可能答案数: selection.json。入力全文・候補ID・観測得点・履歴: inputs.json。

## 静的引用検査

参照推論に明示された引用候補: 0件。結果はstatic_quote_checks.json。
この件数は引用符付き文字列の検出数であり、根拠不足の割合ではない。意味的支持、履歴混同、複数答案の傾向、④と⑤の品質はモデル生成後に検討する。

## 再開

既存Qwen用にGPUが空いてから、リポジトリルートで実行:

```bash
conda activate qwen3
python -m src.recsaver.rater_feedback_pilot pilot
# outputs/rater_feedback_pilot/report.mdとcalls.jsonlを確認しpilot_review.jsonを保存後:
python -m src.recsaver.rater_feedback_pilot remaining
```

成功済み段階は入力・プロンプトfingerprint一致時に再利用。失敗応答はcalls.jsonlに保存。入力やプロンプト変更時は新しいoutput_dirを使い既存出力を残す。

## 今後の個別理由プロンプト改善候補

- 主張ごとに対象／履歴のscope、対象ID、原文引用、位置を構造化して保存。
- 本文の特徴だけでなく、評価方向と観測Overallを説明する条件との関係を明示。
- 程度・頻度・適切さ・伝達阻害を判断する範囲と反例を必須化。短い一節で全体判断を断定させない。
- ルーブリック条件の出典ID、解釈差、証拠不足、判断保留を出力。
- 得点による自己検証と、引用存在・意味的支持の検証を区別。

実生成前の設計上の改善候補であり、生成結果から確認済みの知見とは扱わない。