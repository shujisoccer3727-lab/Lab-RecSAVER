"""入力とサンプリング条件を変えず、スケジューラのバッチ数だけを変更する。"""
from pathlib import Path
from datetime import datetime,timezone
import json
import sys
import yaml
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from src.recsaver.config import load_config
from src.recsaver.human_score_disagreement import digest
from src.recsaver.reasoning_eval_v1 import atomic_json,sha
config=load_config('configs/human_score_disagreement.yaml');out=root/config['output_dir']
clean={k:v for k,v in config.items() if not k.startswith('_')}
previous=yaml.safe_load((out/'scheduler_batch10/resolved_config.yaml').read_text(encoding='utf-8'))
assert dict(previous,batch_size=64)==clean
md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
assert all(sha(root/path)==md['source_sha256'][k] for k,path in md['source_paths'].items())
assert md['fingerprint']==digest(json.dumps(dict(config=previous,hashes=md['source_sha256']),sort_keys=True))
md.setdefault('runtime_migrations',[]).append(dict(timestamp=datetime.now(timezone.utc).isoformat(),
    previous_fingerprint=md['fingerprint'],old_batch_size=10,new_batch_size=64,
    reason='Scheduler throughput adjustment only; per-request prompts, seeds, model and SamplingParams unchanged'))
md['fingerprint']=digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
atomic_json(out/'metadata.json',md)
print('Scheduler-only migration validated; all inference journals retained')
