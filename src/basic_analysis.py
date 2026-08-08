"""採点者×エッセイwideデータを用いたTrait profile中心の基礎分析。"""
from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from .config import (BASIC_ANALYSIS_DIR, BASIC_ANALYSIS_FIGURE_DIR, BASIC_ANALYSIS_TABLE_DIR,
                     DOCS_DIR, EXPECTED_SCORE_VALUES, PROCESSED_DATA_DIR, PROFILE_TRAITS, TRAITS)

LOGGER = logging.getLogger(__name__)
DEFAULT_INPUT = PROCESSED_DATA_DIR / "rater_essay_wide.csv"
REPORT_PATH = DOCS_DIR / "basic_analysis_report.md"
SCORE_LEVELS: tuple[int, ...] = (1, 2, 3, 4, 5)
CORRELATION_PREDICTORS: tuple[str, ...] = (*PROFILE_TRAITS, "trait_mean", "trait_min", "trait_max", "trait_std")

REQUIRED_COLUMNS: tuple[str, ...] = (
    "source_row_id", "Filename", "text_id_kaggle", "Text", "rater_id", "rater_position",
    *TRAITS, "Identifying_Info", "has_invalid_overall", "has_invalid_trait",
    "has_any_invalid_score", "trait_mean", "trait_min", "trait_max", "trait_std",
)


def natural_rater_order(values: Iterable[object]) -> list[str]:
    """末尾の数値を考慮して採点者IDを安定ソートする。"""
    ids = [str(value) for value in values]

    def key(value: str) -> tuple[str, int, str]:
        match = re.search(r"^(.*?)(\d+)$", value)
        return (match.group(1), int(match.group(2)), value) if match else (value, -1, value)

    return sorted(ids, key=key)


def prepare_output_dirs() -> None:
    """新基礎分析の専用出力だけを初期化する。"""
    BASIC_ANALYSIS_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    BASIC_ANALYSIS_FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for path in BASIC_ANALYSIS_TABLE_DIR.glob("*.csv"):
        path.unlink()
    for path in BASIC_ANALYSIS_FIGURE_DIR.glob("*.png"):
        path.unlink()


