"""本番promptを全文・固定Kでtokenizeし、context収容率を集計する。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from transformers import AutoTokenizer

from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .prompts import render
from .utils import read_jsonl

KS = (1, 3, 5, 7, 10)
PHASES = {
    "phase1_prediction": ("zero_shot_prediction.txt", "prediction"),
    "reference_generation": ("reference_generation.txt", "reference"),
    "self_verification": ("self_verification.txt", "verification"),
}


def token_counts(tokenizer, prompts: list[str]) -> list[int]:
    conversations = [[{"role": "user", "content": prompt}] for prompt in prompts]
    encoded = tokenizer.apply_chat_template(
        conversations, tokenize=True, add_generation_prompt=True, padding=False
    )
    return [len(item) for item in encoded]


def representative_reasonings(config: dict) -> list[str]:
    outdir = project_path(config, config["output_dir"])
    candidates = read_jsonl(outdir / "reference_candidates.jsonl")
    values = [r["reference_reasoning"] for r in candidates if r.get("reference_reasoning")]
    if not values:
        raise FileNotFoundError("Self-Verification概算に使うMVP Reference Reasoningがありません")
    return values


def run(config: dict, max_lengths: list[int], min_rater_samples: int = 100) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = load_valid_data(config)
    counts = frame.groupby("rater_id").size()
    eligible_raters = counts[counts >= min_rater_samples].index
    frame = frame[frame["rater_id"].isin(eligible_raters)].copy()
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["model_id"], local_files_only=True,
                                               trust_remote_code=True)
    reasonings = representative_reasonings(config)
    detail = []
    pending_prompts: list[str] = []
    pending_metadata: list[dict] = []

    def flush() -> None:
        if not pending_prompts:
            return
        for metadata, count in zip(pending_metadata, token_counts(tokenizer, pending_prompts)):
            detail.append({**metadata, "prompt_tokens": count})
        pending_prompts.clear()
        pending_metadata.clear()
    rater_groups = {rater: group for rater, group in frame.groupby("rater_id", sort=False)}
    for row_number, (_, target) in enumerate(frame.iterrows()):
        rater_frame = rater_groups[target["rater_id"]]
        try:
            maximum_history = sample_history(rater_frame, target, max(KS), config["seed"], "random")
        except ValueError:
            continue
        for k in KS:
            history = maximum_history.iloc[:k]
            if target["target_id"] in set(history["target_id"]):
                raise AssertionError(f"target leaked into history: {target['target_id']}")
            values_by_phase = {
                "phase1_prediction": {},
                "reference_generation": {"gold_overall": int(target["Overall"])},
                "self_verification": {"reference_reasoning": reasonings[row_number % len(reasonings)]},
            }
            for phase, (template, generation_key) in PHASES.items():
                prompt = render(template, history, target, **values_by_phase[phase])
                pending_prompts.append(prompt)
                pending_metadata.append({"target_id": target["target_id"], "rater_id": target["rater_id"],
                                         "phase": phase, "k": k,
                                         "output_budget": int(config["generation"][generation_key]["max_tokens"]),
                                         "history_ids": "|".join(history["target_id"]),
                                         "target_in_history": False})
                if len(pending_prompts) >= 512:
                    flush()
    flush()
    detail_frame = pd.DataFrame(detail)
    summary_rows = []
    for (phase, k), group in detail_frame.groupby(["phase", "k"], sort=True):
        stats = {"prompt_tokens_mean": group.prompt_tokens.mean(),
                 "prompt_tokens_median": group.prompt_tokens.median(),
                 "prompt_tokens_p90": group.prompt_tokens.quantile(.90),
                 "prompt_tokens_p95": group.prompt_tokens.quantile(.95),
                 "prompt_tokens_max": group.prompt_tokens.max()}
        for maximum in max_lengths:
            fit = group.prompt_tokens + group.output_budget <= maximum
            summary_rows.append({"max_model_len": maximum, "phase": phase, "k": k,
                                 "targets_total": len(group), "targets_fit": int(fit.sum()),
                                 "fit_rate": float(fit.mean()), "output_budget": int(group.output_budget.iloc[0]),
                                 **stats})
    summary = pd.DataFrame(summary_rows)
    outdir = project_path(config, "outputs/context_analysis")
    outdir.mkdir(parents=True, exist_ok=True)
    detail_frame.to_csv(outdir / "context_token_statistics.csv", index=False)
    summary.to_csv(outdir / "context_fit_summary.csv", index=False)
    metadata = {"eligible_raters": len(eligible_raters), "eligible_targets": len(frame),
                "min_rater_samples": min_rater_samples, "seed": config["seed"],
                "reasoning_samples_used": len(reasonings), "tokenizer": config["model"]["model_id"],
                "notes": "Full target/history text; fixed K; no fallback or truncation."}
    (outdir / "context_analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return detail_frame, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    parser.add_argument("--max-model-len", nargs="+", type=int, required=True)
    parser.add_argument("--min-rater-samples", type=int, default=100)
    args = parser.parse_args()
    detail, summary = run(load_config(args.config), args.max_model_len, args.min_rater_samples)
    print(f"token rows={len(detail)} summary rows={len(summary)}")


if __name__ == "__main__":
    main()
