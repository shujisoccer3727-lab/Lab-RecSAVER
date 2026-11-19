"""Mechanical checks only; exact substring matching is not semantic validation."""
from pathlib import Path
import json, importlib.util
OUT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',OUT/'code/run.py');run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)

def audit(stage,rid):
    folder=OUT/f'stage{stage}'/rid
    if not (folder/'parsed.json').exists():return None
    value=run.read(folder/'parsed.json');payload=run.read(folder/'input.json')
    sources={e['essay_id']:e for e in payload.get('source_essays',payload.get('history',[]))}
    if 'target' in payload:sources[payload['target']['essay_id']]=payload['target']
    rubric=payload['rubric'];rubric_text=json.dumps(rubric,ensure_ascii=False)
    quotes=[];ids=[];scores=[]
    def walk(v,path='',eid=None):
        if isinstance(v,dict):
            eid=v.get('history_essay_id',v.get('target_essay_id',eid))
            if eid is not None and ('history_essay_id' in v or 'target_essay_id' in v):
                ids.append(dict(path=path,essay_id=eid,exists=eid in sources))
            for field in ['relevant_observed_history_scores','observed_relevant_scores','observed_target_scores']:
                if field in v and eid in sources:
                    observed=v[field];actual=sources[eid]
                    for k,num in [('Overall',observed.get('Overall'))]+list(observed.get('Traits',{}).items()):
                        expected=actual.get('Overall') if k=='Overall' else actual.get('Traits',{}).get(k)
                        scores.append(dict(path=path+'/'+field+'/'+k,essay_id=eid,value=num,expected=expected,equal=num==expected))
            for k,x in v.items():
                if k=='quotes' and isinstance(x,list):
                    for i,q in enumerate(x):quotes.append(dict(path=path+'/quotes/'+str(i),essay_id=eid,quote=q,exact=isinstance(q,str) and eid in sources and q in sources[eid]['text']))
                elif k=='rubric_quote' and x is not None:
                    quotes.append(dict(path=path+'/rubric_quote',essay_id='rubric',quote=x,exact=isinstance(x,str) and any(x in d for s in rubric['scores'].values() for d in s.values())))
                else:walk(x,path+'/'+k,eid)
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,path+'/'+str(i),eid)
    walk(value)
    refs=[]
    if stage==1:
        a=value.get('score_free_analysis',{});patterns={p['pattern_id'] for p in a.get('history_patterns',[])};evidence={e['evidence_id'] for e in a.get('target_evidence',[])}
        for e in a.get('target_evidence',[]):
            for p in e.get('linked_history_pattern_ids',[]):refs.append(dict(reference=p,exists=p in patterns))
        for t in value.get('observed_score_alignment',{}).get('relevant_trait_alignment',[]):
            for e in t.get('evidence_ids',[]):refs.append(dict(reference=e,exists=e in evidence))
        expected=payload['target']
        align=value.get('observed_score_alignment',{}).get('observed_target_scores',{})
        for key in ['Overall','Traits']:scores.append(dict(path='/observed_score_alignment/observed_target_scores/'+key,equal=align.get(key)==expected[key],value=align.get(key),expected=expected[key]))
    if stage==2:
        a=payload['reference_analysis'];allowed={'used_history_pattern_ids':{p['pattern_id'] for p in a.get('history_patterns',[])},'used_target_evidence_ids':{e['evidence_id'] for e in a.get('target_evidence',[])},'used_history_essay_ids':{e['essay_id'] for e in payload['history']}}
        for key,valid in allowed.items():
            for v in value.get(key,[]):refs.append(dict(field=key,reference=v,exists=v in valid))
    counts=None
    if stage==3:
        records={r['record_id']:r for r in payload['accepted_records']}
        for p in value.get('patterns',[]):
            for c in p.get('supporting_cases',[]):
                for r in c.get('reference_record_ids',[]):refs.append(dict(reference=r,exists=r in records and records[r]['target_essay_id']==c['target_essay_id']))
        scope=value.get('evidence_scope',{});targets={r['target_essay_id'] for r in records.values()}
        counts=dict(record_count_equal=scope.get('accepted_record_count')==len(records),distinct_target_count_equal=scope.get('distinct_target_essay_count')==len(targets),target_ids_equal=set(scope.get('target_essay_ids',[]))==targets)
    result=dict(quote_checks=quotes,id_checks=ids,score_checks=scores,reference_checks=refs,counts=counts,summary=dict(quotes_checked=len(quotes),quote_mismatches=sum(not q['exact'] for q in quotes),invalid_essay_ids=sum(not i['exists'] for i in ids),score_mismatches=sum(not s['equal'] for s in scores),invalid_references=sum(not r['exists'] for r in refs)))
    run.save(folder/'mechanical_checks.json',result)
    return dict(stage=stage,record_id=rid,**result['summary'],counts=counts)

rows=[]
for stage in [1,2,3]:
    for folder in sorted((OUT/f'stage{stage}').iterdir()):
        if not folder.is_dir():continue
        row=audit(stage,folder.name)
        if row:rows.append(row)
run.save(OUT/'mechanical_audit.json',dict(checked_at=run.now(),rows=rows,meaning='Exact quote/source ID/score copying checks only. No correctness or causal faithfulness inferred.'))
print(json.dumps(rows,ensure_ascii=False,indent=2))
