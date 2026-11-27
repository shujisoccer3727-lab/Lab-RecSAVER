"""CPU preview of current input screening; never changes generation or acceptance artifacts."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save, table, valid, inspect_mask

ap = argparse.ArgumentParser()
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
rows = []
for t in read(out / 'manifest.json')['fixed_targets']:
    for k in range(1, cfg['candidates'] + 1):
        key = t['key'] + f'__K{k}'
        f = out / 'stage1' / key
        if valid(f):
            v = inspect_mask(read(f / 'parsed.json'), t)
            a = v['audit']
            rows.append(dict(candidate_id=key, rater_id=t['rater_id'], input_pass=a['automatic_pass'],
                             masked_values=a['value_replacements'], issues=';'.join(sorted({i['kind'] for i in a['quarantine']}))))
table(out / 'mask_screen_preview.csv', rows)
summary = []
for r in [r for p in cfg['pairs'] for r in p['raters']]:
    rr = [x for x in rows if x['rater_id'] == r]
    summary.append(dict(rater_id=r, available=len(rr), input_pass=sum(x['input_pass'] for x in rr),
                        quarantined=sum(not x['input_pass'] for x in rr), issues=sorted({x['issues'] for x in rr if x['issues']})))
save(out / 'mask_screen_preview.json', summary)
print(json.dumps(summary, indent=2))
