"""Mechanical v1.6 contracts, generalized from baseline; no semantic verdicts."""
import re

def array(x,k):return x.get(k,[]) if isinstance(x,dict) and isinstance(x.get(k,[]),list) else []

def need(x,fields,path):
    if not isinstance(x,dict):return [path+': expected object']
    errors=[path+'.'+k+': missing/type' for k,t in fields.items() if k not in x or not isinstance(x[k],t)]
    errors += [path+'.'+k+': unexpected field' for k in set(x)-set(fields)]
    return errors

def obs_schema(o,path):return need(o,dict(observation_id=str,dimension=str,evidence_span_ids=list,feature=str,scoring_relevance=str,limitation=str,next_check=str),path)

def a_schema(v):
    errors=need(v,dict(schema_version=str,target_essay_id=str,observations=list,insufficient_evidence=list),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.5':errors.append('schema_version !=1.5')
    if len(array(v,'observations'))>2:errors.append('more than two observations')
    for i,o in enumerate(array(v,'observations')):errors+=obs_schema(o,f'$.observations[{i}]')
    return errors

def b_schema(v):
    errors=need(v,dict(schema_version=str,rater_id=str,pattern_status=str,pattern=(dict,type(None)),pattern_limit=str,representative_observation_key=(str,type(None)),quote_indices=list,textual_finding=(str,type(None)),evidence_limit=(str,type(None)),rubric_review=dict,next_check=dict),'$')
    if not isinstance(v,dict):return errors
    if v.get('schema_version')!='1.5':errors.append('schema_version !=1.5')
    if v.get('pattern_status') not in ['supported','insufficient_evidence']:errors.append('invalid pattern_status')
    errors+=need(v.get('rubric_review'),dict(observed_band_ref_id=(str,type(None)),comparison_band_ref_id=(str,type(None)),band_assessment=str),'$.rubric_review')
    if isinstance(v.get('rubric_review'),dict) and v['rubric_review'].get('band_assessment') not in ['indeterminate','possible_tension']:errors.append('invalid band assessment')
    errors+=need(v.get('next_check'),dict(inspect=str,distinguish=str,reconsider_if=(str,type(None))),'$.next_check')
    if isinstance(v.get('pattern'),dict):
        errors+=need(v['pattern'],dict(statement=str,support=list),'$.pattern')
        for s in array(v['pattern'],'support'):errors+=need(s,dict(observation_key=str,supports_how=str),'$.pattern.support')
    return errors

def gate_a(v,payload):
    top=need(v,dict(schema_version=str,target_essay_id=str,observations=list,insufficient_evidence=list),'$')
    if not isinstance(v,dict) or v.get('schema_version')!='1.5' or v.get('target_essay_id')!=payload['target_essay_id']:top.append('version/target mismatch')
    if len(array(v,'observations'))>2:top.append('more than two observations')
    catalog={s['span_id']:s for s in payload['evidence_spans']};counts={};passed=[];checks=[]
    for o in array(v,'observations'):
        oid=o.get('observation_id') if isinstance(o,dict) else None
        if isinstance(oid,str):counts[oid]=counts.get(oid,0)+1
    for i,o in enumerate(array(v,'observations')):
        reasons=top+obs_schema(o,f'observations[{i}]');selected=[]
        if isinstance(o,dict):
            oid=o.get('observation_id');ids=array(o,'evidence_span_ids')
            if not isinstance(oid,str) or not oid or counts.get(oid,0)!=1:reasons.append('observation ID missing/duplicated')
            if o.get('dimension') not in payload['dimension_names']:reasons.append('unknown dimension')
            if not ids:reasons.append('no selected spans')
            if any(not isinstance(s,str) or s not in catalog for s in ids):reasons.append('unknown/other-target span ID')
            if len(set(s for s in ids if isinstance(s,str)))!=len(ids):reasons.append('duplicate/invalid span ID')
            selected=[catalog[s] for s in ids if isinstance(s,str) and s in catalog]
        quotes=[payload['target_text'][s['start']:s['end']] for s in selected]
        if any(q!=s['text'] for q,s in zip(quotes,selected)):reasons.append('catalog/source mismatch')
        checks.append(dict(index=i,pass_=not reasons,reasons=reasons,source_spans=selected,reconstructed_quotes=quotes,semantic_support_not_certified=True))
        if not reasons:passed.append(dict(o,quotes=quotes))
    return dict(top_errors=top,checks=checks,passed_observations=passed)

def sentence(text):
    text=text.strip()
    return text if re.search(r'[.!?]["”\x27]?$',text) else text+'.'

def quoted_sentence(prefix,quote):
    # Inspect terminal punctuation without changing even one character inside quote.
    return prefix+'“'+quote+'”'+('' if re.search(r'[.!?]["”\x27]?\s*$',quote) else '.')

def review_and_render(v,payload):
    errors=b_schema(v);checks=[]
    def ck(kind,ok,**details):checks.append(dict(kind=kind,pass_=bool(ok),**details))
    if errors:return dict(pass_=False,schema_errors=errors,checks=[],feedback_paragraph=None)
    obs={o['observation_key']:o for o in payload['verified_observations']};refs={e['rubric_ref_id']:e for e in payload['rubric_entries']};key=v['representative_observation_key'];rep=obs.get(key);indices=v['quote_indices'];rr=v['rubric_review'];nc=v['next_check']
    ck('rater',v['rater_id']==payload['rater_id']);ck('representative_key',key is None or key in obs)
    valid_indices=all(isinstance(i,int) and not isinstance(i,bool) and rep is not None and 0<=i<len(rep['quotes']) for i in indices)
    ck('indices',valid_indices and len(set(i for i in indices if isinstance(i,int)))==len(indices) and (bool(indices) if key is not None else indices==[]))
    ck('representative_fields',all(isinstance(v[k],str) and bool(v[k]) for k in ['textual_finding','evidence_limit']) if key is not None else v['textual_finding'] is None and v['evidence_limit'] is None)
    if v['pattern_status']=='insufficient_evidence':ck('abstention',v['pattern'] is None and bool(v['pattern_limit']))
    else:
        support=array(v.get('pattern'),'support');keys=[s.get('observation_key') for s in support];targets={obs[k]['target_essay_id'] for k in keys if isinstance(k,str) and k in obs}
        ck('supported_pattern_keys',all(isinstance(k,str) and k in obs for k in keys) and key in keys)
        ck('independent_support',len(targets)>=2 and targets<=set(payload['accepted_target_ids']))
    observed=refs.get(rr['observed_band_ref_id']);comparison=refs.get(rr['comparison_band_ref_id']);direction='none'
    expected=next((r['rubric_ref_id'] for r in refs.values() if rep and r['dimension']==rep['dimension'] and r['score_band']==rep['observed_score']),None)
    ck('observed_reference',rr['observed_band_ref_id']==expected)
    ck('comparison_exists',rr['comparison_band_ref_id'] is None or comparison is not None)
    if comparison and rep:
        bands=sorted({e['score_band'] for e in refs.values() if e['dimension']==rep['dimension']});score=rep['observed_score'];neighbors=[]
        if score is not None:
            if any(b<score for b in bands):neighbors.append(max(b for b in bands if b<score))
            if any(b>score for b in bands):neighbors.append(min(b for b in bands if b>score))
        ck('same_dimension_adjacent_band',comparison['dimension']==rep['dimension'] and comparison['score_band'] in neighbors)
        direction='higher' if score is not None and comparison['score_band']>score else 'lower'
        ck('comparison_condition',isinstance(nc['reconsider_if'],str) and bool(nc['reconsider_if']))
    elif rr['comparison_band_ref_id'] is None:ck('no_comparison_condition',nc['reconsider_if'] is None)
    if key is None:ck('no_representative_refs',observed is None and comparison is None and rr['band_assessment']=='indeterminate')
    ok=all(c['pass_'] for c in checks)
    result=dict(pass_=ok,schema_errors=[],checks=checks,comparison_direction=direction,feedback_paragraph=None,selected_evidence=[],semantic_support_not_certified=True)
    if not ok:return result
    parts=[sentence('A scoring pattern cannot be established from these cases. '+v['pattern_limit']) if v['pattern_status']=='insufficient_evidence' else sentence(v['pattern']['statement'])]
    if rep:
        for i in indices:
            q=rep['quotes'][i];parts.append(quoted_sentence(f'In essay {rep["target_essay_id"]}, the relevant excerpt is ',q));result['selected_evidence'].append(dict(observation_key=key,quote_index=i,target_essay_id=rep['target_essay_id'],exact_quote=q))
        parts.append(sentence(v['textual_finding']))
        score=rep['observed_score'];parts.append(f'The recorded {rep["dimension"]} score is {score}.' if score is not None else f'The recorded {rep["dimension"]} score is unavailable.')
        if observed:parts.append(quoted_sentence(f'The official descriptor for {observed["rubric_ref_id"]} is ',observed['descriptor']))
        parts.append('This evidence alone does not establish whether that band is appropriate.' if rr['band_assessment']=='indeterminate' else 'This evidence suggests a possible tension to review; it does not establish a corrected score.')
        parts.append(sentence(v['evidence_limit']))
    parts += [sentence('Next inspect: '+nc['inspect']),sentence('Check: '+nc['distinguish'])]
    if comparison:
        parts.append(quoted_sentence(f'The {direction} comparison band {comparison["rubric_ref_id"]} is described as ',comparison['descriptor']))
        parts.append(sentence(f'For review toward that {direction} band, reconsider if '+nc['reconsider_if']))
    result['feedback_paragraph']=' '.join(parts);return result
