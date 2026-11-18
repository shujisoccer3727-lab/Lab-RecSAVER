# 採点者フィードバック開発3答案・B条件（版2.0）

現在読むファイル:
- `outputs/rater_feedback_pilot_v2/v2_0/report.md` — [本文・対応表](report.md)
- `outputs/rater_feedback_pilot_v2/v2_0/assessment.md` — [所見・失敗](assessment.md)
- [短いフィードバック](feedback.md)
- [原因調査](cause_analysis.md) / [旧主張の対応表](old_claim_lineage.md) / [全来歴JSON](cause_analysis.json)
- [新旧比較](old_new_comparison.md) / [開発レビュー](development_review.json)
- [機械監査](audit.json) / [文章ごとの内部参照](sentence_lineage.json)

指定3答案のみ。27答案への展開・最終評価設計・commit/pushはしない。旧出力は読み取り専用でハッシュ照合した。
入力・元データ照合はinputs.json/input_checks.json、選択はselection.json、設定とソースハッシュはresolved_config.json、コード・全プロンプトはcode/に保存。
生成原本・マスク・検証payload・中間結果・原出力・失敗はstage_inputs/、masks/、stages/、calls.jsonlに保持。生成設定はv1.6を維持、JSON制約は既存outlines、変更点はrevision_note.json。

再開コマンド（GPUが空いている場合のみ。既存処理は停止しない）:
```bash
python -m src.recsaver.rater_feedback_development one
# 1答案の内容点検とone_review.jsonの保存後:
python -m src.recsaver.rater_feedback_development three
python -c "import runpy; runpy.run_path('scripts/report_feedback_development.py',run_name='__main__')"
```
同一fingerprintの成功結果のみ再利用。得点不一致・終端失敗を追加候補生成で埋めない。共通傾向がなければ未確定として報告する。
