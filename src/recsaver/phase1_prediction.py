from __future__ import annotations

import argparse
import json
from pathlib import Path
from .config import load_config, project_path
from .data import load_valid_data, select_targets
from .history import sample_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .prompts import fit_history
from .utils import experiment_metadata, write_jsonl


def run(config: dict, generator=None) -> list[dict]:
    frame = load_valid_data(config)
    targets = select_targets(frame, config)
    exp = config["experiment"]
    mode = exp["prediction_mode"]
    template = "zero_shot_prediction.txt" if mode == "reasoning" else "score_only_prediction.txt"
    prepared = []
    for _, target in targets.iterrows():
        history = sample_history(frame, target, exp["history_size"], config["seed"], exp["history_strategy"])
        prompt, used, estimate = fit_history(template, history, target, config)
        prepared.append((target, used, prompt, estimate))
    generator = generator or VLLMGenerator(config)
    outputs = generator.generate([x[2] for x in prepared], config["generation"]["prediction"])
    metadata = experiment_metadata(config)
    records = []
    for (target, history, prompt, estimate), generated in zip(prepared, outputs):
        raw = generated[0]
        raw_attempts = [raw]
        error = None
        for attempt in range(exp.get("max_parse_retries", 0) + 1):
            try:
                parsed = parse_prediction(raw, require_reasoning=mode == "reasoning")
                error = None
                break
            except Exception as exc:
                parsed = {"predicted_overall": None, "reasoning": ""}
                error = f"{type(exc).__name__}: {exc}"
                if attempt < exp.get("max_parse_retries", 0):
                    raw = generator.generate([prompt], config["generation"]["prediction"])[0][0]
                    raw_attempts.append(raw)
        records.append({
            **metadata, "target_id": target["target_id"], "rater_id": target["rater_id"],
            "gold_overall": int(target["Overall"]), **parsed,
            "history_ids": history["target_id"].tolist(), "requested_history_size": exp["history_size"],
            "history_size": len(history), "prompt_token_estimate": estimate,
            "prompt": prompt, "raw_model_output": raw, "raw_model_output_attempts": raw_attempts,
            "parse_attempts": len(raw_attempts), "parse_error": error,
            "model_id": config["model"]["model_id"], "sampling_parameters": config["generation"]["prediction"],
        })
    output = project_path(config, config["output_dir"]) / "phase1_predictions.jsonl"
    write_jsonl(output, records)
    (output.parent / "resolved_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    args = parser.parse_args()
    records = run(load_config(args.config))
    print(f"Phase 1: {sum(r['predicted_overall'] is not None for r in records)}/{len(records)} parsed")


if __name__ == "__main__":
    main()
