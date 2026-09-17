from __future__ import annotations

import unittest
from pathlib import Path
import pandas as pd
from src.recsaver.history import sample_history, sample_wrong_rater_history
from src.recsaver.k_history_pilot import select_pilot_targets
from src.recsaver.parsing import leaks_score, parse_prediction
from src.recsaver.prompts import prompt_metadata, render


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

    def test_both_prompt_languages_render_and_metadata_has_hashes(self):
        for prompt_dir in ("prompts/ja", "prompts/en"):
            values = {
                "zero_shot_prediction.txt": {},
                "score_only_prediction.txt": {},
                "reference_generation.txt": {"gold_overall": 3},
                "self_verification.txt": {"reference_reasoning": "REFERENCE_MARKER"},
            }
            for name, extra in values.items():
                rendered = render(name, self.history, self.target, prompt_dir=prompt_dir, **extra)
                self.assertIn("essay 0", rendered)
                self.assertNotIn("{history}", rendered)
                self.assertNotIn("{target_essay}", rendered)
            metadata = prompt_metadata({"prompt_dir": prompt_dir})
            self.assertEqual(metadata["prompt_language"], prompt_dir.rsplit("/", 1)[-1])
            self.assertEqual(len(metadata["zero_shot_prediction_prompt_sha256"]), 64)

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

    def test_k0_prompt_has_explicit_empty_history_and_no_target_scores(self):
        target = self.target.copy(); target["Overall"] = 99
        for trait in ["Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]:
            target[trait] = 98
        prompt = render("zero_shot_prediction.txt", self.frame.iloc[:0], target, prompt_dir="prompts/en")
        self.assertIn("No rating history is provided.", prompt)
        self.assertNotIn("99", prompt); self.assertNotIn("98", prompt)

    def test_wrong_rater_history_is_single_rater_deterministic_and_excludes_target_essay(self):
        other = self.frame.copy()
        other["rater_id"] = "rater_2"
        other["rater_position"] = 2
        other["target_id"] = other.source_row_id.astype(str) + ":2"
        combined = pd.concat([self.frame, other], ignore_index=True)
        wrong_rater, history = sample_wrong_rater_history(combined, self.target, 3, 20260906)
        again_rater, again = sample_wrong_rater_history(combined, self.target, 3, 20260906)
        self.assertEqual(wrong_rater, "rater_2")
        self.assertEqual(wrong_rater, again_rater)
        self.assertEqual(history.target_id.tolist(), again.target_id.tolist())
        self.assertEqual(history.rater_id.nunique(), 1)
        self.assertNotIn(self.target.source_row_id, set(history.source_row_id))

    def test_overall_rubric_prompt_has_exact_rubric_and_no_target_scores(self):
        target = self.target.copy(); target["Overall"] = 99
        for trait in ["Cohesion", "Syntax", "Vocabulary", "Phraseology", "Grammar", "Conventions"]:
            target[trait] = 98
        root = Path(__file__).resolve().parents[1]
        rubric = (root / "rubrics/ellipse_overall_rubric.md").read_text(encoding="utf-8")
        template = (root / "prompts/en/rubric_based_prediction.txt").read_text(encoding="utf-8")
        prompt = template.format(overall_rubric=rubric, rating_history="No rating history is provided.",
                                 target_essay=target["Text"])
        self.assertIn(rubric, prompt)
        self.assertNotIn("99", prompt); self.assertNotIn("98", prompt)


if __name__ == "__main__": unittest.main()
