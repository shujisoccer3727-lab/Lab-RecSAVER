# 完了した実験の作業記録

## 最終状態

2026-11-07 19:00 JSTに最終監査を通過。runner_exit_code.txt=0、execution_status=finished/completed_with_exclusions、integrity_validation.all_checks_passed=true。残りの生成・検証ジョブは0。

- 3点差: 7エッセイ・7ペア、処理成功7、参照取得は両者3/片方3/両者なし1。
- 2点差: 252エッセイ・252ペア、処理成功251、対象Trait無効で失敗1を理由付きで保持。参照取得は両者140/片方96/両者なし16。
- 518採点者側のうち517を実行（予測478再利用+39新規）。有効な参照生成4429試行、自己検証1102試行、検証済み参照938件、その全938件の4類似度指標を計算。
- 最終監査で匿名化版の共通本文不一致を4採点者側に検出し、参照rendererを1行修正。該当4対象のみ再生成・再検証・再評価して再監査済み。誤った旧30生成/11検証/11指標はreference_text_fixに隔離保存し、現行集計から除外。
- 人手評価は未実施、human_review.csvはLLMによる記入なし。バイアス是正・実際の人間採点者間の点差縮小は結論しない。

最終結果は report.md、pair_results.csv、human_review.csv、integrity_validation.json。以下は実行中の判断・再開方法の履歴であり、「現在」と書かれた進捗は当時の記録。

ユーザー依頼: ELLIPSEの人間採点者間Overall差3・2点の全ペアについて、JIMAのRec-SAVER手順を適用し、全候補・検証・類似度・人手未記入欄を保存する。実装だけでなく全件実行まで継続する。サブエージェントは使っていない。

## 確定した対象と処理

- raw: 8890行、Filename 8880件、Text完全一致では8890件。
- Filename重複10組は差分を目視確認し、空白/固有名詞の匿名化版違いと判断。同じエッセイとして対応づけ、後方の匿名化済み本文を両採点者に共通入力する。
- 3名以上の採点があるエッセイは10件。同一Filename×採点者の重複1組(rater_2)はOverall一致、Trait一部不一致。後方のレコードを代表として、全元Traitをdata_audit.jsonに保存。
- Overall整数1～5でペア抽出。3点差7エッセイ・7ペア、2点差252エッセイ・252ペア。raw行内の有効2点差251に、別行間の同一エッセイペア1件が加わる。
- raw行内3点差15には0を含む無効8件。最大4点差1件も無効。期待値15/215を強制していない。
- 計518採点者側のうち、8135:2は既存の全Trait有効性条件を満たさず実験対象外。ただしペアから消さず、理由を保存。
- 実験可能517対象の予測を全保存済み。478再利用、39新規。対象本文/同一Filename/非欠損kaggle IDを履歴候補から全採点者分除外し、重複履歴も統合したため一部の既存履歴が変わった。
- 3点差少数例2ペア→指標評価→3点差7ペア全件の生成・検証完了。3点差の参照取得は両者3ペア、片方3ペア、両者なし1ペア、検証済み参照24件。
- 現在は2点差全件の参照生成中。初期の既存参照再利用は36対象、301生成試行・80検証試行。正確な進捗は下記コマンドで確認する。

## 実装と実行

- src/recsaver/human_score_disagreement.py
- configs/human_score_disagreement.yaml
- scripts/run_human_score_disagreement.sh
- scripts/validate_human_score_disagreement.py
- scripts/progress_human_disagreement.py
- tests/test_human_score_disagreement.py（既存reasoning_eval_v1テストと合わせ10テスト通過、tests.log）

WSL Ubuntu、/home/guestuser/miniforge3/envs/qwen3/bin/python。GPU RTX 6000 Ada 48GB。

