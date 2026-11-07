#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export VLLM_USE_V1=0
export VLLM_ENABLE_V1_ENGINE=0
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export PYTHONUNBUFFERED=1
if [[ -f outputs/human_score_disagreement/pilot_gap3_validation.json && -f outputs/human_score_disagreement/metric_metadata.json ]]; then
  /home/guestuser/miniforge3/envs/qwen3/bin/python -m src.recsaver.human_score_disagreement --stage generate
  /home/guestuser/miniforge3/envs/qwen3/bin/python -m src.recsaver.human_score_disagreement --stage evaluate
else
  /home/guestuser/miniforge3/envs/qwen3/bin/python -m src.recsaver.human_score_disagreement --stage all
fi
exec /home/guestuser/miniforge3/envs/qwen3/bin/python scripts/validate_human_score_disagreement.py
