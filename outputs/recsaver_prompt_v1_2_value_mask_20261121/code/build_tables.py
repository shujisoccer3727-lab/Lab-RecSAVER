"""Separate saved replay, masked diagnostics, and the new main experiment."""
import run as r
import csv,json,collections
rows=[]
rv=r.read(r.OUT/'replay_review.json')
for c in r.cases():
    for rid in r.p.ids(c):
        a=r.read(r.OUT/'saved_v1_1_masks'/rid/'mask_audit.json');v=rv['candidates'][rid]
        rows.append(dict(candidate_id=rid,mask_applied=bool(a['changes']),masked_values=a['value_replacements'],changed_fields=a['changed_fields'],value_only_invariant=a['value_only_invariant'],automatic_pass=a['automatic_pass'],review_pass=v['pass'],invalid_history_reference=v['invalid_history_reference'],remaining_input_violation=v['remaining_input_violation'],quarantine_reasons=';'.join(z['kind'] for z in a['quarantine'])))
r.csvsave(r.OUT/'saved_mask_results.csv',rows,list(rows[0]))
diag=[]
for test in ['A','B','C']:
    f=r.OUT/'stage2_diagnostics'/test/'masked';a=r.read(r.OUT/'diagnostic_masks'/test/'mask_audit.json')
    if not (f/'result.json').exists():continue
    res=r.read(f/'result.json');v=r.read(f/'parsed.json') if (f/'parsed.json').exists() else {};raw=(f/'raw.txt').read_text();issues=json.dumps(v.get('reference_analysis_issues',[]),ensure_ascii=False)
    diag.append(dict(test=test,mask_values=a['value_replacements'],strict_json=res['json_valid'],structure=res['schema_valid'],code_fence=raw.lstrip().startswith('```'),status=v.get('status'),overall=v.get('reconstructed_overall'),issues=issues,mask_rejected_as_contamination=v.get('status')=='contaminated_input' and any(z in (issues+' '+v.get('evidence_summary','')).lower() for z in ['mask','placeholder','square','□']),excluded_from_acceptance=True))
if diag:r.csvsave(r.OUT/'stage2_diagnostics.csv',diag,list(diag[0]))
r.save(r.OUT/'replay_summary.json',dict(candidates=6,mask_applied_candidates=sum(v['mask_applied'] for v in rows),mask_values=sum(v['masked_values'] for v in rows),changed_fields=sum(v['changed_fields'] for v in rows),input_pass=sum(v['review_pass'] for v in rows),invalid_history_candidates=sum(v['invalid_history_reference'] for v in rows),quarantined=sum(not v['review_pass'] for v in rows),diagnostic_executions=len(diag),diagnostic_strict_json=sum(v['strict_json'] for v in diag)))
f=r.OUT/'stage3/rater_7/parsed.json';checks=[]
if f.exists():
    v=r.read(f);inp=r.read(f.parent/'input.json');sources={e['essay_id']:e for e in inp['source_essays']};records={e['record_id']:e for e in inp['accepted_records']};targets={e['target_essay_id'] for e in records.values()}
    scope=v['evidence_scope'];checks.append(dict(kind='scope_counts',pass_=scope['accepted_record_count']==len(records) and scope['distinct_target_essay_count']==len(targets) and set(scope['target_essay_ids'])==targets))
    for pattern in v['patterns']:
        support={c['target_essay_id'] for c in pattern['supporting_cases']};checks.append(dict(kind='distinct_pattern_support',pattern_id=pattern['pattern_id'],pass_=len(support)>=2 and support<=targets))
        for case in pattern['counterexamples_and_scope']:
            checks.append(dict(kind='counterexample_target_role',essay_id=case['target_essay_id'],pass_=case['target_essay_id'] in targets))
        for case in pattern['supporting_cases']:
            for record in case['reference_record_ids']:checks.append(dict(kind='record_reference',reference=record,pass_=record in records and records[record]['target_essay_id']==case['target_essay_id']))
        def walk(x,path='',eid=None):
            if isinstance(x,dict):
                eid=x.get('target_essay_id',eid)
                for k,z in x.items():
                    if k=='quotes':
                        for q in z:checks.append(dict(kind='quote',path=path+'/'+k,essay_id=eid,quote=q,pass_=eid in sources and q in sources[eid]['text']))
                    elif k=='rubric_quote' and z is not None:checks.append(dict(kind='rubric_quote',path=path+'/'+k,quote=z,matching_bands=[band for band,ds in inp['rubric']['scores'].items() if z in ds.get(x.get('dimension','Overall'),'')],pass_=any(z in text for band in inp['rubric']['scores'].values() for text in band.values())))
                    elif k=='observed_relevant_scores' and eid in sources:
                        for dim,num in [('Overall',z.get('Overall'))]+list(z.get('Traits',{}).items()):
                            expected=sources[eid]['Overall'] if dim=='Overall' else sources[eid]['Traits'].get(dim)
                            checks.append(dict(kind='score',path=path+'/'+k+'/'+dim,value=num,expected=expected,pass_=num==expected))
                    else:walk(z,path+'/'+k,eid)
            elif isinstance(x,list):
                for i,z in enumerate(x):walk(z,path+'/'+str(i),eid)
        walk(pattern)
    r.save(r.OUT/'stage3/mechanical_checks.json',dict(checks=checks,passed=sum(z['pass_'] for z in checks),total=len(checks),note='Mechanical checks only; semantic support and rater guidance reviewed separately.'))
print(json.dumps(dict(replay=r.read(r.OUT/'replay_summary.json'),diagnostics=diag,stage3_checks=len(checks)),ensure_ascii=False,indent=2))
