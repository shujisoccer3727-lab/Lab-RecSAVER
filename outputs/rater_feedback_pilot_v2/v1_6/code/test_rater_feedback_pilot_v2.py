import copy
import unittest
from src.recsaver.rater_feedback_pilot_v2 import (
    units,mask_string,masked_reason,verification_payload,validate_reason,
    validate_integration,validate_comparison,Engine,condition_catalog,
)


class FeedbackV2Tests(unittest.TestCase):
    def setUp(self):
        self.item={'target_id':'17:2','target':{'essay_id':'17:2','text':'I agree. Three examples.','overall':3,'spans':units('I agree. Three examples.','17:2')},'history':[{'essay_id':'12:1','text':'There are 3 reasons.','overall':4,'traits':{'Grammar':2}}]}
        self.conditions={'Overall.S5.C01':{'condition_id':'Overall.S5.C01','text':'fully clear','aspect':'Overall','level':5}}
        self.claim=dict(claim_id='C1',scope='target',essay_id='17:2',aspect='Overall',kind='presence',feature='Example present',span_ids=['17:2@U002'],direction='positive',score_relation='supports evaluation',condition_ids=['Overall.S5.C01'],semantic_support='supported',support_explanation='Example present',limits='Not evidence of frequency')

    def test_scope_is_not_assumed_from_reference_existence(self):
        c=copy.deepcopy(self.claim);c['scope']='history'
        r=validate_reason({'rationale':'A reason','claims':[c]},self.item,self.conditions)
        self.assertFalse(r['claims'][0]['machine_check']['scope_valid'])

    def test_unknown_references_cannot_enter_evidence(self):
        c=copy.deepcopy(self.claim);c['span_ids']=['12:1@U001']
        r=validate_reason({'rationale':'A reason','claims':[c]},self.item,self.conditions)
        self.assertFalse(r['claims'][0]['machine_check']['span_ids_valid'])
        self.assertEqual(r['claims'][0]['evidence'],[])

    def test_actual_verifier_payload_does_not_disclose_target_scores(self):
        m,logs,residual=masked_reason({'rationale':'Overall is three. Has an example.', 'claims':[self.claim],'gold_overall':3,'traits':{'Grammar':2}})
        p=verification_payload(self.item,m,{'scores':{'1':{'Overall':'weak'},'5':{'Overall':'strong'}}})
        self.assertEqual(set(p['target']),{'essay_id','text'})
        self.assertEqual(p['history'][0]['overall'],4)
        self.assertNotIn('traits',p['history'][0])
        self.assertNotIn('condition_ids',p['masked_reason']['claims'][0])
        self.assertFalse(residual)
        self.assertEqual(p['history'][0]['text'],'There are 3 reasons.')

    def test_mask_quantities_and_ids_unchanged(self):
        text='3 examples, 5 students; 17:2@U003'
        self.assertEqual(mask_string(text,'test')[0],text)
        for x in ['three out of five','score was a three','3 points','第３段階','Overall.S3','a 3-point score','score of about three','総合評価は３','文法: 3']:
            self.assertTrue(mask_string(x,'test')[1],x)

    def test_array_explanations_preserved_and_masked(self):
        c=copy.deepcopy(self.claim)
        r={'rationale':'A reason','claims':[c],'unexplained':['score is three','Uncertain frequency']}
        result,logs,residual=masked_reason(r)
        self.assertIn('Uncertain frequency',result['unexplained'])
        self.assertNotIn('score is three',result['unexplained'])
        self.assertTrue(any(x['reason'].startswith('non-string') for x in logs))
        self.assertFalse(residual)

    def test_duplicate_candidates_are_one_essay(self):
        p={'pattern_id':'P1','support':[{'target_id':'17:2','claim_ids':['a']},{'target_id':'17:2','claim_ids':['b']}]}
        with self.assertRaises(AssertionError):
            validate_integration({'patterns':[p]},{'a':{'target_id':'17:2'},'b':{'target_id':'17:2'}},['17:2'])

    def test_condition_choice_can_be_nonadjacent(self):
        r=dict(issue_id='I1',claim_ids=['a'],span_ids=['17:2@U002'],condition_ids=['Overall.S5.C01'],feature_confirmed='example',inferred_judgment='positive',rubric_based_proposal='local evidence for clarity',agreement_review_unknown='global frequency unknown',scope_limit='local',system_checked=[{'span_ids':['17:2@U002'],'finding':'one example'}],next_action={'where_span_ids':['17:2@U002'],'distinguish':'presence vs adequacy','action':'check what the example supports','reason':'local sufficiency'})
        r['analysis_anchors']=[dict(span_id='17:2@U002',tokens=['Three','examples'],relation='count and noun',interpretation='three examples asserted')]
        result=validate_comparison({'relationships':[r]},self.item,{'a':{'target_id':'17:2'}},self.conditions)
        self.assertEqual(result['relationships'][0]['official_conditions'][0]['level'],5)
        self.assertEqual(result['relationships'][0]['citations'][0]['text'],'Three examples.')

    def test_filenames_portable(self):
        engine=object.__new__(Engine)
        from pathlib import Path
        engine.out=Path('outputs')
        name=engine.path('generate','A|17:2|K1').name
        self.assertFalse(any(c in name for c in '<>:"/\\|?*'))


if __name__=='__main__':
    unittest.main()
