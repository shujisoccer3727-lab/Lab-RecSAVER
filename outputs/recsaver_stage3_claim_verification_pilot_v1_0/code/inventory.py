from pathlib import Path
import json,collections
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
inventory=[]
for name in ['recsaver_mvp/verified_reference_pool.jsonl','human_score_disagreement/reference_text_fix/verified_reference_pool.jsonl','human_score_disagreement/verified_reference_pool.jsonl','reasoning_eval_large/verified_reference_pool.jsonl','reasoning_eval_v1/verified_reference_pool.jsonl','reasoning_eval_v1/dry_run_3/verified_reference_pool.jsonl']:
    path=ROOT/'outputs'/name
    groups=collections.defaultdict(dict);keys=[];count=0
    if not path.exists():continue
    with path.open(encoding='utf-8-sig') as f:
        for line in f:
            r=json.loads(line);keys=list(r);count+=1
            rid=r.get('rater_id',r.get('target_rater'));eid=r.get('target_id')
            groups[rid][eid]=dict(overall=r.get('gold_overall'),verified=r.get('verified',r.get('verification_pass')),score_leak=r.get('score_leak'),reconstructed=r.get('reconstructed_overall'))
    inventory.append(dict(path=name,records=count,keys=keys,groups=groups))
    print(name,'records',count,'raters',len(groups),'groups>=2',sum(len(g)>=2 for g in groups.values()),'rater_7',json.dumps(groups.get('rater_7',{})))
    print('first groups:',json.dumps({r:g for r,g in list(groups.items())[:4]}))
(OUT/'accepted_pool_inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
