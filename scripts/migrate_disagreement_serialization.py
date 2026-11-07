"""生成条件を一切変えないboolシリアライズ修正だけを、証跡付きで移行する。"""
from pathlib import Path
import json
import sys
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from src.recsaver.config import load_config
from src.recsaver.human_score_disagreement import digest
from src.recsaver.reasoning_eval_v1 import atomic_json,sha
config=load_config('configs/human_score_disagreement.yaml');out=root/config['output_dir']
before=out/'serialization_fix/source_before.py'
after=root/'src/recsaver/human_score_disagreement.py'
old_text=before.read_text(encoding='utf-8')
new_text=after.read_text(encoding='utf-8')
old_line="human_review_columns_blank=pd.read_csv(out/'human_review.csv')[REVIEW].isna().all().all())"
new_line="human_review_columns_blank=bool(pd.read_csv(out/'human_review.csv')[REVIEW].isna().all().all()))"
assert old_text.replace(old_line,new_line)==new_text
md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
assert md['source_sha256']['implementation']==sha(before)
assert all(sha(root/path)==md['source_sha256'][k] for k,path in md['source_paths'].items() if k!='implementation')
clean={k:v for k,v in config.items() if not k.startswith('_')}
assert md['fingerprint']==digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
prior=md['fingerprint'];md['source_sha256']['implementation']=sha(after)
md['fingerprint']=digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
md.setdefault('code_migrations',[]).append(dict(timestamp=datetime.now(timezone.utc).isoformat(),previous_fingerprint=prior,
    reason='Only cast pandas/numpy boolean to Python bool for phase-validation JSON; generation, prompts, seeds, inputs unchanged',
    previous_source_snapshot='serialization_fix/source_before.py'))
atomic_json(out/'metadata.json',md)
print('Validated serialization-only migration; preserved all inference journals')
