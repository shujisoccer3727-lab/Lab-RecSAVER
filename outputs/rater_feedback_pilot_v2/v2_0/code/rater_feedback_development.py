"""指定3答案・B条件の開発実行。旧出力を保持し、全段階を別版で保存する。"""
from __future__ import annotations
import argparse
import copy
import json
import re
import shutil
import traceback
from pathlib import Path
from .rater_feedback_pilot_v2 import (ROOT, now, sha, save, append, load, csv_rows, score_record,
    condition_catalog, generation_payload, verification_payload, valid_score, mask_string, rule_flags)
from .feedback_development_schema import output_schema

IDS=['1514:1','1868:1','4902:1']
CONFIG=ROOT/'configs/rater_feedback_development.json'


def bootstrap():
    if CONFIG.exists(): return load(CONFIG)
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json')
    cfg.update(version='feedback-pilot-v2/2.0',output_dir='outputs/rater_feedback_pilot_v2/v2_0',
        prompt_dir='prompts/rater_feedback_pilot_v2/v5',conditions=['B'],target_ids=IDS,
        guided_stages=['generate','ground','merge','integrate','compare','text'],
        selection_purpose='fixed development examples requested by user; no replacement or expansion',
        pilot_rule='one=1514:1 only; three=exact fixed IDS after saved one-case development review',
        acceptance='Overall reconstruction match recorded separately; evidence eligibility requires atomic fully supported claim',
        changes=['new claim fields separate feature/evaluation/score relationships',
            'supported/contradicted/insufficient review with explicit additional evidence',
            'separate common features from repeated evaluation judgments',
            'remove arbitrary word-count/grammar anchors and generic action regex',
            'local rubric comparisons; per-topic sentence-level provenance'],
        reuse='no old reasons or downstream outputs reused; one-to-three reuse only identical fingerprints')
    save(CONFIG,cfg)
    # 自己検証の指示は変更しない。
    destination=ROOT/cfg['prompt_dir']/'verify.txt'
    if not destination.exists(): shutil.copy2(ROOT/'prompts/rater_feedback_pilot_v2/v4/verify.txt',destination)
    return cfg