def load_processed_wide(path: Path = DEFAULT_INPUT) -> pd.DataFrame:
    """processed wideを変更せず読み込み、列と型を検証する。"""
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"processed wideデータが見つかりません: {resolved}")
    try:
        frame = pd.read_csv(resolved, encoding="utf-8", low_memory=False)
    except Exception as exc:
        raise RuntimeError(f"processed wideデータの読み込みに失敗しました: {resolved}: {exc}") from exc
    frame = frame.copy()
    frame.columns = frame.columns.astype(str).str.strip()
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"processed wideデータに必須列がありません: {missing}")
    for column in (*TRAITS, "Identifying_Info", "trait_mean", "trait_min", "trait_max", "trait_std"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    LOGGER.info("processed wide: %s", resolved)
    LOGGER.info("形状: %d行 × %d列", *frame.shape)
    LOGGER.info("列名: %s", list(frame.columns))
    return frame


def valid_sample_mask(frame: pd.DataFrame) -> pd.Series:
    """Overallと6 Traitがすべて1～5のサンプルを特定する。"""
    return frame.loc[:, TRAITS].isin(EXPECTED_SCORE_VALUES).all(axis=1)


def select_valid_samples(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    mask = valid_sample_mask(frame)
    return frame.loc[mask].copy(), mask


def safe_correlation(first: pd.Series, second: pd.Series, method: str) -> tuple[int, float]:
    paired = pd.concat([first, second], axis=1).dropna()
    if len(paired) < 2 or paired.iloc[:, 0].nunique() < 2 or paired.iloc[:, 1].nunique() < 2:
        return len(paired), float("nan")
    result = pearsonr(paired.iloc[:, 0], paired.iloc[:, 1]) if method == "pearson" else spearmanr(paired.iloc[:, 0], paired.iloc[:, 1])
    return len(paired), float(result.statistic)


def dataset_tables(frame: pd.DataFrame, valid: pd.DataFrame, mask: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    rater_counts = frame.groupby("rater_id", dropna=False).agg(
        total_sample_count=("source_row_id", "size"),
        total_unique_essay_count=("source_row_id", "nunique"),
    )
    valid_counts = valid.groupby("rater_id", dropna=False).agg(
        valid_sample_count=("source_row_id", "size"),
        valid_unique_essay_count=("source_row_id", "nunique"),
    )
    rater_counts = rater_counts.join(valid_counts, how="left").fillna(0).reset_index()
    for column in ("valid_sample_count", "valid_unique_essay_count"):
        rater_counts[column] = rater_counts[column].astype(int)
    rater_counts["excluded_sample_count"] = rater_counts["total_sample_count"] - rater_counts["valid_sample_count"]
    order = {rater: index for index, rater in enumerate(natural_rater_order(rater_counts["rater_id"]))}
    rater_counts = rater_counts.sort_values("rater_id", key=lambda s: s.map(order)).reset_index(drop=True)

    valid_count_values = rater_counts["valid_sample_count"]
    rows: list[tuple[str, object]] = [
        ("total_sample_count", len(frame)),
        ("valid_sample_count", len(valid)),
        ("excluded_sample_count", int((~mask).sum())),
        ("invalid_overall_sample_count", int((~frame["Overall"].isin(EXPECTED_SCORE_VALUES)).sum())),
        ("invalid_trait_profile_sample_count", int((~frame.loc[:, PROFILE_TRAITS].isin(EXPECTED_SCORE_VALUES).all(axis=1)).sum())),
        ("missing_required_score_sample_count", int(frame.loc[:, TRAITS].isna().any(axis=1).sum())),
        ("total_unique_source_essay_count", frame["source_row_id"].nunique(dropna=True)),
        ("valid_unique_source_essay_count", valid["source_row_id"].nunique(dropna=True)),
        ("total_unique_filename_count", frame["Filename"].nunique(dropna=True)),
        ("valid_unique_filename_count", valid["Filename"].nunique(dropna=True)),
        ("unique_rater_count", frame["rater_id"].nunique(dropna=True)),
        ("rater_ids", "|".join(natural_rater_order(frame["rater_id"].dropna().unique()))),
        ("valid_samples_per_rater_min", int(valid_count_values.min())),
        ("valid_samples_per_rater_median", float(valid_count_values.median())),
        ("valid_samples_per_rater_mean", float(valid_count_values.mean())),
        ("valid_samples_per_rater_max", int(valid_count_values.max())),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"]), rater_counts


def score_tables(valid: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    descriptive_rows: list[dict[str, object]] = []
    distribution_rows: list[dict[str, object]] = []
    for variable in TRAITS:
        series = valid[variable]
        descriptive_rows.append({
            "score_variable": variable, "count": series.count(), "mean": series.mean(),
            "median": series.median(), "std": series.std(), "min": series.min(), "max": series.max(),
        })
        counts = series.value_counts().reindex(SCORE_LEVELS, fill_value=0)
        for score, count in counts.items():
            distribution_rows.append({
                "score_variable": variable, "score": score, "count": int(count),
                "proportion": float(count / len(series)),
            })
    return pd.DataFrame(descriptive_rows), pd.DataFrame(distribution_rows)


def rater_score_tables(valid: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    descriptive_rows: list[dict[str, object]] = []
    distribution_rows: list[dict[str, object]] = []
    for (rater_id, variable), series in valid.melt(
        id_vars="rater_id", value_vars=TRAITS, var_name="score_variable", value_name="score"
    ).groupby(["rater_id", "score_variable"])["score"]:
        descriptive_rows.append({
            "rater_id": rater_id, "score_variable": variable, "count": series.count(),
            "mean": series.mean(), "median": series.median(), "std": series.std(),
            "min": series.min(), "max": series.max(),
        })
        counts = series.value_counts().reindex(SCORE_LEVELS, fill_value=0)
        for score, count in counts.items():
            distribution_rows.append({
                "rater_id": rater_id, "score_variable": variable, "score": score,
                "count": int(count), "proportion": float(count / len(series)),
            })
    return pd.DataFrame(descriptive_rows), pd.DataFrame(distribution_rows)


def rater_trait_profile_tables(valid: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    profile = valid.groupby("rater_id")[list(PROFILE_TRAITS)].agg(["count", "mean"])
    rows: list[dict[str, object]] = []
    for rater_id in profile.index:
        for trait in PROFILE_TRAITS:
            rows.append({
                "rater_id": rater_id, "trait": trait,
                "count": int(profile.loc[rater_id, (trait, "count")]),
                "mean": float(profile.loc[rater_id, (trait, "mean")]),
            })
    profile_long = pd.DataFrame(rows)
    rater_center = profile_long.groupby("rater_id")["mean"].mean().rename("rater_six_trait_mean")
    relative = profile_long.merge(rater_center, on="rater_id")
    relative["relative_trait_tendency"] = relative["mean"] - relative["rater_six_trait_mean"]
    return profile_long, relative


def overall_trait_correlations(valid: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for predictor in CORRELATION_PREDICTORS:
        n, pearson = safe_correlation(valid["Overall"], valid[predictor], "pearson")
        _, spearman = safe_correlation(valid["Overall"], valid[predictor], "spearman")
        rows.append({"predictor": predictor, "count": n, "pearson_correlation": pearson, "spearman_correlation": spearman})
    return pd.DataFrame(rows)


def trait_mean_analysis(valid: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | int]]:
    calculated = valid.loc[:, PROFILE_TRAITS].mean(axis=1)
    maximum_error = float((calculated - valid["trait_mean"]).abs().max())
    if maximum_error > 1e-12:
        raise ValueError(f"保存済みtrait_meanと6 Traitの再計算値が一致しません: max_error={maximum_error}")

    relation = valid[["source_row_id", "Filename", "text_id_kaggle", "rater_id", "Overall", *PROFILE_TRAITS]].copy()
    relation["trait_mean"] = calculated
    relation["overall_minus_trait_mean"] = relation["Overall"] - relation["trait_mean"]
    relation["absolute_overall_minus_trait_mean"] = relation["overall_minus_trait_mean"].abs()
    relation["rounded_trait_mean_half_up"] = np.floor(relation["trait_mean"] + 0.5).astype(int)
    relation["rounded_trait_mean_matches_overall"] = relation["rounded_trait_mean_half_up"].eq(relation["Overall"])

    mean_groups = relation.groupby("trait_mean")["Overall"].nunique()
    differing_means = mean_groups[mean_groups > 1].index
    relation["same_trait_mean_has_different_overall"] = relation["trait_mean"].isin(differing_means)

    profile_group_columns = list(PROFILE_TRAITS)
    profile_groups = relation.groupby(profile_group_columns, dropna=False).agg(
        sample_count=("Overall", "size"), unique_overall_count=("Overall", "nunique"),
        overall_values=("Overall", lambda x: "|".join(map(str, sorted(x.unique())))),
        rater_count=("rater_id", "nunique"), essay_count=("source_row_id", "nunique"),
    ).reset_index()
    different_profiles = profile_groups[profile_groups["unique_overall_count"] > 1].copy()

    _, pearson = safe_correlation(relation["Overall"], relation["trait_mean"], "pearson")
    _, spearman = safe_correlation(relation["Overall"], relation["trait_mean"], "spearman")
    metrics: dict[str, float | int] = {
        "trait_mean_validation_max_error": maximum_error,
        "mean_overall_minus_trait_mean": float(relation["overall_minus_trait_mean"].mean()),
        "median_overall_minus_trait_mean": float(relation["overall_minus_trait_mean"].median()),
        "mean_absolute_overall_minus_trait_mean": float(relation["absolute_overall_minus_trait_mean"].mean()),
        "pearson_overall_trait_mean": pearson,
        "spearman_overall_trait_mean": spearman,
        "rounded_trait_mean_agreement_rate": float(relation["rounded_trait_mean_matches_overall"].mean()),
        "same_trait_mean_different_overall_mean_value_count": int(len(differing_means)),
        "same_trait_mean_different_overall_sample_count": int(relation["same_trait_mean_has_different_overall"].sum()),
        "same_profile_different_overall_group_count": int(len(different_profiles)),
        "same_profile_different_overall_sample_count": int(different_profiles["sample_count"].sum()),
    }
    return relation, different_profiles, metrics


def rater_overall_trait_correlations(valid: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    predictors = (*PROFILE_TRAITS, "trait_mean")
    for rater_id, group in valid.groupby("rater_id"):
        for predictor in predictors:
            n, pearson = safe_correlation(group["Overall"], group[predictor], "pearson")
            _, spearman = safe_correlation(group["Overall"], group[predictor], "spearman")
            rows.append({
                "rater_id": rater_id, "predictor": predictor, "count": n,
                "pearson_correlation": pearson, "spearman_correlation": spearman,
            })
    return pd.DataFrame(rows)


def rater_overall_trait_gap(valid: pd.DataFrame) -> pd.DataFrame:
    data = valid[["rater_id", "Overall", "trait_mean"]].copy()
    data["unadjusted_overall_trait_gap"] = data["Overall"] - data["trait_mean"]
    return data.groupby("rater_id")["unadjusted_overall_trait_gap"].agg(
        count="count", mean="mean", median="median", std="std", min="min", max="max"
    ).reset_index()


def text_length_features(text: pd.Series) -> pd.DataFrame:
    values = text.fillna("").astype(str)
    result = pd.DataFrame(index=text.index)
    result["character_count"] = values.str.len()
    result["word_count"] = values.str.findall(r"\b[\w']+\b").str.len()
    result["estimated_sentence_count"] = values.str.count(r"[.!?]+")
    result.loc[(values.str.strip() != "") & result["estimated_sentence_count"].eq(0), "estimated_sentence_count"] = 1
    return result


def rater_text_length_summary(valid: pd.DataFrame) -> pd.DataFrame:
    features = text_length_features(valid["Text"])
    data = pd.concat([valid[["rater_id"]], features], axis=1)
    return data.groupby("rater_id").agg(
        sample_count=("word_count", "count"),
        mean_character_count=("character_count", "mean"),
        mean_word_count=("word_count", "mean"),
        median_word_count=("word_count", "median"),
        std_word_count=("word_count", "std"),
        mean_estimated_sentence_count=("estimated_sentence_count", "mean"),
    ).reset_index()


def save_table(frame: pd.DataFrame, filename: str) -> None:
    frame.to_csv(BASIC_ANALYSIS_TABLE_DIR / filename, index=False, encoding="utf-8-sig")


def save_figure(fig: plt.Figure, filename: str) -> None:
    fig.tight_layout()
    fig.savefig(BASIC_ANALYSIS_FIGURE_DIR / filename, dpi=170, bbox_inches="tight")
    plt.close(fig)


def plot_bar(series: pd.Series, title: str, ylabel: str, filename: str, rotation: int = 65) -> None:
    fig, ax = plt.subplots(figsize=(max(9, len(series) * 0.42), 5.5))
    positions = np.arange(len(series))
    ax.bar(positions, series.values, color="#4C78A8")
    ax.set_xticks(positions, labels=series.index.astype(str))
    ax.set_title(title); ax.set_ylabel(ylabel); ax.tick_params(axis="x", rotation=rotation)
    save_figure(fig, filename)


def plot_heatmap(matrix: pd.DataFrame, title: str, filename: str, color_label: str,
                 cmap: str = "viridis", vmin: float | None = None, vmax: float | None = None) -> None:
    fig, ax = plt.subplots(figsize=(max(8, len(matrix.columns) * 1.1), max(7, len(matrix.index) * 0.32)))
    values = np.ma.masked_invalid(matrix.to_numpy(dtype=float))
    image = ax.imshow(values, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(matrix.columns)), labels=matrix.columns)
    ax.set_yticks(range(len(matrix.index)), labels=matrix.index)
    ax.tick_params(axis="x", rotation=40)
    ax.set_title(title)
    colorbar = fig.colorbar(image, ax=ax); colorbar.set_label(color_label)
    save_figure(fig, filename)


def create_figures(valid: pd.DataFrame, rater_counts: pd.DataFrame, score_distribution: pd.DataFrame,
                   rater_descriptive: pd.DataFrame, rater_distribution: pd.DataFrame,
                   trait_profile: pd.DataFrame, correlations: pd.DataFrame,
                   relation: pd.DataFrame, rater_correlations: pd.DataFrame,
                   gap: pd.DataFrame, text_summary: pd.DataFrame) -> None:
    rater_order = natural_rater_order(rater_counts["rater_id"])
    counts = rater_counts.set_index("rater_id").reindex(rater_order)["valid_sample_count"]
    plot_bar(counts, "Valid samples by rater", "Samples", "rater_sample_counts.png")

    overall_dist = score_distribution[score_distribution["score_variable"] == "Overall"].set_index("score")["proportion"]
    plot_bar(overall_dist, "Overall score distribution", "Proportion", "overall_score_distribution.png", 0)

    fig, ax = plt.subplots(figsize=(10, 6))
    width = 0.12; x = np.arange(len(SCORE_LEVELS))
    for index, trait in enumerate(PROFILE_TRAITS):
        values = score_distribution[score_distribution["score_variable"] == trait].set_index("score").reindex(SCORE_LEVELS)["proportion"]
        ax.bar(x + (index - 2.5) * width, values, width, label=trait)
    ax.set_xticks(x, SCORE_LEVELS); ax.set_xlabel("Score"); ax.set_ylabel("Proportion"); ax.set_title("Trait score distributions"); ax.legend(ncol=2)
    save_figure(fig, "trait_score_distributions.png")

    overall_stats = rater_descriptive[rater_descriptive["score_variable"] == "Overall"].set_index("rater_id").reindex(rater_order)
    plot_bar(overall_stats["mean"], "Mean Overall score by rater (unadjusted)", "Mean Overall", "rater_overall_mean.png")
    plot_bar(overall_stats["std"], "Overall score standard deviation by rater", "Standard deviation", "rater_overall_std.png")

    overall_usage = rater_distribution[rater_distribution["score_variable"] == "Overall"].pivot(index="rater_id", columns="score", values="proportion").reindex(rater_order).reindex(columns=SCORE_LEVELS)
    plot_heatmap(overall_usage, "Overall score usage by rater", "rater_overall_score_distribution_heatmap.png", "Proportion", "Blues", 0, 1)

    profile_matrix = trait_profile.pivot(index="rater_id", columns="trait", values="mean").reindex(rater_order).reindex(columns=PROFILE_TRAITS)
    plot_heatmap(profile_matrix, "Mean Trait profile by rater", "rater_trait_profile_heatmap.png", "Mean score", "viridis", 1, 5)

    trait_corr = correlations[correlations["predictor"].isin(PROFILE_TRAITS)].set_index("predictor").reindex(PROFILE_TRAITS)
    fig, ax = plt.subplots(figsize=(10, 5.5)); x = np.arange(len(PROFILE_TRAITS)); width = 0.36
    ax.bar(x - width / 2, trait_corr["pearson_correlation"], width, label="Pearson")
    ax.bar(x + width / 2, trait_corr["spearman_correlation"], width, label="Spearman")
    ax.set_xticks(x, PROFILE_TRAITS, rotation=35, ha="right"); ax.set_ylim(0, 1); ax.set_ylabel("Correlation with Overall"); ax.set_title("Overall and Trait correlations"); ax.legend()
    save_figure(fig, "overall_trait_correlations.png")

    bubble_counts = relation.groupby(["trait_mean", "Overall"]).size().reset_index(name="count")
    fig, ax = plt.subplots(figsize=(8, 6))
    scatter = ax.scatter(bubble_counts["trait_mean"], bubble_counts["Overall"], s=np.sqrt(bubble_counts["count"]) * 5, c=bubble_counts["count"], cmap="viridis", alpha=0.8)
    ax.plot([1, 5], [1, 5], linestyle="--", color="gray", linewidth=1)
    ax.set(xlabel="Trait mean", ylabel="Human Overall", title="Overall and mean of six Traits", xticks=SCORE_LEVELS, yticks=SCORE_LEVELS)
    fig.colorbar(scatter, ax=ax, label="Sample count")
    save_figure(fig, "overall_vs_trait_mean.png")

    corr_matrix = rater_correlations.pivot(index="rater_id", columns="predictor", values="pearson_correlation").reindex(rater_order).reindex(columns=(*PROFILE_TRAITS, "trait_mean"))
    plot_heatmap(corr_matrix, "Rater-specific correlation with Overall", "rater_overall_trait_correlation_heatmap.png", "Pearson correlation", "coolwarm", -1, 1)

    gap_values = gap.set_index("rater_id").reindex(rater_order)["mean"]
    plot_bar(gap_values, "Mean Overall - Trait mean by rater (unadjusted)", "Unadjusted Overall-Trait gap", "rater_overall_minus_trait_mean.png")
    word_values = text_summary.set_index("rater_id").reindex(rater_order)["mean_word_count"]
    plot_bar(word_values, "Mean essay word count by rater", "Mean words", "rater_mean_essay_word_count.png")


def write_report(frame: pd.DataFrame, valid: pd.DataFrame, dataset_summary: pd.DataFrame,
                 rater_counts: pd.DataFrame, descriptive: pd.DataFrame,
                 rater_descriptive: pd.DataFrame, trait_profile: pd.DataFrame,
                 relative_profile: pd.DataFrame, correlations: pd.DataFrame,
                 relation: pd.DataFrame, trait_metrics: dict[str, float | int], rater_correlations: pd.DataFrame,
                 gap: pd.DataFrame, text_summary: pd.DataFrame) -> None:
    summary = dataset_summary.set_index("metric")["value"]
    overall_stats = descriptive.set_index("score_variable").loc["Overall"]
    rater_overall = rater_descriptive[rater_descriptive["score_variable"] == "Overall"]
    def rounded_records(data: pd.DataFrame, columns: list[str], decimals: int = 3) -> list[dict[str, object]]:
        subset = data.loc[:, columns].copy()
        numeric = subset.select_dtypes(include="number").columns
        subset.loc[:, numeric] = subset.loc[:, numeric].round(decimals)
        return subset.to_dict("records")

    low_overall = rounded_records(rater_overall.nsmallest(3, "mean"), ["rater_id", "count", "mean"])
    high_overall = rounded_records(rater_overall.nlargest(3, "mean"), ["rater_id", "count", "mean"])
    strongest = correlations[correlations["predictor"].isin(PROFILE_TRAITS)].iloc[
        correlations[correlations["predictor"].isin(PROFILE_TRAITS)]["pearson_correlation"].abs().argmax()
    ]
    relative_extremes = relative_profile.reindex(relative_profile["relative_trait_tendency"].abs().sort_values(ascending=False).index).head(8)
    corr_ranges = rater_correlations.groupby("predictor")["pearson_correlation"].agg(["min", "max", "std"]).reset_index()
    widest = corr_ranges.loc[(corr_ranges["max"] - corr_ranges["min"]).idxmax()]
    text_min = text_summary.loc[text_summary["mean_word_count"].idxmin()]
    text_max = text_summary.loc[text_summary["mean_word_count"].idxmax()]
    gap_low = rounded_records(gap.nsmallest(3, "mean"), ["rater_id", "count", "mean"])
    gap_high = rounded_records(gap.nlargest(3, "mean"), ["rater_id", "count", "mean"])
    count_records = rounded_records(rater_counts, ["rater_id", "valid_sample_count", "valid_unique_essay_count", "excluded_sample_count"], 0)
    overall_usage = valid.groupby("rater_id")["Overall"].value_counts(normalize=True).unstack(fill_value=0)
    middle_usage = overall_usage.get(3, pd.Series(0.0, index=overall_usage.index))
    extreme_usage = overall_usage.get(1, pd.Series(0.0, index=overall_usage.index)) + overall_usage.get(5, pd.Series(0.0, index=overall_usage.index))
    highest_middle = str(middle_usage.idxmax()); highest_extreme = str(extreme_usage.idxmax())
    lowest_sd = rater_overall.loc[rater_overall["std"].idxmin()]
    highest_sd = rater_overall.loc[rater_overall["std"].idxmax()]
    overall_trait_mean_groups = relation.groupby("Overall")["trait_mean"].agg(["count", "mean", "median", "std", "min", "max"]).reset_index()
    trait_mean_description = relation["trait_mean"].describe()
    score_lines = "\n".join(
        f"- {row.score_variable}: 平均 {row.mean:.3f}、中央値 {row.median:.1f}、標準偏差 {row.std:.3f}"
        for row in descriptive.itertuples()
    )
    corr_lines = "\n".join(
        f"- {row.predictor}: Pearson {row.pearson_correlation:.3f}、Spearman {row.spearman_correlation:.3f}"
        for row in correlations.itertuples()
    )
    report = f"""# ELLIPSE Trait profile基礎分析レポート

## 1. データセット概要

`data/processed/rater_essay_wide.csv`の{int(summary['total_sample_count']):,}サンプルから、Overallと6 Traitがすべて1～5の{int(summary['valid_sample_count']):,}サンプルを主要分析に使用した。除外は{int(summary['excluded_sample_count']):,}サンプルで、内訳はOverall範囲外{int(summary['invalid_overall_sample_count']):,}件、Trait profile範囲外{int(summary['invalid_trait_profile_sample_count']):,}件（重複あり）、必要スコア欠損{int(summary['missing_required_score_sample_count']):,}件だった。元値は変更していない。有効データには{int(summary['valid_unique_source_essay_count']):,}件のsource essay、{int(summary['valid_unique_filename_count']):,}件のユニークFilename、{int(summary['unique_rater_count'])}名の採点者が含まれる。

採点者別の有効件数は最小{int(summary['valid_samples_per_rater_min'])}、中央値{float(summary['valid_samples_per_rater_median']):.1f}、平均{float(summary['valid_samples_per_rater_mean']):.1f}、最大{int(summary['valid_samples_per_rater_max'])}だった。採点者別件数は`{count_records}`で、詳細は`rater_sample_counts.csv`に示す。

## 2. Overall・Traitスコア分布

{score_lines}

Overallの平均は{overall_stats['mean']:.3f}、標準偏差は{overall_stats['std']:.3f}だった。尺度が同じでも各Traitの評価内容は異なるため、平均値だけで単純比較しない。

## 3. 採点者ごとの基本的な採点傾向

Overall平均が低い側の3名は`{low_overall}`、高い側の3名は`{high_overall}`だった。スコア3の使用割合が最も高い採点者は{highest_middle}（{middle_usage.max():.1%}）、1または5の使用割合が最も高い採点者は{highest_extreme}（{extreme_usage.max():.1%}）だった。Overall標準偏差は{lowest_sd['rater_id']}の{lowest_sd['std']:.3f}から{highest_sd['rater_id']}の{highest_sd['std']:.3f}まで分布した。これらは担当答案の難易度や構成を統制していない未調整の評価傾向であり、採点者の厳しさ・甘さを示す確定的な結果ではない。

## 4. 採点者ごとのTrait profile

採点者内部の6 Trait平均からの差が大きい例は`{rounded_records(relative_extremes, ['rater_id','trait','mean','rater_six_trait_mean','relative_trait_tendency'])}`だった。`relative_trait_tendency`は採点者内部の相対的なTrait profileを記述する探索的指標であり、答案構成を統制していない。

## 5. TraitとOverallの関係

{corr_lines}

6 TraitのうちOverallとのPearson相関が最も強かったのは{strongest['predictor']}（{strongest['pearson_correlation']:.3f}）だった。相関は関連を示すが、採点者がそのTraitを因果的に重視したことや、Overall決定時の重みを直接示すものではない。

## 6. Trait平均とOverallの関係

保存済み`trait_mean`と6 Traitからの再計算値の最大誤差は{float(trait_metrics['trait_mean_validation_max_error']):.3g}だった。Trait平均は平均{trait_mean_description['mean']:.3f}、標準偏差{trait_mean_description['std']:.3f}である。OverallとのPearson相関は{float(trait_metrics['pearson_overall_trait_mean']):.3f}、Spearman相関は{float(trait_metrics['spearman_overall_trait_mean']):.3f}である。一方、四捨五入したTrait平均とOverallの一致率は{float(trait_metrics['rounded_trait_mean_agreement_rate']):.1%}、平均絶対差は{float(trait_metrics['mean_absolute_overall_minus_trait_mean']):.3f}だった。Overall別のTrait平均分布は`{rounded_records(overall_trait_mean_groups, ['Overall','count','mean','median','std','min','max'])}`だった。

同じTrait meanで異なるOverallが存在するサンプルは{int(trait_metrics['same_trait_mean_different_overall_sample_count']):,}件、6 Traitが完全に同じでOverallが異なるprofileは{int(trait_metrics['same_profile_different_overall_group_count']):,}組（該当{int(trait_metrics['same_profile_different_overall_sample_count']):,}サンプル）あった。したがって、Trait平均とOverallには強い関連があっても、Trait平均の単純な四捨五入だけでは全サンプルのOverallを再現できない。

## 7. 採点者ごとのTrait→Overall関係

採点者別Pearson相関の範囲が最も広かった予測変数は{widest['predictor']}で、最小{widest['min']:.3f}、最大{widest['max']:.3f}だった。採点件数やスコア分散が異なるため単純比較には注意が必要だが、TraitとOverallの関連パターンが採点者間で一様ではない可能性を探索する根拠になる。

採点者別の未調整`Overall - trait_mean`平均の下位・上位は`{gap_low}` / `{gap_high}`だった。この差も担当答案を統制していない。

## 8. 担当答案構成の違い

採点者別の平均単語数は{text_min['rater_id']}の{text_min['mean_word_count']:.1f}語から{text_max['rater_id']}の{text_max['mean_word_count']:.1f}語まで分布した。本文長だけで答案難易度を説明することはできないが、採点者ごとに担当答案構成が完全には同一でない可能性を示す補助情報である。

## 9. 現時点で分かること

Overallと各TraitおよびTrait平均には統計的な関連があり、6 Traitを構造化された中間情報として分析する意味がある。同時に、同一Trait meanや同一Trait profileでもOverallが異なる実例が存在する。採点者別のTraitとの相関、Trait profile、`Overall - trait_mean`にも探索的な違いが観察された。

## 10. 現時点では言えないこと

採点者平均の高低だけから厳しさ・甘さを断定できない。TraitとOverallの相関を因果的な重みと解釈できない。担当答案の難易度、採点件数、スコア範囲などを統制していないため、観察差を採点者固有の効果として確定できない。

## 11. Rec-SAVER型実験への示唆

6 TraitはOverallと関連する構造化中間情報として利用候補になるが、単純なTrait平均だけではOverallを完全には説明できない。採点者別の関連パターンが一様でない探索的結果があるため、採点者IDや過去のTrait→Overall履歴を入力へ含める価値を比較実験で検証できる。次段階では、同じまたは近いTrait profileに対する採点者別Overall差、採点者履歴あり・なしの予測性能差、答案構成を統制した後にも関連パターン差が残るかを統計的に検証する必要がある。
"""
    REPORT_PATH.write_text(report, encoding="utf-8")


def run(input_path: Path = DEFAULT_INPUT) -> dict[str, pd.DataFrame]:
    prepare_output_dirs()
    frame = load_processed_wide(input_path)
    valid, mask = select_valid_samples(frame)
    dataset_summary, rater_counts = dataset_tables(frame, valid, mask)
    descriptive, score_distribution = score_tables(valid)
    rater_descriptive, rater_distribution = rater_score_tables(valid)
    trait_profile, relative_profile = rater_trait_profile_tables(valid)
    correlations = overall_trait_correlations(valid)
    relation, same_profiles, trait_metrics = trait_mean_analysis(valid)
    rater_correlations = rater_overall_trait_correlations(valid)
    gap = rater_overall_trait_gap(valid)
    text_summary = rater_text_length_summary(valid)

    tables = {
        "dataset_summary.csv": dataset_summary,
        "rater_sample_counts.csv": rater_counts,
        "overall_trait_descriptive_statistics.csv": descriptive,
        "overall_trait_score_distribution.csv": score_distribution,
        "rater_descriptive_statistics.csv": rater_descriptive,
        "rater_score_distribution.csv": rater_distribution,
        "rater_trait_profile.csv": trait_profile,
        "rater_trait_relative_profile.csv": relative_profile,
        "overall_trait_correlations.csv": correlations,
        "trait_mean_vs_overall.csv": relation,
        "same_trait_profile_different_overall.csv": same_profiles,
        "rater_overall_trait_correlations.csv": rater_correlations,
        "rater_overall_minus_trait_mean.csv": gap,
        "rater_text_length_summary.csv": text_summary,
    }
    for filename, table in tables.items():
        save_table(table, filename)
    create_figures(valid, rater_counts, score_distribution, rater_descriptive, rater_distribution,
                   trait_profile, correlations, relation, rater_correlations, gap, text_summary)
    write_report(frame, valid, dataset_summary, rater_counts, descriptive, rater_descriptive,
                 trait_profile, relative_profile, correlations, relation, trait_metrics,
                 rater_correlations, gap, text_summary)
    LOGGER.info("主要分析: total=%d, valid=%d, excluded=%d", len(frame), len(valid), int((~mask).sum()))
    LOGGER.info("出力: %s", BASIC_ANALYSIS_DIR)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="processed wide CSV")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run(args.input)


if __name__ == "__main__":
    main()
