# 履歴件数を揃えた採点者ペア比較

設定は `configs/pair_feedback_20261126.json`、汎用ランナーは
`src/recsaver/pair_feedback.py`。Stage 1〜5を実行し、Stage 6は使用しない。
個別理由・局所所見・統合出力・表示文は英語、報告は日本語。

実行中の追加監査で、数値を含まない `native-like` が最上位帯を特定できる
表現として残っていたため、マスク検査を版1.1へ改訂した。生成条件は変更せず、
固定対象・履歴と保存済み生出力を保持して再開した。
変更前のコード・マニフェスト・監査・中断要求は
`outputs/pair_feedback_20261126/revisions/mask_v1_0/`、照合結果は
`mask_revision_v11.json` に保存。以前の小規模確認で再構成済みだった
影響候補1件は、修正後の採用集計から除外して原出力を保持している。

続行中にWindowsのGPU性能カウンタで約1.9GBの共有メモリへの退避を確認したため、
運用設定の版1.2で `gpu_memory_utilization` を0.9から0.8へ変更した。
モデル、正本、実入力、seed、サンプリング、出力上限は維持し、保存済み150要求の
生出力を保持して再開した。前の割当・メモリ実測・中断要求は
`revisions/gpu_memory_090/`、照合は `gpu_budget_revision.json`。
生成の運用設定が全要求で同一だったとは扱わず、GPUの割当とスケジュールの変更を
実行上の制約として報告する。

## 再実行

WSL2のリポジトリ直下で、既存の `qwen3` 環境を使う。モデルの追加取得は行わない。

```bash
conda activate qwen3
python -m unittest tests.test_pair_feedback -v
python -m src.recsaver.pair_feedback prepare --config configs/pair_feedback_20261126.json
python -m src.recsaver.pair_feedback tokens --config configs/pair_feedback_20261126.json
python scripts/audit_pair_feedback.py --config configs/pair_feedback_20261126.json
python -m src.recsaver.pair_feedback smoke --config configs/pair_feedback_20261126.json
python -m src.recsaver.pair_feedback run --config configs/pair_feedback_20261126.json
python scripts/audit_pair_feedback.py --config configs/pair_feedback_20261126.json
python -m src.recsaver.pair_feedback report --config configs/pair_feedback_20261126.json
python scripts/snapshot_pair_feedback_success.py verify --config configs/pair_feedback_20261126.json
python scripts/finalize_pair_feedback.py --config configs/pair_feedback_20261126.json
# この実行の暫定レビュー注釈を同じ凍結出力から再表示する場合
python scripts/render_pair_feedback_review.py --config configs/pair_feedback_20261126.json \
  --annotations outputs/pair_feedback_20261126/review_annotations.json
```

`run` は成功済み・終端失敗済みの要求を再生成しない。出力のない中断要求は再開できる。
`raw.txt` だけが残った場合はその原出力を再解析し、生成を繰り返さない。
不正JSON、マスク隔離、得点不一致で再サンプリングしない。
候補seedは `SHA256(seed:stage番号::要求キー)` の先頭8桁を整数化し、
`2**31` の剰余を取る。実際の値は各要求の `sampling.json` にも保存する。
固定seedは抽出と要求条件を再現するためのもので、GPUのバッチ構成・スケジュールが
異なる実行間のビット単位の同一性や候補間の統計的独立性は保証しない。
設定・データ・正本・実装のハッシュが凍結後に変わると停止する。
別の条件を試す場合は設定の版と出力先を変更する。

`smoke` は固定20件の各採点者1件を使用する。Stage 1・3・4の要求は本実行と
同一入力・seedであり、本実行で再利用する。小規模確認のStage 5だけは
`stage5/<rater>__smoke/` に分け、最終フィードバックに算入しない。

## 選択と除外

Filename、空欄以外のKaggle ID、空白・改行だけを正規化した本文SHA256の
連結成分で同一エッセイを識別する。衝突・別名を監査し、モデルには各レコードの
原文を渡す。同一エッセイ×採点者の得点プロフィールが矛盾する場合は隔離する。
比較用5件の成分を全6名の全生成段階から除く。

