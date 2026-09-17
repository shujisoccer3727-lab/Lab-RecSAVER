"""K=0 vs K=3で本人採点履歴そのものの有効性を検証する。"""
from __future__ import annotations

import argparse
import json

from .config import load_config, project_path
from .k_history_pilot import dry_run as pilot_dry_run, prepare, run as pilot_run


RENAMES = {
    "k_history_predictions.jsonl": "history_ablation_predictions.jsonl",
    "k_history_summary.csv": "history_ablation_summary.csv",
    "k_history_target_comparison.csv": "history_ablation_target_comparison.csv",
    "k_history_paired_comparison.csv": "history_ablation_paired_comparison.csv",
    "k_history_rater_summary.csv": "rater_summary.csv",
    "experiment_metadata.json": "metadata.json",
}


def _pilot_records(config: dict) -> dict[tuple[str, int], dict]:
    path = project_path(config, config["experiment"]["fixed_history_predictions"])
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return {(record["target_id"], int(record["K"])): record for record in records}


def validate_fixed_conditions(config: dict, prepared: list[dict]) -> None:
    expected = _pilot_records(config)
    wanted = config["experiment"]["num_targets"] * len(config["experiment"]["k_values"])
    if len(prepared) != wanted:
        raise ValueError(f"expected {wanted} prepared conditions, got {len(prepared)}")
    for item in prepared:
        target, history, k = item["target"], item["history"], item["k"]
        prior = expected.get((target["target_id"], k))
        if prior is None:
            raise ValueError(f"condition absent from English Pilot: {(target['target_id'], k)}")
        ids = history["target_id"].tolist()
        if ids != prior["history_ids"]:
            raise ValueError(f"history mismatch: {(target['target_id'], k)}")
        if len(ids) != k or target["target_id"] in ids:
            raise ValueError(f"invalid history: {(target['target_id'], k)}")
        if k and not history["rater_id"].eq(target["rater_id"]).all():
            raise ValueError(f"rater mismatch: {(target['target_id'], k)}")
        if not item["context_fit"]:
            raise ValueError(f"context overflow: {(target['target_id'], k)}")


def _prepared(config: dict):
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["model_id"], local_files_only=True)
    _, prepared = prepare(config, tokenizer)
    validate_fixed_conditions(config, prepared)
    return prepared


def dry_run(config: dict):
    result = pilot_dry_run(config)
    _prepared(config)
    return result


def run(config: dict):
    _prepared(config)
    records, summary = pilot_run(config)
    outdir = project_path(config, config["output_dir"])
    for source, destination in RENAMES.items():
        (outdir / source).replace(outdir / destination)
    return records, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/history_ablation.yaml")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        dry_run(config)
    else:
        _, summary = run(config)
        print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
