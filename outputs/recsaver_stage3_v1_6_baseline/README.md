# Stage 3 v1.6 正本・固定2答案の最低ライン検証

比較元: `bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac` の
`outputs/recsaver_stage3_v1_5_baseline_20261122/`。
v1.6はプロンプト改訂番号で、入出力契約のschema_versionは1.5のまま。
指定英文の追記のみ。保存入力・原文区間表・本人の観測得点・公式基準を再利用する。

初回の生成コマンド（実行済み。再実行しない）:

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_6_baseline
$PY "$DIR/code/run.py" launch
```

3A×2を独立入力として一つのバッチ、今回の所見を渡す通し3B×1を一つのバッチで実行。
計3要求、各要求1出力。候補監査はCPUの別経路で、自由文を3Bへ渡さない。
3B入力に位置メタデータを追加しない。追加モデル判定・再生成・手修正・自己検証・SLM改稿なし。

CPUでの再照合（モデル呼び出しなし）:

```bash
$PY "$DIR/code/source_checks.py"
$PY "$DIR/code/verify.py"
$PY "$DIR/code/report.py"
```

`source_checks.json` は比較コミットと保存物の照合・本人のraw得点を記録。
`invariant_checks.json` は実入力・引用・表示・生成設定の機械検査。
`content_review.json` と `validation_report.md` はCodexの暫定的な内容判定。
内容判定を機械検査の合格として扱わない。Bは参照一致と意味的支持の両方が必要。
`raw.txt` / `parsed.json` は生成時のまま。表示は既存コードが別ファイルへ組み立てる。
固定2答案での回帰確認であり、一般性能・複数seed安定性は評価しない。

最終判定・停止理由・次段階は `baseline_decision.json` とレポートに記録する。
