"""同一target・nested historyでPhase 1のKを比較するPilot。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .prompts import render
from .utils import write_jsonl


def select_pilot_targets(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    exp = config["experiment"]
    counts = frame.groupby("rater_id").size()
    eligible_raters = counts[counts >= exp["min_rater_samples"]].index
    eligible = frame[frame["rater_id"].isin(eligible_raters)]
    max_k = max(exp["k_values"])
    eligible = eligible.groupby("rater_id").filter(lambda group: len(group) - 1 >= max_k)
    return eligible.sample(n=exp["num_targets"], random_state=config["seed"]).sort_values("target_id")


def prepare(config: dict, tokenizer) -> tuple[pd.DataFrame, list[dict]]:
    frame = load_valid_data(config)
    targets = select_pilot_targets(frame, config)
    exp = config["experiment"]
    maximum = max(exp["k_values"])
    prepared = []
    for _, target in targets.iterrows():
        pool = sample_history(frame, target, maximum, config["seed"], "random")
        previous_ids: list[str] = []
        for k in exp["k_values"]:
            history = pool.iloc[:k]
            ids = history["target_id"].tolist()
            assert previous_ids == ids[:len(previous_ids)]
            assert target["target_id"] not in ids
            assert history["rater_id"].eq(target["rater_id"]).all()
            previous_ids = ids
            prompt = render("zero_shot_prediction.txt", history, target)
            chat_tokens = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}], tokenize=True, add_generation_prompt=True
            )
            prompt_tokens = len(chat_tokens)
            fits = prompt_tokens + config["generation"]["prediction"]["max_tokens"] <= config["model"]["max_model_len"]
            prepared.append({"target": target, "k": k, "history": history, "prompt": prompt,
                             "prompt_tokens": prompt_tokens, "context_fit": fits})
    return targets, prepared


def metadata(config: dict, targets: pd.DataFrame, prepared: list[dict]) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config["_root"], check=True,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    pools = {}
    for item in prepared:
        if item["k"] == max(config["experiment"]["k_values"]):
            pools[item["target"]["target_id"]] = item["history"]["target_id"].tolist()
    return {"experiment_id": "k_history_pilot_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
            "seed": config["seed"], "model_id": config["model"]["model_id"],
            "max_model_len": config["model"]["max_model_len"],
            "sampling_parameters": config["generation"]["prediction"],
            "target_ids": targets["target_id"].tolist(), "nested_history_pools": pools}


def summarize(records: list[dict], outdir: Path) -> pd.DataFrame:
    valid = pd.DataFrame([r for r in records if r["parse_success"]])
    rows = []
    for k, group in valid.groupby("K"):
        all_k = [r for r in records if r["K"] == k]
        rows.append({"K": k, "n": len(group), "exact_accuracy": group.exact_correct.mean(),
                     "mae": group.absolute_error.mean(), "rmse": math.sqrt(group.squared_error.mean()),
                     "qwk": quadratic_weighted_kappa(group.gold_overall, group.predicted_overall),
                     "parse_success_rate": len(group) / len(all_k),
                     "mean_prompt_tokens": np.mean([r["prompt_tokens"] for r in all_k]),
                     "median_prompt_tokens": np.median([r["prompt_tokens"] for r in all_k]),
                     "p90_prompt_tokens": np.quantile([r["prompt_tokens"] for r in all_k], .9),
                     "mean_inference_time_seconds": np.mean([r["inference_time_seconds"] for r in all_k]),
                     "total_inference_time_seconds": sum(r["inference_time_seconds"] for r in all_k),
                     "parse_errors": sum(not r["parse_success"] for r in all_k),
                     "context_overflows": sum(not r["context_fit"] for r in all_k)})
    summary = pd.DataFrame(rows).sort_values("K")
    summary.to_csv(outdir / "k_history_summary.csv", index=False)
    comparison = valid.pivot(index="target_id", columns="K", values="absolute_error").reset_index()
    comparison.to_csv(outdir / "k_history_target_comparison.csv", index=False)
    paired = []
    ks = summary.K.tolist()
    for lower, upper in zip(ks, ks[1:]):
        delta = comparison[lower] - comparison[upper]
        paired.append({"from_K": lower, "to_K": upper, "improved_targets": int((delta > 0).sum()),
                       "unchanged_targets": int((delta == 0).sum()), "worsened_targets": int((delta < 0).sum()),
                       "mean_ae_difference": delta.mean(), "median_ae_difference": delta.median(),
                       "paired_targets": int(delta.notna().sum())})
    pd.DataFrame(paired).to_csv(outdir / "k_history_paired_comparison.csv", index=False)
    rater = valid.groupby(["K", "rater_id"]).agg(
        count=("target_id", "size"), accuracy=("exact_correct", "mean"), mae=("absolute_error", "mean")
    ).reset_index()
    rater.to_csv(outdir / "k_history_rater_summary.csv", index=False)
    return summary


def run(config: dict) -> tuple[list[dict], pd.DataFrame]:
    generator = VLLMGenerator(config)
    targets, prepared = prepare(config, generator.tokenizer)
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    meta = metadata(config, targets, prepared)
    (outdir / "experiment_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    records = []
    for k in config["experiment"]["k_values"]:
        items = [item for item in prepared if item["k"] == k]
        fit_items = [item for item in items if item["context_fit"]]
        started = time.perf_counter()
        generated = []
        batch_size = int(config["experiment"].get("batch_size", len(fit_items)))
        for offset in range(0, len(fit_items), batch_size):
            chunk = fit_items[offset:offset + batch_size]
            generated.extend(generator.generate(
                [item["prompt"] for item in chunk], config["generation"]["prediction"]
            ))
        elapsed = time.perf_counter() - started
        per_item = elapsed / len(fit_items) if fit_items else 0.0
        output_map = {item["target"]["target_id"]: values[0] for item, values in zip(fit_items, generated)}
        for item in items:
            target, history = item["target"], item["history"]
            raw = output_map.get(target["target_id"], "")
            attempts = [raw] if raw else []
            error = None; parsed = {"predicted_overall": None, "reasoning": ""}
            if item["context_fit"]:
                for attempt in range(config["experiment"]["max_parse_retries"] + 1):
                    try:
                        parsed = parse_prediction(raw, require_reasoning=True); error = None; break
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {exc}"
                        if attempt < config["experiment"]["max_parse_retries"]:
                            retry_started = time.perf_counter()
                            raw = generator.generate([item["prompt"]], config["generation"]["prediction"])[0][0]
                            per_item += time.perf_counter() - retry_started; attempts.append(raw)
            else:
                error = "context overflow"
            predicted = parsed["predicted_overall"]
            gold = int(target["Overall"])
            output_tokens = len(generator.tokenizer.encode(raw, add_special_tokens=False)) if raw else 0
            records.append({"target_id": target["target_id"], "source_row_id": int(target["source_row_id"]),
                            "rater_id": target["rater_id"], "K": k, "gold_overall": gold,
                            "predicted_overall": predicted, "exact_correct": predicted == gold if predicted else None,
                            "absolute_error": abs(predicted-gold) if predicted else None,
                            "squared_error": (predicted-gold)**2 if predicted else None,
                            "prediction_reasoning": parsed["reasoning"],
                            "history_ids": history["target_id"].tolist(),
                            "history_rater_ids": history["rater_id"].tolist(),
                            "prompt_tokens": item["prompt_tokens"], "output_tokens": output_tokens,
                            "context_fit": item["context_fit"], "parse_success": predicted is not None,
                            "retry_count": max(0, len(attempts)-1), "parse_error": error,
                            "inference_time_seconds": per_item, "raw_model_output": raw,
                            "raw_model_output_attempts": attempts, "prompt": item["prompt"]})
        write_jsonl(outdir / "k_history_predictions.jsonl", records)
    return records, summarize(records, outdir)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/k_history_pilot.yaml")
    args = parser.parse_args(); records, summary = run(load_config(args.config)); print(summary.to_string(index=False))


if __name__ == "__main__": main()
