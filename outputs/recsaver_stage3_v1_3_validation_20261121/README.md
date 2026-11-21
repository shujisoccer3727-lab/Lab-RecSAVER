# Stage 3 v1.3 固定検証

Aは区間IDからの原文復元、Bは前回の同一入力での3B文面比較、
Cは新しい3A所見による3B統合を測る。BとCは入力が異なる。

WSL Ubuntu・既存conda qwen3でリポジトリルートから:

```bash
PY=/home/guestuser/miniforge3/envs/qwen3/bin/python
DIR=outputs/recsaver_stage3_v1_3_validation_20261121
$PY "$DIR/code/test_checks.py"
# 初回のみに使用。既存rawやprocess.jsonを削除して再生成しない。
$PY "$DIR/code/run.py" launch
```

生成完了後、以下はモデル呼び出しを行わない。

```bash
$PY "$DIR/code/verify.py"
$PY "$DIR/code/report.py"
$PY "$DIR/code/verify.py"
```

4要求を事前固定し、Aの2要求とBの1要求を独立入力として同じEngineで
バッチ処理、監査後にCを1回処理する。各要求seed925847335、出力上限5000、
temperature0.2、top_p0.8。正本はINPUT_JSONだけを置換する。
既存の生成・観測点付与・公式ルーブリック取得・3B検査を再利用した。
v1.3の版判定は検査用コピー上だけで既存検査に対応させ、
モデルの生出力やparsedを改変しない。区間からのquotes復元は仕様上の処理。

原文位置はPythonのUnicodeコードポイントであり、UTF-8バイトやUTF-16単位ではない。
正規化・空白修復は行わない。段落、短い連続区間、隣接区間を保存する。
意味評価による所見修正や選別を主実行に入れない。
独立した再現実験には新ディレクトリを使い、OUTと比較コミット条件を確認する。
GPU実行順序によるトークン単位の再現性は保証しない。
