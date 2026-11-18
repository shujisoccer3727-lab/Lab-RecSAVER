"""他処理を止めず、空きGPUを最大15分待って指定1答案だけを実行する。"""
import subprocess
import sys
import time
from src.recsaver.rater_feedback_development import ROOT,CONFIG,load,save,now,append


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir'];deadline=time.monotonic()+900
    save(out/'status.json',dict(timestamp=now(),status='waiting_for_gpu',scope='one',max_wait_seconds=900))
    while time.monotonic()<deadline:
        query=subprocess.run(['nvidia-smi','--query-gpu=memory.free,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
        free,total=map(int,query.stdout.strip().splitlines()[0].split(','))
        required=int(total*cfg['model']['gpu_memory_utilization'])+1024
        row=dict(timestamp=now(),free_mib=free,required_mib=required)
        append(out/'gpu_wait.jsonl',row);print(row,flush=True)
        if free>=required:
            append(out/'execution_history.jsonl',dict(timestamp=now(),event='gpu_ready_start_one'))
            completed=subprocess.run([sys.executable,'-m','src.recsaver.rater_feedback_development','one'],cwd=ROOT)
            sys.exit(completed.returncode)
        time.sleep(20)
    save(out/'status.json',dict(timestamp=now(),status='gpu_wait_timeout',scope='one',model_called=False,
        reason='Another workload retained GPU memory; no other process stopped; run one when GPU is available.'))
    sys.exit(3)


if __name__=='__main__':main()
