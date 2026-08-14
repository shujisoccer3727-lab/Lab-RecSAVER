from __future__ import annotations

from pathlib import Path
from .history import format_history

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


def render(name: str, history, target, **values) -> str:
    template = (PROMPT_DIR / name).read_text(encoding="utf-8")
    return template.format(history=format_history(history), target_essay=target["Text"], **values)


def fit_history(name: str, history, target, config: dict, **values):
    max_prompt_tokens = config["model"]["max_model_len"] - config["context"]["reserved_output_tokens"]
    chars_per_token = config["context"]["approximate_chars_per_token"]
    current = history.copy()
    while True:
        prompt = render(name, current, target, **values)
        estimate = int(len(prompt) / chars_per_token) + 1
        if estimate <= max_prompt_tokens or current.empty:
            if estimate > max_prompt_tokens:
                raise ValueError(f"target+instructions exceed context estimate: {estimate}")
            return prompt, current, estimate
        current = current.iloc[:-1]
