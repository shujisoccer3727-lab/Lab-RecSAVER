import unittest
from src.recsaver.feedback_output_schema import output_schema
try:
    import jsonschema
except ImportError:
    jsonschema=None


@unittest.skipIf(jsonschema is None,'jsonschema is not installed in this CPU environment')
class OutputSchemaTests(unittest.TestCase):
    def test_merge_unknowns_array_rejected(self):
        schema=output_schema('merge',{'claims':[{'id':'a'}]})
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'groups':[],'differences':[],'unknowns':[]},schema)
        jsonschema.validate({'groups':[],'differences':[],'unknowns':''},schema)

    def test_comparison_requires_named_object(self):
        schema=output_schema('compare',{'target_spans':[{'span_id':'s1'}],'eligible_claims':[{'id':'a'}],'condition_catalog':{'Overall.S3.C01':{}}})
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate([],schema)
        jsonschema.validate({'relationships':[]},schema)

    def test_comparison_rejects_singular_reference_field(self):
        schema=output_schema('compare',{'target_spans':[{'span_id':'s1'}],'eligible_claims':[{'id':'a'}],'condition_catalog':{'Overall.S3.C01':{}}})
        relation=dict(issue_id='I1',claim_ids=['a'],span_ids=['s1'],condition_ids=['Overall.S3.C01'],feature_confirmed='x',inferred_judgment='x',rubric_based_proposal='x',agreement_review_unknown='x',system_checked=[{'span_id':'s1','finding':'x'}],next_action=dict(distinguish='x',where_span_ids=['s1'],action='x',reason='x'),scope_limit='local')
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'relationships':[relation]},schema)
        relation['system_checked']=[{'span_ids':['s1'],'finding':'x'}]
        jsonschema.validate({'relationships':[relation]},schema)
        relation['condition_ids']=['made-up criterion']
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'relationships':[relation]},schema)

    def test_one_support_is_not_common_pattern(self):
        schema=output_schema('integrate',{'essays':[{'target_id':'t1','eligible_claims':[{'id':'a'}]},{'target_id':'t2','eligible_claims':[{'id':'b'}]}]})
        pattern=dict(pattern_id='P1',feature_context='x',repeated_judgment='x',inferred_tendency='x',support=[{'target_id':'t1','claim_ids':['a']}],counterexamples=[],non_applicable=[],insufficient_target_ids=['t2'],limits='x')
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate({'patterns':[pattern],'unknowns':''},schema)


if __name__=='__main__': unittest.main()
