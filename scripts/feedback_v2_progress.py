"""キャッシュ済み段階と実呼出し数の進捗。完了数と対象選択数を区別する。"""
import collections
import json
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    result=dict(timestamp=now(),status=load(out/'status.json')['status'],stages={})
    for stage in ['generate','verify','ground','merge','integrate','compare','text']:
        files=list((out/'stages'/stage).glob('*.json'))
        values=[load(p) for p in files]
        result['stages'][stage]=dict(saved=len(values),succeeded=sum(v['result'] is not None for v in values),failed=sum(v['result'] is None for v in values))
    rows=[json.loads(s) for s in (out/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    result['new_model_calls']=sum(not c.get('reused_not_new_call',False) for c in rows)
    result['reused_call_records']=sum(bool(c.get('reused_not_new_call')) for c in rows)
    result['latest_context_stage']=json.loads((out/'context_checks.jsonl').read_text(encoding='utf-8').splitlines()[-1])['stage']
    result['full_snapshot_saved']=(out/'full_results.json').exists()
    save(out/'progress.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
