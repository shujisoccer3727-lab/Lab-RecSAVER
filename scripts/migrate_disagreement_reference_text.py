"""監査で検出した4対象だけを隔離し、共通本文で参照生成を再実行する。"""
from pathlib import Path
from datetime import datetime,timezone
import json
import os
import shutil
import sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from src.recsaver.config import load_config
from src.recsaver.human_score_disagreement import digest
from src.recsaver.reasoning_eval_v1 import atomic_json,sha
from src.recsaver.utils import read_jsonl,write_jsonl
config=load_config('configs/human_score_disagreement.yaml');out=root/config['output_dir'];backup=out/'reference_text_fix'
old_source=(backup/'source_before.py').read_text(encoding='utf-8')
new_source=(root/'src/recsaver/human_score_disagreement.py').read_text(encoding='utf-8')
assert old_source.replace("target_essay=target.Text, gold_overall=item['gold_overall'])",
                          "target_essay=item['essay'], gold_overall=item['gold_overall'])")==new_source
md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
assert sha(backup/'source_before.py')==md['source_sha256']['implementation']
assert all(sha(root/path)==md['source_sha256'][k] for k,path in md['source_paths'].items() if k!='implementation')
affected={r['target_id'] for r in json.loads((out/'prompt_audit_mismatches.json').read_text(encoding='utf-8'))}
assert affected=={'479:1','479:2','816:2','5081:1'}
counts={}
for filename in ['reference_candidates.jsonl','self_verification_results.jsonl','verified_reference_pool.jsonl','metric_pairs.jsonl']:
    path=out/filename;records=read_jsonl(path)
    assert not (backup/filename).exists(), 'Migration already started; inspect backup before retrying'
    shutil.copy2(path,backup/filename)
    removed=[r for r in records if r['target_id'] in affected]
    write_jsonl(backup/(filename+'.quarantined.jsonl'),removed)
    temporary=out/(filename+'.migrating')
    write_jsonl(temporary,[r for r in records if r['target_id'] not in affected])
    os.replace(temporary,path);counts[filename]=len(removed)
clean={k:v for k,v in config.items() if not k.startswith('_')}
assert md['fingerprint']==digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
prior=md['fingerprint'];md['source_sha256']['implementation']=sha(root/'src/recsaver/human_score_disagreement.py')
md['fingerprint']=digest(json.dumps(dict(config=clean,hashes=md['source_sha256']),sort_keys=True))
md.setdefault('code_migrations',[]).append(dict(timestamp=datetime.now(timezone.utc).isoformat(),
    previous_fingerprint=prior,affected_targets=sorted(affected),quarantined_records=counts,
    reason='Reference renderer incorrectly used original text for four anonymization variants; use identical canonical essay for prediction/reference/verification. Unaffected target outputs and all predictions retained.',
    previous_source_snapshot='reference_text_fix/source_before.py'))
md['status']='reference_text_correction_pending'
atomic_json(out/'metadata.json',md)
atomic_json(backup/'migration.json',dict(affected_targets=sorted(affected),quarantined_records=counts,
    prediction_records_unchanged=True,unaffected_reference_records_unchanged=True))
print(json.dumps(dict(affected_targets=sorted(affected),quarantined_records=counts),ensure_ascii=False))
