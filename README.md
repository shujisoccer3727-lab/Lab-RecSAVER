# ELLIPSE Trait Profile 基礎分析

ELLIPSE Corpusの人間採点データを使い、採点者ごとのOverall評価と、6 Traitを一体の`Trait profile`として扱う探索分析プロジェクトです。研究上の1サンプルは「1エッセイ×1採点者」です。raw・processedデータは変更しません。

## ディレクトリ構成

- `data/`: raw CSVと、Git管理外のprocessedデータ
- `data/processed/rater_essay_wide.csv`: 基礎分析の入力
- `src/`: データ整形、基礎分析、GPU入力準備
- `tests/`: CPUで実行できる整合性テスト
- `notebooks/basic_analysis.ipynb`: `src`の関数を呼ぶ確認用Notebook
- `outputs/basic_analysis/tables/`: 新基礎分析の14表
- `outputs/basic_analysis/figures/`: 新基礎分析の12図
- `docs/basic_analysis_report.md`: 実データによる日本語レポート

## CPU分析環境

WindowsノートPCでは次のように実行します。

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-analysis.txt
python -m src.basic_analysis
```

WSL2 / LinuxのConda環境でも同じPythonモジュールを実行できます。

```bash
conda activate qwen3
pip install -r requirements-analysis.txt
python -m src.basic_analysis
```

入力を変更する場合:

```bash
python -m src.basic_analysis --input data/processed/rater_essay_wide.csv
```

基礎分析はCPUのみを使用し、vLLM、PyTorch、Transformers、CUDAには依存しません。GPU推論は`requirements-gpu.txt`と`src/gpu_inference/`へ分離しています。

## processed wideの再生成

```bash
conda activate qwen3
python -c "import pandas, numpy; print(pandas.__version__, numpy.__version__)"
python -m src.create_rater_essay_wide \
  --input data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv
```

既定出力は`data/processed/rater_essay_wide.csv`です。スコア0や欠損を補正せず保持し、無効フラグを付けます。保存先は`--output`、raw入力は`--input`で変更できます。

研究室PCでは、clone後に再配布対象外のraw CSVを
`data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv`として配置してください。
`pandas`または`numpy`が不足する場合だけ不足パッケージを追加し、
`requirements.txt`や`requirements-gpu.txt`を一括インストールしないでください。
既存のvLLM、PyTorch、Transformers、CUDA環境を維持したまま上記コマンドでwideを生成し、
生成確認後にLLM実験へ進みます。

## Notebookとテスト

```bash
jupyter notebook notebooks/basic_analysis.ipynb
python -m unittest discover -s tests -v
```

## 分析上の注意

主要統計はOverallと6 Traitがすべて1～5のサンプルに限定します。採点者平均の高低は担当答案の構成を統制していない未調整の評価傾向です。TraitとOverallの相関は因果的な重みを意味しません。OverallはTrait平均から再計算せず、元の人間採点値を使用します。

raw、processed、モデル、GPU入力、生成された分析出力は`.gitignore`でGit管理から除外します。

## Rec-SAVER型MVP

設定は`configs/recsaver_mvp.yaml`、プロンプトは`prompts/`、実装は
`src/recsaver/`に分離しています。各Phaseは中間結果を
`outputs/recsaver_mvp/`へ保存します。

```bash
conda activate qwen3
export VLLM_USE_V1=0
export VLLM_ENABLE_V1_ENGINE=0

python -m src.recsaver.phase1_prediction
python -m src.recsaver.phase2_reference
python -m src.recsaver.self_verification
python -m src.recsaver.phase3_reasoning_eval
python -m src.recsaver.phase4_analysis
```

既定MVPは10 target、履歴5件、Reference Candidate 3件です。context上限に近い場合は
Target Essayを優先して履歴末尾から減らします。Phase 3のMETEORとBERTScoreは任意依存であり、
依存を追加していない環境では欠損として記録されます。

context lengthと固定history sizeの収容率分析は次で再実行できます。

```bash
python -m src.recsaver.context_analysis \
  --config configs/context_analysis.yaml \
  --max-model-len 4096 8192 16384 32768 \
  --min-rater-samples 100
```

この分析は全文を維持し、history数のfallbackを使いません。結果の解説は
`docs/context_history_analysis.md`にあります。
