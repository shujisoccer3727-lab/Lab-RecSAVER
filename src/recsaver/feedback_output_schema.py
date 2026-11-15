"""統合以降の形式・参照IDを制約する。意味的な支持を保証しない。"""
import re


def output_schema(stage,payload):
    string={'type':'string'}
    def obj(**fields):
        return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
    def array(item,minimum=0,maximum=None):
        result=dict(type='array',items=item,minItems=minimum)
        if maximum is not None: result['maxItems']=maximum
        return result
    def ids(values,minimum=0):
        values=list(dict.fromkeys(values))
        return array(dict(type='string',enum=values),minimum) if values else dict(type='array',items=string,maxItems=0)
    if stage=='merge':
        claims=[c['id'] for c in payload['claims']]
        return obj(groups=array(obj(summary=string,claim_ids=ids(claims,1))),
                   differences=array(obj(description=string,claim_ids=ids(claims,1))),unknowns=string)
    if stage=='integrate':
        essays=payload['essays'];targets=[g['target_id'] for g in essays]
        claims=[c['id'] for g in essays for c in g['eligible_claims']]
        support=obj(target_id=dict(type='string',enum=targets),claim_ids=ids(claims,1))
        counter=obj(target_id=dict(type='string',enum=targets),claim_ids=ids(claims,1),reason=string)
        non_app=obj(target_id=dict(type='string',enum=targets),reason=string)
        pattern=obj(pattern_id=string,feature_context=string,repeated_judgment=string,inferred_tendency=string,
                    support=array(support,2),counterexamples=array(counter),non_applicable=array(non_app),
                    insufficient_target_ids=ids(targets),limits=string)
        return obj(patterns=array(pattern,0,2),unknowns=string)
    if stage=='compare':
        spans=[s['span_id'] for s in payload['target_spans']]
        claims=[c['id'] for c in payload['eligible_claims']]
        words=list(dict.fromkeys(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)?|\d+",payload['target_text'])))
        anchor=obj(span_id=dict(type='string',enum=spans),tokens=ids(words,2),relation=string,interpretation=string)
        relation=obj(issue_id=string,claim_ids=ids(claims,1),span_ids=ids(spans,1),analysis_anchors=array(anchor,1,2),
                     condition_ids=ids(payload['condition_catalog'],1),feature_confirmed=string,
                     inferred_judgment=string,rubric_based_proposal=string,agreement_review_unknown=string,
                     system_checked=array(obj(span_ids=ids(spans,1),finding=string),1),
                     next_action=obj(distinguish=string,where_span_ids=ids(spans,1),action=string,reason=string),
                     scope_limit=string)
        return obj(relationships=array(relation,0,1))
    if stage=='text':
        return obj(**{k:string for k in ['criterion_intro','tendency','examples_intro','relationship','next_checks','limits']})
    raise ValueError(stage)
