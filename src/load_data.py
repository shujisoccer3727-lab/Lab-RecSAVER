"""CSV の検出と安全な読み込み。"""
from __future__ import annotations

import csv
import logging
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, REQUIRED_COLUMNS, SCORE_COLUMNS

LOGGER = logging.getLogger(__name__)


def find_csv_candidates(data_dir: Path = DATA_DIR) -> list[Path]:
    return sorted(path for path in data_dir.glob("*.csv") if path.is_file())


def detect_csv_format(path: Path) -> tuple[str, str]:
    raw = path.read_bytes()[:262_144]
    encoding = "utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8"
    try:
        sample = raw.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(f"UTF-8 で読み込めません: {path}: {exc}") from exc
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error as exc:
        raise ValueError(f"CSV 区切り文字を判定できません: {path}") from exc
    return encoding, delimiter


def resolve_input_path(input_path: Path | None = None) -> Path:
    if input_path is not None:
        path = input_path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"入力 CSV が存在しません: {path}")
        return path
    candidates = find_csv_candidates()
    if not candidates:
        raise FileNotFoundError(f"CSV が見つかりません: {DATA_DIR}")
    if len(candidates) > 1:
        names = ", ".join(path.name for path in candidates)
        raise ValueError(f"CSV が複数あります。--input で指定してください: {names}")
    return candidates[0]


def load_raw_scores(input_path: Path | None = None) -> tuple[pd.DataFrame, Path, str, str]:
    """元ファイルを書き換えず、検証・型変換したコピーを返す。"""
    path = resolve_input_path(input_path)
    encoding, delimiter = detect_csv_format(path)
    try:
        frame = pd.read_csv(path, encoding=encoding, sep=delimiter, low_memory=False)
    except Exception as exc:
        raise RuntimeError(f"CSV 読み込みに失敗しました: {path}: {exc}") from exc
    frame = frame.copy()
    frame.columns = frame.columns.astype(str).str.strip()
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"必須列がありません: {missing}")
    for column in SCORE_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    LOGGER.info("CSV: %s", path)
    LOGGER.info("形式: encoding=%s delimiter=%r", encoding, delimiter)
    LOGGER.info("形状: %d 行 × %d 列", *frame.shape)
    LOGGER.info("列名: %s", list(frame.columns))
    return frame, path, encoding, delimiter
