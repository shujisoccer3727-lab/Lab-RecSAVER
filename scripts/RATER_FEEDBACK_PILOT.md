# 自己検証済み参照推論からのフィードバック予備検証

リポジトリルートで、既存のWSL2 / qwen3環境を使用する。

```bash
conda activate qwen3
python -m src.recsaver.rater_feedback_pilot prepare
python scripts/snapshot_feedback_pilot.py
python -m src.recsaver.rater_feedback_pilot pilot
```

`pilot` は選択記録の先頭採点者だけを実行する。A、B、Cの成功済みファイルを
段階ごとに再利用する。プロンプト・入力・モデル・当該段階の生成条件が変わると
fingerprint不一致で停止するので、新しいoutput_dirを指定するか、影響する段階の
ファイルを別名で保存してから再実行する。失敗した応答はcalls.jsonlに残す。
参照推論生成や得点による自己検証を再実行する処理はない。

最初の結果を読み、問題点・修正内容・展開可否を
`outputs/rater_feedback_pilot/pilot_review.json` に保存する。

```json
{"proceed": true, "reviewer": "reviewer name", "pilot_result_sha256": "SHA256 of results/rater_7.json", "issues": [], "changes": [], "limitations": []}
```

内容確認後、選択済みの残り最大2名を実行する。

```bash
python -m src.recsaver.rater_feedback_pilot remaining
python -m src.recsaver.rater_feedback_pilot report
python -m unittest tests.test_rater_feedback_pilot -v
```

入力は`inputs.json`、全採点者の利用可能数と選択規則は`selection.json`、出典と
制約は`provenance.json`。生成後の`report.md`、`feedback.json`、`checks.json`を読む。
静的検査のみの`preflight_report.md`は過去時点の準備・中断記録であり、生成後の
結果レポートと区別する。引用の位置はUnicode文字0始まり、終端を含まない。
意味的支持は生成モデルによる暫定判断で、人間による独立評価ではない。

最初の採点者を確認してから同じロード済みモデルで残りへ進める場合は
`pilot-and-expand`を使用する。最初の結果を保存後、最大10分間レビューを待つ。
`pilot_review.json`のproceedと結果ハッシュが一致した場合だけ残りへ進む。
レビュー前にそのファイルを作成しない。C v2では具体的な引用アンカー・対象ID・
観測得点・隣接段階との比較を検査し、③の原文引用はプログラムが挿入する。
初回Cやエラー、レビューによる保留の記録はrevisions/、calls.jsonl、
semantic_review.jsonに残す。文脈長は初回8192から16384へ拡張した。

GPU空き容量が24,000 MiB未満なら新しいQwenをロードせず失敗記録を保存する。
他の実験やサービスを停止しない。24,000 MiB以上でも既存GPU利用がある場合には
vLLM初期化が失敗する可能性があるため、原則として他のGPU実験がない時に実行する。
