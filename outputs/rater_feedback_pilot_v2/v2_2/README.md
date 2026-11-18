# 採点者フィードバック開発3答案・B条件（実行修正版2.2、意味仕様2.1）

保存済み結果の範囲: **three**。現在の実行状態: **completed / three**。
oneは1514:1のみであり、固定3答案の結果とは区別する。

現在読むファイル:
- `outputs/rater_feedback_pilot_v2/v2_2/report.md` — [本文・対応表](report.md)
- `outputs/rater_feedback_pilot_v2/v2_2/assessment.md` — [所見・失敗](assessment.md)
- [短いフィードバック](feedback.md)
- [原因調査](cause_analysis.md) / [旧主張の対応表](old_claim_lineage.md) / [全来歴JSON](cause_analysis.json)
- [新旧比較](old_new_comparison.md) / [開発レビュー](development_review.json)
- [機械監査](audit.json) / [文章ごとの内部参照](sentence_lineage.json)

指定3答案のみ。27答案への展開・最終評価設計・commit/pushはしない。旧出力は読み取り専用でハッシュ照合した。
入力・元データ照合はinputs.json/input_checks.json、選択はselection.json、設定とソースハッシュはresolved_config.json、コード・全プロンプトはcode/に保存。
生成原本・マスク・検証payload・中間結果・原出力・失敗はstage_inputs/、masks/、stages/、calls.jsonlに保持。生成設定はv1.6を維持、JSON制約は既存outlines、変更点はrevision_note.json。

再開コマンド（GPUが空いている場合のみ。既存処理は停止しない）:
```bash
# 上流は版2.1の同一入力・成功済み結果を再利用
# 1答案の内容点検とone_review.jsonの保存後:
python -c "import runpy; runpy.run_path('scripts/resume_feedback_v22.py',run_name='__main__')"
python -c "import runpy; runpy.run_path('scripts/report_feedback_development_v22.py',run_name='__main__')"
```
同一fingerprintの成功結果のみ再利用。得点不一致・終端失敗を追加候補生成で埋めない。共通傾向がなければ未確定として報告する。


## 今回の最終状態（実行修正版2.2）

指定rater_7・B条件・1514:1 / 1868:1 / 4902:1の開発実行。上流は版2.1と同一の入力・プロンプト・生成設定・成功済み結果を使用し、2.2では重複入力の参照化だけを修正した。プロンプト版6および意味仕様2.1の表記は引継ぎ条件を示し、実行修正版は2.2である。参照化前の完全payloadはstage_inputs_expanded/、実payloadはstage_inputs/、毎回の完全復元検査はcompaction_checks.jsonl。

現在読むべき正確なパス:
- `outputs/rater_feedback_pilot_v2/v2_2/report.md`
- `outputs/rater_feedback_pilot_v2/v2_2/assessment.md`

[3答案の開発レビュー](three_development_review.json)・[厳密な参照監査](three_audit.json)・[完了範囲と段階別件数](completion.json)・[短い生成原文](feedback.md)・[機械可読の生成本文](feedback.json)・[修正と引継ぎ条件](revision_note.json)・[保持した失敗と修正履歴](execution_failures.json)。

今後のプロンプト改善はassessment.md末尾。今回の内容点検はCodexによる開発レビューであり、独立した人間評価でも有効性・バイアス是正効果の検証でもない。原出力を内容レビューに合わせて書き換えてはいない。
