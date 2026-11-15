#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
export VLLM_USE_V1=0 VLLM_ENABLE_V1_ENGINE=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
task_output=outputs/human_score_disagreement_rater_tendency_inline
mkdir -p "$task_output"
printf 'running\n' > "$task_output/runner_exit_code.txt"
/home/guestuser/miniforge3/envs/qwen3/bin/python -m src.recsaver.human_score_disagreement_rater_tendency_inline --stage "${1:-pilot}" > "$task_output/run.log" 2>&1
task_code=$?
printf '%s\n' "$task_code" > "$task_output/runner_exit_code.txt"
exit "$task_code"
