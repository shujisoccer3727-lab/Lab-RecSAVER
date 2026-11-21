# Stage 3 v1.2：3A個別確認 → 3B統合

比較元と正本は `run_manifest.json`、結果は `validation_report.md` を参照。
Stage 1・2は実行しない。主実行には意味評価による修正や再生成を入れない。

WSL Ubuntu / Python 3.10（既存conda `qwen3`）でリポジトリルートから:

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_2_pipeline_20261121
$PY "$DIR/code/test_checks.py"
# 初回のみ。保存結果のあるディレクトリで再生成しない。
$PY "$DIR/code/run.py" launch
```

生成完了後の再点検とレポート再作成（モデル呼び出しなし）:

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/quote_diagnostics.py"
$PY "$DIR/code/report.py"
$PY "$DIR/code/verify.py"
```

最後のverifyは追加コードの最終ハッシュもmanifestへ記録する。
生成時コードのハッシュはcode_sha256_beforeに保持する。
生成後の不正配列を扱う防御処理の追加はmanifestへ記録し、
実際の保存済み所見・受け渡し・検査結果が同じになることを確認した。

3Aは2つの独立した入力を同一エンジンでバッチ処理し、3Bは検査後に
別リクエストとして1回処理する。全要求はuserメッセージ1件、
既定chat templateを使う。各要求のseedは比較元Stage3と同じ925847335。
各要求の出力上限も同じ5000。正本の置換は `{{INPUT_JSON}}` のみ。
候補のrecord_idは既に実ID表記なので同値正規化し、対応を保存する。

検査不合格の所見・issueは原出力を保持して受け渡しから除外する。
3A全体の形式エラーと所見単位のエラーを区別する。
原文一致は意味的な支持を保証しない。意味はCodexが別に暫定評価する。
同一引用の繰り返しは1件とし、重なる引用範囲を独立証拠に数えない。

別の再現実験では新しいディレクトリを使い、`OUT` と比較コミット条件を
確認する。保存済みの `raw.txt` を削除して選別再生成しない。
GPUの実行順序により、同じseedでも完全なトークン再現性は保証しない。
