import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

from src.recsaver.data import TRAITS
from src.recsaver.history import format_history
from src.recsaver.full_prediction_experiment import append_jsonl, atomic_json, sha
from src.recsaver.full_history_only_experiment import (
    CONDITION, REFERENCE, PREDICTIONS, render_raw, validate_row, run, wait_for_gpu,
)
from src.recsaver.full_history_only_analysis import analyze, bootstrap


class FakeTokenizer:
    def encode(self, text, **kwargs):
        return list(text)


class FakeGenerator:
    def __init__(self, config):
        self.tokenizer = FakeTokenizer()
        self.calls = []

    def generate(self, jobs, parameters):
        self.calls.extend(j['target_id'] for j in jobs)
        return ['invalid' if j['target_id']=='0' else '{"predicted_overall":3,"reasoning":"test"}' for j in jobs]


class HistoryOnlyTests(unittest.TestCase):
    def setUp(self):
        self.target = pd.Series(dict(target_id='0',source_row_id=0,rater_id='a',Text='target',Overall=4,
                                     **{t:4 for t in TRAITS}))
        self.history = pd.DataFrame([dict(target_id=str(i),source_row_id=i,rater_id='a',Text=f'essay {i}',Overall=i,
                                          **{t:i for t in TRAITS}) for i in range(1,4)])
        self.row = dict(target_id='0',source_row_id=0,target_rater='a',gold_overall=4,
                        correct_history_ids=['1','2','3'],condition_available={REFERENCE:True})
        self.template = '{overall_rubric}\n{rating_history}\n{target_essay}'
        self.saved = dict(target_id='0',source_row_id=0,rater_id='a',gold_overall=4,condition=REFERENCE,
            history_ids=['1','2','3'],history_rater_ids=['a']*3,K=3,context_fit=True,
            prompt=self.template.format(overall_rubric='rubric',rating_history=format_history(self.history),target_essay='target'))

    def test_saved_prompt_detects_changed_trait_text_and_order(self):
        validate_row(self.row,self.saved,self.target,self.history,self.template,'rubric')
        for column,value in [('Overall',5),(TRAITS[0],5),('Text','changed')]:
            changed = self.history.copy()
            changed.loc[0,column] = value
            with self.assertRaisesRegex(ValueError,'Saved prompt'):
                validate_row(self.row,self.saved,self.target,changed,self.template,'rubric')
        with self.assertRaisesRegex(ValueError,'IDs/order'):
            validate_row(self.row,self.saved,self.target,self.history.iloc[::-1],self.template,'rubric')

    def test_same_source_and_text_leakage_rejected(self):
        for column,value in [('source_row_id',0),('Text','target')]:
            changed = self.history.copy()
            changed.loc[0,column] = value
            with self.assertRaisesRegex(ValueError,'leakage'):
                validate_row(self.row,self.saved,self.target,changed,self.template,'rubric')

    def test_target_scores_do_not_enter_prompt(self):
        altered = self.target.copy()
        for trait in ['Overall',*TRAITS]:
            altered[trait] = 999
        self.assertEqual(render_raw('{history}\n{target_essay}',self.target,self.history),
                         render_raw('{history}\n{target_essay}',altered,self.history))

    def test_retry_tail_recovery_skip_and_changed_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            atomic_json(out/'metadata.json',{})
            config = dict(batch_size=2,generation={},generation_seed=17,max_parse_retries=1)
            jobs = []
            for i in range(3):
                target = self.target.copy()
                target.target_id = str(i)
                jobs.append(dict(target_id=str(i),target=target,history=self.history,prompt=f'prompt{i}',prompt_tokens=12))
            generator = FakeGenerator(config)
            with patch('src.recsaver.full_history_only_experiment.SeededGenerator',return_value=generator), \
                 patch('src.recsaver.full_history_only_analysis.analyze'):
                run(config,out,jobs[:2])
                self.assertEqual(generator.calls,['0','1','0'])
                with (out/PREDICTIONS).open('ab') as stream:
                    stream.write(b'{"partial":')
                run(config,out,jobs)
                self.assertEqual(generator.calls,['0','1','0','2'])
                run(config,out,jobs)
                self.assertEqual(generator.calls,['0','1','0','2'])
                changed = copy.deepcopy(jobs)
                changed[0]['prompt'] = 'changed'
                with self.assertRaisesRegex(ValueError,'Resume record'):
                    run(config,out,changed)
            status = json.loads((out/'progress.json').read_text())
            self.assertEqual(status['completed_targets'],3)
            self.assertEqual(status['parse_errors'],1)

    def test_analysis_common_intersection_and_reference_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source,out = root/'source',root/'out'
            source.mkdir();out.mkdir()
            config = dict(_root=directory,output_dir='out',target_source='source',history_assignment_source='source',
                          bootstrap_seed=1,bootstrap_repetitions=20,model={},generation={},generation_seed=2)
            manifest = [dict(target_id=str(i),source_row_id=i//2,target_rater=str(i%2),gold_overall=1+i%5) for i in range(10)]
            for row in manifest:
                append_jsonl(source/'target_manifest.jsonl',row)
            for condition,path in [('k0',source/'predictions_k0.jsonl'),(REFERENCE,source/'predictions_correct_k3_rubric.jsonl'),(CONDITION,out/PREDICTIONS)]:
                for i,target in enumerate(manifest):
                    pred = None if (condition=='k0' and i==0) or (condition==CONDITION and i==1) else 3
                    append_jsonl(path,dict(target_id=target['target_id'],source_row_id=target['source_row_id'],rater_id=target['target_rater'],
                        condition=condition,gold_overall=target['gold_overall'],predicted_overall=pred,parse_success=pred is not None,
                        retry_count=0,context_fit=True,prompt_tokens=100,inference_time_seconds=1))
            hashes = {p.name:sha(p) for p in source.iterdir()}
            atomic_json(out/'metadata.json',{'reference_file_sha256':hashes})
            pd.DataFrame([dict(item='target_count',count=10)]).to_csv(out/'dataset_audit.csv',index=False)
            analyze(config)
            summary = pd.read_csv(out/'comparison_summary.csv')
            self.assertEqual(summary.n.tolist(),[8,8,8])
            self.assertEqual(hashes,{p.name:sha(p) for p in source.iterdir()})
            ci = pd.read_csv(out/'bootstrap_ci.csv')
            self.assertEqual(len(ci),8)
            self.assertTrue(ci.point_estimate.eq(0).all())
            self.assertEqual(json.loads((out/'metadata.json').read_text())['status'],'completed')

    def test_gpu_wait_preserves_other_jobs(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            config = {'model':{'gpu_memory_utilization':.9}}
            responses = [SimpleNamespace(stdout=s) for s in ['49000,12000','1234','49000,500','']]
            with patch('src.recsaver.full_history_only_experiment.subprocess.run',side_effect=responses), \
                 patch('src.recsaver.full_history_only_experiment.time.sleep') as sleep:
                wait_for_gpu(config,out)
                sleep.assert_called_once_with(60)
            status = json.loads((out/'progress.json').read_text())
            self.assertEqual(status['status'],'waiting_for_gpu')
            self.assertEqual(status['completed_targets'],0)


if __name__ == '__main__':
    unittest.main()
