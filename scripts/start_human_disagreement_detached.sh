#!/usr/bin/env bash
# 同じtmuxセッションを二重作成せず、既存ログを退避して再開する。
set -euo pipefail
cd "$(dirname "$0")/.."
if tmux has-session -t recsaver-human-disagreement 2>/dev/null; then
  printf '%s\n' 'Experiment session already exists; no duplicate started.'
  exit 0
fi
if [[ -f outputs/human_score_disagreement/run.log ]]; then
  cp outputs/human_score_disagreement/run.log "outputs/human_score_disagreement/run.before-detached-$(date -u +%Y%m%dT%H%M%SZ).log"
fi
task_repo_dir=$(pwd)
tmux new-session -d -s recsaver-human-disagreement "bash '$task_repo_dir/scripts/run_human_disagreement_detached.sh'"
printf '%s\n' 'Started independent tmux session recsaver-human-disagreement.'