def prepare(cfg):
    out=ROOT/cfg['output_dir']; out.mkdir(parents=True,exist_ok=True)
    if (out/'resolved_config.json').exists():
        resolved=load(out/'resolved_config.json')
        assert resolved['config']==cfg,'Use a new version for changed settings'
        assert all(sha(ROOT/p)==h for p,h in resolved['source_sha256'].items()),'Source changed; use a new version'
        return out
    old=load(ROOT/'outputs/rater_feedback_pilot_v2/v1_6/inputs.json')
    wide=csv_rows(ROOT/cfg['wide_path']); raw=csv_rows(ROOT/cfg['raw_path'])
    byid={f"{r['source_row_id']}:{r['rater_position']}":r for r in wide}
    items=[];checks=[]
    for tid in IDS:
        item=copy.deepcopy(next(i for i in old if i['target_id']==tid))
        assert item['rater_id']=='rater_7' and len(item['history'])==3
        for entry in [item['target'],*item['history']]:
            actual=score_record(byid[entry['essay_id']],raw,'rater_7')
            assert not actual['invalid_scores']
            assert all(actual[k]==entry[k] for k in actual), (tid,entry['essay_id'])
            assert all(entry['text'][s['start']:s['end']]==s['text'] for s in entry['spans'])
            assert ''.join(s['text'] for s in entry['spans'])==entry['text']
        assert len({e['source_row_id'] for e in [item['target'],*item['history']]})==4
        items.append(item)
        checks.append(dict(target_id=tid,actual_raw_rater_id=item['rater_id'],raw_wide_old_text_and_all_scores_equal=True,
            history_ids=[e['essay_id'] for e in item['history']],overall=item['target']['overall'],traits=item['target']['traits']))
    rubric=load(ROOT/cfg['rubric_path']); catalog=condition_catalog(rubric)
    save(out/'inputs.json',items);save(out/'input_checks.json',checks)
    save(out/'rubric.json',rubric);save(out/'conditions.json',catalog)
    save(out/'selection.json',dict(target_ids=IDS,condition='B',rater='rater_7',histories_per_target=3,
        seed=cfg['seed'],candidates_per_target=cfg['candidates_per_target'],representative_sample=False))
    code=[Path(__file__),ROOT/'src/recsaver/feedback_development_schema.py',
        ROOT/'src/recsaver/feedback_development_engine.py',ROOT/'src/recsaver/rater_feedback_pilot_v2.py',
        ROOT/'src/recsaver/model.py',ROOT/'src/recsaver/rater_feedback_pilot.py',CONFIG,
        ROOT/'tests/test_feedback_development.py',
        *sorted((ROOT/cfg['prompt_dir']).glob('*.txt'))]
    inputs=[ROOT/cfg[k] for k in ['raw_path','wide_path','rubric_path']]
    inputs += [ROOT/'outputs/rater_feedback_pilot_v2/v1_6/inputs.json']
    archive=out/'code';archive.mkdir(exist_ok=True)
    for p in code: shutil.copy2(p,archive/p.name)
    save(out/'resolved_config.json',dict(timestamp=now(),config=cfg,
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in code+inputs},
        no_old_reasons_in_generation=True,rubric_limitation='stored transcription; original DOCX unavailable'))
    save(out/'revision_note.json',dict(timestamp=now(),version=cfg['version'],changes=cfg['changes'],
        unchanged='model, sampling settings, seed policy, two candidates, one format retry, fixed source data and histories',
        impact='All reasons changed; no v1.6 generation or dependent stage is reused',
        handoff='If prompts/code/config change after execution, use a new version. Score mismatch never triggers regeneration.'))
    return out


def masked_reason(reason):
    safe={}; logs=[]; residual=[]
    for field in ['rationale','unexplained']:
        safe[field],a,b=mask_string(reason[field],field);logs+=a;residual+=b
    safe['claims']=[]
    for claim in reason['claims']:
        c={k:claim[k] for k in ['claim_id','scope','essay_id','aspect','judgment_type','direction','span_ids']}
        for field in ['feature','evaluation','overall_relation','trait_relation','limits']:
            c[field],a,b=mask_string(claim[field],claim['claim_id']+'.'+field);logs+=a;residual+=b
        safe['claims'].append(c)
    return safe,logs,residual


def validate_reason(obj,item):
    claims=obj['claims'];assert 1<=len(claims)<=4
    assert len({c['claim_id'] for c in claims})==len(claims)
    essays={e['essay_id']:e for e in [item['target'],*item['history']]}
    for c in claims:
        assert c['essay_id'] in essays
        assert (c['scope']=='target')==(c['essay_id']==item['target_id'])
        spans={s['span_id']:s for s in essays[c['essay_id']]['spans']}
        assert c['span_ids'] and all(s in spans for s in c['span_ids'])
        c['evidence']=[dict(essay_id=c['essay_id'],**spans[s]) for s in c['span_ids']]
        assert c['feature'].strip() and c['evaluation'].strip()
    return obj


def validate_ground(obj,claims,item):
    assert sorted(r['claim_id'] for r in obj['reviews'])==sorted(c['claim_id'] for c in claims)
    for r in obj['reviews']:
        c=next(c for c in claims if c['claim_id']==r['claim_id'])
        e=next(e for e in [item['target'],*item['history']] if e['essay_id']==c['essay_id'])
        spans={s['span_id'] for s in e['spans']}
        assert all(s in spans for s in r['added_span_ids']+r['counter_span_ids'])
        assert not set(r['added_span_ids']) & set(c['span_ids']), 'Additional evidence must be explicitly new'
        if r['verdict']=='supported':
            assert r['atomic'] and r['feature_supported'] and r['evaluation_supported'],'Partial or composite support cannot be supported'
    return obj


