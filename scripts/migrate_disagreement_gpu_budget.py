"""GPU確保量だけの運用変更を検証し、科学的条件が同じjournalを引き継ぐ。"""
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
previous=yaml.safe_load((out/'startup_gpu_060/resolved_config.yaml').read_text(encoding='utf-8'))
assert dict(previous,runtime_gpu_memory_utilization=0.50)==clean
md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
assert all(sha(root/path)==md['source_sha256'][k] for k,path in md['source_paths'].items())
assert md['fingerprint']==digest(json.dumps(dict(config=previous,hashes=md['source_sha256']),sort_keys=True))
md.setdefault('runtime_migrations',[]).append(dict(timestamp=datetime.now(timezone.utc).isoformat(),
    previous_fingerprint=md['fingerprint'],old_gpu_memory_utilization=.60,new_gpu_memory_utilization=.50,
    reason='VRAM usage reached 48GB and one batch stalled; reduce GPU reservation only; model/prompts/history/sampling/seeds unchanged'))
md['fingerprint']=digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
atomic_json(out/'metadata.json',md)
print('GPU allocation-only migration validated; existing inference journals retained')
