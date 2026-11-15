"""実行コードと設定の追記式スナップショット。認証情報にはアクセスしない。"""
import json
import shutil
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import now, save, sha

out=ROOT/'outputs/rater_feedback_pilot'
stamp=now().replace(':','_')
dest=out/'snapshots'/stamp
dest.mkdir(parents=True)
paths=[ROOT/'src/recsaver/rater_feedback_pilot.py',ROOT/'src/recsaver/model.py',ROOT/'configs/rater_feedback_pilot.json',
       *sorted((ROOT/'prompts/en').glob('rater_feedback_pilot_*.txt'))]
for p in paths:
    shutil.copy2(p,dest/p.name)
save(dest/'manifest.json',dict(timestamp=now(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths}))
print(dest)
