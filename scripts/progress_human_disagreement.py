"""保存済みjournalだけから進捗を表示する（モデルをロードしない）。"""
from pathlib import Path
from collections import Counter
import json
import re

out=Path(__file__).resolve().parents[1]/'outputs/human_score_disagreement'
def read(name):
    p=out/name
    if not p.exists():return []
    records=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        try:records.append(json.loads(line))
        except json.JSONDecodeError:pass # 稼働中の末尾書込みを次回読む
    return records
pairs=read('extracted_pairs.jsonl');refs=read('reference_candidates.jsonl');vs=read('self_verification_results.jsonl')
preds=read('predictions.jsonl');counts=Counter((r['target_id'],r['candidate_index']) for r in refs)
accepted={(r['target_id'],r['candidate_index']) for r in refs if r['accepted_as_leakage_free']}
latest={(r['target_id'],r['candidate_index']):r for r in vs}
def terminal(tid):
    return all(((tid,k) in accepted and (tid,k) in latest and
                (latest[tid,k]['parse_success'] or latest[tid,k]['attempt_index']>=2)) or
               ((tid,k) not in accepted and counts[tid,k]>=5) for k in [1,2,3])
state=json.loads((out/'execution_status.json').read_text(encoding='utf-8')) if (out/'execution_status.json').exists() else {}
summary=dict(phase=state.get('phase'),status=state.get('status'),predictions_saved=len(preds),
             new_predictions=sum(not r.get('reused',False) for r in preds),reference_attempts=len(refs),
             new_reference_attempts=sum(not r.get('reused',False) for r in refs),verification_attempts=len(vs),
             verified_references=sum(r['verified'] for r in latest.values()),by_gap={})
log=(out/'run.log').read_text(encoding='utf-8',errors='replace') if (out/'run.log').exists() else ''
matches=re.findall(r'Processed prompts:[^\r\n]+',log)
summary['running_batch']=matches[-1] if matches else ''
summary['execution_failure_count']=len(read('execution_failures.jsonl'))
exit_path=out/'runner_exit_code.txt'
summary['runner_exit_code']=exit_path.read_text(encoding='utf-8').strip() if exit_path.exists() else None
for gap in [3,2]:
    part=[p for p in pairs if p['gap']==gap];ids={p[k] for p in part for k in ['target_a','target_b']}
    summary['by_gap'][gap]=dict(pairs=len(part),targets=len(ids),completed_targets=sum(terminal(t) for t in ids),
        accepted_reference_slots=sum(t in ids for t,k in accepted),
        verified_references=sum(r['target_id'] in ids and r['verified'] for r in latest.values()))
print(json.dumps(summary,ensure_ascii=False))
