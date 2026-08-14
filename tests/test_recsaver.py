from __future__ import annotations

import unittest
import pandas as pd
from src.recsaver.history import sample_history
from src.recsaver.k_history_pilot import select_pilot_targets
from src.recsaver.parsing import leaks_score, parse_prediction
from src.recsaver.prompts import render


class RecSaverTest(unittest.TestCase):
    def setUp(self):
        rows = []
        for i in range(7):
            rows.append({"target_id": f"{i}:1", "source_row_id": i, "rater_position": 1,
                         "rater_id": "rater_1", "Text": f"essay {i}", "Overall": 3,
                         "Cohesion": 3, "Syntax": 3, "Vocabulary": 3,
                         "Phraseology": 3, "Grammar": 3, "Conventions": 3})
        self.frame = pd.DataFrame(rows); self.target = self.frame.iloc[0]
        self.history = sample_history(self.frame, self.target, 5, 42)

    def test_target_never_in_history_and_sampling_is_reproducible(self):
        self.assertNotIn(self.target.target_id, set(self.history.target_id))
        again = sample_history(self.frame, self.target, 5, 42)
        self.assertEqual(self.history.target_id.tolist(), again.target_id.tolist())

    def test_prompt_information_boundaries(self):
        target = self.target.copy(); target["Overall"] = 99
        target["Text"] = "TARGET_MARKER"
        for trait in ["Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]:
            target[trait] = 98
        phase1 = render("zero_shot_prediction.txt", self.history, target)
        reference = render("reference_generation.txt", self.history, target, gold_overall=99)
        verification = render("self_verification.txt", self.history, target, reference_reasoning="REFERENCE_MARKER")
        self.assertNotIn("99", phase1); self.assertNotIn("98", phase1)
        self.assertIn("99", reference); self.assertNotIn("98", reference)
        self.assertNotIn("99", verification); self.assertIn("REFERENCE_MARKER", verification)

    def test_safe_parsing_and_leak_detection(self):
        parsed = parse_prediction('prefix {"predicted_overall": 4, "reasoning": "clear"} suffix')
        self.assertEqual(parsed["predicted_overall"], 4)
        with self.assertRaises(ValueError): parse_prediction('{"predicted_overall": 8, "reasoning": "x"}')
        self.assertTrue(leaks_score("Overall 3 because it is adequate", 3))

    def test_nested_history_prefixes_and_target_sampling_reproduce(self):
        pool = sample_history(self.frame, self.target, 5, 42)
        self.assertEqual(pool.iloc[:1].target_id.tolist(), pool.iloc[:3].target_id.tolist()[:1])
        self.assertEqual(pool.iloc[:3].target_id.tolist(), pool.iloc[:5].target_id.tolist()[:3])
        config = {"seed": 7, "experiment": {"min_rater_samples": 2, "k_values": [1, 3, 5], "num_targets": 2}}
        first = select_pilot_targets(self.frame, config).target_id.tolist()
        second = select_pilot_targets(self.frame, config).target_id.tolist()
        self.assertEqual(first, second)


if __name__ == "__main__": unittest.main()
