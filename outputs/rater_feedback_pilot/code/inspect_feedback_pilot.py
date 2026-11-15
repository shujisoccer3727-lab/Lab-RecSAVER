import json, csv, sys, importlib.util
from pathlib import Path
root=Path(__file__).resolve().parents[1]
print('python',sys.version)
print('vllm',bool(importlib.util.find_spec('vllm')))
import torch
print('cuda',torch.cuda.is_available())
for name in ['verified_reference_pool.jsonl','reference_candidates.jsonl','self_verification_results.jsonl']:
    rows=[json.loads(s) for s in (root/'outputs/reasoning_eval_large'/name).read_text().splitlines()]
    print(name,len(rows),list(rows[0]))
    print({k:v for k,v in rows[0].items() if k not in ['prompt','raw_model_output','reference_reasoning']})
for f in ['data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv','data/processed/rater_essay_wide.csv']:
    with (root/f).open(newline='',encoding='utf-8') as h:
        rows=list(csv.DictReader(h))
    print(f,len(rows),{k:v for k,v in rows[0].items() if k!='Text'})
print('docx',list(root.rglob('*.docx')))
print('metadata',json.loads((root/'outputs/reasoning_eval_large/metadata.json').read_text()).keys())
