"""Analysis checks without any new model generations."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.recsaver.boundary_aware_history import analyze
from src.recsaver.config import load_config, project_path


class BoundaryAnalysisTests(unittest.TestCase):
    def test_completed_run_integrity(self):
        config = load_config('configs/boundary_aware_history.yaml')
        out = project_path(config, config['output_dir'])
        metadata = out / 'metadata.json'
        if not metadata.exists():
            self.skipTest('No saved run')
        md = json.loads(metadata.read_text(encoding='utf-8'))
        if md['status'] != 'completed':
            self.skipTest('Run is not complete')
        source = project_path(config, config['source_predictions'])
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), md['source_predictions_sha256'])
        for key in ['rubric', 'existing_prompt', 'boundary_prompt']:
            path = project_path(config, md[key + '_path'])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), md[key + '_sha256'])
        self.assertEqual(hashlib.sha256(project_path(config, 'src/recsaver/parsing.py').read_bytes()).hexdigest(), md['parser_sha256'])
        old = {r['target_id']: r for r in map(json.loads, source.read_text(encoding='utf-8').splitlines()) if r['condition'] == 'raw_k3_with_rubric'}
        records = list(map(json.loads, (out / 'boundary_aware_predictions.jsonl').read_text(encoding='utf-8').splitlines()))
        self.assertEqual(len(records), 100)
        self.assertEqual([r['target_id'] for r in records], md['target_ids'])
        for r in records:
            baseline = old[r['target_id']]
            self.assertEqual(r['history_ids'], baseline['history_ids'])
            self.assertEqual(r['history_rater_ids'], [r['rater_id']] * 3)
            self.assertEqual(r['gold_overall'], baseline['gold_overall'])
            marker = '[Official Overall Scoring Rubric]'
            self.assertEqual(r['prompt'].split(marker, 1)[1], baseline['prompt'].split(marker, 1)[1])
            self.assertEqual(len(r['raw_model_output_attempts']), 1)
            self.assertEqual(r['retry_count'], 0)
            self.assertLessEqual(r['prompt_tokens'] + 384, 8192)
        self.assertEqual(md['parse_errors'], sum(not r['parse_success'] for r in records))
        for name in ['boundary_aware_summary.csv', 'paired_comparison.csv', 'prediction_distribution.csv',
                     'score_collapse_summary.csv', 'score_transitions.csv', 'rater_summary.csv',
                     'reasoning_examples.json', 'reasoning_usage_summary.csv', 'resolved_config.yaml', 'report.md']:
            self.assertTrue((out / name).exists(), name)

    def test_reused_baseline_identity_and_directed_transitions(self):
        config = load_config('configs/boundary_aware_history.yaml')
        source = project_path(config, config['source_predictions'])
        rows = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines()]
        baseline = [dict(r, condition=config['baseline_condition']) for r in rows if r['condition'] == 'raw_k3_with_rubric']
        same = [dict(r, condition=config['new_condition']) for r in baseline]
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            summary = analyze(config, baseline, same, out)
            self.assertEqual(summary.n.tolist(), [100, 100])
            self.assertEqual(summary.exact_accuracy.tolist(), [.56, .56])
            self.assertEqual(summary.mae.tolist(), [.48, .48])
            pair = pd.read_csv(out / 'paired_comparison.csv').iloc[0]
            self.assertEqual(pair.unchanged_targets, 100)
            self.assertEqual(pair.mean_ae_difference, 0)
            self.assertTrue(pd.read_csv(out / 'score_transitions.csv').empty)
        # Exercise a known move toward gold and one away, independent of model output.
        original, changed = [], []
        for i, gold in enumerate([2, 2]):
            base = dict(baseline[i], target_id=f'test:{i}', gold_overall=gold,
                        predicted_overall=3, exact_correct=False, absolute_error=1, squared_error=1)
            pred = [2, 4][i]
            original.append(base)
            changed.append(dict(base, condition=config['new_condition'], predicted_overall=pred,
                                exact_correct=pred == gold, absolute_error=abs(pred-gold), squared_error=(pred-gold)**2))
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            analyze(config, original, changed, out)
            result = pd.read_csv(out / 'score_transition_summary.csv').set_index('transition')
            self.assertEqual(result.loc['3 -> 2', 'toward_gold'], 1)
            self.assertEqual(result.loc['3 -> 4', 'away_from_gold'], 1)
            pair = pd.read_csv(out / 'paired_comparison.csv').iloc[0]
            self.assertEqual(pair.improved_targets, 1)
            self.assertEqual(pair.worsened_targets, 1)


if __name__ == '__main__':
    unittest.main()
