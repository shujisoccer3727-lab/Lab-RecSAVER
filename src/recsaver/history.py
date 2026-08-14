from __future__ import annotations

import hashlib
import random
from .data import TRAITS


def _stable_seed(seed: int, value: str) -> int:
    digest = hashlib.sha256(f"{seed}:{value}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def sample_history(frame, target, size: int, seed: int, strategy: str = "random"):
    if strategy != "random":
        raise ValueError(f"unsupported history strategy: {strategy}")
    candidates = frame[(frame["rater_id"] == target["rater_id"]) & (frame["target_id"] != target["target_id"])]
    if len(candidates) < size:
        raise ValueError(f"history不足: target={target['target_id']} available={len(candidates)}")
    indices = list(candidates.index)
    random.Random(_stable_seed(seed, target["target_id"])).shuffle(indices)
    history = candidates.loc[indices[:size]].copy()
    assert target["target_id"] not in set(history["target_id"])
    return history


def format_history(history) -> str:
    blocks = []
    for number, (_, row) in enumerate(history.iterrows(), 1):
        traits = "\n".join(f"{name}: {int(row[name])}" for name in TRAITS)
        blocks.append(
            f"[History {number}; ID={row['target_id']}]\nEssay:\n{row['Text']}\n\n"
            f"Overall: {int(row['Overall'])}\n\nTrait Scores:\n{traits}"
        )
    return "\n\n---\n\n".join(blocks)
