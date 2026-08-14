from __future__ import annotations

import argparse
import json
from .config import load_config, project_path
from .data import load_valid_data
from .history import sample_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .prompts import fit_history
from .utils import read_jsonl, write_jsonl


def run(config: dict, generator=None) -> list[dict]:
    outdir = project_path(config, config["output_dir"])
    candidates = read_jsonl(outdir / "reference_candidates_unverified.jsonl")
    frame = load_valid_data(config); indexed = frame.set_index("target_id", drop=False)
    exp = config["experiment"]; prepared = []
    for candidate in candidates:
        if candidate["parse_error"]:
            continue
        target = indexed.loc[candidate["target_id"]]
        history = sample_history(frame, target, exp["history_size"], config["seed"], exp["history_strategy"])
        prompt, used, estimate = fit_history(
            "self_verification.txt", history, target, config,
            reference_reasoning=candidate["reference_reasoning"],
        )
        prepared.append((candidate, used, prompt, estimate))
    generator = generator or VLLMGenerator(config)
    outputs = generator.generate([x[2] for x in prepared], config["generation"]["verification"])
    verified_records = []
    by_key = {(r["target_id"], r["candidate_id"]): r for r in candidates}
    for (candidate, history, prompt, estimate), generated in zip(prepared, outputs):
        raw = generated[0]; error = None
        try:
            reconstructed = parse_prediction(raw, require_reasoning=False)["predicted_overall"]
        except Exception as exc:
            reconstructed = None; error = f"{type(exc).__name__}: {exc}"
        record = by_key[(candidate["target_id"], candidate["candidate_id"])]
        record.update({"reconstructed_overall": reconstructed,
                       "verified": reconstructed == record["gold_overall"],
                       "verification_prompt": prompt, "verification_raw_output": raw,
                       "verification_parse_error": error, "verification_prompt_token_estimate": estimate})
    for record in candidates:
        if "verified" not in record:
            record.update({"reconstructed_overall": None, "verified": False,
                           "verification_parse_error": "reference generation failed"})
    write_jsonl(outdir / "reference_candidates.jsonl", candidates)
    pool = [r for r in candidates if r["verified"]]
    write_jsonl(outdir / "verified_reference_pool.jsonl", pool)
    targets = {r["target_id"] for r in candidates}; targets_verified = {r["target_id"] for r in pool}
    summary = {
        "targets_total": len(targets), "targets_with_verified_reference": len(targets_verified),
        "targets_without_verified_reference": len(targets - targets_verified),
        "candidate_total": len(candidates), "verified_total": len(pool),
        "verification_pass_rate": len(pool) / len(candidates) if candidates else 0,
        "mean_verified_references_per_target": len(pool) / len(targets) if targets else 0,
    }
    (outdir / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return candidates


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--config", default="configs/recsaver_mvp.yaml")
    args = parser.parse_args(); records = run(load_config(args.config))
    print(f"Verification: {sum(r['verified'] for r in records)}/{len(records)} passed")


if __name__ == "__main__": main()
