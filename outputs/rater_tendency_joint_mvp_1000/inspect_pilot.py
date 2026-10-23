"""CPU-only inspection helpers; does not alter predictions or generation config."""
import json
from pathlib import Path
import numpy as np
from src.recsaver import rater_tendency_joint_mvp_1000 as experiment

out = Path(__file__).resolve().parent
rows = experiment.read(out / 'predictions.jsonl')
manifest = {r['target_id']:r for r in experiment.read(out / 'target_history_manifest.jsonl')}
references = experiment.read(experiment.ROOT / 'outputs/reasoning_eval_v1/verified_reference_pool.jsonl')
overlap = [r for r in references if r['target_id'] in manifest]
matching = [r for r in overlap if r['history_ids'] == manifest[r['target_id']]['correct_history_ids']]
summary = {'completed':len(rows), 'valid':sum(r['parse_success'] for r in rows),
           'reference_overlap_targets':len({r['target_id'] for r in overlap}),
           'reference_matching_history_targets':len({r['target_id'] for r in matching})}
if rows:
    tokens = [a['output_tokens'] for r in rows for a in r['attempts']]
    summary['output_tokens_min_median_max'] = [int(min(tokens)), float(np.median(tokens)), int(max(tokens))]
print(json.dumps(summary, indent=2))
for r in rows:
    if not r['parse_success']:
        continue
    print(json.dumps({'id':r['target_id'], 'score':r['predicted_overall'],
                      'tendency':r['rater_tendency'], 'reasoning':r['reasoning']}, ensure_ascii=False))
