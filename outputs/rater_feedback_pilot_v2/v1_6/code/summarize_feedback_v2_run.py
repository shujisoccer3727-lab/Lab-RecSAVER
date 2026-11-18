"""実測の段階別進捗・失敗・候補採否・引用・条件選択を集計。"""
import collections
import json
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now,sha


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    calls=[json.loads(s) for s in (out/'calls.jsonl').read_text(encoding='utf-8').splitlines()] if (out/'calls.jsonl').exists() else []
    stages=collections.defaultdict(collections.Counter)
    for c in calls:
        s=stages[c['stage']];s['calls']+=1;s[c['status']]+=1
        s['reused_call_records']+=bool(c.get('reused_not_new_call'))
        s['new_model_calls']+=not c.get('reused_not_new_call',False)
        s['length_finish']+=c.get('finish_reason')=='length'
    phase='full' if (out/'full_results.json').exists() else 'pilot'
    p=out/f'{phase}_results.json'
    summary=dict(timestamp=now(),stages={k:dict(v) for k,v in stages.items()},failures=[{k:c.get(k) for k in ['stage','key','attempt','error','finish_reason','output_tokens']} for c in calls if c['status']!='ok'])
    if p.exists():
        snap=load(p)
        groups=snap['essay_groups'];cs=snap['candidates']
        summary.update(phase=phase,target_count=len(snap['target_ids']),conditions={},raters=[])
        for cond in cfg['conditions']:
            entries=[c for c in cs if c['condition']==cond]
            claims=[cl for c in entries if c.get('original_reason') for cl in c['original_reason']['claims']]
            reviewed=[cl for cl in claims if cl.get('grounding_review')]
            ids={c['target_id'] for c in entries if c['accepted']}
            eligible_ids={g['target_id'] for g in groups if g['condition']==cond and g['eligible_claims']}
            summary['conditions'][cond]=dict(candidates=len(entries),generated=sum(bool(c.get('original_reason')) for c in entries),accepted=sum(c['accepted'] for c in entries),accepted_targets=sorted(ids),eligible_evidence_targets=sorted(eligible_ids),claims=len(claims),history_claims=sum(c['scope']=='history' for c in claims),mechanically_invalid=sum(not all(c['machine_check'].values()) for c in claims),reviewed_claims=len(reviewed),semantic_support_counts=dict(collections.Counter(c['grounding_review']['support'] for c in reviewed)),eligible_claims=sum(len(g['eligible_claims']) for g in groups if g['condition']==cond))
            inputs={i['target_id']:i for i in load(out/'inputs.json')}
            score_buckets={}
            for score in range(1,6):
                bucket=[c for c in entries if inputs[c['target_id']]['target']['overall']==score]
                if bucket:
                    score_buckets[str(score)]=dict(candidate_count=len(bucket),generated=sum(bool(c.get('original_reason')) for c in bucket),accepted=sum(c['accepted'] for c in bucket),selected_targets=len({c['target_id'] for c in bucket}),accepted_targets=len({c['target_id'] for c in bucket if c['accepted']}))
            summary['conditions'][cond]['adoption_by_observed_overall']=score_buckets
        a=set(summary['conditions']['A']['accepted_targets']);b=set(summary['conditions']['B']['accepted_targets'])
        summary['adoption_difference']=dict(A_only=sorted(a-b),B_only=sorted(b-a),common=sorted(a&b))
        for result in snap['results']:
            rels=[r for obj in result['comparisons'].values() if obj for r in obj['relationships']]
            level_counts=collections.Counter(c['level'] for r in rels for c in r['official_conditions'])
            facets=collections.Counter(c['aspect'] for r in rels for c in r['official_conditions'])
            summary['raters'].append(dict(condition=result['condition'],rater_id=result['rater_id'],generation_status=result['generation_status'],patterns=len(result['synthesis']['patterns']),relationships=len(rels),official_level_counts=dict(level_counts),official_aspect_counts=dict(facets)))
    save(out/'run_metrics.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
