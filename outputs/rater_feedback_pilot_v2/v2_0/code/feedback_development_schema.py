"""開発3答案用。参照整合性を制約し、意味的正しさとは分離する。"""
def output_schema(stage, p):
    s={'type':'string'}
    b={'type':'boolean'}
    def obj(**fields):
        return dict(type='object',properties=fields,required=list(fields),additionalProperties=False)
    def arr(item, minimum=0, maximum=None):
        result=dict(type='array',items=item,minItems=minimum)
        if maximum is not None: result['maxItems']=maximum
        return result
    def enum(values): return dict(type='string',enum=list(dict.fromkeys(values)))
    def ids(values, minimum=0):
        values=list(dict.fromkeys(values))
        return arr(enum(values),minimum) if values else arr(s,0,0)
    if stage=='generate':
        essays=[p['target'],*p['history']]
        return obj(rationale=s,claims=arr(obj(claim_id=enum(['C1','C2','C3','C4']),
            scope=enum(['target','history']),essay_id=enum([e['essay_id'] for e in essays]),
            aspect=enum(['Overall','Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']),
            judgment_type=enum(['presence','extent','impact','organization','range','appropriateness']),
            feature=s,evaluation=s,span_ids=ids([x['span_id'] for e in essays for x in e['spans']],1),
            direction=enum(['positive','negative','mixed','unclear']),
            overall_relation=s,trait_relation=s,limits=s),1,4),unexplained=s)
    if stage=='ground':
        spans=[s['span_id'] for e in p['essays'] for s in e['spans']]
        return obj(reviews=arr(obj(claim_id=enum([c['claim_id'] for c in p['claims']]),
            verdict=enum(['supported','contradicted','insufficient']),atomic=b,
            feature_supported=b,evaluation_supported=b,explanation=s,
            added_span_ids=ids(spans),counter_span_ids=ids(spans)),1,4))
    if stage=='merge':
        refs=ids([c['id'] for c in p['claims']],1)
        return obj(groups=arr(obj(summary=s,claim_ids=refs)),differences=arr(obj(description=s,claim_ids=refs)),unknowns=s)
    if stage=='integrate':
        claims=[c for e in p['essays'] for c in e['eligible_claims']]
        tids=[e['target_id'] for e in p['essays']]
        support=obj(target_id=enum(tids),claim_ids=ids([c['id'] for c in claims],1))
        return obj(common_features=arr(obj(feature_id=s,description=s,support=arr(support,2)),0,2),
            judgment_patterns=arr(obj(pattern_id=s,feature_context=s,repeated_judgment=s,
                relationship_to_observed_scores=s,support=arr(support,2),
                counterexamples=arr(obj(target_id=enum(tids),claim_ids=ids([c['id'] for c in claims],1),reason=s)),
                unknowns=s),0,2),unknowns=s)
    if stage=='compare':
        spans=ids([x['span_id'] for x in p['target']['spans']],1)
        return obj(relationships=arr(obj(issue_id=enum(['I1']),claim_ids=ids([c['id'] for c in p['claims']],1),
            span_ids=spans,feature_confirmed=s,inferred_judgment=s,
            condition_ids=ids(p['condition_catalog'],1),rubric_based_proposal=s,
            agreement=s,review=s,unknowns=s,conclusion_scope=enum(['local_only','cannot_judge']),
            next_action=obj(actor=enum(['rater']),evaluation_target=s,distinguish=s,procedure=s,criterion_relation=s)),0,1))
    if stage=='text':
        return obj(sentences=arr(obj(element=dict(type='integer',enum=[1,2,3,4,5]),text=s,
            claim_ids=ids(p['claims'],1),issue_ids=ids(p['issues']),condition_ids=ids(p['conditions'])),5,7),limits=s)
    raise ValueError(stage)
