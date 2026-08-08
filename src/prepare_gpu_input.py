"""基礎分析結果からGPU推論へ渡す、実装非依存の入力を作成する。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import GPU_INPUT_DIR, TRAITS


def prepare_gpu_inference_input(frame: pd.DataFrame) -> pd.DataFrame:
    """1エッセイ1行の再利用可能な推論入力を返す。"""
    columns = ["Filename", "text_id_kaggle", "Text", "Rater_1", "Rater_2"]
    columns.extend(f"{trait}_{position}" for position in (1, 2) for trait in TRAITS)
    result = frame.loc[:, columns].copy()
    result.insert(0, "inference_id", result["text_id_kaggle"].astype("string"))
    return result


def save_gpu_inference_input(frame: pd.DataFrame, output_dir: Path = GPU_INPUT_DIR) -> tuple[Path, Path]:
    """CSVとJSONLを保存する。モデル固有ライブラリは使用しない。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    prepared = prepare_gpu_inference_input(frame)
    csv_path = output_dir / "gpu_inference_input.csv"
    jsonl_path = output_dir / "gpu_inference_input.jsonl"
    prepared.to_csv(csv_path, index=False, encoding="utf-8")
    prepared.to_json(jsonl_path, orient="records", lines=True, force_ascii=False)
    return csv_path, jsonl_path
