from __future__ import annotations

import pandas as pd
from .config import project_path
from .utils import target_id

TRAITS = ["Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]
VALID = {1, 2, 3, 4, 5}


def load_valid_data(config: dict) -> pd.DataFrame:
    frame = pd.read_csv(project_path(config, config["data"]["processed_path"]), low_memory=False)
    required = {"source_row_id", "Text", "rater_id", "rater_position", "Overall", *TRAITS}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"required columns missing: {sorted(missing)}")
    mask = frame["Overall"].isin(VALID) & frame[TRAITS].isin(VALID).all(axis=1)
    result = frame.loc[mask].copy()
    result["target_id"] = result.apply(target_id, axis=1)
    return result


def select_targets(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    exp = config["experiment"]
    eligible = frame.groupby("rater_id").filter(lambda group: len(group) - 1 >= exp["history_size"])
    raters = exp.get("target_raters") or []
    if raters:
        eligible = eligible[eligible["rater_id"].isin(raters)]
    if len(eligible) < exp["num_targets"]:
        raise ValueError(f"eligible targets不足: {len(eligible)}")
    return eligible.sample(n=exp["num_targets"], random_state=config["seed"]).sort_values("target_id")
