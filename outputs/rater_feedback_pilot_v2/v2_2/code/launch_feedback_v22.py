import json
import os
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1];out=root/'outputs/rater_feedback_pilot_v2/v2_2'
if (out/'process.json').exists():
    prior=json.loads((out/'process.json').read_text())
    if Path('/proc',str(prior['pid']),'cmdline').exists():
        raise RuntimeError('Existing process; do not launch twice')
log=root/'outputs/rater_feedback_pilot_v2/v2_2_attempt_01.log'
with log.open('ab') as handle:
    p=subprocess.Popen([sys.executable,'-c',"import runpy;runpy.run_path('scripts/resume_feedback_v22.py',run_name='__main__')"],cwd=root,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
    process=dict(pid=p.pid,log=str(log))
    # 起動直後のbootstrap中も二重起動を防ぐ。
    out.mkdir(parents=True,exist_ok=True)
    (out/'process.json').write_text(json.dumps(process),encoding='utf-8')
print(json.dumps(dict(pid=p.pid,log=str(log))))
