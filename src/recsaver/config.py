from __future__ import annotations

from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    with path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    config["_config_path"] = str(path)
    config["_root"] = str(ROOT)
    return config


def project_path(config: dict, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(config["_root"]) / path
