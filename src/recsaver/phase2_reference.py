from __future__ import annotations

import argparse
from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .model import VLLMGenerator
from .parsing import leaks_score, parse_reasoning
from .prompts import fit_history
from .utils import read_jsonl, write_jsonl


def run(config: dict, generator=None) -> list[dict]:
    outdir = project_path(config, config["output_dir"])
    phase1 = read_jsonl(outdir / "phase1_predictions.jsonl")
    frame = load_valid_data(config)
    indexed = frame.set_index("target_id", drop=False)
    exp = config["experiment"]
    prepared = []
    for prediction in phase1:
        target = indexed.loc[prediction["target_id"]]
        history = sample_history(frame, target, exp["history_size"], config["seed"], exp["history_strategy"])
        prompt, used, estimate = fit_history(
            "reference_generation.txt", history, target, config, gold_overall=int(target["Overall"])
        )
        prepared.append((target, used, prompt, estimate))
    generator = generator or VLLMGenerator(config)
    outputs = generator.generate(
        [x[2] for x in prepared], config["generation"]["reference"], n=exp["num_reference_candidates"]
    )
    records = []
    for (target, history, prompt, estimate), candidates in zip(prepared, outputs):
        for candidate_id, raw in enumerate(candidates, 1):
            error = None; score_leak = False
            try:
                reasoning = parse_reasoning(raw)
                score_leak = leaks_score(reasoning, int(target["Overall"]))
                if score_leak:
                    raise ValueError("gold score leaked in reasoning")
            except Exception as exc:
                reasoning = ""
                error = f"{type(exc).__name__}: {exc}"
            records.append({
                "target_id": target["target_id"], "rater_id": target["rater_id"], "candidate_id": candidate_id,
                "gold_overall": int(target["Overall"]), "reference_reasoning": reasoning,
                "score_leak": score_leak, "history_ids": history["target_id"].tolist(),
                "history_size": len(history), "prompt_token_estimate": estimate,
                "prompt": prompt, "raw_model_output": raw, "parse_error": error,
                "sampling_parameters": config["generation"]["reference"],
            })
    write_jsonl(outdir / "reference_candidates_unverified.jsonl", records)
    return records


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    args = parser.parse_args(); records = run(load_config(args.config))
    print(f"Reference generation: {sum(not r['parse_error'] for r in records)}/{len(records)} parsed")


if __name__ == "__main__": main()
