# 研究室PC環境

確認日: 2026-08-08

- OS: WSL2 Ubuntu
- Conda環境: `qwen3` (`/home/guestuser/miniforge3/envs/qwen3`)
- Python: 3.10.20
- pandas: 2.3.3
- NumPy: 1.26.4
- vLLM: 0.6.6.post1
- PyTorch: 2.5.1+cu121
- Transformers: 4.48.3
- GPU: NVIDIA RTX 6000 Ada Generation (49,140 MiB)
- NVIDIA driver: 596.72
- `nvidia-smi`表示CUDA: 13.2
- PyTorchビルドCUDA: 12.1 (`cu121`)

今回追加したパッケージはpandas 2.3.3と、その必須依存である
python-dateutil 2.9.0.post0、pytz 2026.3.post1、tzdata 2026.3です。
既存のNumPy、vLLM、PyTorch、Transformers、CUDA関連パッケージは変更していません。

## データ再生成

raw CSVの配置先:

```text
data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv
```

実行コマンド:

```bash
conda activate qwen3
export VLLM_USE_V1=0
export VLLM_ENABLE_V1_ENGINE=0
python -m src.create_rater_essay_wide \
  --input data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv
```

出力は`data/processed/rater_essay_wide.csv`です。rawおよびprocessed CSVは
`.gitignore`によりGit管理外です。
