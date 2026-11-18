# 採点者フィードバック予備実験v2

実行範囲: pilot。条件A=Traitなし、B=本人Traitあり。新規理由2候補／対象・条件。

- report.md: 採点者別にA/Bの理由比較・5要素本文・引用と公式条件・対応表
- assessment.md: 件数・条件別の採否差・所見と制約
- pilot_results.json / pilot_summary.json: 機械可読の全結果と集計
- inputs.json / selection.json / input_checks.json: 元データ照合・選択・欠損
- conditions.json: 公式条件ID・原文・親段階・文字位置
- conditions/A, conditions/B: 別々の候補・マスク履歴・実検証入力・最終結果
- stages/: 生成・検証・意味的点検・候補整理・統合・全文比較・文章化の中間出力
- calls.jsonl / context_checks.jsonl: 全呼出し・失敗・seed・日時・コンテキスト検査
- resolved_config.json / code/: 実行設定とコード・プロンプトの版

旧実験を上書きせず、最終実験・評価モデルの学習は行っていない。
再開: python -m src.recsaver.rater_feedback_pilot_v2 full
同一入力・設定・プロンプトの成功段階のみ再利用。変更する場合は新しい版・実行先を使う。
