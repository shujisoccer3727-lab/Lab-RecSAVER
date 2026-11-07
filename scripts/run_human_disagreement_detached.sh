#!/usr/bin/env bash
# tmuxの独立セッション内で実行し、終了コードを記録する。
set -uo pipefail
cd "$(dirname "$0")/.."
printf '%s\n' "$$" > outputs/human_score_disagreement/runner_pid.txt
printf '%s\n' running > outputs/human_score_disagreement/runner_exit_code.txt
bash scripts/run_human_score_disagreement.sh > outputs/human_score_disagreement/run.log 2>&1
task_exit_code=$?
printf '%s\n' "$task_exit_code" > outputs/human_score_disagreement/runner_exit_code.txt
exit "$task_exit_code"
