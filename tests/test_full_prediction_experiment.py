import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.recsaver.full_prediction_analysis import qwk
from src.recsaver.full_prediction_experiment import (
    generation_seed, recover_jsonl, sample_correct, sample_wrong,
)
from src.recsaver.phase4_analysis import quadratic_weighted_kappa


class FullPredictionTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {'target_id':f'{source}:{position}', 'source_row_id':source, 'rater_id':rater}
            for source, position, rater in [(1,1,'a'),(1,2,'b'),(2,1,'a'),(3,1,'a'),(4,1,'a'),
                                             (2,2,'b'),(3,2,'b'),(4,2,'b'),(5,1,'c'),(6,1,'c'),(7,1,'c')]
        ])
        self.groups = {r:g for r,g in self.frame.groupby('rater_id')}

    def test_history_is_deterministic_single_rater_and_source_safe(self):
        target = self.frame.iloc[0]
        first = sample_correct(self.groups,target,3,20260814)
        second = sample_correct(self.groups,target,3,20260814)
        self.assertEqual(first.target_id.tolist(),second.target_id.tolist())
        self.assertEqual(len(first),3)
        self.assertTrue(first.rater_id.eq('a').all())
        self.assertNotIn(1,set(first.source_row_id))
        wrong_rater,wrong = sample_wrong(self.groups,target,3,20260906)
        self.assertNotEqual(wrong_rater,'a')
        self.assertEqual(wrong.rater_id.nunique(),1)
        self.assertNotIn(1,set(wrong.source_row_id))

    def test_generation_seed_is_stable_and_condition_specific(self):
        config={'generation_seed':20260814}
        seed=generation_seed(config,'k0','1:1',1)
        self.assertEqual(seed,generation_seed(config,'k0','1:1',1))
        self.assertNotEqual(seed,generation_seed(config,'k0_overall_rubric','1:1',1))
        self.assertNotEqual(seed,generation_seed(config,'k0','1:1',2))

    def test_fast_qwk_matches_existing_implementation(self):
        gold=[2,3,3,4,5,2];pred=[2,3,4,3,4,2]
        self.assertAlmostEqual(qwk(gold,pred),quadratic_weighted_kappa(gold,pred))

    def test_tail_recovery_preserves_complete_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'rows.jsonl';path.write_bytes(b'{"a":1}\n{"b":')
            self.assertEqual(recover_jsonl(path),[{'a':1}])
            self.assertEqual(len(list(Path(directory).glob('*.partial-*'))),1)


if __name__=='__main__':
    unittest.main()
