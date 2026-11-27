"""Input isolation, score masking, strict parsing, provenance and sampling regressions."""
import copy
import unittest
from src.recsaver.pair_feedback import strict_json, spans, rank, number, inspect_mask
from src.recsaver.pair_feedback_masking import mask_analysis
from src.recsaver.pair_feedback_contracts import gate_a, review_and_render


class PairFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.history = [dict(essay_id='H' + str(i), text='3 is printed here.', Overall=3,
                             Traits={'Grammar': 2}) for i in range(3)]
        self.target = dict(essay_id='T', text='3 reasons. I is ready.', Overall=2, Traits={'Grammar': 2})

    def mask(self, analysis):
        original = copy.deepcopy(analysis)
        result = mask_analysis(analysis, self.history, self.target)
        self.assertEqual(analysis, original)
        self.assertTrue(result['audit']['value_only_invariant'])
        return result

    def test_value_units_and_non_score_numbers(self):
        v = self.mask(dict(decision_explanation='There are 3 paragraphs. Overall score is three; Syntax levels 2 or 4.'))
        self.assertEqual(v['masked_analysis']['decision_explanation'],
                         'There are 3 paragraphs. Overall score is [MASK]; Syntax levels [MASK] or [MASK].')
        self.assertEqual(v['audit']['value_replacements'], 3)

    def test_numeric_fields_and_string_fields(self):
        v = self.mask(dict(Overall=3, Grammar='two'))
        self.assertEqual(v['masked_analysis'], dict(Overall='[MASK]', Grammar='[MASK]'))

    def test_quotes_ids_and_history_scores_preserved(self):
        a = dict(history_patterns=[dict(pattern_id='H1', pattern='The history received Overall score 3.',
                   support=[dict(history_essay_id='H0', quotes=['3 is printed here.'],
                                 relevant_observed_history_scores={'Overall': 3}, interpretation='Overall score 3.')], counterevidence=[])],
                 target_evidence=[dict(evidence_id='T1', quotes=['3 reasons.'], observable_feature='3 reasons are named.')])
        self.assertEqual(self.mask(a)['masked_analysis'], a)

    def test_recoverable_relations_and_unknown_attribution(self):
        for text in ['The target received the same Overall score as history essay H0.',
                     'The target Overall is 2 + 1.', 'The target fits the highest band.',
                     'The target has the same rating as H0.', 'It received three for Overall.',
                     'The essay shows native-like facility in language use.',
                     'It is unclear whether the score of three refers to target or history.']:
            with self.subTest(text=text):
                self.assertFalse(self.mask(dict(decision_explanation=text))['audit']['automatic_pass'])

    def test_self_or_unknown_history(self):
        for eid in ['T', 'not-supplied']:
            v = self.mask(dict(history_patterns=[dict(support=[dict(history_essay_id=eid)], counterevidence=[])]))
            self.assertFalse(v['audit']['automatic_pass'])

    def test_history_mixed_with_target(self):
        text = 'History essay H0 received an Overall score of 3 but the target Overall score is four.'
        self.assertEqual(self.mask(dict(decision_explanation=text))['masked_analysis']['decision_explanation'],
                         'History essay H0 received an Overall score of 3 but the target Overall score is [MASK].')

    def test_mask_is_valid_analysis_string(self):
        self.assertEqual(strict_json('{"reference_analysis":{"Overall":"[MASK]"}}')['reference_analysis']['Overall'], '[MASK]')
        for raw in ['```json\n{}\n```', '{} trailing', '{"x":1,"x":2}', '{"x":NaN}', '[]']:
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_input_order_independent_sampling(self):
        cfg = {'seed': 20261126}
        values = ['C', 'A', 'B']
        self.assertEqual(sorted(values, key=lambda e: rank(cfg, 'history', 'r', e)),
                         sorted(reversed(values), key=lambda e: rank(cfg, 'history', 'r', e)))
        self.assertIsNone(number(True))
        self.assertIsNone(number(''))
        self.assertIsNone(number(0))

    def test_source_offsets_and_score_free_stage4(self):
        text = 'First sentence.\r\n\r\nI is ready.'
        catalog = spans(text)
        for s in catalog:
            self.assertEqual(text[s['start']:s['end']], s['text'])
        payload = dict(target_essay_id='T', target_text=text, evidence_spans=catalog, dimension_names=['Grammar'])
        obs = dict(observation_id='O1', dimension='Grammar', evidence_span_ids=[catalog[-1]['span_id']],
                   feature='A subject and verb do not agree.', scoring_relevance='Agreement.', limitation='Local.', next_check='Check other verbs.')
        v = dict(schema_version='1.5', target_essay_id='T', observations=[obs], insufficient_evidence=[])
        gate = gate_a(v, payload)
        self.assertEqual(gate['passed_observations'][0]['quotes'], ['I is ready.'])
        obs['evidence_span_ids'] = ['unknown']
        self.assertFalse(gate_a(v, payload)['passed_observations'])

    def test_single_essay_cannot_support_pattern(self):
        o = dict(observation_key='T::O1', target_essay_id='T', quotes=['I is ready.'], dimension='Grammar', observed_score=2)
        payload = dict(rater_id='r', verified_observations=[o], accepted_target_ids=['T'],
                       rubric_entries=[dict(rubric_ref_id='Grammar:2', dimension='Grammar', score_band=2, descriptor='Many errors.')])
        v = dict(schema_version='1.5', rater_id='r', pattern_status='supported',
                 pattern=dict(statement='A pattern.', support=[dict(observation_key='T::O1', supports_how='One case.')]),
                 pattern_limit='', representative_observation_key='T::O1', quote_indices=[0], textual_finding='An agreement error.',
                 evidence_limit='One example.', rubric_review=dict(observed_band_ref_id='Grammar:2', comparison_band_ref_id=None, band_assessment='indeterminate'),
                 next_check=dict(inspect='Other sentences', distinguish='Agreement', reconsider_if=None))
        self.assertFalse(review_and_render(v, payload)['pass_'])


if __name__ == '__main__':
    unittest.main()
