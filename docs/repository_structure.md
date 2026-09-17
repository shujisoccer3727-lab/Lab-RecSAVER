# Lab-RecSAVER リポジトリ構成

更新日: 2026-09-12

## A. リポジトリ構成

```text
Lab-RecSAVER/
├── configs/
│   ├── recsaver_mvp.yaml
│   ├── context_analysis.yaml
│   ├── history_ablation.yaml
│   ├── rater_history_placebo.yaml
│   ├── rater_profile.yaml
│   ├── overall_rubric_ablation.yaml
│   ├── rubric_rater_placebo.yaml
│   ├── full_rubric_ablation.yaml
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
│   ├── history_ablation/       # K=0 vs K=3 history ablation
│   ├── rater_history_placebo/  # correct vs wrong rater K=3
│   ├── rater_profile/          # natural-language rater profiles and predictions
│   ├── overall_rubric_ablation/ # Overall Rubric ablation
│   ├── rubric_rater_placebo/    # Rubricあり correct vs wrong rater K=3
│   ├── full_rubric_ablation/    # Overall-only vs Full Rubric
│   ├── k_history_pilot/       # English prompt official Pilot (K=0/1/3/5/7)
│   ├── k_history_pilot_ja/    # Preserved Japanese prompt Pilot (K=1/3/5/7)
│   └── k_history_robustness/
├── prompts/
│   ├── ja/                  # 過去実験の再現・比較用
│   │   ├── zero_shot_prediction.txt
│   │   ├── score_only_prediction.txt
│   │   ├── reference_generation.txt
│   │   └── self_verification.txt
│   └── en/                  # 今後の新規実験用（default）
│       ├── zero_shot_prediction.txt
│       ├── score_only_prediction.txt
│       ├── reference_generation.txt
│       ├── self_verification.txt
│       └── full_rubric_prediction.txt
├── rubrics/
│   ├── ellipse_overall_rubric.md
│   ├── ellipse_rubric_structured.md
│   └── ellipse_rubric_structured.json
├── src/
│   ├── basic_analysis.py
│   ├── create_rater_essay_wide.py
│   ├── transform_data.py
│   └── recsaver/
│       ├── context_analysis.py
│       ├── history_ablation.py
│       ├── rater_history_placebo.py
│       ├── rater_profile_generation.py
│       ├── rater_profile_prediction.py
│       ├── overall_rubric_ablation.py
│       ├── rubric_rater_placebo.py
│       ├── full_rubric_ablation.py
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
| `outputs/history_ablation/` | K=0 vs K=3で採点者履歴そのものの有効性を検証する正式アブレーション。 |
| `outputs/rater_history_placebo/` | target rater本人と別採点者のK=3履歴を比較し、採点者固有情報と一般的few-shot効果を切り分ける。 |
| `outputs/rater_profile/` | 履歴から自然言語Profileを生成し、raw historyより採点者固有情報を明示的に利用できるか検証する。 |
| `outputs/overall_rubric_ablation/` | Overall Rubric単体の効果と、RubricがCorrect-rater raw history活用を助けるか検証する。 |
| `outputs/rubric_rater_placebo/` | Overall Rubricを固定し、correct-rater K=3とwrong-rater K=3を比較する。 |
| `outputs/full_rubric_ablation/` | Overall Rubricに6 Trait Rubricを追加し、一般予測とcorrect-rater履歴中のTrait情報解釈への効果を検証する。 |
| `outputs/k_history_pilot/` | 英語prompt・同一100 targetにおけるK=0/1/3/5/7比較（公式Pilot）。 |
| `outputs/k_history_pilot_ja/` | 旧日本語prompt Pilot（K=1/3/5/7）。履歴成果物として内容不変で保存。 |
| `outputs/k_history_robustness/` | K=3/5の複数history seed確認。完了した結果のみ格納する。 |
| `prompts/ja/` | 日本語prompt。過去実験の再現・言語比較用として内容を保持する。 |
| `prompts/en/` | 英語prompt。今後の新規実験でconfigから選択する既定template。 |
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
| `python -m src.recsaver.history_ablation` | K=0 vs K=3の本人採点履歴アブレーション | `configs/history_ablation.yaml` | `outputs/history_ablation/` |
| `python -m src.recsaver.rater_history_placebo` | 本人K=3 vs 他人K=3の履歴placebo | `configs/rater_history_placebo.yaml` | `outputs/rater_history_placebo/` |
| `python -m src.recsaver.rater_profile_generation` | target非依存の自然言語Rater Profile生成 | `configs/rater_profile.yaml` | `outputs/rater_profile/` |
| `python -m src.recsaver.rater_profile_prediction` | Profile-onlyによるOverall予測 | `configs/rater_profile.yaml` | `outputs/rater_profile/` |
| `python -m src.recsaver.overall_rubric_ablation` | Overall Rubricあり／なし×K=0／Raw K=3比較 | `configs/overall_rubric_ablation.yaml` | `outputs/overall_rubric_ablation/` |
| `python -m src.recsaver.rubric_rater_placebo` | Overall Rubricありのcorrect-rater K=3 vs wrong-rater K=3 | `configs/rubric_rater_placebo.yaml` | `outputs/rubric_rater_placebo/` |
| `python -m src.recsaver.full_rubric_ablation` | Overall-only vs Full RubricをK=0／correct K=3で比較 | `configs/full_rubric_ablation.yaml` | `outputs/full_rubric_ablation/` |
| `python -m src.recsaver.max_model_len_probe` | 1条件のモデルロード・短文推論probe | CLI引数 | 指定したJSON path |
| `python -m src.recsaver.k_history_pilot` | 英語prompt・同一targetのK=0/1/3/5/7比較 | `configs/k_history_pilot.yaml` | `outputs/k_history_pilot/` |
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

## Prompt言語方針

今後の新規実験では`prompt_dir: prompts/en`を使用する。日本語版は削除せず、
過去実験の再現・比較用に`prompts/ja/`へ保存する。prompt言語の変更は実験条件の
変更として扱い、resolved configとmetadataにprompt directory、language、各ファイルの
SHA-256を記録する。既存output内のmetadata/config snapshotは変更しない。
2026-08-22以降の新規実験では、原則として英語promptを正式条件とする。

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

2026-08-22に、日本語prompt版K History Pilotを次のとおり内容不変で移動した。

```text
outputs/k_history_pilot/ -> outputs/k_history_pilot_ja/
```

以後、`outputs/k_history_pilot/`は英語prompt版の正式Pilot（K=0/1/3/5/7）に使用する。

## Boundary-aware History Prompt ablation

Overall Rubric + Correct-rater History K=3を固定し、Rubric上のscore boundaryをHistoryから明示的に比較させることで、履歴利用とscore calibrationが改善するか検証するPromptアブレーション。

- `configs/boundary_aware_history.yaml`: 既存model/generation条件、固定入力の参照先、新規100件の設定。
- `prompts/en/boundary_aware_rubric_prediction.txt`: 隣接スコアと履歴を比較し、簡潔な採点根拠のみを出力するinstruction。
- `src/recsaver/boundary_aware_history.py`: 既存loading/parser/metrics/paired/distributionを再利用し、dry run、新規条件のみ推論、探索分析を保存。
- `outputs/boundary_aware_history/`: 予測、比較CSV、Reasoning例、入力一致検証、metadata、resolved config。

実行: `python -m src.recsaver.boundary_aware_history --dry-run`、続いて同コマンドの`--dry-run`なし。
新規生成は100件に限定しparse retryは行わない。既存予測ファイルがある場合は再実行を拒否する。
pairedのMean/Median AE differenceはExisting minus Boundary（正が改善）。Rater better/same/worseはMAEによる探索的比較。
Reasoningのkeyword監査は正式評価ではなく、隣接スコア比較の検出には対比表現と隣接する明示的score番号を要求する。

## Reasoning Evaluation V1

- `configs/reasoning_eval_v1.yaml`: Correct K=3 + Overall Rubric + Existing Promptの既存100-target predictionを参照する評価設定。
- `prompts/en/reference_generation_rubric.txt`: Gold条件付きの定性的Reference生成。score番号や採点者属性の推測を禁止。
- `prompts/en/self_verification_rubric.txt`: Goldを入力せず、Referenceが示すOverallを再構成。
- `src/recsaver/reasoning_eval_v1.py`: 入力固定の検証、attempt単位の保存、漏洩時retry、Self-verification、resume。
- `src/recsaver/reference_audit.py`: 採点文脈に限定したGold/他scoreの明示検出、採点者属性の簡易warning。
- `src/recsaver/reasoning_eval_metrics.py`: 既存BLEU/ROUGEを再利用し、実際のMETEOR/BERTScore、reference別・target別max/mean、coverage別group分析、Jaccard多様性を計算。
- `src/recsaver/reasoning_eval_report.py`: 保存済み入力の再照合、結果レポート。
- `requirements-reasoning-eval.txt`: 評価用の追加依存。
- `tests/test_reasoning_eval_v1.py`: 漏洩判定、retry上限、parse retry、Gold分離、skip/resume、末尾journal破損の復旧。
- `outputs/reasoning_eval_v1/`: 正本のattempt JSONL、pool、指標、監査、metadata、レポート。`dry_run_3/`に初期3件の確認時点を保存。

Reference候補枠は3、各枠の生成は初回を含め最大5回。Self-verificationはscore不一致をretryしない。
実行は `python -m src.recsaver.reasoning_eval_v1 --stage validate`、`--stage generate --limit 3`、`--stage evaluate`、確認後に`--stage generate`で残りを再開する。
評価完了後は `python -m src.recsaver.reasoning_eval_report --require-complete`。Prediction生成は行わない。
各requestのseedはtarget/candidate/attempt/stageから決定し、完了済みrequestはskip。configまたはsource hashが変わる再開は拒否する。
新しい固定manifestへの拡張は別runのoutput_dirを使い、今回はdataset全件を実行しない。

## Full-scale Prediction Experiment

- `configs/full_prediction_experiment.yaml`: Pilotで固定した4条件、履歴・生成・bootstrap seed、resume設定。
- `src/recsaver/full_prediction_experiment.py`: 全件audit、同一source除外、固定履歴manifest、条件別の追記保存・再開、既存JSON parserによる推論。
- `src/recsaver/full_prediction_analysis.py`: 全利用可能sampleと共通target集合の指標、paired比較、分布、rater/Gold/same-essay分析、target bootstrap CI、レポート。
- `tests/test_full_prediction_experiment.py`: 履歴の決定性・同一source除外、request seed、QWK、末尾JSONL復旧。
- `outputs/full_prediction_experiment/`: 条件別prediction JSONL、target manifest、audit、分析、metadata、resolved config、report。

実行順は `--stage audit` の後、`--stage run --condition k0`、`k0_overall_rubric`、`wrong_k3_overall_rubric`、`correct_k3_overall_rubric`。各condition完了時に中間summaryを保存する。
各request seedはgeneration seed・condition・target ID・attemptから決まり、完了済みtargetをskipする。config/input hash変更時のresumeは拒否する。
主比較は4条件すべてでparse成功した共通target集合。AE differenceはfrom minus to、QWK deltaはto minus from。