def validate_refs(obj,cmap,collections_to_check):
    for field in collections_to_check:
        for node in obj[field]:
            assert node['claim_ids'] and all(c in cmap for c in node['claim_ids'])
    return obj


def validate_integration(obj,cmap):
    for field in ['common_features','judgment_patterns']:
        for p in obj[field]:
            assert len({s['target_id'] for s in p['support']})>=2
            for s in p['support']+p.get('counterexamples',[]):
                assert s['claim_ids'] and all(c in cmap and cmap[c]['target_id']==s['target_id'] for c in s['claim_ids'])
    assert not rule_flags(json.dumps(obj,ensure_ascii=False))
    return obj


def validate_comparison(obj,item,cmap,catalog,key):
    spans={s['span_id']:s for s in item['target']['spans']}
    for issue in obj['relationships']:
        assert all(c in cmap and cmap[c]['target_id']==item['target_id'] for c in issue['claim_ids'])
        assert issue['span_ids'] and all(s in spans for s in issue['span_ids'])
        assert issue['condition_ids'] and all(c in catalog for c in issue['condition_ids'])
        issue['id']=key+'/'+issue['issue_id'];issue['target_id']=item['target_id']
        issue['citations']=[dict(essay_id=item['target_id'],**spans[s]) for s in issue['span_ids']]
        issue['official_conditions']=[catalog[c] for c in issue['condition_ids']]
        issue['machine_checks']=dict(citations_exact=all(item['target']['text'][s['start']:s['end']]==s['text'] for s in issue['citations']),
            condition_ids_exact=True,overall_score_not_determined=True)
        assert issue['next_action']['actor']=='rater'
        assert not rule_flags(json.dumps(issue,ensure_ascii=False))
    return obj


def validate_text(obj,payload):
    assert {s['element'] for s in obj['sentences']}==set(range(1,6))
    for s in obj['sentences']:
        assert s['claim_ids'] and all(c in payload['claims'] for c in s['claim_ids'])
        assert all(i in payload['issues'] for i in s['issue_ids'])
        assert all(c in payload['conditions'] for c in s['condition_ids'])
        if s['element'] in [4,5]:
            assert s['issue_ids']
            available={c for i in s['issue_ids'] for c in payload['issues'][i]['claim_ids']}
            assert set(s['claim_ids'])<=available, 'Sentence claims must belong to its cited issue'
            allowed_conditions={c for i in s['issue_ids'] for c in payload['issues'][i]['condition_ids']}
            assert set(s['condition_ids'])<=allowed_conditions, 'Sentence criteria must belong to its cited issue'
        if s['element'] in [1,4,5]: assert s['condition_ids']
        available_spans={e['span_id'] for c in s['claim_ids'] for e in payload['claims'][c]['evidence']}
        mentioned=set(re.findall(r'\d+:[12]@U\d+',s['text']))
        assert mentioned<=available_spans,'Foreign span mentioned in final sentence'
        targets={payload['claims'][c]['target_id'] for c in s['claim_ids']}
        assert set(re.findall(r'\b\d+:[12]\b',s['text']))<=targets,'Foreign target mentioned in final sentence'
        s['source_target_ids']=sorted(targets)
    assert not rule_flags(json.dumps(obj,ensure_ascii=False))
    return obj


