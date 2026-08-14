from __future__ import annotations

import argparse
from collections import Counter
import math
import re
import pandas as pd
from .config import load_config, project_path
from .utils import read_jsonl


def tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def rouge1_f1(hypothesis: str, reference: str) -> float:
    hyp, ref = Counter(tokens(hypothesis)), Counter(tokens(reference))
    overlap = sum((hyp & ref).values())
    if not hyp or not ref or not overlap:
        return 0.0
    precision, recall = overlap / sum(hyp.values()), overlap / sum(ref.values())
    return 2 * precision * recall / (precision + recall)


def sentence_bleu(hypothesis: str, reference: str) -> float:
    hyp, ref = tokens(hypothesis), tokens(reference)
    if not hyp or not ref:
        return 0.0
    precisions = []
    for n in range(1, 5):
        h = Counter(tuple(hyp[i:i+n]) for i in range(max(0, len(hyp)-n+1)))
        r = Counter(tuple(ref[i:i+n]) for i in range(max(0, len(ref)-n+1)))
        matches, total = sum((h & r).values()), sum(h.values())
        precisions.append((matches + 1) / (total + 1))
    brevity = 1.0 if len(hyp) > len(ref) else math.exp(1 - len(ref) / len(hyp))
    return brevity * math.exp(sum(math.log(p) for p in precisions) / 4)


def run(config: dict) -> pd.DataFrame:
    outdir = project_path(config, config["output_dir"])
    predictions = {r["target_id"]: r for r in read_jsonl(outdir / "phase1_predictions.jsonl")}
    pool = read_jsonl(outdir / "verified_reference_pool.jsonl")
    grouped = {}
    for reference in pool:
        grouped.setdefault(reference["target_id"], []).append(reference)
    rows = []
    for target, references in grouped.items():
        prediction = predictions.get(target)
        if not prediction or not prediction.get("reasoning"):
            continue
        bleu = [sentence_bleu(prediction["reasoning"], r["reference_reasoning"]) for r in references]
        rouge = [rouge1_f1(prediction["reasoning"], r["reference_reasoning"]) for r in references]
        rows.append({"target_id": target, "rater_id": prediction["rater_id"],
                     "bleu_max": max(bleu), "bleu_mean": sum(bleu)/len(bleu),
                     "rouge1_f1_max": max(rouge), "rouge1_f1_mean": sum(rouge)/len(rouge),
                     "meteor_max": float("nan"), "meteor_mean": float("nan"),
                     "bertscore_f1_max": float("nan"), "bertscore_f1_mean": float("nan"),
                     "num_verified_references": len(references),
                     "metric_note": "METEOR/BERTScore unavailable: optional dependencies not installed"})
    result = pd.DataFrame(rows)
    result.to_csv(outdir / "reasoning_quality.csv", index=False)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    args = parser.parse_args(); print(f"Reasoning evaluation: {len(run(load_config(args.config)))} targets")


if __name__ == "__main__": main()
