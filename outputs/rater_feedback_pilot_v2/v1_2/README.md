# 採点者フィードバック予備実験v2：準備済み・GPU待機

版: feedback-pilot-v2/1.2。更新日時: 2026-11-15T17:55:16.352185+09:00。
**新規モデル生成は0件。A/B比較結果・生成例はまだ存在しない。**
旧参照推論を新規生成結果として流用していない。

- [入力確認と実行状況](report.md)、[未確認事項と改善点](assessment.md)
- inputs.json: 同じ3名27答案と本人履歴3件、本人Overallと6Trait、本文の位置付き参照単位
- input_checks.json / independent_audit.json / preflight_checks.json / tests.txt: 元データ照合・出典不変・位置・マスク・54入力の長さ検査
- generation_input_manifest.json: 108候補の入力ID、履歴ID、seed、入力・プロンプトのハッシュ
- conditions/A/generation_inputs/、conditions/B/generation_inputs/: 実生成に使う54入力。AにTrait値なし、Bには本人のTraitだけ
- conditions.json / rubric.json: 公式転記原文と81条件のID、原文位置、親段階全文
- resolved_config.json / code/: モデル・設定・日時・出典ハッシュ・実行コードとプロンプト
- gpu_blocker.json / gpu_wait_history.jsonl / gpu_wait_status.json: GPU使用元と待機履歴
- ../revision_history.json、../v1/status.json: 修正履歴と初回GPU起動失敗（旧版も保持）

GPU待機処理は空き容量が設定上の必要量45,250MiB以上になるまで最大30分待つ。
既存プロセスは停止しない。待機状態はgpu_wait_status.jsonの日時とstatusを参照。
空きができたら3答案のA/B全段階を実行し、27答案への展開前にレビュー用ゲートで停止する。
生成後にreport.mdとassessment.mdは実測の結果に更新される。

## 実行と再開

```bash
# リポジトリ直下・既存WSL qwen3環境で実行
python -m src.recsaver.rater_feedback_pilot_v2 prepare
python -c "import runpy; runpy.run_path('scripts/check_feedback_v2.py', run_name='__main__')"
python -m src.recsaver.rater_feedback_pilot_v2 pilot-and-full
```

既に待機プロセスが動いている場合、二重起動しない。
pilot-and-fullはPILOT_READY表示後、pilot_results.jsonを点検したうえで
pilot_review.jsonにproceed=trueとpilot_sha256（実ファイルSHA256）を保存する。
このゲートはユーザー承認要求ではなく、固定3答案の出力確認を先に行うための処理上の制御。
比較段階以降も含め、中間結果はstages/に保存され、同じ入力の完了段階を再利用する。
入力・プロンプト等の変更時は新しい版の出力先を使用する。
全実行後の監査:
`python -c "import runpy; runpy.run_path('scripts/audit_feedback_v2.py', run_name='__main__')"`
