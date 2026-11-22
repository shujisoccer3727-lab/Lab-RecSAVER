# Stage 3 v1.5 基準方式の固定検証

既存WSL Ubuntu / conda qwen3、リポジトリルートから:

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_5_baseline_20261122
# launchはGPU初期化より前に保存済み引用で11件を検査する。
# 初回だけ実行。保存結果を削除して再生成しない。
$PY "$DIR/code/run.py" launch
```

保存結果のCPU再点検（モデル呼び出しなし）:

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/report.py"
$PY "$DIR/code/verify.py"
```

3A×2を独立入力でバッチ処理し、元観測点と公式基準を付けて通し3B×1を実行。
候補の監査は別の決定的処理で、3A/3Bへ候補文・監査自由文を渡さない。
各要求seed925847335、temperature0.2、top_p0.8、max_tokens5000。
正本はINPUT_JSONだけを置換。原文区間表はv1.4の保存物をバイト同一で使用。

モデルのstructured outputはraw.txt/parsed.jsonに、コードの参照・表示検査は
render_result.jsonに、成功時の完成文はfeedback_paragraph.txtに保存する。
不正キー・indexを別引用で救済しない。引用本文を変えず外側の句読点を制御する。
indeterminateの説明は固定文、比較方向は公式帯の差からコードで決める。
モデルの内容が固定説明と矛盾する場合は、内容評価で不合格として記録する。

合否はユーザー指定A〜Cだけで判定。好み・監査網羅性・pattern件数で再調整しない。
合格ならbaseline_method.jsonに固定方式を記録し、この2答案の調整を終了。
未達なら障害項目と最小修正1件を報告して終了する。
別の再現実験には新しいOUTを作り比較コミット条件を確認する。
同じseedでもGPUの実行順序によるトークン単位の一致は保証しない。
