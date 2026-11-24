from pathlib import Path
import json,csv
ROOT=Path(__file__).resolve().parents[3]
ids={'8699:1','873:1','2016:1','2387:1','3650:1','5293:1'}
with (ROOT/'data/processed/rater_essay_wide.csv').open(newline='',encoding='utf-8-sig') as f:
    for r in csv.DictReader(f):
        eid=r['source_row_id']+':'+r['rater_position']
        if eid in ids:
            print(json.dumps(dict(essay_id=eid,rater_id=r['rater_id'],scores={d:r[d] for d in ['Overall','Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']},text=r['Text']),ensure_ascii=False))
case=json.loads((ROOT/'outputs/recsaver_prompt_v1_0_initial_20261118/case_manifest.json').read_text())
print('Prior development cases:',json.dumps(case,ensure_ascii=False)[:300])
