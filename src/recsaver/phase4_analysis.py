from __future__ import annotations

import argparse
import json
import numpy as np
import pandas as pd
from .config import load_config, project_path
from .utils import read_jsonl


def quadratic_weighted_kappa(gold, predicted, minimum=1, maximum=5) -> float:
    gold, predicted = np.asarray(gold, int), np.asarray(predicted, int)
    n = maximum - minimum + 1
    observed = np.zeros((n, n)); expected = np.zeros((n, n))
    for a, b in zip(gold, predicted): observed[a-minimum, b-minimum] += 1
    gh = np.bincount(gold-minimum, minlength=n); ph = np.bincount(predicted-minimum, minlength=n)
    expected = np.outer(gh, ph) / len(gold)
    weights = np.fromfunction(lambda i, j: ((i-j)/(n-1))**2, (n, n))
    denominator = (weights * expected).sum()
    return float(1 - (weights * observed).sum()/denominator) if denominator else float("nan")


def run(config: dict) -> dict:
    outdir = project_path(config, config["output_dir"])
    valid = [r for r in read_jsonl(outdir / "phase1_predictions.jsonl") if r.get("predicted_overall")]
    detail = pd.DataFrame({"target_id": [r["target_id"] for r in valid],
                           "rater_id": [r["rater_id"] for r in valid],
                           "gold_overall": [r["gold_overall"] for r in valid],
                           "predicted_overall": [r["predicted_overall"] for r in valid]})
    detail["exact_correct"] = detail.gold_overall == detail.predicted_overall
    detail["absolute_error"] = (detail.gold_overall-detail.predicted_overall).abs()
    detail["squared_error"] = (detail.gold_overall-detail.predicted_overall)**2
    metrics = {"n": len(detail), "exact_accuracy": float(detail.exact_correct.mean()),
               "mae": float(detail.absolute_error.mean()), "rmse": float(np.sqrt(detail.squared_error.mean())),
               "qwk": quadratic_weighted_kappa(detail.gold_overall, detail.predicted_overall)}
    quality_path = outdir / "reasoning_quality.csv"
    if quality_path.exists():
        detail = detail.merge(pd.read_csv(quality_path), on=["target_id", "rater_id"], how="left")
    detail.to_csv(outdir / "prediction_per_target.csv", index=False)
    metric_columns = [c for c in ["bleu_max", "rouge1_f1_max", "meteor_max", "bertscore_f1_max"] if c in detail]
    group_rows = []
    for correct, group in detail.groupby("exact_correct"):
        for metric in metric_columns:
            values = group[metric].dropna()
            group_rows.append({"exact_correct": bool(correct), "metric": metric, "mean": values.mean(),
                               "median": values.median(), "std": values.std(), "count": len(values)})
    pd.DataFrame(group_rows).to_csv(outdir / "reasoning_quality_by_correctness.csv", index=False)
    correlations = [{"metric": m, "spearman_with_absolute_error": detail[[m,"absolute_error"]].corr(method="spearman").iloc[0,1],
                     "count": int(detail[m].notna().sum())} for m in metric_columns]
    pd.DataFrame(correlations).to_csv(outdir / "reasoning_error_correlations.csv", index=False)
    (outdir / "prediction_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    args = parser.parse_args(); print(json.dumps(run(load_config(args.config)), indent=2))


if __name__ == "__main__": main()
