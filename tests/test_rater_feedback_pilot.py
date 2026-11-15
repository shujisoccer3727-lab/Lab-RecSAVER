"""引用一致と意味的支持を独立に検査し、不適格証拠の段階間混入を防ぐ。"""
import unittest
import tempfile
import json
from pathlib import Path
from src.recsaver.rater_feedback_pilot import locate, validate_a, validate_b, validate_c, apply_review, audit_synthesis, review_synthesis, Runner


class EvidenceTests(unittest.TestCase):
    def claim(self, **changes):
        c = dict(rationale_claim='frequent errors', scope='target', feature='grammar', direction='negative',
                 quotes=['A bad sentence.'], semantic_support='supported', semantic_explanation='provisional',
                 overall_relation='negative', limitations='global frequency not established')
        c.update(changes)
        return c

    def audit(self, **changes):
        return validate_a({'claims':[self.claim(**changes)]},
                          dict(target_id='1:2', target_text='A bad sentence.\nA bad sentence.', reference_reasoning='There are frequent errors.'))['claims'][0]

    def test_exact_offsets_and_repeated_occurrences(self):
        self.assertEqual(locate('a\r\nb a', 'a'), [dict(start=0,end=1,line_start=1,line_end=1),dict(start=5,end=6,line_start=2,line_end=2)])

    def test_absent_quote_excluded(self):
        c=self.audit(quotes=['Invented quotation'])
        self.assertFalse(c['usable_for_synthesis'])
        self.assertEqual(c['semantic_support'], 'supported')

    def test_uncertain_semantics_not_rescued_by_exact_quote(self):
        c=self.audit(semantic_support='uncertain')
        self.assertTrue(c['quotes_verified'])
        self.assertFalse(c['usable_for_synthesis'])

    def test_history_never_target_support(self):
        self.assertFalse(self.audit(scope='history')['usable_for_synthesis'])

    def test_invented_rationale_claim_excluded(self):
        self.assertFalse(self.audit(rationale_claim='invented')['usable_for_synthesis'])

    def test_multiple_candidates_one_target_do_not_establish_pattern(self):
        e=self.audit()
        obj={'patterns':[dict(pattern_id='P1',support_evidence_ids=['a','b'],counterexample_evidence_ids=[],non_applicable_target_ids=[],inferred_tendency='x',evaluation_score_relation='x',unknowns='x')], 'undetermined':'', 'cross_essay_review':''}
        with self.assertRaises(AssertionError):
            validate_b(obj, {'a':e,'b':dict(e)}, ['1:2'])

    def test_review_downgrade_excludes_and_preserves_model_label(self):
        c=self.audit()
        rows=apply_review([{'claims':[c]}],{'reviewer':'test', 'overrides':{'1:2.E1':{'semantic_support':'uncertain','reason':'scope insufficient'}}})
        reviewed=rows[0]['claims'][0]
        self.assertEqual(reviewed['model_semantic_support'],'supported')
        self.assertFalse(reviewed['usable_for_synthesis'])

    def test_review_cannot_promote_uncertain_evidence(self):
        with self.assertRaises(AssertionError):
            apply_review([{'claims':[self.audit(semantic_support='uncertain')]}],{'reviewer':'test', 'overrides':{'1:2.E1':{'semantic_support':'supported','reason':'unsupported promotion'}}})

    def test_missing_evidence_is_unassessed_not_nonapplicable(self):
        b={'patterns':[{'non_applicable_target_ids':['1:2','2:1']}]}
        result=audit_synthesis(b,{'e':self.audit()})['patterns'][0]
        self.assertEqual(result['non_applicable_target_ids'],['1:2'])
        self.assertEqual(result['unassessed_target_ids'],['2:1'])
        self.assertEqual(result['model_non_applicable_target_ids'],['1:2','2:1'])

    def test_structured_C_keeps_actual_scores_and_exact_quotes(self):
        c1=self.audit()
        c2=dict(c1,evidence_id='2:1.E1',target_id='2:1')
        evidence={c1['evidence_id']:c1,c2['evidence_id']:c2}
        b={'patterns':[dict(pattern_id='P1',support_evidence_ids=list(evidence),model_inferred_tendency_before_review='BAD_RULE')],
           'reviewed_for_unsupported_scoring_rules':True,'undetermined':'未確定','cross_essay_review':'不明'}
        rubric={f'Overall.S{s}':f'Official level {s}; complete frequency condition.' for s in [2,3,4]}
        def fake_call(stage,key,payload,validator):
            if stage=='C_text':
                self.assertNotIn('BAD_RULE',json.dumps(payload))
            fields=(['evidence_to_condition','judgment_to_condition','interpretation_or_missing_evidence','next_check']
                    if stage=='C_relation' else ['tendency_feedback','scope_note','relationship_feedback','next_check_feedback','limits'])
            return validator({k:'証拠の範囲を確認し、判断を保留する。' for k in fields})
        with tempfile.TemporaryDirectory() as directory:
            runner=Runner({},Path(directory),{'model':{'max_model_len':8192}})
            runner.call=fake_call
            result=runner.structured_c('test',{'observed_scores':{'1:2':2,'2:1':4}},evidence,b,rubric)
        self.assertEqual([r['observed_overall'] for r in result['relations']],[2,4])
        self.assertEqual([r['rubric_id'] for r in result['relations']],['Overall.S2','Overall.S4'])
        self.assertEqual(result['citations'][0]['quote'],'A bad sentence.')
        self.assertEqual([e['number'] for e in result['elements']],[1,2,3,4,5])

    def test_unsupported_rule_review_preserves_raw_but_excludes_rule(self):
        b={'patterns':[{'pattern_id':'P1','inferred_tendency':'bad score cap'}],'cross_essay_review':'bad rule'}
        review={'raters':{'r':{'reason':'unsupported','patterns':{'P1':{'inferred_tendency':'tentative feature pattern'}},'cross_essay_review':'unknown'}}}
        result=review_synthesis(b,'r',review)
        self.assertEqual(result['patterns'][0]['inferred_tendency'],'tentative feature pattern')
        self.assertEqual(result['patterns'][0]['model_inferred_tendency_before_review'],'bad score cap')


if __name__ == '__main__':
    unittest.main()
