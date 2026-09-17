"""Generate target-independent natural-language profiles from rater histories."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import random
import subprocess
import time

import pandas as pd
import yaml

from .config import load_config, project_path
from .data import load_valid_data, TRAITS
from .history import _stable_seed, format_history
from .model import VLLMGenerator
from .prompts import prompt_metadata
from .utils import write_jsonl


FORBIDDEN = ["personality", "nationality", "education", " age ", "gender",
             "teaching experience", "strict personality", "likely reflects"]


def inputs(config: dict):
    frame = load_valid_data(config)
    meta = json.loads(project_path(config, config["source_metadata"]).read_text(encoding="utf-8"))
    target_ids = meta["target_ids"]
    targets = frame.set_index("target_id", drop=False).loc[target_ids]
    target_essay_ids = set(targets.source_row_id)
    raters = targets.rater_id.drop_duplicates().tolist()
    size = int(config["profile_history_size"])
    result = []
    for rater in raters:
        pool = frame[(frame.rater_id == rater) & ~frame.source_row_id.isin(target_essay_ids)]
        if len(pool) < size:
            raise ValueError(f"rater {rater} has only {len(pool)} leakage-safe histories")
        indices = list(pool.index)
        random.Random(_stable_seed(config["profile_generation_seed"], f"profile:{rater}")).shuffle(indices)
        history = pool.loc[indices[:size]].copy()
        template = project_path(config, config["profile_prompt"]).read_text(encoding="utf-8")
        prompt = template.format(history=format_history(history))
        result.append({"rater_id": rater, "history": history, "prompt": prompt})
    return targets, result


def parse_profile(text: str) -> str:
    from .parsing import extract_json
    profile = str(extract_json(text).get("rater_profile", "")).strip()
    if not profile:
        raise ValueError("rater_profile is empty")
    return profile


def write_audits(config: dict, items: list[dict], profiles: list[dict]) -> None:
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    assignment = []
    numeric = []
    for item in items:
        history = item["history"]
        assignment.extend({"rater_id": item["rater_id"], "history_order": i+1,
                           "history_id": row.target_id, "source_row_id": int(row.source_row_id)}
                          for i, (_, row) in enumerate(history.iterrows()))
        row = {"rater_id": item["rater_id"], "n": len(history), "mean_overall": history.Overall.mean()}
        for trait in TRAITS:
            row[f"mean_{trait.lower()}"] = history[trait].mean()
            row[f"corr_{trait.lower()}_overall"] = history[trait].corr(history.Overall)
        numeric.append(row)
    pd.DataFrame(assignment).to_csv(outdir / "profile_history_assignment.csv", index=False)
    pd.DataFrame(numeric).to_csv(outdir / "profile_numeric_summary.csv", index=False)
    checks = []
    hashes = [hashlib.sha256(row["profile_text"].encode()).hexdigest() for row in profiles]
    for row, digest in zip(profiles, hashes):
        lower = f" {row['profile_text'].lower()} "
        checks.append({"rater_id": row["rater_id"], "word_count": len(row["profile_text"].split()),
                       "profile_sha256": digest, "duplicate": hashes.count(digest) > 1,
                       "hallucination_warning": "|".join(term.strip() for term in FORBIDDEN if term in lower)})
    pd.DataFrame(checks).to_csv(outdir / "profile_quality_checks.csv", index=False)


def run(config: dict, initial: bool = False, force: bool = False):
    generator = VLLMGenerator(config)
    _, all_items = inputs(config)
    items = all_items[:config["profile_num_raters_initial"]] if initial else all_items
    outdir = project_path(config, config["output_dir"]); outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "profiles.jsonl"
    existing = ([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
                if path.exists() and not force else [])
    done = {row["rater_id"] for row in existing}; profiles = list(existing)
    prompt_hash = hashlib.sha256(project_path(config, config["profile_prompt"]).read_bytes()).hexdigest()
    for item in [item for item in items if item["rater_id"] not in done]:
        started = time.perf_counter(); params = dict(config["generation"]["profile"])
        params["seed"] = config["profile_generation_seed"]
        raw = generator.generate([item["prompt"]], params)[0][0]
        profile = parse_profile(raw)
        if not 150 <= len(profile.split()) <= 300:
            params["seed"] = config["profile_generation_seed"] + 1
            retry_prompt = item["prompt"] + "\nEnsure the rater_profile value itself contains 150-300 words."
            raw = generator.generate([retry_prompt], params)[0][0]
            profile = parse_profile(raw)
        profiles.append({"rater_id": item["rater_id"], "profile_text": profile,
            "profile_history_ids": item["history"].target_id.tolist(), "profile_history_size": len(item["history"]),
            "prompt_sha256": prompt_hash, "generation_seed": config["profile_generation_seed"],
            "word_count": len(profile.split()), "inference_time_seconds": time.perf_counter()-started,
            "raw_model_output": raw})
        write_jsonl(path, profiles)
    write_audits(config, all_items, profiles)
    metadata = {"experiment_name": config["experiment_name"], "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": subprocess.run(["git","rev-parse","HEAD"], cwd=config["_root"], capture_output=True,
                                     text=True).stdout.strip(), "model": config["model"], **prompt_metadata(config),
        "profile_prompt": config["profile_prompt"], "profile_prompt_sha256": prompt_hash,
        "profile_generation_seed": config["profile_generation_seed"], "profile_history_size": config["profile_history_size"],
        "rater_ids": [item["rater_id"] for item in items]}
    (outdir / "profile_generation_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    serializable = {k:v for k,v in config.items() if k != "_root"}
    (outdir / "resolved_config.yaml").write_text(yaml.safe_dump(serializable, sort_keys=False), encoding="utf-8")
    return profiles


def sensitivity(config: dict):
    generator = VLLMGenerator(config); _, items = inputs(config)
    items = items[:config["profile_sensitivity_num_raters"]]
    rows = []
    for item in items:
        for seed in [config["profile_generation_seed"], *config["profile_sensitivity_seeds"]]:
            params = dict(config["generation"]["profile"]); params["seed"] = seed
            raw = generator.generate([item["prompt"]], params)[0][0]; profile = parse_profile(raw)
            rows.append({"rater_id": item["rater_id"], "generation_seed": seed, "profile_text": profile,
                         "word_count": len(profile.split())})
    outdir = project_path(config, config["output_dir"])
    write_jsonl(outdir / "profile_sensitivity.jsonl", rows)
    comparisons = []
    for rater, group in pd.DataFrame(rows).groupby("rater_id"):
        texts = group.profile_text.tolist()
        for i in range(len(texts)):
            for j in range(i+1, len(texts)):
                a, b = set(texts[i].lower().split()), set(texts[j].lower().split())
                comparisons.append({"rater_id": rater, "seed_a": group.iloc[i].generation_seed,
                    "seed_b": group.iloc[j].generation_seed, "word_jaccard": len(a & b) / len(a | b)})
    pd.DataFrame(comparisons).to_csv(outdir / "profile_sensitivity_summary.csv", index=False)


def audit_only(config: dict):
    _, items = inputs(config); outdir = project_path(config, config["output_dir"])
    profiles = [json.loads(line) for line in (outdir / "profiles.jsonl").read_text(encoding="utf-8").splitlines() if line]
    write_audits(config, items, profiles)


def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",default="configs/rater_profile.yaml")
    p.add_argument("--initial",action="store_true"); p.add_argument("--force",action="store_true")
    p.add_argument("--sensitivity",action="store_true"); p.add_argument("--audit-only",action="store_true")
    a=p.parse_args(); config=load_config(a.config)
    if a.sensitivity: sensitivity(config)
    elif a.audit_only: audit_only(config)
    else: run(config,a.initial,a.force)
if __name__ == "__main__": main()
