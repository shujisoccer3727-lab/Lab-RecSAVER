from __future__ import annotations

import hashlib
from pathlib import Path
from .history import format_history

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PROMPT_DIR = "prompts/en"


def resolve_prompt_dir(prompt_dir: str | Path = DEFAULT_PROMPT_DIR) -> Path:
    path = Path(prompt_dir)
    return path if path.is_absolute() else ROOT_DIR / path


def render(name: str, history, target, *, prompt_dir: str | Path = DEFAULT_PROMPT_DIR, **values) -> str:
    template = (resolve_prompt_dir(prompt_dir) / name).read_text(encoding="utf-8")
    return template.format(history=format_history(history), target_essay=target["Text"], **values)


def prompt_metadata(config: dict) -> dict:
    configured = config.get("prompt_dir", DEFAULT_PROMPT_DIR)
    directory = resolve_prompt_dir(configured)
    hashes = {
        f"{path.stem}_prompt_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.glob("*.txt"))
    }
    return {"prompt_language": directory.name, "prompt_dir": str(configured), **hashes}


def fit_history(name: str, history, target, config: dict, **values):
    max_prompt_tokens = config["model"]["max_model_len"] - config["context"]["reserved_output_tokens"]
    chars_per_token = config["context"]["approximate_chars_per_token"]
    current = history.copy()
    while True:
        prompt = render(name, current, target, prompt_dir=config.get("prompt_dir", DEFAULT_PROMPT_DIR), **values)
        estimate = int(len(prompt) / chars_per_token) + 1
        if estimate <= max_prompt_tokens or current.empty:
            if estimate > max_prompt_tokens:
                raise ValueError(f"target+instructions exceed context estimate: {estimate}")
            return prompt, current, estimate
        current = current.iloc[:-1]
