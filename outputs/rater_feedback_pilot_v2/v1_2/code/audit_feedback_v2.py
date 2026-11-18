"""生成前後に共通する独立した機械監査。生成しない。"""
import collections
import json
from src.recsaver.rater_feedback_pilot_v2 import ROOT, load, sha, save, now, LEAK_PATTERNS
import re


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    items=load(out/'inputs.json');byid={i['target_id']:i for i in items}
    config=load(out/'resolved_config.json');conditions=load(out/'conditions.json')
    checks=[];errors=[]
    def check(name,ok,detail=None):
        checks.append(dict(check=name,passed=bool(ok),detail=detail))
        if not ok: errors.append(name)
    for path,original_hash in config['source_sha256'].items():
        check('source unchanged: '+path,sha(ROOT/path)==original_hash)
    check('27 unique targets',len(byid)==len(items)==27)
    check('same three raters and counts',dict(collections.Counter(i['rater_id'] for i in items))=={'rater_7':10,'rater_17':7,'rater_4':10})
    for item in items:
        for e in [item['target'],*item['history']]:
            check('own rater '+item['target_id']+'/'+e['essay_id'],e['rater_id']==item['rater_id'])
            check('lossless spans '+e['essay_id'],''.join(s['text'] for s in e['spans'])==e['text'])
            check('exact offsets '+e['essay_id'],all(e['text'][s['start']:s['end']]==s['text'] for s in e['spans']))
    for cid,c in conditions.items():
        check('official condition '+cid,c['parent_text'][c['start']:c['end']]==c['text'])
    all_results=out/('full_results.json' if (out/'full_results.json').exists() else 'pilot_results.json')
    counts=collections.Counter();semantic=collections.Counter();mask_events=0
    if all_results.exists():
        snapshot=load(all_results)
        for c in snapshot['candidates']:
            counts[c['condition']+'_generated']+=bool(c.get('original_reason'))
            counts[c['condition']+'_accepted']+=c['accepted']
            if c.get('verification_input'):
                p=load(out/c['verification_input']);target=byid[c['target_id']]['target']
                check('verify target whitelist '+c['key'],set(p['target'])=={'essay_id','text'})
                check('verify target exact text '+c['key'],p['target']['text']==target['text'])
                check('verify history whitelist '+c['key'],all(set(h)=={'essay_id','text','overall'} for h in p['history']))
                check('verify no linked condition IDs '+c['key'],'condition_ids' not in json.dumps(p['masked_reason']))
                reason=p['masked_reason'];free=[reason['rationale'],reason['unexplained']]
                free.extend(v for cl in reason['claims'] for k,v in cl.items() if k in ['feature','score_relation','support_explanation','limits'])
                leaks=[(r,m.group()) for text in free for r,pat in LEAK_PATTERNS for m in re.finditer(pat,text,re.I)]
                check('verify direct score scan '+c['key'],not leaks,leaks)
                mask_events+=len(load(out/c['mask_artifact'])['mask_log'])
            if c.get('grounding_review'):
                semantic.update(r['support'] for r in c['grounding_review']['reviews'])
            if c['accepted']:
                check('accepted only on exact Overall '+c['key'],c['verification']['predicted_overall']==byid[c['target_id']]['target']['overall'])
        for g in snapshot['essay_groups']:
            check('one independent essay '+g['condition']+g['target_id'],g['independent_essay_count'] in [0,1])
            for c in g['eligible_claims']:
                check('eligible target supported '+c['id'],c['scope']=='target' and all(c['machine_check'].values()) and c['grounding_review']['support']=='supported')
        for result in snapshot['results']:
            for p in result['synthesis']['patterns']:
                check('two distinct supports '+result['condition']+p['pattern_id'],len({s['target_id'] for s in p['support']})>=2)
            for tid,obj in result['comparisons'].items():
                if obj is None: continue
                for r in obj['relationships']:
                    target=byid[tid]['target']
                    check('comparison full target '+tid,r['full_target_seen'])
                    check('comparison official IDs '+tid,all(cid in conditions for cid in r['condition_ids']))
                    check('comparison exact quotes '+tid,all(target['text'][q['start']:q['end']]==q['text'] for q in r['citations']))
                    check('action linked to issue '+tid,bool(r['next_action']['distinguish']) and bool(r['next_action']['action']) and bool(r['next_action']['where_span_ids']))
        phase=snapshot['phase']
    else:
        phase='prepared; no generated results'
    audit=dict(timestamp=now(),phase=phase,all_machine_checks_passed=not errors,errors=errors,
               counts=dict(counts),semantic_model_assessments=dict(semantic),mask_events=mask_events,
               checks=checks,limitation='Semantic correctness, usefulness, true rater reasoning and causal Trait effects are not established.')
    save(out/'independent_audit.json',audit)
    print(json.dumps({k:v for k,v in audit.items() if k!='checks'},ensure_ascii=False),flush=True)
    assert not errors,errors


if __name__=='__main__':
    main()
