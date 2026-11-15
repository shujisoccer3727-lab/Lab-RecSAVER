import json
import unittest
import tempfile
from pathlib import Path

from src.recsaver.human_score_disagreement_rater_tendency_inline import render, validate, recover


class InlinePredictionTests(unittest.TestCase):
    def setUp(self):
        self.item = dict(essay='A clear claim. Some supporting detail.', history_ids=['10:1', '20:2', '30:1'],
                         history=[dict(target_id='10:1', Overall=3, Text='History one.'),
                                  dict(target_id='20:2', Overall=4, Text='History two.'),
                                  dict(target_id='30:1', Overall=3, Text='History three.')])
        self.reason = ('There is insufficient evidence for a rater-specific tendency from history 10:1 (Overall 3) '
                       'and history 20:2 (Overall 4). The target has "A clear claim." and "Some supporting detail." '
                       'These features support Overall 3 under the rubric, with no reliable personal adjustment.')

    def output(self, **changes):
        return json.dumps(dict(predicted_overall=3, reasoning=self.reason, **changes))

    def test_insufficient_tendency_is_valid(self):
        _, errors, checks = validate(self.output(), self.item)
        self.assertEqual(errors, [])
        self.assertTrue(checks['insufficient_evidence_explicit'])

    def test_strict_schema_and_score(self):
        for value in (True, 3.0, 0, 6, '3'):
            _, errors, _ = validate(json.dumps(dict(predicted_overall=value, reasoning=self.reason)), self.item)
            self.assertIn('score_not_integer_1_to_5', errors)
        _, errors, _ = validate(self.output(rater_tendency='extra'), self.item)
        self.assertIn('expected_exactly_two_keys', errors)

    def test_unknown_history_id_and_wrong_recorded_score(self):
        raw = self.output().replace('10:1', '999:1').replace('Overall 4', 'Overall 2')
        _, errors, _ = validate(raw, self.item)
        self.assertIn('history_id_outside_input', errors)
        self.assertIn('incorrect_recorded_history_overall', errors)

    def test_invented_quote_is_detected(self):
        _, errors, _ = validate(self.output().replace('A clear claim.', 'A fabricated claim.'), self.item)
        self.assertIn('quotation_not_found_in_supplied_essays', errors)

    def test_proposed_correction_is_not_a_claimed_source_quotation(self):
        reason = self.reason + ' The writer used "A clear claim." instead of "A clearer claim."'
        _, errors, checks = validate(json.dumps(dict(predicted_overall=3, reasoning=reason)), self.item)
        self.assertEqual(errors, [])
        self.assertEqual(checks['explicitly_proposed_corrections'], [dict(observed='A clear claim.', proposed='A clearer claim.')])

    def test_invented_observed_phrase_cannot_pass_as_a_correction(self):
        reason = self.reason + ' It says "Invented source." instead of "A replacement."'
        _, errors, _ = validate(json.dumps(dict(predicted_overall=3, reasoning=reason)), self.item)
        self.assertIn('quotation_not_found_in_supplied_essays', errors)

    def test_render_accepts_only_safe_fields(self):
        template = '{overall_rubric}\n{rating_history}\n{target_essay}'
        self.assertEqual(render(template, rubric='R', history_text='H', essay='E'), 'R\nH\nE')
        with self.assertRaises(TypeError):
            render(template, rubric='R', history_text='H', essay='E', gold_overall=5)

    def test_interrupted_journal_preserves_completed_records_and_bad_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'attempts.jsonl'
            path.write_bytes(b'{"target_id":"10:1"}\n{"partial":')
            self.assertEqual(recover(path), [{'target_id': '10:1'}])
            self.assertEqual(path.read_bytes(), b'{"target_id":"10:1"}\n')
            archives = list(path.parent.glob('attempts.jsonl.partial-*'))
            self.assertEqual(len(archives), 1)
            self.assertEqual(archives[0].read_bytes(), b'{"partial":')

    def test_corrupt_middle_record_is_not_silently_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'attempts.jsonl'
            path.write_bytes(b'bad\n{}\n')
            with self.assertRaises(ValueError):
                recover(path)


if __name__ == '__main__':
    unittest.main()
