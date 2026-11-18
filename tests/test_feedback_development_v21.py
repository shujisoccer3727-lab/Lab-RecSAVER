import copy
import re
import unittest
import jsonschema
from src.recsaver.rater_feedback_development_v21 import masked_reason,DIRECT_SCORE_PATTERN,ROOT,load
from src.recsaver.feedback_development_schema_v21 import output_schema


class ObservedRegressionTests(unittest.TestCase):
    def test_observed_unseparated_score_leak_removed_from_all_prose(self):
        original=load(ROOT/'outputs/rater_feedback_pilot_v2/v2_0/stages/generate/B__1514_1__K1.json')['result']
        safe,logs,residual=masked_reason(original)
        self.assertFalse(residual)
        self.assertTrue(any(l['original']=='評価3' for l in logs))
        for text in [safe['rationale'],safe['unexplained']]+[c[k] for c in safe['claims'] for k in ['feature','evaluation','overall_relation','trait_relation','limits']]:
            self.assertIsNone(re.search(DIRECT_SCORE_PATTERN,text,re.I))
        self.assertEqual(original['claims'][0]['span_ids'],safe['claims'][0]['span_ids'])

    def test_optional_separator_does_not_remove_essay_quantities(self):
        original=copy.deepcopy(load(ROOT/'outputs/rater_feedback_pilot_v2/v2_0/stages/generate/B__1514_1__K1.json')['result'])
        original['rationale']='評価３、Overall 3、文法は三。一方、policy 1と3例と10 yearsは本文の数量。'
        safe,_,rest=masked_reason(original)
        self.assertFalse(rest)
        self.assertNotIn('評価３',safe['rationale']);self.assertNotIn('文法は三',safe['rationale'])
        for quantity in ['policy 1','3例','10 years']: self.assertIn(quantity,safe['rationale'])

    def test_single_essay_cannot_claim_commonality_even_with_two_candidates(self):
        p=dict(essays=[dict(target_id='1514:1',eligible_claims=[dict(id='1514:1/K1/C1'),dict(id='1514:1/K2/C1')])])
        schema=output_schema('integrate',p)
        jsonschema.validate(dict(common_features=[],judgment_patterns=[],unknowns='one essay only'),schema)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(dict(common_features=['duplicate support'],judgment_patterns=[],unknowns=''),schema)


if __name__=='__main__':unittest.main()
