"""本人K=3と他人K=3を比較するrater-history placebo実験。"""
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
import yaml

from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_wrong_rater_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .prompts import prompt_metadata, render
from .utils import write_jsonl


def source_records(config: dict) -> tuple[list[str], dict[tuple[str, int], dict]]:
    exp = config["experiment"]
    metadata = json.loads(project_path(config, exp["source_metadata"]).read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in project_path(config, exp["source_predictions"]).read_text(
        encoding="utf-8").splitlines() if line]
    return metadata["target_ids"], {(row["target_id"], int(row["K"])): row for row in rows}


def prepare(config: dict, tokenizer) -> tuple[list[dict], pd.DataFrame]:
    frame = load_valid_data(config)
    target_ids, prior = source_records(config)
    if len(target_ids) != config["experiment"]["num_targets"]:
        raise ValueError("source target count mismatch")
    indexed = frame.set_index("target_id", drop=False)
    items, assignments = [], []
    size = int(config["experiment"]["history_size"])
    for target_id in target_ids:
        target = indexed.loc[target_id]
        correct = prior[(target_id, size)]
        if correct["rater_id"] != target["rater_id"]:
            raise ValueError(f"source target rater mismatch: {target_id}")
        wrong_rater, history = sample_wrong_rater_history(
            frame, target, size, int(config["wrong_rater_seed"]))
        prompt = render("zero_shot_prediction.txt", history, target, prompt_dir=config["prompt_dir"])
        prompt_tokens = len(tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}], tokenize=True, add_generation_prompt=True))
        context_fit = prompt_tokens + config["generation"]["prediction"]["max_tokens"] <= config["model"]["max_model_len"]
        ids = history["target_id"].tolist()
        if len(ids) != size or history["rater_id"].nunique() != 1 or wrong_rater == target["rater_id"]:
            raise ValueError(f"invalid wrong-rater history: {target_id}")
        if target["source_row_id"] in set(history["source_row_id"]):
            raise ValueError(f"target essay leakage: {target_id}")
        if not context_fit:
            raise ValueError(f"context overflow: {target_id}")
        items.append({"target": target, "history": history, "wrong_rater": wrong_rater,
                      "prompt": prompt, "prompt_tokens": prompt_tokens, "context_fit": context_fit})
        cids = correct["history_ids"]
        assignments.append({"target_id": target_id, "target_rater": target["rater_id"],
            "correct_history_rater": target["rater_id"], "wrong_history_rater": wrong_rater,
            **{f"correct_history_id_{i+1}": cids[i] for i in range(size)},
            **{f"wrong_history_id_{i+1}": ids[i] for i in range(size)}})
    return items, pd.DataFrame(assignments)


