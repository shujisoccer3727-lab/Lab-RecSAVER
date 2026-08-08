"""Overall予測用の1エッセイ×1採点者データを生成するCLI。"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from .config import EXPECTED_SCORE_VALUES, POSITIONS, PROCESSED_DATA_DIR, PROFILE_TRAITS
from .load_data import load_raw_scores
from .transform_data import create_rater_essay_wide, validate_rater_essay_wide

LOGGER = logging.getLogger(__name__)
DEFAULT_OUTPUT = PROCESSED_DATA_DIR / "rater_essay_wide.csv"


def create_conversion_summary(raw: pd.DataFrame, wide: pd.DataFrame) -> pd.DataFrame:
    valid_overall = wide["Overall"].isin(EXPECTED_SCORE_VALUES)
    valid_profile = wide.loc[:, PROFILE_TRAITS].isin(EXPECTED_SCORE_VALUES).all(axis=1)
    values: list[tuple[str, int]] = [
        ("raw_row_count", len(raw)),
        ("wide_row_count", len(wide)),
        ("unique_filename_count", wide["Filename"].nunique(dropna=True)),
        ("unique_rater_count", wide["rater_id"].nunique(dropna=True)),
        ("valid_overall_count", int(valid_overall.sum())),
        ("valid_trait_profile_count", int(valid_profile.sum())),
        ("invalid_overall_count", int((~valid_overall).sum())),
        ("invalid_trait_profile_count", int((~valid_profile).sum())),
        ("any_invalid_score_count", int(wide["has_any_invalid_score"].sum())),
        ("duplicate_filename_position_rows", int(wide.duplicated(["Filename", "rater_position"], keep=False).sum())),
        ("duplicate_source_row_position_rows", int(wide.duplicated(["source_row_id", "rater_position"], keep=False).sum())),
    ]
    values.extend(
        (f"rater_position_{position}_count", int((wide["rater_position"] == position).sum()))
        for position in POSITIONS
    )
    return pd.DataFrame(values, columns=["metric", "value"])


def create_rater_count_summary(wide: pd.DataFrame) -> pd.DataFrame:
    position_counts = wide.groupby(["rater_id", "rater_position"], dropna=False).size().unstack(fill_value=0)
    result = pd.DataFrame(index=position_counts.index)
    result["sample_count"] = position_counts.sum(axis=1)
    for position in POSITIONS:
        result[f"position_{position}_count"] = position_counts.get(position, 0)
    result = result.reset_index()
    order = pd.to_numeric(result["rater_id"].astype("string").str.extract(r"(\d+)$", expand=False), errors="coerce")
    return result.assign(_order=order).sort_values(["_order", "rater_id"], kind="stable").drop(columns="_order")


def run(input_path: Path | None = None, output_path: Path = DEFAULT_OUTPUT) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw, source_path, _, _ = load_raw_scores(input_path)
    wide = create_rater_essay_wide(raw)
    validate_rater_essay_wide(raw, wide)
    summary = create_conversion_summary(raw, wide)
    rater_summary = create_rater_count_summary(wide)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(output_path, index=False, encoding="utf-8")
    summary.to_csv(output_path.with_name("rater_essay_wide_summary.csv"), index=False, encoding="utf-8")
    rater_summary.to_csv(output_path.with_name("rater_essay_wide_rater_counts.csv"), index=False, encoding="utf-8")
    LOGGER.info("入力: %s", source_path)
    LOGGER.info("wide出力: %s (%d行 × %d列)", output_path, *wide.shape)
    LOGGER.info("整合性検証: OK")
    return wide, summary, rater_summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="入力raw CSV。省略時はdata内の唯一のCSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="wide CSVの保存先")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(args.input, args.output)


if __name__ == "__main__":
    main()
