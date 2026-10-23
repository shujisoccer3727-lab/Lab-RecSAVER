"""CPU-only candidate selection; exact quotations are not semantic validation."""
import json
import re
from src.recsaver import rater_tendency_grounded_pilot_v2 as rev
from src.recsaver.rater_tendency_grounded_review_v2 import quotes

rev.setup()
core = rev.core
frame = core.previous.data()
rows = core.records()
ranked = []
for tid, r in rows.items():
    if not r['parse_success'] or r['predicted_overall'] != frame.loc[tid,'Overall']:
        continue
    description = r['rater_tendency']['description']
    if description.lower().startswith('insufficient'):
        continue
    qs = quotes(r['reasoning']['essay_evidence'])
    exact = [q for q in qs if q in str(frame.loc[tid,'Text'])]
    if len(exact) < 2:
        continue
    ids = r['rater_tendency']['supporting_history_ids']
    score = len(exact) + sum(h in description for h in ids) * 2
    score += 3 * (len(set(int(frame.loc[h,'Overall']) for h in ids)) > 1)
    score += 3 * bool(re.search(r'contrast|whereas|while|however',description,re.I))
    ranked.append((score,tid,r))
for score,tid,r in sorted(ranked,reverse=True)[:10]:
    print(json.dumps({'target_id':tid,'rank':score,'gold':int(frame.loc[tid,'Overall']),
          'history':[{'id':h,'overall':int(frame.loc[h,'Overall'])} for h in r['history_ids']],
          'output':{k:r[k] for k in ['predicted_overall','rater_tendency','reasoning']}},ensure_ascii=False))
