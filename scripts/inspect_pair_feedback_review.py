"""Read-only local inspection for the post-generation provisional review."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, load_dataset, spans

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=['comparisons', 'feedback', 'findings', 'failures'])
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
if args.mode == 'comparisons':
    _, rows, _ = load_dataset(cfg)
    for pair in cfg['pairs']:
        for case in pair['cases']:
            row = next(r for r in rows if r['Filename'] == case['filename'])
            print(json.dumps(dict(pair_id=pair['pair_id'], filename=case['filename'],
                                  raters=pair['raters'], overall=case['overall'], spans=spans(row['Text'])), ensure_ascii=False))
elif args.mode == 'feedback':
    for pair in cfg['pairs']:
        for rater in pair['raters']:
            f = out / 'stage5' / rater
            print(rater)
            for name in ['parsed.json', 'render_checks.json', 'skip.json']:
                if (f / name).exists():
                    print(name, (f / name).read_text(encoding='utf-8'))
elif args.mode == 'findings':
    for f in sorted((out / 'stage4').glob('*/observations.json')):
        if read(f):
            print(f.parent.name, json.dumps(read(f), ensure_ascii=False))
else:
    for f in sorted(out.glob('stage*/*/result.json')):
        if not read(f)['schema_valid']:
            print(str(f.relative_to(out)), json.dumps(read(f)))