Qwen2.5-32B-Instruct-GPTQ-Int4、GPTQ Marlin、max_model_len8192、K=3、既存英語Overallルーブリックと3プロンプトを使用。履歴seed20260814、参照/検証seed20260916（reasoning_eval_largeと一致）。新規予測39件は追加実験request_seed(stage=prediction,base=20260916)。再利用予測はfull_predictionの基準seed20260814の規則を保持。この差は最終監査スクリプトがreportに明記する。

既存generate/verification_prompt/leakage_audit/MetricEngineを再利用。3参照枠×最大5生成試行、検証parse再試行1回。スコア開示は除外・再生成し、検証は実スコアを入力しない。指標はBLEU/ROUGE-1/METEOR/BERTScore(roberta-large17層)。人手欄は一切LLMで埋めていない。

GPU共有のため運用設定を変更: 既存0.90→0.60→0.50。0.60でもWDDMのVRAMが48GB近くに達して停滞したが、0.50で改善。スケジューラbatch10→64へ移行。model基準設定の0.90は互換比較用に残し、new_generatorでruntime_gpu_memory_utilizationを適用する。入力・サンプリング・request seedはこれらの運用移行で変えていない。metadataのruntime_migrationsと各退避ログを参照。

bool_のJSONシリアライズ不具合を1回修正した。生成条件を変えない1行修正とソースhashを検証し、metadataのcode_migrationsに記録。以後coreコードは変更していない。全journalを保持したままfingerprint移行を行った。

接続更新後の確認で推論プロセスが消失していたため、1470参照試行のcheckpointからtmux独立セッションに切り替えて再開する。途中の64件バッチは未保存分のみ同じseedで再生成する。

現行の起動コマンド（稼働中に二重実行しない）:

```bash
cd /mnt/c/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER
bash scripts/start_human_disagreement_detached.sh
```

現行wrapperは既存のpilot検証とmetricsがあればgenerate→evaluate→validateを別プロセスで実行し、最後に独立監査・枠別の取得失敗理由・採点者別誤差・指標集計を追記する。GPU推論とBERTScoreを別プロセスにしてVRAMを解放する。

進捗コマンド:

```bash
/home/guestuser/miniforge3/envs/qwen3/bin/python scripts/progress_human_disagreement.py
tail -n 5 outputs/human_score_disagreement/run.log
```

独立tmux session=recsaver-human-disagreement。runner_pid.txt/runner_exit_code.txtで親と終了を確認する。以前のexec_command session_id=64189は接続更新で消失した。停止・再起動する場合は必ず現在のpsで今回のPIDを確認し、自分の実験だけを操作する。

## GPU共有についてのユーザーの確定指示

別のQwen3-8B llama-server(tmux tf-o4-llama, port18080)が稼働しGPU約14GBと計算資源を使用している。async質問に対してユーザーは「別サービスを維持して、このまま実験を続ける」と明示した。別サービスを停止しない。停止許可を再度求めず、共存設定（GPU確保量0.50、batch64）で依頼された全件実験を継続する。

## 残作業

1. 長時間計算を監視して2点差全件の生成・自己検証を完了させる。バッチ途中の推論済み件数はtqdm、保存済み試行数はprogressスクリプトで確認。64件バッチは数分かかる。
2. wrapperによる全参照の指標計算と独立監査完了を確認。必要時はstage evaluateまたはvalidateスクリプトだけ再開。核心設定・入力・コード変更時はfingerprintが拒否するので安易に消さない。
3. integrity_validation.json all_checks_passed=true、execution_status finished、各群のpending=0、metric数=pool数、未記入human_reviewを確認する。validatorが最後に枠別失敗理由、rater別予測誤差、スコア分布を追記する。
4. 最終報告は日本語で対象数・成功/失敗・参照取得状況・出力リンク・既存からの変更と限界を示す。「バイアス是正」「実際の点差縮小」は結論しない。人が次にCSVで根拠と再確認点を記入する。

既存のrater_feedback_score_comparison_mvp_30関連の未追跡ファイルは今回以前のユーザー作業なので触っていない。raw/processed元データを変更していない。Git commitは依頼されていない。
