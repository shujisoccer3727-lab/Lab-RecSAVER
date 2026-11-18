"""版2.1の固定3答案を、必要な空きがある場合のみ同じ設定で実行する。"""
import subprocess
import sys
import time
from src.recsaver.rater_feedback_development_v21 import ROOT,CONFIG,load,save,append,now


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir']
    assert load(out/'one_review.json')['proceed_to_fixed_three']
    deadline=time.monotonic()+900
    while time.monotonic()<deadline:
        q=subprocess.run(['nvidia-smi','--query-gpu=memory.free,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
        free,total=map(int,q.stdout.strip().splitlines()[0].split(','));required=int(total*cfg['model']['gpu_memory_utilization'])+1024
        row=dict(timestamp=now(),free_mib=free,required_mib=required,scope='three')
        append(out/'gpu_wait.jsonl',row);print(row,flush=True)
        if free>=required:
            sys.exit(subprocess.run([sys.executable,'-m','src.recsaver.rater_feedback_development_v21','three'],cwd=ROOT).returncode)
        save(out/'status.json',dict(timestamp=now(),status='waiting_for_gpu',scope='three',one_case_completed=True,last_check=row))
        time.sleep(20)
    save(out/'status.json',dict(timestamp=now(),status='gpu_wait_timeout',scope='three',one_case_completed=True,
        reason='Other GPU workload; model and generation settings maintained; no other process stopped'))
    sys.exit(3)


if __name__=='__main__':main()