採点時刻が元データに存在しないため、未使用エッセイを用いた事後的な事例分析とする。
行順・ID順を採点時系列としない。固定seed、目的、採点者、安定したエッセイIDの
SHA256順で20件と参照3件を選ぶ。得点・モデル出力を抽出順位に使わない。

Stage 5のMは出典照合済み所見のあるエッセイ数のペア内最小値。
固定順位の先頭M件を使い、除外された所見も保持する。Stage 5が容量を超える場合に限り
両側を同じ件数ずつ減らし、`equalization.json` に自然なMと適用上限を記録する。
M=1では局所所見に限定し、傾向の支持には異なる2エッセイを要する。
M=0では `skip.json` に証拠不足を記録する。

## 保存物

出力先は `outputs/pair_feedback_20261126/`。学生原文と巨大出力を含むためGit対象外。

|ファイル|内容|
|---|---|
|`manifest.json`|全120ターゲットエッセイ、本人履歴3件、元レコード、順位、候補seed、設定とハッシュ|
|`dataset_audit.json` / `identity_audit.json`|データ版・件数・同一性衝突と隔離|
|`exclusion_manifest.json`|固定5件の両者得点・原文ハッシュ・全別名除外|
|`cpu_input_checks.csv` / `cpu_audit_checks.csv`|原文を含まない照合結果|
|`cpu_validation.json` / `request_inventory.csv`|検証集計と段階別トークン数|
|`stage1/<候補>/`|全文の実入力、チャット、seed、生出力、厳密JSON、検査|
|`stage2/<候補>/`|マスク前後、変更位置・理由、隔離理由|
|`stage3/<候補>/`|得点を外した実入力、再構成生出力・JSON|
|`candidate_results.*` / `essay_decisions/`|候補とエッセイ単位の採否|
|`stage4/<ターゲット>/`|得点・理由を渡さない入力、原文区間表、局所所見、引用復元と出典照合|
|`equalization.json`|ペア内M、固定順位による採用ID、未使用ID|
|`stage5/<採点者>/input_3b.json`|直接統合への実入力|
|`stage5/<採点者>/parsed.json` / `feedback.txt`|生成された構造化出力とコードによる英語表示文|
|`summary.csv` / `summary.json` / `report_ja.md`|採点者ごとの段階別集計|
|`final_summary.csv` / `final_summary.json`|厳密JSON失敗と表示成立を区別した最終集計|
|`results_ja.md`|英語生成文、内容点検、比較用5エッセイの10事例を含む日本語報告|
|`review_annotations.json`|この実行のCodex暫定点検。未知の生成物の自動判定には使用しない|
|`comparison_case_review.json` / `feedback_content_review.json`|原文区間・対応基準・確認点・意味的な限界|
|`request_manifest.json` / `cost_summary.json`|各要求の生成seed・実入力ハッシュ・状態・GPU割当・トークン数|
|`final_integrity.json` / `output_provenance.json`|引用・得点・同数化・表示の照合、出力と報告コードのハッシュ|

機械検査は引用・ID・値と出典の一致を確認する。意味的支持は保証しない。
過去の実験固有のレビュー判定を自動評価に転用しない。
Stage 5の生成内容は手直しせず保持する。内容上の限界と固定5件との対応は
別ファイルの暫定レビューとして記録する。人手評価、真の理由の復元、再採点による
点差縮小、一般的な比較性能を主張しない。

`scripts/bootstrap_pair_feedback.py` は初期の機械契約抽出の来歴を残す補助コード。
既存の生成後に再実行しない。正本への参照と検査は現在の凍結コードが担う。

## 今回の実行結果

Stage 1は240候補の厳密JSONが成立し、マスク検査232候補、完全一致161候補、
採用89エッセイ。出典照合済み所見付きは88エッセイ、全ペア双方M=14。
Stage 5は6名とも実行し、英語表示文は5名で成立した。
`rater_13` はコードフェンス付き生出力で厳密JSONが不成立となり、原出力と失敗記録を保持した。
表示成立5名は全て評価傾向を保留。意味的な分類の問題や、比較用エッセイへ確認点を
直接対応できない事例は `results_ja.md` に別記している。
