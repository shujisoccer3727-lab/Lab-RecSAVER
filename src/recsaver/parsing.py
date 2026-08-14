from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    for candidate in [text.strip(), *re.findall(r"\{.*?\}", text, flags=re.S)]:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    raise ValueError("JSON object not found")


def parse_prediction(text: str, require_reasoning: bool = True) -> dict:
    value = extract_json(text)
    score = value.get("predicted_overall")
    if isinstance(score, str) and score.strip().isdigit():
        score = int(score.strip())
    if not isinstance(score, int) or score not in range(1, 6):
        raise ValueError("predicted_overall must be integer 1..5")
    reasoning = str(value.get("reasoning", "")).strip()
    if require_reasoning and not reasoning:
        raise ValueError("reasoning is empty")
    return {"predicted_overall": score, "reasoning": reasoning}


def parse_reasoning(text: str) -> str:
    reasoning = str(extract_json(text).get("reasoning", "")).strip()
    if not reasoning:
        raise ValueError("reasoning is empty")
    return reasoning


def leaks_score(reasoning: str, score: int) -> bool:
    patterns = [rf"\b{score}\b", rf"{score}\s*点", rf"score\s*[:=]?\s*{score}", rf"overall\s*[:=]?\s*{score}"]
    return any(re.search(pattern, reasoning, flags=re.I) for pattern in patterns)
