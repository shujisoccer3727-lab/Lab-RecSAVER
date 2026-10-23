# 実行状況（2026-10-14、Asia/Tokyo）

## 完了（10月14日16:46 JST）

全7条件の同一1,000件評価、paired bootstrap 2,000回、Profile分析、最終integrity auditが完了しました。
新規5条件は各1,000件成功、最終parse failure=0。新規PredictionのretryはCが1回、D他者が2回、その他0回。
Integrity auditは20項目すべてpass。Profile記述のgroundingではrater_1の頻度説明に不整合を発見し、reportに明記しました（結果を除外・補正していません）。
最終reportは `report.md`、全手法の実際の採点理由・採点傾向例は `prediction_output_examples.md` を参照してください。
以下は途中経過の履歴です。

## 2026-10-14の再開状況

10月13日13:06 JSTに初回pipelineは停止しました。27 Profileの応答はすべてMarkdown JSON fenceで囲まれ、パーサーの未対応により検証失敗として扱われていました。各Profileで3回の不要retryが発生しています。
10月14日にfenceだけを除去するパーサーへ修正し、保存済み応答の最初のschema-valid attemptを採用して27/27を復旧しました。内容やスコアは変更せず、再生成もしていません。
元の失敗記録と全応答は `profiles/rater_profiles_pre_fence_repair.jsonl` に保存、修復auditは `profiles/profile_parse_repair_audit.csv` に保存しています。

10月14日02:39 JSTにpipelineを再起動し、現在はdry-run前のGPU待機です。別研究ジョブのGPUを停止せず、空きメモリ確認後に自動再開します。
新規5条件のPredictionは依然0件、既存再利用2条件は各1,000件です。
GPUの空き時刻とPredictionの処理速度が未確定なので、最終完了日時はまだ算出できません。
再開後20件以上の実測から `dry_run/prediction_progress.json` / `prediction_progress.json` に処理速度と推定終了時刻（JST）を保存します。
現在の状態は常に `execution_status.json` を優先してください。以下は前日までの履歴です。

## 最新状況

2026-10-12にProfile生成のみcontext上限16,384への変更が承認されました。設定・コードへ反映済み。
2026-10-13の再auditで全27 Profile promptとB/Cの3,000 prediction promptのoverflow=0を確認しました。
同日12:37 JSTにバックグラウンドpipelineを起動し、指定QwenモデルのGPUロード・初期化が完了しました。

現在の実行段階・開始終了時刻・終了コードは `execution_status.json`、段階別ログは `profiles.log` / `dry.log` / `full.log` で確認してください。
順序はProfile生成→新規5条件各5件dry-run→dry-run成功時のみ固定1,000件本実行です。
生成済み件数は `profiles/rater_profiles.jsonl` および `predictions/*.jsonl` に実際に保存された行で確認できます。
以下の古い記述は準備時点の履歴です。最終結果は本実行終了後に集計し、reportを更新します。

実験は未完了です。新規条件のLLM推論、dry-run、本実行はまだ行っていません。

## 保存済み

- `git_status_before.txt`：作業開始時点のgit status（既存の変更あり）。
- `git_status_before.stderr.txt`：gitの警告。
- `prompts/en/traitfree_direct_prediction.txt`
- `prompts/en/traitfree_joint_profile_prediction.txt`
- `prompts/en/rater_profile_generation_traitfree_mvp_1000.txt`
- `prompts/en/profile_based_prediction_traitfree_mvp_1000.txt`

最後の2件は指定名の既存promptを上書きしないため別名で新規作成しました。

## 読み取りで確認済み

- `outputs/full_prediction_main_results/common_targets.csv` とmetadataに共通母集団17,725件。
- `outputs/full_prediction_experiment/target_manifest.jsonl` に本人／他者のK=3履歴ID。
- 条件AとRubric Onlyの既存予測ファイルが存在。
- `rubrics/ellipse_rubric_structured.json` に6観点のrubricと既存定義が存在。
- WSLの `/home/guestuser/miniforge3/envs/qwen3/bin/python` はPython 3.10.20。

## 追加で保存・実行済み

- `common_targets_1000.csv`：17,725件からOverall×raterで層化比例抽出、seed=20261012、固定N=1,000。
- `sampling_strata.csv`：層別人口と抽出配分。
- `target_history_manifest.jsonl`：既存K=3の本人／他者履歴ID。
- `profile_history_availability.csv`：27採点者の履歴audit。全target source/filename/exact textを除外後の最少件数26、全員K=20可。
- `profiles/profile_history_manifest.csv`：固定K=20、全540件。
- `wrong_profile_assignments.csv`：固定他者Profile割当。
- `experiment_config.json`、`rubric_definitions_used.md`。
- `integrity_audit.csv`、`history_overlap_audit.csv`、`prompt_audit_samples.jsonl`。
- `prompt_token_audit.csv`：指定Qwen tokenizerによる全3,027 promptの長さ確認。
- `predictions/A_current_trait_history.jsonl` と `predictions/B_nohistory_rubric.jsonl`：各1,000件の既存予測再利用、参照元path/hashあり。
- `condition_summary.csv`、`prediction_distribution.csv`：再利用2条件のみ指標取得。他5条件はmissing=1,000。
- `pairwise_comparison.csv`、`paired_bootstrap_ci.csv`：全7条件共通N=0のためヘッダーのみ。差やCIは未算出。
- `report.md`：現状を明示した暫定report。
- `profiles/profile_similarity.csv`、`profiles/joint_profile_stability.csv`：未生成のためヘッダーのみ。
- `profiles/profile_examples_for_manual_review.md`：Profile未実行を明示。
- `src/recsaver/rater_profile_mvp_1000.py`：prepare/token-audit/dry/full/analyze実装。prepare・token-audit・analyzeをCPUで実行済み。GPUコードは未実行・未検証。
- `git_status_after.txt`：現時点のstatus。`git_status_before.txt`は出力ディレクトリを作成した直後、他の新規ファイルを作成する前のstatus。

## 実行上の制約

確認時、RTX 6000 Ada（49,140 MiB）の46,660 MiBを別研究のMinistral vLLMジョブが使用していました。
指定Qwenモデルを新規ロードする余裕がなく、既存ジョブは停止していません。
その後の再確認ではGPU使用553 MiB・使用率0%となり、別ジョブ終了を確認しました。こちらから停止はしていません。

現在の停止理由はcontext長です。K=20のProfile生成promptは全27件が既存8,192-token上限を超えました（最大入力15,451＋出力予算768）。B_correct/B_wrong/Cは各1,000件すべて上限内です。
Profile生成時のみmax_model_len=16,384へ拡張する案についてユーザーに確認済み、回答待ちです。K縮小・本文切り詰め・対象除外・モデル変更は行っていません。

## 未完了

1. Context上限の設計判断。
2. 各新規条件5〜10件のLLM dry-runとGPUコード検証。
3. 1,000件の本実行。
4. 全条件共通target比較、paired bootstrap、Profile analysis、推論後audit。
5. 最終report・最終git status。

性能結果や仮説の支持・棄却はまだありません。
