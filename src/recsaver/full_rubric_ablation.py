"""Compare Overall-only and Full Rubric prompts at K=0 and correct-rater K=3."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml

from .config import load_config, project_path
from .data import load_valid_data
from .history import format_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .phase4_analysis import quadratic_weighted_kappa
from .utils import write_jsonl

ORDER = ["k0_overall_rubric", "k0_full_rubric", "correct_k3_overall_rubric", "correct_k3_full_rubric"]
KEY_TERMS_HEADER = "## Key Terms and Definitions"
TRAITS = ["Overall", "Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]


def load_sources(config):
    meta = json.loads(project_path(config, config["source_metadata"]).read_text(encoding="utf-8"))
    rows = [json.loads(x) for x in project_path(config, config["source_predictions"]).read_text(encoding="utf-8").splitlines() if x]
    by_condition = {(r["target_id"], r["condition"]): r for r in rows}
    return meta, by_condition


def rubric_without_key_terms(text):
    if text.count(KEY_TERMS_HEADER) != 1:
        raise ValueError("Full rubric must contain exactly one Key Terms header")
    rubric = text.split(KEY_TERMS_HEADER, 1)[0].rstrip()
    if "Key Terms" in rubric:
        raise ValueError("Key Terms leaked into Full Rubric")
    for trait in TRAITS:
        if rubric.count(f"### {trait}") != 5:
            raise ValueError(f"Full Rubric does not contain five score entries for {trait}")
    return rubric


def prepare(config, tokenizer):
    frame = load_valid_data(config)
    indexed = frame.set_index("target_id", drop=False)
    meta, prior = load_sources(config)
    source_full = project_path(config, config["full_rubric_path"]).read_text(encoding="utf-8")
    full_rubric = rubric_without_key_terms(source_full)
    template = project_path(config, config["prediction_prompt"]).read_text(encoding="utf-8")
    items = []
    for target_id in meta["target_ids"]:
        target = indexed.loc[target_id]
        for k, condition, old_condition in [
            (0, "k0_full_rubric", "k0_with_rubric"),
            (3, "correct_k3_full_rubric", "raw_k3_with_rubric"),
        ]:
            old = prior[(target_id, old_condition)]
            ids = old["history_ids"]
            history = indexed.loc[ids] if ids else frame.iloc[:0]
            if history.target_id.tolist() != ids or len(history) != k:
                raise ValueError(f"history mismatch: {target_id}")
            if k and not history.rater_id.eq(target.rater_id).all():
                raise ValueError(f"wrong history rater: {target_id}")
            if target.source_row_id in set(history.source_row_id):
                raise ValueError(f"target in history: {target_id}")
            prompt = template.format(full_rubric=full_rubric, rating_history=format_history(history), target_essay=target.Text)
            target_block = prompt.split("[Target Essay]", 1)[1]
            forbidden = [str(int(target.Overall))] + [str(int(target[x])) for x in TRAITS[1:]]
            # Leakage is structural: target block contains only essay text, never score fields.
            if "Target Overall" in target_block or "Target Trait" in target_block:
                raise ValueError(f"target score field leaked: {target_id}")
            tokens = len(tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=True, add_generation_prompt=True))
            fit = tokens + config["generation"]["max_tokens"] <= config["model"]["max_model_len"]
            items.append({"target": target, "history": history, "condition": condition, "prompt": prompt, "prompt_tokens": tokens, "context_fit": fit})
    return meta, prior, items, full_rubric


def metric_row(condition, records):
    all_rows = [r for r in records if r["condition"] == condition]
    valid = pd.DataFrame([r for r in all_rows if r["parse_success"]])
    return {"condition": condition, "n": len(valid), "exact_accuracy": valid.exact_correct.mean(),
            "mae": valid.absolute_error.mean(), "rmse": math.sqrt(valid.squared_error.mean()),
            "qwk": quadratic_weighted_kappa(valid.gold_overall, valid.predicted_overall),
            "parse_success_rate": len(valid) / len(all_rows),
            "mean_prompt_tokens": np.mean([r["prompt_tokens"] for r in all_rows]),
            "median_prompt_tokens": np.median([r["prompt_tokens"] for r in all_rows]),
            "p90_prompt_tokens": np.quantile([r["prompt_tokens"] for r in all_rows], .9),
            "mean_inference_time_seconds": np.mean([r["inference_time_seconds"] for r in all_rows]),
            "total_inference_time_seconds": sum(r["inference_time_seconds"] for r in all_rows),
            "parse_errors": sum(not r["parse_success"] for r in all_rows),
            "context_overflows": sum(not r["context_fit"] for r in all_rows)}


def summarize(records, out):
    valid = pd.DataFrame([r for r in records if r["parse_success"]])
    summary = pd.DataFrame([metric_row(c, records) for c in ORDER])
    summary.to_csv(out / "full_rubric_summary.csv", index=False)
    sm = summary.set_index("condition")
    pivot = valid.pivot(index="target_id", columns="condition", values="absolute_error")
    comparisons = [("k0_overall_rubric", "k0_full_rubric"),
                   ("correct_k3_overall_rubric", "correct_k3_full_rubric"),
                   ("k0_full_rubric", "correct_k3_full_rubric")]
    paired = []
    for a, b in comparisons:
        delta = pivot[a] - pivot[b]
        paired.append({"from_condition": a, "to_condition": b, "improved_targets": int((delta > 0).sum()),
                       "unchanged_targets": int((delta == 0).sum()), "worsened_targets": int((delta < 0).sum()),
                       "mean_ae_difference": delta.mean(), "median_ae_difference": delta.median(),
                       "accuracy_delta": sm.loc[b].exact_accuracy-sm.loc[a].exact_accuracy,
                       "mae_delta": sm.loc[b].mae-sm.loc[a].mae, "rmse_delta": sm.loc[b].rmse-sm.loc[a].rmse,
                       "qwk_delta": sm.loc[b].qwk-sm.loc[a].qwk})
    pd.DataFrame(paired).to_csv(out / "paired_comparisons.csv", index=False)
    dist = []
    gold = valid.drop_duplicates("target_id").gold_overall
    for label, values in [("gold", gold)] + [(c, valid[valid.condition == c].predicted_overall) for c in ORDER]:
        counts = values.value_counts().reindex(range(1, 6), fill_value=0)
        dist.extend({"series": label, "score": int(score), "count": int(n), "rate": n/len(values)} for score, n in counts.items())
    pd.DataFrame(dist).to_csv(out / "prediction_distribution.csv", index=False)
    collapse = []
    for c in ORDER:
        counts = valid[valid.condition == c].predicted_overall.value_counts()
        collapse.append({"condition": c, "unique_predicted_scores": len(counts), "most_frequent_score": int(counts.index[0]), "most_frequent_score_ratio": counts.iloc[0]/counts.sum()})
    pd.DataFrame(collapse).to_csv(out / "score_collapse_summary.csv", index=False)
    valid.groupby(["condition", "rater_id"]).agg(n=("target_id", "size"), accuracy=("exact_correct", "mean"), mae=("absolute_error", "mean")).reset_index().to_csv(out / "rater_summary.csv", index=False)
    changed = []
    pred = valid.pivot(index=["target_id", "rater_id", "gold_overall"], columns="condition", values="predicted_overall").reset_index()
    for a, b in comparisons[:2]:
        for _, row in pred[pred[a] != pred[b]].iterrows():
            changed.append({"comparison": f"{a}_to_{b}", "target_id": row.target_id, "target_rater": row.rater_id,
                            "gold": int(row.gold_overall), "overall_rubric_prediction": int(row[a]), "full_rubric_prediction": int(row[b]),
                            "overall_rubric_error": abs(int(row[a])-int(row.gold_overall)), "full_rubric_error": abs(int(row[b])-int(row.gold_overall))})
    pd.DataFrame(changed).to_csv(out / "changed_targets.csv", index=False)
    examples = {}
    for c in ["k0_full_rubric", "correct_k3_full_rubric"]:
        rows = valid[valid.condition == c].copy()
        rows["trait_mentions"] = rows.prediction_reasoning.apply(lambda x: [t for t in TRAITS[1:] if t.lower() in x.lower()])
        rows = rows.sort_values("trait_mentions", key=lambda s: s.map(len), ascending=False).head(5)
        examples[c] = [{"target_id": str(r.target_id), "gold": int(r.gold_overall), "prediction": int(r.predicted_overall),
                        "trait_mentions": r.trait_mentions, "reasoning": r.prediction_reasoning} for _, r in rows.iterrows()]
    (out / "reasoning_examples.json").write_text(json.dumps(examples, indent=2), encoding="utf-8")
    return summary


def dry_run(config):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["model_id"], local_files_only=True)
    _, _, items, rubric = prepare(config, tokenizer)
    out = project_path(config, config["output_dir"]); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_id": x["target"].target_id, "condition": x["condition"], "history_count": len(x["history"]),
                   "prompt_tokens": x["prompt_tokens"], "context_fit": x["context_fit"]} for x in items]).to_csv(out / "dry_run_conditions.csv", index=False)
    if not all(x["context_fit"] for x in items):
        raise ValueError("Context overflow; inference was not started")
    print(f"conditions={len(items)} fit={sum(x['context_fit'] for x in items)} max_prompt_tokens={max(x['prompt_tokens'] for x in items)} rubric_chars={len(rubric)}")


def run(config):
    generator = VLLMGenerator(config)
    meta, prior, items, full_rubric = prepare(config, generator.tokenizer)
    if not all(x["context_fit"] for x in items):
        raise ValueError("Context overflow; inference was not started")
    out = project_path(config, config["output_dir"]); out.mkdir(parents=True, exist_ok=True)
    records = []
    for target_id in meta["target_ids"]:
        for old, new in [("k0_with_rubric", "k0_overall_rubric"), ("raw_k3_with_rubric", "correct_k3_overall_rubric")]:
            row = dict(prior[(target_id, old)]); row["condition"] = new; row["reused"] = True; records.append(row)
    for offset in range(0, len(items), config["batch_size"]):
        chunk = items[offset:offset+config["batch_size"]]
        start = time.perf_counter(); outputs = generator.generate([x["prompt"] for x in chunk], config["generation"]); per = (time.perf_counter()-start)/len(chunk)
        for item, values in zip(chunk, outputs):
            raw = values[0]; attempts = [raw]; error = None
            try: parsed = parse_prediction(raw, True)
            except Exception as exc:
                error = str(exc); raw = generator.generate([item["prompt"]], config["generation"])[0][0]; attempts.append(raw)
                try: parsed = parse_prediction(raw, True); error = None
                except Exception as exc2: parsed = {"predicted_overall": None, "reasoning": ""}; error = str(exc2)
            target = item["target"]; pred = parsed["predicted_overall"]; gold = int(target.Overall)
            records.append({"target_id": target.target_id, "source_row_id": int(target.source_row_id), "rater_id": target.rater_id,
                            "condition": item["condition"], "K": len(item["history"]), "gold_overall": gold, "predicted_overall": pred,
                            "exact_correct": pred == gold if pred else None, "absolute_error": abs(pred-gold) if pred else None,
                            "squared_error": (pred-gold)**2 if pred else None, "prediction_reasoning": parsed["reasoning"],
                            "history_ids": item["history"].target_id.tolist(), "history_rater_ids": item["history"].rater_id.tolist(),
                            "prompt_tokens": item["prompt_tokens"], "output_tokens": len(generator.tokenizer.encode(raw, add_special_tokens=False)),
                            "context_fit": item["context_fit"], "parse_success": pred is not None, "retry_count": len(attempts)-1,
                            "parse_error": error, "inference_time_seconds": per, "raw_model_output": raw,
                            "raw_model_output_attempts": attempts, "prompt": item["prompt"], "reused": False})
        write_jsonl(out / "full_rubric_predictions.jsonl", records)
    full_path = project_path(config, config["full_rubric_path"]); overall_path = project_path(config, config["overall_rubric_path"]); prompt_path = project_path(config, config["prediction_prompt"])
    metadata = {"experiment_name": config["experiment_name"], "timestamp": datetime.now(timezone.utc).isoformat(),
                "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=config["_root"], capture_output=True, text=True).stdout.strip(),
                "model": config["model"], "quantization": config["model"]["quantization"], "target_seed": config["seed"], "history_seed": config["seed"],
                "target_ids": meta["target_ids"], "history_ids": {tid: prior[(tid, "raw_k3_with_rubric")]["history_ids"] for tid in meta["target_ids"]},
                "full_rubric_path": config["full_rubric_path"], "full_rubric_sha256": hashlib.sha256(full_path.read_bytes()).hexdigest(),
                "full_rubric_prompt_section_sha256": hashlib.sha256(full_rubric.encode()).hexdigest(),
                "overall_rubric_path": config["overall_rubric_path"], "overall_rubric_sha256": hashlib.sha256(overall_path.read_bytes()).hexdigest(),
                "prompt_path": config["prediction_prompt"], "prompt_sha256": hashlib.sha256(prompt_path.read_bytes()).hexdigest(), "generation_config": config["generation"]}
    try: metadata["GPU"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception: metadata["GPU"] = "unknown"
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (out / "resolved_config.yaml").write_text(yaml.safe_dump({k:v for k,v in config.items() if k != "_root"}, sort_keys=False), encoding="utf-8")
    return summarize(records, out)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/full_rubric_ablation.yaml"); parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(); config = load_config(args.config)
    if args.dry_run: dry_run(config)
    else: print(run(config).to_string(index=False))


if __name__ == "__main__":
    main()
