"""チャット側セッションの消失と独立した実行。二重起動を防ぎログを保持する。"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from src.recsaver.rater_feedback_development import ROOT,CONFIG,load,save,now,append


def main():
    parser=argparse.ArgumentParser();parser.add_argument('scope',choices=['one','three','guidance','wait_one']);a=parser.parse_args()
    cfg=load(CONFIG);out=ROOT/cfg['output_dir']
    process_file=out/'process.json'
    if process_file.exists():
        last=load(process_file)
        path=Path('/proc')/str(last['pid'])/'cmdline'
        if path.exists() and b'feedback_development' in path.read_bytes():
            raise RuntimeError(f"Already running PID {last['pid']}")
    previous=load(out/'status.json') if (out/'status.json').exists() else None
    if previous and previous['status']=='running':
        append(out/'execution_history.jsonl',dict(timestamp=now(),event='prior_process_absent',previous_status=previous,
            cause='unknown; log ended during model loading; not evidence of completed generation'))
    number=len(list(out.glob(a.scope+'_attempt_*.log')))+1
    path=out/f'{a.scope}_attempt_{number:02}.log'
    command=[sys.executable,'-m','src.recsaver.rater_feedback_development',a.scope]
    if a.scope=='guidance': command=[sys.executable,'-c',"import runpy; runpy.run_path('scripts/check_feedback_development_guidance.py',run_name='__main__')"]
    if a.scope=='wait_one': command=[sys.executable,'-c',"import runpy; runpy.run_path('scripts/wait_feedback_development_gpu.py',run_name='__main__')"]
    with path.open('wb') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record=dict(timestamp=now(),pid=process.pid,scope=a.scope,log=path.relative_to(ROOT).as_posix(),command=command)
    save(process_file,record);append(out/'execution_history.jsonl',dict(event='launch',**record))
    print(json.dumps(record,ensure_ascii=False))


if __name__=='__main__':main()
