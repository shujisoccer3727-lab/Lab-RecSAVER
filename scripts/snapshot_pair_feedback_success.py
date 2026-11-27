"""Record immutable successful smoke outputs and prove reuse after the full run."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save, sha

ap = argparse.ArgumentParser()
ap.add_argument('phase', choices=['snapshot', 'verify'])
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
path = out / 'smoke_success_snapshot.json'
if args.phase == 'snapshot':
    assert not path.exists()
    files = {}
    for stage in [1, 3, 4]:
        for result in (out / f'stage{stage}').glob('*/result.json'):
            if read(result)['schema_valid']:
                for name in ['raw.txt', 'parsed.json', 'generation.json', 'input.json', 'sampling.json']:
                    f = result.parent / name
                    files[str(f.relative_to(out))] = sha(f)
    save(path, files)
    print('Snapshot files:', len(files))
else:
    files = read(path)
    changed = [f for f, h in files.items() if sha(out / f) != h]
    save(out / 'smoke_reuse_checks.json', dict(passed=not changed, checked_files=len(files), changed=changed))
    assert not changed, changed
    print('Reused without modification:', len(files))
