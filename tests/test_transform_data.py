from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src.transform_data import create_rater_essay_wide, validate_rater_essay_wide


class CreateRaterEssayWideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = pd.DataFrame({
            "Filename": ["essay_a", "essay_a"],
            "text_id_kaggle": ["id_a", pd.NA],
            "Text": ["First essay.", "Second essay."],
            "Rater_1": ["rater_1", "rater_3"],
            "Overall_1": [3, 0], "Cohesion_1": [3, 0], "Syntax_1": [2, 2],
            "Vocabulary_1": [3, 3], "Phraseology_1": [3, 3], "Grammar_1": [3, 3],
            "Conventions_1": [2, 2], "Identifying_Info_1": [0, 0],
            "Rater_2": ["rater_2", "rater_4"],
            "Overall_2": [3, 4], "Cohesion_2": [4, 4], "Syntax_2": [3, 4],
            "Vocabulary_2": [4, 4], "Phraseology_2": [3, 4], "Grammar_2": [4, np.nan],
            "Conventions_2": [3, 4], "Identifying_Info_2": [0, 1],
        })
        self.wide = create_rater_essay_wide(self.raw)

    def test_position_1_maps_only_suffix_1_columns(self) -> None:
        row = self.wide.query("source_row_id == 0 and rater_position == 1").iloc[0]
        self.assertEqual(row["rater_id"], self.raw.loc[0, "Rater_1"])
        for column in ("Overall", "Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"):
            self.assertEqual(row[column], self.raw.loc[0, f"{column}_1"])

    def test_position_2_maps_only_suffix_2_columns(self) -> None:
        row = self.wide.query("source_row_id == 0 and rater_position == 2").iloc[0]
        self.assertEqual(row["rater_id"], self.raw.loc[0, "Rater_2"])
        for column in ("Overall", "Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"):
            self.assertEqual(row[column], self.raw.loc[0, f"{column}_2"])

    def test_source_row_and_position_are_unique(self) -> None:
        self.assertFalse(self.wide.duplicated(["source_row_id", "rater_position"]).any())
        # rawで同じFilenameが複数行ならFilename+positionは重複するが、追跡キーは一意。
        expected = int(self.raw["Filename"].duplicated(keep=False).sum() * 2)
        actual = int(self.wide.duplicated(["Filename", "rater_position"], keep=False).sum())
        self.assertEqual(actual, expected)
        validate_rater_essay_wide(self.raw, self.wide)

    def test_invalid_values_are_preserved_and_flagged(self) -> None:
        zero_row = self.wide.query("source_row_id == 1 and rater_position == 1").iloc[0]
        self.assertEqual(zero_row["Overall"], 0)
        self.assertEqual(zero_row["Cohesion"], 0)
        self.assertTrue(zero_row["has_invalid_overall"])
        self.assertTrue(zero_row["has_invalid_trait"])
        missing_row = self.wide.query("source_row_id == 1 and rater_position == 2").iloc[0]
        self.assertTrue(pd.isna(missing_row["Grammar"]))
        self.assertTrue(missing_row["has_invalid_trait"])

    def test_raw_is_not_modified(self) -> None:
        before = self.raw.copy(deep=True)
        create_rater_essay_wide(self.raw)
        pd.testing.assert_frame_equal(self.raw, before)


if __name__ == "__main__":
    unittest.main()
