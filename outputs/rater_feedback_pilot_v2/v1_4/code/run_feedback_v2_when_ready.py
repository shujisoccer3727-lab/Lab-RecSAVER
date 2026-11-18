"""既存GPUジョブを変更せず、必要な空き容量を待って固定3答案から実行。"""
import argparse
import json
import os
import runpy
import subprocess
import sys
import time
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,append,now


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wait-minutes',type=int,default=30)
    args=parser.parse_args()
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    deadline=time.monotonic()+args.wait_minutes*60
    while True:
        gpu=subprocess.run(['nvidia-smi','--query-gpu=memory.free,memory.total,utilization.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
        free,total,util=map(int,gpu.stdout.strip().splitlines()[0].split(','))
        required=int(total*cfg['model']['gpu_memory_utilization'])+1024
        state=dict(timestamp=now(),status='waiting_for_gpu',pid=os.getpid(),free_mib=free,total_mib=total,required_mib=required,utilization_percent=util)
        append(out/'gpu_wait_history.jsonl',state)
        save(out/'gpu_wait_status.json',state)
        print(json.dumps(state,ensure_ascii=False),flush=True)
        if free>=required:
            break
        if time.monotonic()>=deadline:
            state.update(status='gpu_wait_timeout',ended_at=now())
            save(out/'gpu_wait_status.json',state)
            print('GPU wait timed out; no model call made; inputs and failures retained.',flush=True)
            return
        time.sleep(min(30,max(0,deadline-time.monotonic())))
    state.update(status='launching_pilot_and_full',started_at=now())
    save(out/'gpu_wait_status.json',state)
    sys.argv=['rater_feedback_pilot_v2','pilot-and-full']
    try:
        runpy.run_module('src.recsaver.rater_feedback_pilot_v2',run_name='__main__')
        state.update(status='completed',ended_at=now())
    except BaseException as exc:
        state.update(status='failed',error=f'{type(exc).__name__}: {exc}',ended_at=now())
        raise
    finally:
        save(out/'gpu_wait_status.json',state)


if __name__=='__main__':
    main()
