from __future__ import annotations

import unittest

import pandas as pd

from src.basic_analysis import select_valid_samples, trait_mean_analysis, valid_sample_mask


class BasicAnalysisTest(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = pd.DataFrame({
            "source_row_id": [0, 0, 1], "Filename": ["a", "a", "b"],
            "text_id_kaggle": ["x", "x", "y"], "rater_id": ["r1", "r2", "r1"],
            "Overall": [3, 4, 0], "Cohesion": [3, 3, 2], "Syntax": [3, 3, 2],
            "Vocabulary": [3, 3, 2], "Phraseology": [3, 3, 2],
            "Grammar": [3, 3, 2], "Conventions": [3, 3, 2],
            "trait_mean": [3.0, 3.0, 2.0], "trait_min": [3, 3, 2],
            "trait_max": [3, 3, 2], "trait_std": [0.0, 0.0, 0.0],
        })

    def test_only_complete_one_to_five_profiles_are_valid(self) -> None:
        mask = valid_sample_mask(self.frame)
        self.assertEqual(mask.tolist(), [True, True, False])
        valid, returned_mask = select_valid_samples(self.frame)
        self.assertEqual(len(valid), 2)
        self.assertTrue(mask.equals(returned_mask))

    def test_same_profile_with_different_overall_is_detected(self) -> None:
        valid, _ = select_valid_samples(self.frame)
        relation, profiles, metrics = trait_mean_analysis(valid)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(int(profiles.iloc[0]["unique_overall_count"]), 2)
        self.assertEqual(int(metrics["same_profile_different_overall_sample_count"]), 2)
        self.assertTrue(relation["same_trait_mean_has_different_overall"].all())


if __name__ == "__main__":
    unittest.main()
