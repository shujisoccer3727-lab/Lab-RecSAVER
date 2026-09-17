import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from src.recsaver.reference_audit import leakage_audit, score_disclosures, quality_warnings
from src.recsaver.reasoning_eval_v1 import generate, recover_log, request_seed, verification_prompt


class FakeTokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return list(range(len(messages[0]['content'].split())))


class FakeGenerator:
    tokenizer = FakeTokenizer()

    def __init__(self):
        self.calls = 0

    def generate(self, jobs, parameters):
        self.calls += len(jobs)
        if parameters['max_tokens'] == 384:
            return [json.dumps({'reasoning': 'Overall 3' if j['attempt_index'] == 1 or j['candidate_index'] == 3
                                else 'The organization is uneven but the argument is understandable.'}) for j in jobs]
        return ['not JSON' if j['attempt_index'] == 1 else '{"predicted_overall": 3}' for j in jobs]


class ReasoningV1Tests(unittest.TestCase):
    def test_score_context_and_non_score_numbers(self):
        for text in ['Overall 3', 'score 3', 'rating 3', 'rated 3', '3 out of 5', 'level 3',
                     'The Overall score is 3', 'This essay deserves a score of 3', 'Overall: 3',
                     'score three', 'rated a three', '3/5', '3', 'The essay merits a three',
                     '{"predicted_overall": 3}', '{"overall_score": "3"}']:
            self.assertTrue(score_disclosures(text, 3), text)
        for text in ['The essay gives 3 examples.', 'In History 3, the writer discusses school.',
                     'The essay mentions 3 years of schooling.', 'The writer makes three arguments.']:
            self.assertFalse(score_disclosures(text, 3), text)
        self.assertFalse(leakage_audit('score 4', '', 3)['leaked'])
        self.assertTrue(leakage_audit('score 4', '', 3)['other_score_disclosure'])
        self.assertTrue(quality_warnings('The rater has teaching experience.'))
        self.assertTrue(quality_warnings("The rater's background explains the evaluation."))
        self.assertFalse(quality_warnings('The essay discusses the background of a story.'))

    def test_retry_exhaustion_parse_retry_resume_and_gold_separation(self):
        config = {'seed': 123, 'num_reference_candidates': 3, 'max_reference_retries': 5,
                  'max_verification_parse_retries': 1, 'batch_size': 10, 'model': {'max_model_len': 8192},
                  'generation': {'reference': {'max_tokens': 384}, 'verification': {'max_tokens': 64}}}
        item = dict(target_id='test:1', target_rater='rater', gold_overall=3, history_ids=['a', 'b', 'c'],
                    rubric='rubric', history_text='history', essay='essay', reference_prompt='conditioned input', reference_prompt_tokens=4)
        template = '{overall_rubric} {rating_history} {target_essay} {reference_reasoning}'
        self.assertEqual(verification_prompt(template, item, 'rationale'), 'rubric history essay rationale')
        other_gold = dict(item, gold_overall=5)
        self.assertEqual(verification_prompt(template, item, 'rationale'), verification_prompt(template, other_gold, 'rationale'))
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory); (out / 'metadata.json').write_text('{}')
            fake = FakeGenerator(); generate(config, [item], template, out, generator=fake)
            refs = recover_log(out / 'reference_candidates.jsonl')
            self.assertEqual(len(refs), 9)  # slots 1/2: two each; exhausted slot 3: five
            self.assertEqual(sum(r['accepted_as_leakage_free'] for r in refs), 2)
            self.assertEqual(len(recover_log(out / 'self_verification_results.jsonl')), 4)
            self.assertEqual(len(recover_log(out / 'verified_reference_pool.jsonl')), 2)
            calls = fake.calls; generate(config, [item], template, out, generator=fake)
            self.assertEqual(fake.calls, calls)
            self.assertEqual(len(recover_log(out / 'reference_candidates.jsonl')), 9)
            self.assertEqual(json.loads((out / 'metadata.json').read_text())['status'], 'generation_completed')
        self.assertNotEqual(request_seed(config, 'reference', 'test:1', 1, 1), request_seed(config, 'reference', 'test:1', 2, 1))

    def test_partial_tail_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'journal.jsonl'
            path.write_bytes(b'{"done": 1}\n{"unfinished":')
            self.assertEqual(recover_log(path), [{'done': 1}])
            self.assertEqual(len(list(Path(directory).glob('*.partial-*'))), 1)
            self.assertEqual(recover_log(path), [{'done': 1}])
            path.write_bytes(b'invalid\n{"done":1}\n')
            with self.assertRaises(ValueError):
                recover_log(path)

    def test_metric_aggregation_and_uncovered_targets(self):
        from src.recsaver.reasoning_eval_metrics import evaluate, METRICS
        from src.recsaver.utils import write_jsonl
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            config = {'_root': directory, 'output_dir': directory, 'source_predictions': str(out / 'source.jsonl')}
            pd.DataFrame([{'target_id':'a', 'completed':True}, {'target_id':'b', 'completed':True}]).to_csv(out / 'target_reference_summary.csv', index=False)
            write_jsonl(out / 'source.jsonl', [dict(target_id=t, condition='raw_k3_with_rubric', rater_id='r',
                        gold_overall=3, predicted_overall=p, exact_correct=p == 3, absolute_error=abs(p-3), prediction_reasoning='text')
                        for t,p in [('a',3), ('b',2)]])
            write_jsonl(out / 'verified_reference_pool.jsonl', [dict(target_id='a', candidate_index=i, reference_reasoning='identical reference') for i in [1,2]])
            with patch('src.recsaver.reasoning_eval_metrics.MetricEngine') as engine:
                engine.return_value.metadata = {}
                engine.return_value.score.return_value = [{m:v for m in METRICS} for v in [.2,.8]]
                evaluate(config)
            rows = pd.read_csv(out / 'reasoning_metrics_by_target.csv').set_index('target_id')
            self.assertEqual(rows.loc['a','bleu_mean'], .5)
            self.assertEqual(rows.loc['a','bleu_max'], .8)
            self.assertEqual(rows.loc['b','verified_reference_count'], 0)
            self.assertTrue(pd.isna(rows.loc['b','bleu_mean']))
            aggregate = pd.read_csv(out / 'reasoning_metrics_summary.csv')
            self.assertTrue(aggregate.n.eq(1).all())
            diversity = pd.read_csv(out / 'reference_diversity.csv')
            self.assertEqual(len(diversity), 1)
            self.assertTrue(diversity.exact_duplicate.iloc[0])


if __name__ == '__main__':
    unittest.main()
