# Stage 3C v1.1：固定主張による回帰診断

比較元：`38697e9bc153f8824c5e62c394e44b5be73fe759` の
`outputs/recsaver_stage3_claim_verification_pilot_v1_0/`。
Stage 1〜3Bは再実行せず、known / contrast / limitedのAをバイト同一で再利用する。
4902:1の有効なCohesion所見は保持確認用で、改善集計から除外する。

22命題をCodexが人手相当で分割し、claim_manifest.jsonへ推論前に固定。
位置2命題はコード、20命題はLLM。4群をそれぞれ1要求とする計4要求のみ。
主張と、その主張に固定した正確な引用・必要な公式基準・記録得点だけをモデルへ渡す。
上流解釈、採点理由、過去の評価・修正例、表示候補、独立参照判定は渡さない。

現行vLLMのoutlinesによるJSON制約を使用。各要求のschemaをCPUでコンパイルした。
厳密JSONのみを採用し、コードフェンス除去・JSON本文修復・再生成は行わない。
ID欠落・重複・未知ID・未定義ラベル・追加フィールドは処理失敗。

実行済みコマンド（再実行しない）：

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_claim_verification_pilot_v1_1
$PY "$DIR/code/pipeline.py" prepare
$PY "$DIR/code/test_pipeline.py"
$PY "$DIR/code/pipeline.py" launch
```

モデルを呼ばない再点検・報告：

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/report.py"
```

code_verdicts.jsonと各群stage3c/parsed.jsonを分けて保存する。
支持された固定表示候補だけを固定順序で組み立て、非支持の前提を使う確認点を除く。
局所所見がなくても別の所見で埋めず、保留として表示する。
生出力・解析結果、初稿Aと試作B、形式失敗時の理由、要求数と設定を保存する。

independent_reference_review.jsonは推論前に別工程で保存した原文照合の参照判定。
3Cの自己判定を正解に使わず、表示後の残存誤りも記録する。
位置検査、人手相当の分割、LLM判定、JSON制約を合わせた既知例の診断であり、個別の効果や未知答案での性能は識別しない。
1回で終了し、自動的なプロンプト調整を行わない。
