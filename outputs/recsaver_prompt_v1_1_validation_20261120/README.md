# 英文プロンプトv1.1：固定候補比較と同一入力診断

検証完了。Stage 1は形式6/6・観測得点保存6/6だが、数値帯適用6/6で事前点検通過0件。Stage 2同一入力診断は厳密JSONが0/3→3/3に改善した一方、汚染停止は0/2。主実行・統合は未実施。詳細は`validation_report.md`。

比較元コミット`078ae7e912a42e4f3c2f97b5ecd9ed752a583052`の保存済みv1.0結果を保持し、同じrater_7・3答案・本人履歴各3件・各2候補・seed割当・モデル設定で検証する。正本はStage 1/2=v1.1、Stage 3=v1.0。Stage 2の診断だけ旧v1.0も使う。正本の`{{INPUT_JSON}}`だけを置換し、出力を修復しない。

`run_manifest.json`に正本実パスと前後ハッシュ、同名ファイルの検索結果、比較元全ファイルのハッシュ、コード版、条件差を記録。`case_manifest.json`と実際のStage 1入力は比較元と同一。従来のuserメッセージにtokenizerが加える既定system文も維持する。

`code/run.py`はv1.0の読み取り専用ライブラリを構造検査・小さな保存関数に再利用する。v1.0ディレクトリ内の正本例から必要キー/型を検査するのは、v1.1もschema_version=1.0で同じ構造だからである。観測得点の全項目保持は別に検査し、項目欠落と値の誤記を区別する。

## 実行・再開

リポジトリ直下のWSLで既存Conda Pythonを使用する。新規インストール・モデルダウンロードなし。

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
EXP=outputs/recsaver_prompt_v1_1_validation_20261120
$PY "$EXP/code/run.py" --phase prepare
$PY "$EXP/code/launch.py"
# Stage 1完了後、code/audit_common.pyと全score_free_analysisを点検
# Codexの確定した事前点検結果をpreflight_review.jsonへ保存するとworkerが続行
# score_free_analysisの自動書換え・疑いだけでの自動除外はしない
$PY "$EXP/code/check_invariants.py"
$PY "$EXP/code/audit_common.py"
$PY "$EXP/code/collect_results.py"
$PY "$EXP/code/finalize.py"
```

workerは`status.json`で状態を更新し、`execution.log`にログを残す。保存済みresult/errorがある呼出しは再生成しない。rawのみ残った中断は自動で上書きせず停止する。事前点検待ちから再起動した場合も、Stage 1完了分をスキップして続行できる。

今回の凍結したCodex事前判定・診断Cの作成手順は`code/save_preflight.py`。これは全6候補を原文で点検した記録の保存コードであり、汎用の自動意味評価器ではない。新規候補やプロンプト改訂へ無条件で使い回さない。診断Cは明示的に作成した対照で、モデル候補の修復としては扱わない。

## 結果の区分

- `stage1/`: v1.1の6候補。入力、全userメッセージ、chat template適用文、seed、原出力、厳密解析・構造検査。
- `common_mechanical_audit.json`: 両版同じ方法での引用一致・空白差・その他差、得点欠落/誤記、全フィールドの機械的疑い。原文を変更しない。
- `preflight_review.json`: Codexの暫定意味判断。直接/復元可能な開示と番号付き対象帯/範囲を区別し、Stage 2前に凍結。
- `stage2_diagnostics/`: 同一入力A/B/C×旧新版。厳密解析と、許可された診断用コード枠除去読取は別ファイル。診断読取を採用条件に使わない。
- `stage2/`, `external_decisions/`: 本実行のみ。モデル入力と得点比較を分離。
- `stage3/`: 異なる採用答案が2件以上の場合だけ統合。採用数kと答案数を区別。
- `stage1_comparison.csv`, `stage2_diagnostics.csv`, `candidate_results.csv`, `essay_results.csv`, `validation_report.md`: 比較・集計・英語原文と和訳・限界。

内容判断はCodexによる暫定点検で、人手評価・確定正解ではない。3答案すべて観測Overall=3、既利用の開発標本であり、点数一致だけで理由の正しさや一般的性能向上を主張しない。未使用の最終確認標本は確保できておらず、今回も保留答案を生成しない。
