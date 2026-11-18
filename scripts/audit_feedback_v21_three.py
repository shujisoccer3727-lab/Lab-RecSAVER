"""固定3答案の実データを監査する。意味判定の正しさは別途開発レビューする。"""
import collections
import json
import re
from src.recsaver.rater_feedback_development_v21 import ROOT,CONFIG,IDS,load,save,sha,now,DIRECT_SCORE_PATTERN
from src.recsaver.rater_feedback_pilot_v2 import LEAK_PATTERNS


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir'];r=load(out/'three_results.json')
    assert r['target_ids']==IDS and cfg['conditions']==['B'] and len(r['candidates'])==6
    base=load(ROOT/'configs/rater_feedback_pilot_v2.json')
    preserved=['model','generation','max_tokens','seed','candidates_per_target','format_retries']
    assert all(cfg[k]==base[k] for k in preserved)
    assert all(sha(ROOT/p)==h for p,h in load(out/'resolved_config.json')['source_sha256'].items())
    assert all(sha(ROOT/p)==h for p,h in load(out/'old_output_hashes.json').items())
    before=load(out/'three_resume_cache_before.json')['records']
    assert all(sha(out/p)==v['sha256'] for p,v in before.items())
    items={i['target_id']:i for i in load(out/'inputs.json')};catalog=load(out/'conditions.json')
    calls=[json.loads(s) for s in (out/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    assert not any(n>1 for n in collections.Counter(c['key'] for c in calls if c['stage']=='generate' and c['status']=='ok').values())
    payload_checks=[];quotes=[];claimmap={};ground_counts=collections.Counter();cases=[]
    for c in r['candidates']:
        tid=c['target_id'];original=c.get('original_reason');review=c.get('grounding_review')
        assert c['score_match']==bool(c.get('verification') and c['verification']['predicted_overall']==items[tid]['target']['overall'])
        if original:
            for claim in original['claims']:
                if claim.get('grounding_review'): ground_counts[claim['grounding_review']['verdict']]+=1
                else: ground_counts['not_reviewed']+=1
                if claim.get('eligible_for_integration'):
                    g=claim['grounding_review']
                    assert c['score_match'] and claim['scope']=='target'
                    assert g['verdict']=='supported' and g['atomic'] and g['feature_supported'] and g['evaluation_supported']
                    assert claim['effective_evidence_ids']==list(dict.fromkeys(claim['span_ids']+g['added_span_ids']))
                    for e in claim['evidence']: assert items[tid]['target']['text'][e['start']:e['end']]==e['text']
                    claimmap[claim['id']]=claim
        cases.append(dict(candidate_key=c['key'],generated=original is not None,score_match=c['score_match'],
            predicted_overall=(c.get('verification') or {}).get('predicted_overall'),
            grounding_success=review is not None,eligible_claim_ids=[x['id'] for x in (original or {}).get('claims',[]) if x.get('eligible_for_integration')]))
    for path in (out/'stage_inputs/verify').glob('*.json'):
        p=load(path);assert set(p['target'])=={'essay_id','text'}
        assert all(set(h)=={'essay_id','text','overall'} for h in p['history'])
        prose=[p['masked_reason'][k] for k in ['rationale','unexplained']]
        for c in p['masked_reason']['claims']:
            assert not {'condition_ids','overall','traits'} & set(c)
            prose += [c[k] for k in ['feature','evaluation','overall_relation','trait_relation','limits']]
        hits=[m.group() for text in prose for _,pat in [*LEAK_PATTERNS,('extra',DIRECT_SCORE_PATTERN)] for m in re.finditer(pat,text,re.I)]
        assert not hits,(path,hits)
        payload_checks.append(path.name)
    synthesis=r.get('synthesis')
    for field in ['common_features','judgment_patterns']:
        for pattern in (synthesis or {}).get(field,[]):
            assert len({s['target_id'] for s in pattern['support']})>=2
            for s in pattern['support']:
                assert s['claim_ids'] and all(c in claimmap and claimmap[c]['target_id']==s['target_id'] for c in s['claim_ids'])
    issue_map={};citation_count=0
    for comparison in r['comparisons'].values():
        for issue in (comparison or {}).get('relationships',[]):
            assert all(c in claimmap and claimmap[c]['target_id']==issue['target_id'] for c in issue['claim_ids'])
            assert issue['official_conditions']==[catalog[c] for c in issue['condition_ids']]
            for criterion in issue['official_conditions']:
                assert criterion['parent_text'][criterion['start']:criterion['end']]==criterion['text']
            for e in issue['citations']:
                assert e['essay_id']==issue['target_id']
                assert items[issue['target_id']]['target']['text'][e['start']:e['end']]==e['text'];citation_count+=1
            issue_map[issue['id']]=issue
    sentence_count=0
    for key,text in r['texts'].items():
        if text is None: continue
        p=r['text_payloads'][key]
        assert {s['element'] for s in text['sentences']}==set(range(1,6))
        for sentence in text['sentences']:
            sentence_count+=1;assert set(sentence['claim_ids'])<=set(p['claims'])
            assert set(sentence['issue_ids'])<=set(p['issues'])
            assert set(sentence['condition_ids'])<=set(p['conditions'])
            if sentence['element'] in [4,5]:
                assert sentence['issue_ids']
                assert set(sentence['claim_ids'])<={c for i in sentence['issue_ids'] for c in p['issues'][i]['claim_ids']}
            spans=[e['text'] for c in sentence['claim_ids'] for e in p['claims'][c]['evidence']]
            for match in re.finditer(r'「([^」]+)」|"([^"\n]+)"|“([^”]+)”',sentence['text']):
                quoted=next(g for g in match.groups() if g is not None)
                if re.search('[A-Za-z]',quoted):
                    quotes.append(dict(topic=key,element=sentence['element'],quote=quoted,
                        occurs_in_cited_span=any(quoted in s for s in spans),status='free-text quote requires development review'))
    contexts=[json.loads(s) for s in (out/'context_checks.jsonl').read_text().splitlines()]
    terminal={}
    for stage in cfg['max_tokens']:
        caches=[load(p) for p in (out/'stages'/stage).glob('*.json')]
        terminal[stage]=dict(saved=len(caches),success=sum(c['result'] is not None for c in caches),failed=sum(c['result'] is None for c in caches))
    audit=dict(timestamp=now(),scope='three',all_reference_checks_passed=True,model_sampling_seed_retry_budget_preserved=True,
        old_outputs_and_frozen_sources_unchanged=True,reused_success_cache_records_unchanged=len(before),
        duplicate_successful_candidate_generations=0,verification_payloads_checked=len(payload_checks),direct_score_leaks=0,
        generated_success=sum(c['original_reason'] is not None for c in r['candidates']),
        generated_failures=sum(c['original_reason'] is None for c in r['candidates']),
        verification_success=sum(c.get('verification') is not None for c in r['candidates']),
        score_matches=sum(c['score_match'] for c in r['candidates']),ground_counts=dict(ground_counts),
        integration_succeeded=synthesis is not None,evidence_eligible_unique_targets=len({c['target_id'] for c in claimmap.values()}),
        exact_comparison_citations=citation_count,final_sentences=sentence_count,
        context_overflows=[c for c in contexts if not c['fits']],terminal_caches_including_one_trial=terminal,
        candidates=cases,free_text_quote_flags=quotes,
        limitation='Reference and literal checks only; semantic support, usefulness and true rater thought are not established.')
    save(out/'three_audit.json',audit)
    material=dict(observed={tid:{k:items[tid]['target'][k] for k in ['overall','traits']} for tid in IDS},
        candidates=[dict(key=c['key'],score_match=c['score_match'],verification=c.get('verification'),
            claims=[{k:v for k,v in cl.items() if k!='evidence'} for cl in (c.get('original_reason') or {}).get('claims',[])]) for c in r['candidates']],
        synthesis=synthesis,comparisons={k:None if v is None else dict(relationships=[{k:v for k,v in i.items() if k not in ['citations','official_conditions']} for i in v['relationships']]) for k,v in r['comparisons'].items()},texts=r['texts'])
    save(out/'three_review_material.json',material)
    print(json.dumps({k:v for k,v in audit.items() if k not in ['candidates','free_text_quote_flags','terminal_caches_including_one_trial']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
