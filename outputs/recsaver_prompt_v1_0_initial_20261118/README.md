# 英文プロンプト v1.0 初回検証

正本3ファイルを変更せず、既存の開発セット（rater_7、1514:1 / 1868:1 / 4902:1、本人履歴各3件、各2候補）で参照理由→Overall再構成→統合を検証する。既存開発セットを優先したため、暫定3採点者×4答案には拡張しない。全対象Overall=3であり、一般的な採点再現性能を測る標本ではない。

原データ・旧出力・正本プロンプトは上書きしない。Stage 1は対象の観測Overall/Traitsを見た事後説明であり、人間の実際の思考の復元とは扱わない。内容点検はCodexの暫定判断で、人手評価・確定正解ではない。

## 主な成果物

- `run_manifest.json`: モデル、生成上限、seed、再試行、正本SHA-256の前後比較、コード版。
- `case_manifest.json` / `input_checks.json`: 固定対象・履歴、raw/wide/旧入力照合、保留答案。
- `stage1/`, `stage2/`, `stage3/`: 入力JSON、userメッセージ、実際のchat template適用文、トークン容量、生成設定、未加工出力、解析JSON、形式判定。Stage 2の`external_decision.json`はモデル入力に入らない。
- `leak_review.json`: 機械的疑いと確認済み漏洩を分けるCodexの点検。
- `candidate_results.csv` / `essay_results.csv` / `summary.json`: 候補単位と答案単位の集計。
- `content_review.md` / `validation_report.md`: 出典付き内容点検と結果・限界・次回提案。
- `code/run.py`: 実行・再開コード。正本の`{{INPUT_JSON}}`だけを置換する。

## 実行・再開（リポジトリ直下、WSL）

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
RUN=outputs/recsaver_prompt_v1_0_initial_20261118/code/run.py
$PY "$RUN" --phase prepare
$PY "$RUN" --phase stage12 --dry-run
$PY "$RUN" --phase stage12
# Stage 1全候補のscore_free_analysisを点検し、leak_review.jsonに根拠とconfirmed_leakを保存
$PY "$RUN" --phase stage3 --dry-run
$PY "$RUN" --phase stage3
$PY "$RUN" --phase summarize
```

HF/Transformersはofflineで既存キャッシュを使用。新規契約・モデルダウンロード・追加評価LLMは使わない。既存のqwen3環境とvLLM 0.6.6.post1を使用する。

`result.json`または`error.json`がある呼び出しは再生成しない。出力JSONの抽出、Markdown除去、修復、得点不一致による追加生成はしない。通信例外は最大1回だけ再試行し、履歴を保存する。入力超過は切り詰めず停止する。プロセス中断によりrawのみ残りresultがない場合は、rawを保全し、状態を調査してから再開すること。

既存tokenizerはuserメッセージにデフォルトsystem文を付ける。文面はmanifestと各`rendered_chat.txt`に記録。課題固有の追加指示はない。最終確認候補8540:1 / 8612:1は今回の全入力から除外する。過去の利用歴が未確定なので「未使用の最終確認用」とは認定しない。