def summarize(records: list[dict], outdir: Path) -> pd.DataFrame:
    valid = pd.DataFrame([row for row in records if row["parse_success"]])
    rows = []
    order = ["k0", "wrong_rater_history", "correct_rater_history"]
    for condition in order:
        group = valid[valid.condition == condition]
        all_rows = [row for row in records if row["condition"] == condition]
        rows.append({"condition": condition, "n": len(group), "exact_accuracy": group.exact_correct.mean(),
            "mae": group.absolute_error.mean(), "rmse": math.sqrt(group.squared_error.mean()),
            "qwk": quadratic_weighted_kappa(group.gold_overall, group.predicted_overall),
            "parse_success_rate": len(group) / len(all_rows),
            "mean_prompt_tokens": np.mean([row["prompt_tokens"] for row in all_rows]),
            "median_prompt_tokens": np.median([row["prompt_tokens"] for row in all_rows]),
            "p90_prompt_tokens": np.quantile([row["prompt_tokens"] for row in all_rows], .9),
            "mean_inference_time_seconds": np.mean([row["inference_time_seconds"] for row in all_rows]),
            "total_inference_time_seconds": sum(row["inference_time_seconds"] for row in all_rows),
            "parse_errors": sum(not row["parse_success"] for row in all_rows),
            "context_overflows": sum(not row["context_fit"] for row in all_rows)})
    summary = pd.DataFrame(rows)
    summary.to_csv(outdir / "rater_history_placebo_summary.csv", index=False)
    pivot = valid.pivot(index="target_id", columns="condition", values="absolute_error")
    delta = pivot.wrong_rater_history - pivot.correct_rater_history
    pd.DataFrame([{"from_condition": "wrong_rater_history", "to_condition": "correct_rater_history",
        "improved_targets": int((delta > 0).sum()), "unchanged_targets": int((delta == 0).sum()),
        "worsened_targets": int((delta < 0).sum()), "mean_ae_difference": delta.mean(),
        "median_ae_difference": delta.median(), "paired_targets": int(delta.notna().sum())}]).to_csv(
            outdir / "paired_comparison.csv", index=False)
    distributions = []
    gold = valid.drop_duplicates("target_id").gold_overall
    for label, values in [("gold", gold)] + [(condition, valid[valid.condition == condition].predicted_overall) for condition in order]:
        counts = values.value_counts().reindex(range(1, 6), fill_value=0)
        distributions.extend({"series": label, "score": score, "count": int(count), "rate": count / len(values)}
                             for score, count in counts.items())
    pd.DataFrame(distributions).to_csv(outdir / "prediction_distribution.csv", index=False)
    valid[valid.condition.isin(["wrong_rater_history", "correct_rater_history"])].groupby(
        ["condition", "rater_id"]).agg(n=("target_id", "size"), accuracy=("exact_correct", "mean"),
                                        mae=("absolute_error", "mean")).reset_index().to_csv(
                                            outdir / "rater_summary.csv", index=False)
    majority = int(gold.mode().iloc[0])
    pd.DataFrame([{"baseline": "majority", "majority_score": majority, "n": len(gold),
        "exact_accuracy": (gold == majority).mean(), "mae": (gold-majority).abs().mean(),
        "rmse": math.sqrt(((gold-majority)**2).mean()),
        "qwk": quadratic_weighted_kappa(gold, pd.Series([majority]*len(gold)))}]).to_csv(
            outdir / "majority_baseline.csv", index=False)
    return summary


def metadata(config: dict, assignments: pd.DataFrame) -> dict:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config["_root"], check=True,
                                capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
                              "--format=csv,noheader,nounits"], check=True,
                             capture_output=True, text=True).stdout.strip()
    except Exception:
        gpu = "unknown"
    exp = config["experiment"]
    return {"experiment_name": config["experiment_name"], "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit, "model": config["model"]["model_id"],
        "quantization": config["model"]["quantization"], **prompt_metadata(config),
        "prompt_path": str(Path(config["prompt_dir"]) / "zero_shot_prediction.txt"),
        "target_seed": exp["target_seed"], "history_seed": exp["history_seed"],
        "wrong_rater_seed": config["wrong_rater_seed"], "target_ids": assignments.target_id.tolist(),
        "correct_history_ids": {row.target_id: [row[f"correct_history_id_{i}"] for i in range(1, 4)]
                                for _, row in assignments.iterrows()},
        "wrong_history_ids": {row.target_id: [row[f"wrong_history_id_{i}"] for i in range(1, 4)]
                              for _, row in assignments.iterrows()},
        "wrong_rater_ids": dict(zip(assignments.target_id, assignments.wrong_history_rater)),
        "generation_config": config["generation"]["prediction"], "gpu": gpu}


def dry_run(config: dict):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["model_id"], local_files_only=True)
    items, assignments = prepare(config, tokenizer)
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    assignments.to_csv(outdir / "history_assignment.csv", index=False)
    assignments.groupby("wrong_history_rater").size().rename("assignment_count").reset_index().rename(
        columns={"wrong_history_rater": "wrong_rater"}).to_csv(outdir / "wrong_rater_assignment_summary.csv", index=False)
    pd.DataFrame([{"target_id": item["target"]["target_id"], "wrong_rater": item["wrong_rater"],
                   "history_count": len(item["history"]), "prompt_tokens": item["prompt_tokens"],
                   "context_fit": item["context_fit"], "prompt_language": prompt_metadata(config)["prompt_language"]}
                  for item in items]).to_csv(outdir / "dry_run_conditions.csv", index=False)
    print(f"targets={len(items)} fit={sum(item['context_fit'] for item in items)} "
          f"max_prompt_tokens={max(item['prompt_tokens'] for item in items)}")
    return items, assignments


