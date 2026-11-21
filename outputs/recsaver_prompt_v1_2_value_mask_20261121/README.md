# v1.2：対象得点の値だけをマスクする方式

検証完了。保存済み6候補は15値をマスクし5/6入力通過、対象自身の履歴参照1件を隔離。新規6候補は15値をマスクし6/6入力通過・Stage2有効推定6/6・一致採用4/6。2答案でStage3初回評価まで実施したが、Overall4の基準を3と整合させる等の内容問題があり、完成稿としては使わない。`validation_report.md`参照。

比較元はコミット`c52617a669149b895c412165591d71257e4c0e8c`、`outputs/recsaver_prompt_v1_1_validation_20261120/`。原出力・履歴・旧成果物は変更しない。Stage 1=v1.2、Stage 2=v1.1、Stage 3=v1.0の正本を使用し、`{{INPUT_JSON}}`だけを置換する。

`code/masking.py`がscore_free_analysisをdeep copyし、対象に帰属する明示得点・番号付き帯/範囲の値を`□`に置換する。数字と英語の数詞に対応。文・節の削除、ID/引用/履歴得点の修復は行わない。JSON path・元/変更後・値の位置・理由は`mask_audit.json`に保存し、モデルには渡さない。

実際の履歴ID集合を照合し、不正な履歴参照、明示的な履歴得点との等値、計算、固有帯の名称、曖昧な帰属は隔離する。自動判定に加え、Codexがマスク後の全体を点検してからStage 2を許可する。一般的な特徴の類似性と、得点が等しいという明示的な関係は区別する。検出器の網羅性を保証するものではない。

## 実行手順

リポジトリ直下、WSLの既存環境を使用。

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
EXP=outputs/recsaver_prompt_v1_2_value_mask_20261121
$PY "$EXP/code/run.py" --phase prepare
$PY "$EXP/code/test_masking.py"
# 保存済み6候補・診断A/B/Cを原文で点検してreplay_review.jsonを保存
$PY "$EXP/code/launch.py"
# 新Stage 1完了後、全マスクを点検してmain_mask_review.jsonを保存すると続行
$PY "$EXP/code/audit.py"
$PY "$EXP/code/build_tables.py"
$PY "$EXP/code/finalize.py"
```

`save_replay_review.py`は今回の原文点検を保存するコードで、汎用の自動意味評価器ではない。別の生成結果へ無条件で適用しない。workerは`status.json`と`execution.log`に進捗を残す。result/errorが保存済みの呼出しは再生成しない。rawのみ残る中断は自動上書きせず、調査してから再開する。

## 成果物

- `run_manifest.json`: 正本実パス・SHA-256、比較元全成果物ハッシュ、モデル/seed/生成上限、差異と正本内の指示の併存。
- `saved_v1_1_masks/`: 保存済み6候補の未変更レコード・元分析・マスク後・置換監査。
- `diagnostic_masks/`: 旧A/B/Cの診断用コピーと、等値で復元可能なDの隔離対照。本実行と別管理。
- `stage2_diagnostics/`: マスク後A/B/Cの独立呼出し。採否に含めない。
- `stage1/`, `masks/`, `stage2/`, `external_decisions/`, `stage3/`: 新v1.2の本実行。採否に使う観測値はモデル入力と分離。統合では採用候補のマスク前レコードを使う。
- `masking_tests.json`, `invariant_checks.json`, `source_and_quote_audit.json`: 単体対照と実入力/不変性の検査。
- `candidate_results.csv`, `essay_results.csv`, `validation_report.md`: 本実行の集計と英語原文・和訳・内容評価。

GPU生成前に発見した役割判定の実装バグの修正前コード・監査を`implementation_revision_0/1`に保持した。`limited history`を帰属曖昧と誤認するケースと、後続のhistory言及で対象得点を保護するケースを修正し、回帰対照を追加した。正本・モデル・seedは変更していない。

生成後・本実行Stage2の前に、明示的な履歴得点まで伏せた2箇所を修正した。旧コピーは`implementation_revision_2`、修正手順は`code/repair_masks_revision.py`。原出力を再生成せず、実行済み診断入力も変えずにコピーを再計算した。最終検査は21対照。

今回の新6候補の確定した事前点検は`code/save_main_review.py`で保存した。これは今回の原文に対するCodex点検で、未知の候補の汎用自動判定器ではない。再開は同じ凍結コード・既存結果のスキップで行い、修正前スナップショットへ戻して生成し直さない。

全3答案の観測Overallは3。得点一致と理由の内容品質は分け、Codexの暫定内容点検を人手評価とは呼ばない。マスクで本文所見を保っても、その所見を引用が支えなければ内容改善とは扱わない。
