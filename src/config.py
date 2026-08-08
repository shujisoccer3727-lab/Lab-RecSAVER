"""分析設定。"""
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
TABLE_DIR = ROOT_DIR / "outputs" / "tables"
FIGURE_DIR = ROOT_DIR / "outputs" / "figures"
DOCS_DIR = ROOT_DIR / "docs"
GPU_INPUT_DIR = ROOT_DIR / "outputs" / "gpu"
BASIC_ANALYSIS_DIR = ROOT_DIR / "outputs" / "basic_analysis"
BASIC_ANALYSIS_TABLE_DIR = BASIC_ANALYSIS_DIR / "tables"
BASIC_ANALYSIS_FIGURE_DIR = BASIC_ANALYSIS_DIR / "figures"

TRAITS: tuple[str, ...] = (
    "Overall", "Cohesion", "Syntax", "Vocabulary",
    "Phraseology", "Grammar", "Conventions",
)
PROFILE_TRAITS: tuple[str, ...] = TRAITS[1:]
POSITIONS: tuple[int, int] = (1, 2)
PAIR_MIN_COUNT = 20
EXPECTED_SCORE_VALUES: frozenset[float] = frozenset({1.0, 2.0, 3.0, 4.0, 5.0})
BASE_COLUMNS: tuple[str, ...] = ("Filename", "text_id_kaggle", "Text", "Rater_1", "Rater_2")
SCORE_COLUMNS: tuple[str, ...] = tuple(
    f"{trait}_{position}" for position in POSITIONS
    for trait in (*TRAITS, "Identifying_Info")
)
REQUIRED_COLUMNS: tuple[str, ...] = (*BASE_COLUMNS, *SCORE_COLUMNS)


def ensure_output_dirs() -> None:
    """出力ディレクトリを作成する。"""
    for path in (TABLE_DIR, FIGURE_DIR, DOCS_DIR, GPU_INPUT_DIR, BASIC_ANALYSIS_TABLE_DIR, BASIC_ANALYSIS_FIGURE_DIR):
        path.mkdir(parents=True, exist_ok=True)
