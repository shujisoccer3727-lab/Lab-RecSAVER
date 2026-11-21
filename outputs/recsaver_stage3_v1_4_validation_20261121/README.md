# Stage 3 v1.4：表示組み立て・固定3B・通し検証

WSL Ubuntu、既存conda qwen3、リポジトリルートで実行する。

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_4_validation_20261121
# CPUのみ。launchもこれをGPUより前に実行する。
$PY "$DIR/code/run.py" assembly_tests
$PY "$DIR/code/test_checks.py"
# 初回のみ。保存結果を削除して再生成しない。
$PY "$DIR/code/run.py" launch
```

生成後の再点検・レポート再作成（モデル呼び出しなし）:

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/template_checks.py"
$PY "$DIR/code/report.py"
$PY "$DIR/code/verify.py"
```

3A×2、固定入力3B×1を独立入力としてバッチ処理し、通し3B×1を
機械検査後に処理する。各seed925847335、max_tokens5000、temperature0.2、top_p0.8。
比較元の原文区間表・3A入力・固定3B入力をバイト同一でコピーする。
正本はINPUT_JSONだけを置換する。モデル生出力はraw.txt、解析テンプレートは
parsed.jsonとparsed_template.json、組み立て結果はassembly_result.jsonと
assembled_feedback.txtに分ける。失敗時は組み立て結果をnullにし、別引用に救済しない。

A_display_tests.jsonとmechanical_test_fixtures/は明示した合成検証データで、
旧モデル・新モデルの生成成功には数えない。
検査用の版・フィールド対応コピーは既存スキーマ検査再利用のためだけに使い、
生出力・解析結果を書き換えない。quotesの区間復元と表示組み立ては仕様の処理。
意味評価で主実行を手直ししない。別の再現実験は新しいOUTを用意し、
比較コミット条件を確認する。同じseedでもGPU実行順序によるトークン一致は保証しない。
