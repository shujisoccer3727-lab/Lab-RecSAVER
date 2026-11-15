#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
task_output=outputs/human_score_disagreement_rater_tendency_inline
if [[ -f "$task_output/run.log" ]]; then
  cp "$task_output/run.log" "$task_output/run.before-full-$(date -u +%Y%m%dT%H%M%SZ).log"
fi
bash scripts/run_tendency_inline_detached.sh all
task_code=$?
if [[ "$task_code" -eq 0 ]]; then
  printf 'auditing\n' > "$task_output/runner_exit_code.txt"
  /home/guestuser/miniforge3/envs/qwen3/bin/python scripts/audit_tendency_inline_outputs.py >> "$task_output/run.log" 2>&1
  task_code=$?
fi
printf '%s\n' "$task_code" > "$task_output/runner_exit_code.txt"
exit "$task_code"