def run(config: dict):
    generator = VLLMGenerator(config)
    items, assignments = prepare(config, generator.tokenizer)
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    target_ids, prior = source_records(config)
    records = []
    for target_id in target_ids:
        for k, condition in ((0, "k0"), (3, "correct_rater_history")):
            row = dict(prior[(target_id, k)]); row["condition"] = condition; row["reused"] = True
            records.append(row)
    batch_size = int(config["experiment"]["batch_size"])
    for offset in range(0, len(items), batch_size):
        chunk = items[offset:offset+batch_size]; started = time.perf_counter()
        generated = generator.generate([item["prompt"] for item in chunk], config["generation"]["prediction"])
        per_item = (time.perf_counter()-started) / len(chunk)
        for item, values in zip(chunk, generated):
            raw, attempts, error = values[0], [values[0]], None
            parsed = {"predicted_overall": None, "reasoning": ""}
            for attempt in range(config["experiment"]["max_parse_retries"] + 1):
                try:
                    parsed = parse_prediction(raw, require_reasoning=True); error = None; break
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    if attempt < config["experiment"]["max_parse_retries"]:
                        retry_started = time.perf_counter()
                        raw = generator.generate([item["prompt"]], config["generation"]["prediction"])[0][0]
                        per_item += time.perf_counter()-retry_started; attempts.append(raw)
            target, predicted = item["target"], parsed["predicted_overall"]
            gold = int(target["Overall"])
            records.append({"target_id": target["target_id"], "source_row_id": int(target["source_row_id"]),
                "rater_id": target["rater_id"], "condition": "wrong_rater_history", "K": 3,
                "wrong_rater_id": item["wrong_rater"], "gold_overall": gold,
                "predicted_overall": predicted, "exact_correct": predicted == gold if predicted else None,
                "absolute_error": abs(predicted-gold) if predicted else None,
                "squared_error": (predicted-gold)**2 if predicted else None,
                "prediction_reasoning": parsed["reasoning"], "history_ids": item["history"]["target_id"].tolist(),
                "history_rater_ids": item["history"]["rater_id"].tolist(), "prompt_tokens": item["prompt_tokens"],
                "output_tokens": len(generator.tokenizer.encode(raw, add_special_tokens=False)),
                "context_fit": True, "parse_success": predicted is not None,
                "retry_count": len(attempts)-1, "parse_error": error, "inference_time_seconds": per_item,
                "raw_model_output": raw, "raw_model_output_attempts": attempts, "prompt": item["prompt"],
                "reused": False})
        write_jsonl(outdir / "rater_history_placebo_predictions.jsonl", records)
    assignments.to_csv(outdir / "history_assignment.csv", index=False)
    assignments.groupby("wrong_history_rater").size().rename("assignment_count").reset_index().rename(
        columns={"wrong_history_rater": "wrong_rater"}).to_csv(outdir / "wrong_rater_assignment_summary.csv", index=False)
    (outdir / "metadata.json").write_text(json.dumps(metadata(config, assignments), ensure_ascii=False, indent=2), encoding="utf-8")
    serializable = {key: value for key, value in config.items() if key != "_root"}
    (outdir / "resolved_config.yaml").write_text(yaml.safe_dump(serializable, sort_keys=False), encoding="utf-8")
    return records, summarize(records, outdir)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/rater_history_placebo.yaml")
    parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args(); config = load_config(args.config)
    if args.dry_run: dry_run(config)
    else:
        _, summary = run(config); print(summary.to_string(index=False))


if __name__ == "__main__": main()
