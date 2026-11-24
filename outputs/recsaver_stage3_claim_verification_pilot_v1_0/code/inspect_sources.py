"""Inventory saved accepted data without looking at new model outputs."""
from pathlib import Path
import json,csv,collections
ROOT=Path(__file__).resolve().parents[3]
for name in ['recsaver_mvp/verified_reference_pool.jsonl','recsaver_prompt_v1_2_value_mask_20261121/candidate_results.csv','recsaver_prompt_v1_1_validation_20261120/candidate_results.csv','recsaver_prompt_v1_0_initial_20261118/candidate_results.csv']:
    p=ROOT/'outputs'/name
    if p.suffix=='.jsonl':
        rows=[json.loads(l) for l in p.read_text().splitlines()]
        groups=collections.defaultdict(dict)
        for r in rows:
            groups[r['rater_id']][r['target_id']]=dict(overall=r.get('gold_overall'),candidate_id=r.get('candidate_id'),verified=r.get('verified'),score_leak=r.get('score_leak'),keys=list(r))
        print(name,json.dumps(groups,ensure_ascii=False))
    else:
        rows=list(csv.DictReader(p.open()))
        print(name,json.dumps([r for r in rows if r['accepted']=='True']))
print('Other candidate acceptance artifacts:')
for p in sorted((ROOT/'outputs').glob('**/*')):
    if p.is_file() and p.suffix in ['.jsonl','.csv'] and any(s in p.name.lower() for s in ['accepted','verified','candidate_result']):
        print(p.relative_to(ROOT))
