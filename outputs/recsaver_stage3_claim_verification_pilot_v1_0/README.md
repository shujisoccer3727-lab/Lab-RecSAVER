# Stage 3 主張単位自己検証パイロット v1.0

比較元は `2d49a6f4b635cedece5fdf25eda9d2ac9c48cb3d` のStage 3 v1.6。
既存3Bの構造化初稿と同じ入力をA/Bで共有し、Bにだけ原文位置情報を使う3Cを1回追加する。
追加モデル呼び出しと追加位置情報の寄与は個別に識別しない。

対象はselection_manifest.jsonで出力前に固定。
既知ペアは動作確認専用で、Aを保存物から再利用。新規2群は各2答案。
新規要求は3A×4、3B×2、3C×3の計9回。各要求1回、輸送再試行も無効。
3Cが不正ならBを処理失敗とし、Aへ差し替えない。

生成に使ったコマンド（実行済み。再実行しない）：

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_claim_verification_pilot_v1_0
$PY "$DIR/code/test_pipeline.py"
$PY "$DIR/code/pipeline.py" launch
```

旧ランナー固有の「両方Overall=3」という説明を新群へ渡さないため、モデル初期化を推論開始前に1回中断。
中断時の準備要求・プロセス・証拠はinitialization_interruption.json等に保存。推論0、生成出力の破棄0。
新群の限界説明だけを中立な2答案の説明へ変更し、既知ペアの保存入力は維持した。

CPUでの照合・レビュー表生成（モデル呼び出しなし）：

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/export_review.py"
$PY "$DIR/code/report.py"
$PY "$DIR/code/final_integrity.py"
```

review_blind.csv / .jsonは条件名と3C判定を除いたレビュー用出力。
対応表はreview_key.json。実装者であるCodexには条件の事前知識があるため、真の条件盲検とは呼ばない。
review_judgments.jsonの暫定判定は原文・本人得点・公式基準から行い、3C判定を正解に使わない。

各群のsources.jsonは本人の観測値、evidence_spansは原文区間表、input_3b.jsonとA/parsed.jsonは共通初稿、
input_3c.jsonは初稿と出典位置を付けた固定候補、stage3cは実入力・生出力・解析JSON、Bは通過した修正と表示。
source_positions.jsonはコード復元した引用位置と境界。3Aの解釈はupstream_interpretationに分離。
claim_comparison.csvは独立の暫定レビューで分解した命題と出典。保持・置換・新規の未支持主張は別に記録する。

1回のパイロットで終了。再生成、自動プロンプト再調整、追加自動採点モデル、Stage 1/2再実行、SLM改稿は行わない。

今回の結果は未達。3Cは3群ともMarkdownコードフェンス付きのため厳密JSON不成立で、Bの正式parsed.json・表示文はない。
診断用の隔離解析はstage3c/diagnostic_only.jsonに保存したが、Bの成功や保持・改善の件数には算入していない。
B/processing_failure.txtは失敗説明であり、Aの代替表示ではない。
