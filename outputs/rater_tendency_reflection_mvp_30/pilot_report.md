# Pilot report

状態: 30/30 targets checkpointed; valid JSON/schema 30/30 attempted targets.
Full 1,000件は未承認。Pilot完了後に停止し、明示承認を得る。

設定: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 768}; max_model_len=8192; K=3; English.
Aのmax_tokens=384に対し、長いJSON用に768を初期候補として選択。最終推奨は実測後に判断。
選択: Reuse byte-identical grounded v2 pilot_targets.csv; 30 targets, no resampling; seed=20260914。対象IDとGold/raterはpilot_targets.csv。

出力token数: [457, 440, 414, 444, 443, 424, 424, 490, 444, 446, 431, 471, 412, 426, 466, 401, 437, 400, 399, 450, 531, 472, 404, 364, 379, 385, 400, 407, 382, 481]
length終了attempt数: 0 / 30
retry総数: 0
失敗・除外: []

integrity_audit.csv: 1,000件の既存A再利用・履歴一致・重複Essay排除・Gold改変不変性を確認。
参照IDはparse()で提供済みK=3内に限定。全入出力・人手確認欄: reasoning_review_examples.md。
構造の出力率は内容の正しさを示さない。人手評価は未実施。
