# Stage 3 v1.1 固定入力検証

比較元は `outputs/recsaver_prompt_v1_2_value_mask_20261121/stage3/rater_7/`。
Stage 1・2は実行しない。比較元は読み取りのみ。正本の英語本文は変更しない。

実行環境は WSL Ubuntu の既存 conda `qwen3`。リポジトリルートから:

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_1_validation_20261121
$PY "$DIR/code/test_audit.py"
$PY "$DIR/code/run.py" audit
$PY "$DIR/code/report.py"
$PY "$DIR/code/finalize.py"
```

`audit` はモデルをロードせず、保存済み両版を再検査する。
初回生成には `$PY "$DIR/code/run.py" launch` を使用した。
既存の `result.json` / `raw.txt` を書き換える再生成はしない。
独立した再現実験は、この実験ディレクトリを変更せず新しいディレクトリを用意し、
`OUT` と固定元のパス、および比較コミットの条件を確認すること。
乱数seedを固定してもGPUの実行順序によるトークン単位の一致は保証しない。

生成処理は既存 `outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py`
の Engine を再利用し、Stage 3のスキーマ判定だけを追加コードに置き換えた。
旧スキーマは既存検査、新スキーマはv1.1の必須フィールド・型の検査を用いる。
帯・観点・引用・観測値・IDの対応は両版に適用する別検査に保存する。
検査用の合成データはモデルへ渡さず、実験結果にも加算しない。