def run(cfg,out,engine,scope):
    items=load(out/'inputs.json')[:1] if scope=='one' else load(out/'inputs.json')
    byid={i['target_id']:i for i in items}
    rubric=load(out/'rubric.json'); catalog=load(out/'conditions.json')
    def batch(stage,jobs):
        for key,payload,validator in jobs:
            save(out/'stage_inputs'/stage/(key.replace(':','_').replace('|','__')+'.json'),payload)
        return engine.batch(stage,jobs)
    jobs=[];candidates=[]
    for item in items:
        for k in range(1,cfg['candidates_per_target']+1):
            key=f"B|{item['target_id']}|K{k}"
            candidates.append(dict(key=key,target_id=item['target_id'],candidate_index=k))
            jobs.append((key,generation_payload(item,'B',rubric,catalog),lambda x,it=item:validate_reason(x,it)))
    generated=batch('generate',jobs); jobs=[]
    for c in candidates:
        reason=generated[c['key']];c['original_reason']=reason
        if reason is None: continue
        safe,logs,residual=masked_reason(reason)
        assert not residual
        payload=verification_payload(byid[c['target_id']],safe,rubric)
        assert set(payload['target'])=={'essay_id','text'}
        assert not any('condition_ids' in x for x in safe['claims'])
        c['mask']=dict(masked_reason=safe,logs=logs,residual=residual,
            target_score_fields_absent=True,target_linked_condition_ids_absent=True)
        save(out/'masks'/(c['key'].replace(':','_').replace('|','__')+'.json'),c['mask'])
        jobs.append((c['key'],payload,valid_score))
    verified=batch('verify',jobs);jobs=[]
    for c in candidates:
        v=verified.get(c['key']);c['verification']=v
        c['score_match']=bool(v and v['predicted_overall']==byid[c['target_id']]['target']['overall'])
        if not c['score_match']: continue
        item=byid[c['target_id']]
        payload=dict(claims=masked_reason(c['original_reason'])[0]['claims'],
                     essays=[{k:e[k] for k in ['essay_id','text','spans']} for e in [item['target'],*item['history']]])
        jobs.append((c['key'],payload,lambda x,it=item,cl=c['original_reason']['claims']:validate_ground(x,cl,it)))
    grounded=batch('ground',jobs);groups=[];cmap={}
    for item in items:
        eligible=[]
        for c in candidates:
            if c['target_id']!=item['target_id']: continue
            review=grounded.get(c['key']);c['grounding_review']=review
            for claim in (c['original_reason'] or {}).get('claims',[]):
                claim['id']=f"{item['target_id']}/K{c['candidate_index']}/{claim['claim_id']}"
                claim['target_id']=item['target_id'];claim['candidate_index']=c['candidate_index']
                r=next((r for r in (review or {}).get('reviews',[]) if r['claim_id']==claim['claim_id']),None)
                claim['grounding_review']=r
                claim['eligible_for_integration']=bool(c['score_match'] and r and r['verdict']=='supported' and claim['scope']=='target')
                if claim['eligible_for_integration']:
                    spans={s['span_id']:s for s in item['target']['spans']}
                    claim['effective_evidence_ids']=list(dict.fromkeys(claim['span_ids']+r['added_span_ids']))
                    claim['evidence']=[dict(essay_id=item['target_id'],**spans[s]) for s in claim['effective_evidence_ids']]
                    eligible.append(claim);cmap[claim['id']]=claim
        groups.append(dict(target_id=item['target_id'],observed_overall=item['target']['overall'],
            observed_traits=item['target']['traits'],eligible_claims=eligible))
    save(out/f'{scope}_candidates.json',candidates)
    jobs=[]
    for g in groups:
        if not g['eligible_claims']: continue
        cm={c['id']:c for c in g['eligible_claims']}
        jobs.append((f"B|{g['target_id']}",dict(claims=g['eligible_claims']),
            lambda x,cm=cm:validate_refs(x,cm,['groups','differences'])))
    merged=batch('merge',jobs)
    for g in groups: g['candidate_comparison']=merged.get(f"B|{g['target_id']}")
    essays=[g for g in groups if g['eligible_claims']]
    integrated=None
    if essays:
        integrated=batch('integrate',[(f'B|{scope}_rater_7',dict(essays=essays),lambda x:validate_integration(x,cmap))])[f'B|{scope}_rater_7']
    topics=[]
    for pattern in (integrated or {}).get('judgment_patterns',[]):
        refs=[cid for s in pattern['support'] for cid in s['claim_ids']]
        topics.append(dict(topic_id=pattern['pattern_id'],status='inferred_judgment_candidate',pattern=pattern,claim_ids=refs))
    if not topics:
        for g in essays:
            topics.append(dict(topic_id='local_'+g['target_id'],status='common_judgment_undetermined',
                pattern=None,claim_ids=[c['id'] for c in g['eligible_claims']]))
    jobs=[]
    for topic in topics:
        for tid in dict.fromkeys(cmap[c]['target_id'] for c in topic['claim_ids']):
            cm={c:cmap[c] for c in topic['claim_ids'] if cmap[c]['target_id']==tid}
            key=f"B|{scope}_{topic['topic_id']}_{tid}"
            payload=dict(target=byid[tid]['target'],claims=list(cm.values()),topic=topic,
                         condition_catalog=catalog,official_rubric=rubric['scores'])
            jobs.append((key,payload,lambda x,it=byid[tid],cm=cm,key=key:validate_comparison(x,it,cm,catalog,key)))
    comparisons=batch('compare',jobs);jobs=[];text_payloads={}
    for topic in topics:
        keys=[k for k in comparisons if k.startswith(f"B|{scope}_{topic['topic_id']}_")]
        issues={x['id']:x for k in keys for x in (comparisons[k] or {}).get('relationships',[])}
        if not issues: continue
        refs=set(c for x in issues.values() for c in x['claim_ids'])
        # 全体の傾向を文章化する際だけ、その傾向の支持主張を含める。
        if topic['pattern']: refs.update(topic['claim_ids'])
        payload=dict(topic=topic,claims={c:cmap[c] for c in refs},issues=issues,
            conditions={cid:catalog[cid] for i in issues.values() for cid in i['condition_ids']})
        key=f"B|{scope}_{topic['topic_id']}";text_payloads[key]=payload
        jobs.append((key,payload,lambda x,p=payload:validate_text(x,p)))
    texts=batch('text',jobs)
    result=dict(timestamp=now(),version=cfg['version'],scope=scope,target_ids=list(byid),candidates=candidates,
        essay_groups=groups,synthesis=integrated,topics=topics,comparisons=comparisons,texts=texts,
        text_payloads=text_payloads,semantic_status='provisional model outputs, awaiting Codex development review')
    save(out/f'{scope}_results.json',result)
    summary=dict(targets=len(items),candidates=len(candidates),generated=sum(c['original_reason'] is not None for c in candidates),
        verification_success=sum(c.get('verification') is not None for c in candidates),score_matches=sum(c['score_match'] for c in candidates),
        evidence_eligible_claims=len(cmap),evidence_eligible_targets=len(essays),
        common_features=len((integrated or {}).get('common_features',[])),
        judgment_patterns=len((integrated or {}).get('judgment_patterns',[])),
        comparisons_succeeded=sum(x is not None for x in comparisons.values()),comparisons_attempted=len(comparisons),
        texts_succeeded=sum(x is not None for x in texts.values()),texts_attempted=len(texts))
    save(out/f'{scope}_summary.json',summary)
    save(out/'status.json',dict(timestamp=now(),status='completed_with_recorded_failures' if any(x is None for x in [*comparisons.values(),*texts.values()]) else 'completed',scope=scope,summary=summary))
    print(json.dumps(summary,ensure_ascii=False),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('scope',choices=['prepare','one','three']);args=parser.parse_args()
    cfg=bootstrap();out=prepare(cfg)
    if args.scope=='prepare': return
    if args.scope=='three':
        assert load(out/'one_review.json')['proceed_to_fixed_three'], 'Review one case before three-case execution'
    from .feedback_development_engine import Engine
    save(out/'status.json',dict(timestamp=now(),status='running',scope=args.scope))
    try: run(cfg,out,Engine(cfg,out),args.scope)
    except BaseException:
        save(out/'status.json',dict(timestamp=now(),status='failed',scope=args.scope,traceback=traceback.format_exc()))
        raise


if __name__=='__main__': main()
