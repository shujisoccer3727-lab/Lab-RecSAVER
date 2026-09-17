"""同一target・nested historyでPhase 1のKを比較するPilot。"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import subprocess
import time
import yaml

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .prompts import prompt_metadata, render
from .utils import write_jsonl


def select_pilot_targets(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    exp = config["experiment"]
    counts = frame.groupby("rater_id").size()
    eligible_raters = counts[counts >= exp["min_rater_samples"]].index
    eligible = frame[frame["rater_id"].isin(eligible_raters)]
    max_k = max(exp["k_values"])
    eligible = eligible.groupby("rater_id").filter(lambda group: len(group) - 1 >= max_k)
    fixed = exp.get("fixed_targets_metadata")
    if fixed:
        source = json.loads(project_path(config, fixed).read_text(encoding="utf-8"))
        target_ids = source["target_ids"]
        if len(target_ids) != exp["num_targets"] or len(set(target_ids)) != len(target_ids):
            raise ValueError("fixed target list size/uniqueness does not match the experiment")
        indexed = eligible.set_index("target_id", drop=False)
        missing = [target_id for target_id in target_ids if target_id not in indexed.index]
        if missing:
            raise ValueError(f"fixed targets unavailable: {missing[:5]}")
        return indexed.loc[target_ids].reset_index(drop=True)
    return eligible.sample(n=exp["num_targets"], random_state=config["seed"]).sort_values("target_id")


def prepare(config: dict, tokenizer) -> tuple[pd.DataFrame, list[dict]]:
    frame = load_valid_data(config)
    targets = select_pilot_targets(frame, config)
    exp = config["experiment"]
    maximum = max(exp["k_values"])
    prepared = []
    for _, target in targets.iterrows():
        history_seed = exp.get("history_seed", config["seed"])
        pool = sample_history(frame, target, maximum, history_seed, "random")
        previous_ids: list[str] = []
        for k in exp["k_values"]:
            history = pool.iloc[:k]
            ids = history["target_id"].tolist()
            assert previous_ids == ids[:len(previous_ids)]
            assert target["target_id"] not in ids
            assert history.empty or history["rater_id"].eq(target["rater_id"]).all()
            previous_ids = ids
            prompt = render("zero_shot_prediction.txt", history, target, prompt_dir=config["prompt_dir"])
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
    experiment_name = config.get("experiment_name", "k_history_pilot")
    try:
        gpu_query = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
            check=True, capture_output=True, text=True).stdout.strip()
    except Exception:
        gpu_query = "unknown"
    exp = config["experiment"]
    return {"experiment_name": experiment_name,
            "experiment_id": experiment_name + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            "timestamp": datetime.now(timezone.utc).isoformat(), "git_commit": commit,
            "seed": config["seed"], "target_seed": exp.get("target_seed", config["seed"]),
            "history_seed": exp.get("history_seed", config["seed"]),
            "model_id": config["model"]["model_id"], "quantization": config["model"]["quantization"],
            "tensor_parallel_size": config["model"]["tensor_parallel_size"],
            "max_model_len": config["model"]["max_model_len"],
            "gpu_memory_utilization": config["model"]["gpu_memory_utilization"], "gpu": gpu_query,
            "k_values": exp["k_values"],
            "sampling_parameters": config["generation"]["prediction"], **prompt_metadata(config),
            "prompt_path": str(Path(config["prompt_dir"]) / "zero_shot_prediction.txt"),
            "target_ids": targets["target_id"].tolist(), "nested_history_pools": pools,
            "fixed_targets_metadata": config["experiment"].get("fixed_targets_metadata")}


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
                     "p95_prompt_tokens": np.quantile([r["prompt_tokens"] for r in all_k], .95),
                     "max_prompt_tokens": max(r["prompt_tokens"] for r in all_k),
                     "mean_inference_time_seconds": np.mean([r["inference_time_seconds"] for r in all_k]),
                     "total_inference_time_seconds": sum(r["inference_time_seconds"] for r in all_k),
                     "parse_errors": sum(not r["parse_success"] for r in all_k),
                     "context_overflows": sum(not r["context_fit"] for r in all_k)})
    summary = pd.DataFrame(rows).sort_values("K")
    summary.to_csv(outdir / "k_history_summary.csv", index=False)
    comparison = valid.pivot(index="target_id", columns="K", values="absolute_error").reset_index()
    comparison.to_csv(outdir / "k_history_target_comparison.csv", index=False)
    paired = []
    requested_pairs = [(0, 1), (0, 3), (1, 3), (3, 5), (5, 7)]
    for lower, upper in requested_pairs:
        if lower not in comparison or upper not in comparison:
            continue
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
    distributions = []
    for label, values in [("gold", valid.drop_duplicates("target_id").gold_overall)]:
        counts = values.value_counts().reindex(range(1, 6), fill_value=0)
        distributions.extend({"series": label, "K": "", "score": score, "count": int(count),
                              "rate": count / len(values)} for score, count in counts.items())
    for k, group in valid.groupby("K"):
        counts = group.predicted_overall.value_counts().reindex(range(1, 6), fill_value=0)
        distributions.extend({"series": "prediction", "K": int(k), "score": score, "count": int(count),
                              "rate": count / len(group)} for score, count in counts.items())
    pd.DataFrame(distributions).to_csv(outdir / "prediction_distribution.csv", index=False)

    targets = valid.drop_duplicates("target_id")
    majority = int(targets.gold_overall.mode().iloc[0])
    baseline = pd.DataFrame({"gold": targets.gold_overall, "prediction": majority})
    pd.DataFrame([{"baseline": "majority", "majority_score": majority, "n": len(baseline),
                   "exact_accuracy": (baseline.gold == majority).mean(),
                   "mae": (baseline.gold - majority).abs().mean(),
                   "rmse": math.sqrt(((baseline.gold - majority) ** 2).mean()),
                   "qwk": quadratic_weighted_kappa(baseline.gold, baseline.prediction)}]).to_csv(
                       outdir / "majority_baseline.csv", index=False)

    ja_dir = outdir.parent / f"{outdir.name}_ja"
    ja_predictions = ja_dir / "k_history_predictions.jsonl"
    if ja_predictions.exists():
        ja_records = [json.loads(line) for line in ja_predictions.read_text(encoding="utf-8").splitlines() if line]
        ja_targets = {record["target_id"] for record in ja_records}
        en_targets = set(valid.target_id)
        if ja_targets != en_targets:
            raise ValueError("Japanese/English comparison requires an identical target set")
        language_metrics = {}
        for language, language_records in (("ja", ja_records), ("en", records)):
            language_valid = pd.DataFrame([r for r in language_records if r["parse_success"]])
            for k, group in language_valid.groupby("K"):
                language_metrics[(language, int(k))] = {"n": len(group),
                    "exact_accuracy": group.exact_correct.mean(), "mae": group.absolute_error.mean(),
                    "rmse": math.sqrt(group.squared_error.mean()),
                    "qwk": quadratic_weighted_kappa(group.gold_overall, group.predicted_overall)}
        comparison_rows = []
        for k in sorted(set(k for language, k in language_metrics if language == "ja") &
                        set(k for language, k in language_metrics if language == "en")):
            ja, en = language_metrics[("ja", k)], language_metrics[("en", k)]
            comparison_rows.append({"K": k, "n": ja["n"],
                "japanese_accuracy": ja["exact_accuracy"], "english_accuracy": en["exact_accuracy"],
                "japanese_mae": ja["mae"], "english_mae": en["mae"],
                "japanese_rmse": ja["rmse"], "english_rmse": en["rmse"],
                "japanese_qwk": ja["qwk"], "english_qwk": en["qwk"]})
        pd.DataFrame(comparison_rows).to_csv(outdir / "prompt_language_comparison.csv", index=False)
    return summary


def run(config: dict) -> tuple[list[dict], pd.DataFrame]:
    generator = VLLMGenerator(config)
    targets, prepared = prepare(config, generator.tokenizer)
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    meta = metadata(config, targets, prepared)
    (outdir / "experiment_metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    serializable_config = {k: v for k, v in config.items() if k != "_root"}
    (outdir / "resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (outdir / "resolved_config.yaml").write_text(yaml.safe_dump(serializable_config, sort_keys=False), encoding="utf-8")
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


def dry_run(config: dict) -> pd.DataFrame:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["model_id"], local_files_only=True)
    targets, prepared = prepare(config, tokenizer)
    rows = [{"target_id": item["target"]["target_id"], "rater_id": item["target"]["rater_id"],
             "K": item["k"], "history_count": len(item["history"]),
             "history_ids": "|".join(item["history"]["target_id"].tolist()),
             "prompt_tokens": item["prompt_tokens"],
             "context_fit": item["context_fit"],
             "target_leaked": item["target"]["target_id"] in item["history"]["target_id"].tolist(),
             "prompt_language": prompt_metadata(config)["prompt_language"]} for item in prepared]
    result = pd.DataFrame(rows)
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    result.to_csv(outdir / "dry_run_conditions.csv", index=False)
    print(result.groupby("K").agg(targets=("target_id", "size"), context_fit=("context_fit", "sum"),
                                    max_prompt_tokens=("prompt_tokens", "max")).to_string())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/k_history_pilot.yaml")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args(); config = load_config(args.config)
    if args.dry_run:
        dry_run(config)
    elif args.summarize_only:
        outdir = project_path(config, config["output_dir"])
        records = [json.loads(line) for line in (outdir / "k_history_predictions.jsonl").read_text(
            encoding="utf-8").splitlines() if line]
        print(summarize(records, outdir).to_string(index=False))
    else:
        records, summary = run(config); print(summary.to_string(index=False))


if __name__ == "__main__": main()
