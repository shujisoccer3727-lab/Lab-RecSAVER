# Lab-RecSAVER リポジトリ構成

更新日: 2026-08-21

## A. リポジトリ構成

```text
Lab-RecSAVER/
├── configs/
│   ├── recsaver_mvp.yaml
│   ├── context_analysis.yaml
│   ├── k_history_pilot.yaml
│   └── k_history_robustness.yaml
├── data/
│   ├── raw/                 # Git管理外のELLIPSE元データ
│   └── processed/           # Git管理外の再生成データ
├── docs/
│   ├── basic_analysis_report.md
│   ├── context_history_analysis.md
│   ├── data_profile.md
│   ├── lab_environment.md
│   ├── research_context.md
│   └── repository_structure.md
├── notebooks/
│   └── basic_analysis.ipynb
├── outputs/
│   ├── basic_analysis/
│   │   ├── figures/
│   │   └── tables/
│   ├── recsaver_mvp/
│   ├── context_analysis/
│   ├── k_history_pilot/
│   └── k_history_robustness/
├── prompts/
│   ├── zero_shot_prediction.txt
│   ├── score_only_prediction.txt
│   ├── reference_generation.txt
│   └── self_verification.txt
├── src/
│   ├── basic_analysis.py
│   ├── create_rater_essay_wide.py
│   ├── transform_data.py
│   └── recsaver/
│       ├── context_analysis.py
│       ├── k_history_pilot.py
│       ├── k_history_robustness.py
│       ├── max_model_len_probe.py
│       ├── phase1_prediction.py
│       ├── phase2_reference.py
│       ├── phase3_reasoning_eval.py
│       ├── phase4_analysis.py
│       └── self_verification.py
├── tests/
│   ├── test_basic_analysis.py
│   ├── test_recsaver.py
│   └── test_transform_data.py
├── AGENTS.md
├── README.md
├── requirements-analysis.txt
└── requirements-gpu.txt
```

未実装の`k0_baseline`、`rater_history_placebo`、`reasoning_ablation`、
`reference_generation`、`full_experiment`は、実装時に対応する
`outputs/<experiment_name>/`を作る。空フォルダは先行作成しない。

## B. 各主要フォルダの役割

| Path | Role |
|---|---|
| `configs/` | 実験条件、モデル設定、seed、output directoryを管理する。 |
| `data/raw/` | 再配布しないELLIPSE元CSV。Git管理外。 |
| `data/processed/` | 元CSVから再生成するwideデータ。Git管理外。 |
| `docs/` | 環境、データ、分析結果、リポジトリ構成の記録。 |
| `outputs/` | GitHubで同期する実験結果。原則として1実験1ディレクトリ。 |
| `outputs/basic_analysis/` | 基礎分析の表と図。 |
| `outputs/recsaver_mvp/` | 10 targetの初期Rec-SAVER MVP。Phase 1～4の結果を含む。 |
| `outputs/context_analysis/` | max contextロード試験と固定K収容率分析。 |
| `outputs/k_history_pilot/` | 同一100 targetにおけるK=1/3/5/7比較。 |
| `outputs/k_history_robustness/` | K=3/5の複数history seed確認。完了した結果のみ格納する。 |
| `prompts/` | Phase別の外部prompt template。 |
| `src/` | データ変換、基礎分析、Rec-SAVER実験コード。 |
| `tests/` | データ整合性、漏洩防止、nested sampling等のCPUテスト。 |

## C. 主要実行スクリプト

| Script | Purpose | Config | Output directory |
|---|---|---|---|
| `python -m src.create_rater_essay_wide` | raw CSVから1 essay×1 raterのwide CSVを生成 | CLI引数 | `data/processed/` |
| `python -m src.basic_analysis` | ELLIPSE基礎分析 | CLI引数 | `outputs/basic_analysis/` |
| `python -m src.recsaver.phase1_prediction` | 初期MVPのOverall予測 | `configs/recsaver_mvp.yaml` | `outputs/recsaver_mvp/` |
| `python -m src.recsaver.phase2_reference` | 初期MVPのReference Candidate生成 | 同上 | `outputs/recsaver_mvp/` |
| `python -m src.recsaver.self_verification` | 初期MVPの自己検証 | 同上 | `outputs/recsaver_mvp/` |
| `python -m src.recsaver.phase3_reasoning_eval` | 初期MVPの理由類似度評価 | 同上 | `outputs/recsaver_mvp/` |
| `python -m src.recsaver.phase4_analysis` | 初期MVPの予測性能集計 | 同上 | `outputs/recsaver_mvp/` |
| `python -m src.recsaver.context_analysis` | 固定Kのcontext収容率分析 | `configs/context_analysis.yaml`＋CLI | `outputs/context_analysis/` |
| `python -m src.recsaver.max_model_len_probe` | 1条件のモデルロード・短文推論probe | CLI引数 | 指定したJSON path |
| `python -m src.recsaver.k_history_pilot` | 同一targetのK=1/3/5/7比較 | `configs/k_history_pilot.yaml` | `outputs/k_history_pilot/` |
| `python -m src.recsaver.k_history_robustness` | K=3/5の複数seed比較 | `configs/k_history_robustness.yaml` | `outputs/k_history_robustness/` |

## D. Git管理方針

### Git管理する

- `src/`
- `configs/`
- `docs/`
- `tests/`
- `prompts/`
- `outputs/`内の再利用・確認に必要なCSV、JSON、JSONL、PNG、metadata、config snapshot

### Git管理しない

- `data/raw/`と`data/processed/`のdataset
- model weights、checkpoint、Hugging Face/vLLM cache
- Python cache、Notebook checkpoint、仮想環境
- `outputs/gpu/`の大規模GPU入力・生成物
- `outputs/**/tmp/`、`outputs/**/cache/`、`outputs/**/*.log`

## Outputsのサイズ方針

2026-08-21時点で100 MB以上の単一ファイルはない。最大は
`outputs/context_analysis/context_token_statistics.csv`（約21.9 MB）で、GitHubの
単一ファイル上限には抵触しない。ただし更新を繰り返すとGit履歴が膨らむため注意する。
`k_history_predictions.jsonl`（約6.0 MB）などの追跡用JSONLはGit管理可能である。

## 既存outputの移動記録

2026-08-21に、初期10-target MVPを次のとおり移動した。

```text
outputs/recsaver/ -> outputs/recsaver_mvp/
```

11ファイルを内容変更せず移動した。`outputs/recsaver_mvp/resolved_config.json`は
実験実行時のsnapshotであるため、内部の旧output pathは履歴情報として維持する。
