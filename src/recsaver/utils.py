from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def target_id(row) -> str:
    return f"{int(row['source_row_id'])}:{int(row['rater_position'])}"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def experiment_metadata(config: dict) -> dict:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=config["_root"], check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except Exception:
        commit = "unknown"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return {"experiment_id": f"recsaver_mvp_{stamp}", "timestamp": stamp, "git_commit": commit}
