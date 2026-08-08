"""一致度指標。"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import cohen_kappa_score


def _safe_correlation(a: pd.Series, b: pd.Series, method: str) -> float:
    if len(a) < 2 or a.nunique() < 2 or b.nunique() < 2:
        return float("nan")
    result = pearsonr(a, b) if method == "pearson" else spearmanr(a, b)
    return float(result.statistic)


def agreement_metrics(first: pd.Series, second: pd.Series) -> dict[str, float | int]:
    paired = pd.concat([first, second], axis=1).dropna()
    paired.columns = ["a", "b"]
    if paired.empty:
        return {key: float("nan") for key in (
            "exact_agreement_rate", "within_one_point_rate", "two_or_more_point_rate",
            "mean_signed_difference", "mean_absolute_difference", "rmse",
            "pearson_correlation", "spearman_correlation", "cohen_kappa", "quadratic_weighted_kappa",
        )} | {"paired_count": 0}
    diff = paired["a"] - paired["b"]
    # 半点尺度を整数化して kappa のカテゴリとして扱う。
    a_cat = (paired["a"] * 2).round().astype(int)
    b_cat = (paired["b"] * 2).round().astype(int)
    return {
        "paired_count": len(paired),
        "exact_agreement_rate": float((diff == 0).mean()),
        "within_one_point_rate": float((diff.abs() <= 1).mean()),
        "one_point_difference_rate": float((diff.abs() == 1).mean()),
        "two_or_more_point_rate": float((diff.abs() >= 2).mean()),
        "mean_signed_difference": float(diff.mean()),
        "mean_absolute_difference": float(diff.abs().mean()),
        "rmse": float(np.sqrt(np.mean(np.square(diff)))),
        "pearson_correlation": _safe_correlation(paired["a"], paired["b"], "pearson"),
        "spearman_correlation": _safe_correlation(paired["a"], paired["b"], "spearman"),
        "cohen_kappa": float(cohen_kappa_score(a_cat, b_cat)),
        "quadratic_weighted_kappa": float(cohen_kappa_score(a_cat, b_cat, weights="quadratic")),
    }
