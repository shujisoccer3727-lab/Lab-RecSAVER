import unittest
from src.recsaver.rater_feedback_development import masked_reason,validate_ground,validate_integration,validate_text


class DevelopmentGuards(unittest.TestCase):
    def test_new_relation_fields_are_masked(self):
        r=dict(rationale='文の意味は追えるが文法に課題がある。Overall is 3',unexplained='文法は3',claims=[dict(
            claim_id='C1',scope='target',essay_id='1514:1',aspect='Grammar',judgment_type='presence',
            direction='negative',span_ids=['1514:1@U001'],feature='文法上の不一致',evaluation='Grammar: 3',
            overall_relation='Overallは3',trait_relation='Grammar.S3.C01',limits='頻度は不明')])
        safe,logs,residual=masked_reason(r)
        self.assertFalse(residual);self.assertGreaterEqual(len(logs),4)
        self.assertNotIn('Grammar.S3',str(safe));self.assertIn('1514:1@U001',str(safe))

    def test_partial_composite_cannot_pass(self):
        item=dict(target=dict(essay_id='1:1',spans=[dict(span_id='1:1@U001')]),history=[])
        claims=[dict(claim_id='C1',essay_id='1:1',span_ids=['1:1@U001'])]
        obj=dict(reviews=[dict(claim_id='C1',verdict='supported',atomic=False,
            feature_supported=True,evaluation_supported=False,added_span_ids=[],counter_span_ids=[])])
        with self.assertRaises(AssertionError): validate_ground(obj,claims,item)

    def test_two_candidates_are_not_two_essays(self):
        cm={'1:1/K1/C1':dict(target_id='1:1'),'1:1/K2/C1':dict(target_id='1:1')}
        obj=dict(common_features=[],judgment_patterns=[dict(support=[dict(target_id='1:1',claim_ids=[c]) for c in cm])])
        with self.assertRaises(AssertionError): validate_integration(obj,cm)

    def test_other_topic_claim_cannot_enter_sentence(self):
        p=dict(claims={'1:1/K1/C1':dict(target_id='1:1',evidence=[])},issues={'I':dict(claim_ids=['other'])},conditions={'G':{}})
        sentences=[dict(element=i,text='採点時の判断',claim_ids=['1:1/K1/C1'],issue_ids=['I'],condition_ids=['G']) for i in range(1,6)]
        with self.assertRaises(AssertionError): validate_text(dict(sentences=sentences),p)


if __name__=='__main__': unittest.main()
