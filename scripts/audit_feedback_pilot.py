"""最終成果物の独立した機械検査。既存実験は読取専用。"""
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import save,sha,now,locate,validate_b,validate_c,evidence_map


def main():
    out=ROOT/'outputs/rater_feedback_pilot'
    inputs=json.loads((out/'inputs.json').read_text())
    byid={r['target_id']:r for r in inputs}
    rubric=json.loads((out/'rubric.json').read_text())
    prov=json.loads((out/'provenance.json').read_text())
    original_quotes=[]
    for item in inputs:
        spans=re.findall(r'"([^"\n]{3,})"|“([^”\n]{3,})”|(?<![A-Za-z])\x27([^\x27\n]{3,})\x27(?![A-Za-z])',item['reference_reasoning'])
        for span in spans:
            quote=next(s for s in span if s)
            original_quotes.append(dict(target_id=item['target_id'],quote=quote,
                target_occurrences=locate(item['target_text'],quote),
                punctuation_trimmed_match=bool(quote.rstrip(',.!?;:') and quote.rstrip(',.!?;:') in item['target_text']),
                history_matches=[h['target_id'] for h in item['history'] if quote in h['text']]))
    save(out/'reference_quote_audit.json',dict(method='Heuristic double, smart and single quotation mark extraction; not exhaustive claim detection',
        explicit_quote_count=len(original_quotes),target_count_with_explicit_quotes=len({q['target_id'] for q in original_quotes}),quotes=original_quotes))
    history_scope=[]
    for item in inputs:
        statements=[s for s in re.split(r'(?<=[.!?])\s+',item['reference_reasoning'])
                    if re.search(r'rater|evaluation|histor',s,re.I) and re.search(r'previous|past|histor',s,re.I)]
        if statements:
            afile=out/'A'/f"{item['target_id'].replace(':','_')}.json"
            a=json.loads(afile.read_text())['result'] if afile.exists() else {}
            separation=a.get('history_separation','')
            history_scope.append(dict(target_id=item['target_id'],history_ids=item['history_ids'],
                history_statements=statements,scope='input history, not target essay evidence',
                A_history_separation=separation,A_unassessed_claims=a.get('unassessed_claims',''),
                A_history_denial_needs_review=bool(re.search(r'no explicit|no reference|no mention|none',separation,re.I)),
                support_policy='never treated as target evidence; claims about history accuracy not independently validated'))
    save(out/'history_scope_audit.json',history_scope)
    source_checks=[dict(path=p,unchanged=sha(ROOT/p)==h) for p,h in prov['source_sha256'].items()]
    results=[]
    for file in sorted((out/'results').glob('*.json')):
        result=json.loads(file.read_text())
        assert not re.search(r'3点程度|3点に留ま|3点にとどま',json.dumps(result['C']['elements'],ensure_ascii=False)), 'Rejected score cap remains in final feedback'
        ev=evidence_map(result['A'])
        for c in ev.values():
            assert not (c['usable_for_synthesis'] and re.search(r"rater.s previous|previous evaluations|rating history",c['rationale_claim'],re.I)), 'History claim leaked into target evidence'
        validate_b(result['B'],ev,list(result['observed_scores']))
        validate_c(result['C'],ev,result['B'],rubric)
        quotes=[]
        for c in ev.values():
            for q in c['quote_checks']:
                actual=locate(byid[c['target_id']]['target_text'],q['quote'])
                assert actual==q['occurrences'], 'stored offsets do not reproduce'
                target=byid[c['target_id']]['target_text']
                nq=' '.join(q['quote'].split())
                nt=' '.join(target.split())
                quotes.append(dict(evidence_id=c['evidence_id'],quote=q['quote'],exists=bool(actual),eligible=c['usable_for_synthesis'],
                    whitespace_normalized_match=bool(nq and nq in nt),
                    whitespace_casefold_match=bool(nq and nq.casefold() in nt.casefold()),
                    note='Normalization is diagnostic only; never restores evidence eligibility'))
        narrative=[]
        for cite in result['C'].get('citations',[]):
            eid=cite['evidence_id']
            assert ev[eid]['usable_for_synthesis'] and cite['target_id']==ev[eid]['target_id']
            positions=locate(byid[cite['target_id']]['target_text'],cite['quote'])
            assert positions and positions==cite['positions']
            narrative.append(dict(quote=cite['quote'],target_matches=[cite['target_id']],rubric_match=False,ok=True,
                                  origin='programmatically inserted from exact-validated evidence'))
        for e in result['C']['elements']:
            if e['number']!=3:
                continue
            text=e['text'].split('\n\n',1)[0] if result['C'].get('citations') else e['text']
            spans=re.findall(r'「([^」]+)」|“([^”]+)”|"([^"\n]+)"',text)
            for span in spans:
                q=next(s for s in span if s)
                # 日本語の説明用の括弧書きは本文引用と判定しない。
                if len(re.findall(r'[A-Za-z]',q)) < 10:
                    continue
                tids={ev[i]['target_id'] for i in e['evidence_ids']}
                matches=[t for t in tids if q in byid[t]['target_text']]
                rubric_match=any(q in v for v in rubric.values())
                narrative.append(dict(quote=q,target_matches=matches,rubric_match=rubric_match,ok=bool(matches or rubric_match)))
        results.append(dict(rater_id=result['rater_id'],target_count=result['target_count'],quotation_checks=quotes,
                            element3_narrative_quotes=narrative,valid_B_C_references=True,
                            semantic_claims='model-assessed, no independent human judgment'))
    audit=dict(timestamp=now(),sources_unchanged=all(r['unchanged'] for r in source_checks),source_checks=source_checks,
               raters=results,narrative_quote_failures=sum(not q['ok'] for r in results for q in r['element3_narrative_quotes']),
               exact_quote_failures=sum(not q['exists'] for r in results for q in r['quotation_checks']),
               failed_quotes_whitespace_only=sum(not q['exists'] and q['whitespace_normalized_match'] for r in results for q in r['quotation_checks']))
    save(out/'final_audit.json',audit)
    print(json.dumps({k:v for k,v in audit.items() if k not in ['source_checks','raters']},ensure_ascii=False))
    return audit


if __name__=='__main__':
    main()
