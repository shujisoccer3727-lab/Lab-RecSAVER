# 採点者フィードバック予備検証v2：現在の参照先

現在読むべき完成版は **v1_6**。保存済みの全27答案（3採点者：10・7・10答案）、履歴各3件、A/B各2候補の結果を監査した。

- レポートの正確なパス: `outputs/rater_feedback_pilot_v2/v1_6/report.md`
- 所見の正確なパス: `outputs/rater_feedback_pilot_v2/v1_6/assessment.md`

条件AはOverallのみ、Bは同じ採点者の6観点の得点も提示。モデルはQwen2.5-32B-Instruct-GPTQ-Int4、保存済み版1.6と生成設定を維持した。

各条件54候補中53生成成功・1失敗。Overall一致はA35候補／20答案、B34候補／19答案。統合・最終文章はA/B各3採点者で成功。答案別④⑤はA11/20、B13/19成功、計15件は既定再試行後の失敗として保持している。未処理バッチはなく、今回の再開で新しいモデル呼出しは行っていない。

機械監査は通過したが、文法分析の誤り、一般的すぎる傾向、Overall条件がない照合4件、採点上の確認より添削に寄る行動が残る。実際の採点者への利用に妥当性が確認されたフィードバックではない。有効性・バイアス是正効果は結論しない。

旧版・成功出力・全失敗試行は保持した。前回利用上限によって自動承認審査が完了しなかった履歴集約コマンドは実行せず、迂回もしていない。版別のログ・pilot_review.json・upstream_reuse.jsonと今回のresume_completion.jsonを参照する。Gitのcommit/pushは行っていない。

- [report.md](report.md)
- [assessment.md](assessment.md)
- [feedback.json](feedback.json)
- [full_results.json](full_results.json)
- [full_summary.json](full_summary.json)
- [run_metrics.json](run_metrics.json)
- [resume_completion.json](resume_completion.json)
- [progress.json](progress.json)
- [resolved_config.json](resolved_config.json)
