"""wide 形式から分析用 long 形式への変換。"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import EXPECTED_SCORE_VALUES, POSITIONS, PROFILE_TRAITS, TRAITS


def to_rater_trait_long(frame: pd.DataFrame) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    identity = ["Filename", "text_id_kaggle"]
    for position in POSITIONS:
        partner = 2 if position == 1 else 1
        for trait in TRAITS:
            part = frame[identity].copy()
            part["rater_position"] = position
            part["rater_id"] = frame[f"Rater_{position}"].astype("string").str.strip()
            part["trait"] = trait
            part["score"] = frame[f"{trait}_{position}"]
            part["partner_rater_id"] = frame[f"Rater_{partner}"].astype("string").str.strip()
            part["partner_score"] = frame[f"{trait}_{partner}"]
            records.append(part)
    return pd.concat(records, ignore_index=True)


def to_essay_rater_long(frame: pd.DataFrame) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for position in POSITIONS:
        partner = 2 if position == 1 else 1
        part = frame[["Filename", "text_id_kaggle"]].copy()
        part["rater_position"] = position
        part["rater_id"] = frame[f"Rater_{position}"].astype("string").str.strip()
        part["partner_rater_id"] = frame[f"Rater_{partner}"].astype("string").str.strip()
        for trait in TRAITS:
            part[trait] = frame[f"{trait}_{position}"]
        records.append(part)
    return pd.concat(records, ignore_index=True)


def create_rater_essay_wide(frame: pd.DataFrame) -> pd.DataFrame:
    """1行を1エッセイ×1採点者とするTrait profileデータを作る。

    スコア0・欠損・その他の範囲外値は変更せず、無効フラグだけを付ける。
    `source_row_id` は読み込んだraw DataFrameの論理行順（0始まり）である。
    """
    required = {"Filename", "text_id_kaggle", "Text"}
    required.update(f"Rater_{position}" for position in POSITIONS)
    required.update(
        f"{column}_{position}"
        for position in POSITIONS
        for column in (*TRAITS, "Identifying_Info")
    )
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"wide変換に必要な列がありません: {missing}")

    records: list[pd.DataFrame] = []
    source_row_ids = np.arange(len(frame), dtype=np.int64)
    for position in POSITIONS:
        part = frame[["Filename", "text_id_kaggle", "Text"]].copy()
        part.insert(0, "source_row_id", source_row_ids)
        part["rater_id"] = frame[f"Rater_{position}"].to_numpy(copy=True)
        part["rater_position"] = position
        for column in (*TRAITS, "Identifying_Info"):
            part[column] = frame[f"{column}_{position}"].to_numpy(copy=True)

        trait_scores = part.loc[:, PROFILE_TRAITS]
        part["has_invalid_overall"] = ~part["Overall"].isin(EXPECTED_SCORE_VALUES)
        part["has_invalid_trait"] = (~trait_scores.isin(EXPECTED_SCORE_VALUES)).any(axis=1)
        part["has_any_invalid_score"] = part["has_invalid_overall"] | part["has_invalid_trait"]
        # 不完全なTrait profileを部分平均で覆い隠さないため、欠損があれば派生値も欠損とする。
        part["trait_mean"] = trait_scores.mean(axis=1, skipna=False)
        part["trait_min"] = trait_scores.min(axis=1, skipna=False)
        part["trait_max"] = trait_scores.max(axis=1, skipna=False)
        part["trait_std"] = trait_scores.std(axis=1, ddof=0, skipna=False)
        records.append(part)

    result = pd.concat(records, ignore_index=True)
    result = result.sort_values(["source_row_id", "rater_position"], kind="stable").reset_index(drop=True)
    return result


def validate_rater_essay_wide(frame: pd.DataFrame, wide: pd.DataFrame) -> None:
    """rawの両positionとwideの全行が混線なく対応することを検証する。"""
    expected_rows = len(frame) * len(POSITIONS)
    if len(wide) != expected_rows:
        raise ValueError(f"変換後行数が不正です: expected={expected_rows}, actual={len(wide)}")
    if wide.duplicated(["source_row_id", "rater_position"]).any():
        raise ValueError("source_row_id + rater_position が重複しています")
    expected_filename_position_duplicates = int(
        frame["Filename"].duplicated(keep=False).sum() * len(POSITIONS)
    )
    actual_filename_position_duplicates = int(
        wide.duplicated(["Filename", "rater_position"], keep=False).sum()
    )
    if actual_filename_position_duplicates != expected_filename_position_duplicates:
        raise ValueError(
            "Filename + rater_position の重複数がrawのFilename重複から期待される数と一致しません: "
            f"expected={expected_filename_position_duplicates}, "
            f"actual={actual_filename_position_duplicates}"
        )
    if set(wide["rater_position"].dropna().unique()) != set(POSITIONS):
        raise ValueError("rater_position に想定外値またはposition欠落があります")

    identity_columns = ("Filename", "text_id_kaggle", "Text")
    mapped_columns = ("Overall", *PROFILE_TRAITS, "Identifying_Info")
    for position in POSITIONS:
        subset = wide[wide["rater_position"] == position].sort_values("source_row_id")
        if not np.array_equal(subset["source_row_id"].to_numpy(), np.arange(len(frame))):
            raise ValueError(f"position={position} のsource_row_idがraw行順と一致しません")
        comparisons = [("rater_id", f"Rater_{position}")]
        comparisons.extend((column, column) for column in identity_columns)
        comparisons.extend((column, f"{column}_{position}") for column in mapped_columns)
        for wide_column, raw_column in comparisons:
            actual = subset[wide_column].reset_index(drop=True)
            expected = frame[raw_column].reset_index(drop=True)
            try:
                pd.testing.assert_series_equal(actual, expected, check_dtype=False, check_names=False)
            except AssertionError as exc:
                raise ValueError(
                    f"position={position}: {wide_column} と raw列 {raw_column} が一致しません"
                ) from exc
