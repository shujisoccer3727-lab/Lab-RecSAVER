"""④⑤の原文語・位置・参照の追加監査。意味的妥当性は別途点検。"""
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    phase='full' if (out/'full_results.json').exists() else 'pilot'
    snap=load(out/f'{phase}_results.json');byid={i['target_id']:i for i in load(out/'inputs.json')}
    checks=[];warnings=[]
    for result in snap['results']:
        for tid,obj in result['comparisons'].items():
            if not obj: continue
            text=byid[tid]['target']['text'];spans={s['span_id']:s for s in byid[tid]['target']['spans']}
            for r in obj['relationships']:
                assert len(obj['relationships'])<=1
                assert r['analysis_anchors']
                for a in r['analysis_anchors']:
                    for t in a['token_positions']:
                        assert text[t['start']:t['end']]==t['token']
                        assert spans[a['span_id']]['start']<=t['start']<t['end']<=spans[a['span_id']]['end']
                    assert a['span_id'] in r['span_ids']
                    assert len(set(a['tokens']))>=2
                assert any(a['span_id'] in r['next_action']['where_span_ids'] for a in r['analysis_anchors'])
                checks.append(dict(condition=result['condition'],target_id=tid,issue_id=r['issue_id'],tokens=[t for a in r['analysis_anchors'] for t in a['tokens']],positions_verified=True,action_linked_to_analyzed_span=True))
                if not any(c.startswith('Overall.') for c in r['condition_ids']):
                    warnings.append(dict(condition=result['condition'],target_id=tid,issue_id=r['issue_id'],issue='Only auxiliary analytic conditions selected; no explicit Overall condition in this relationship'))
    save(out/'anchor_audit.json',dict(timestamp=now(),phase=phase,all_machine_checks_passed=True,relationships=len(checks),checks=checks,content_warnings=warnings,limitation='Real words and valid positions do not establish that the grammatical or rubric interpretation is correct.'))
    print(f'{phase}: {len(checks)} relationships; anchor positions verified; {len(warnings)} auxiliary-only warnings',flush=True)


if __name__=='__main__': main()
