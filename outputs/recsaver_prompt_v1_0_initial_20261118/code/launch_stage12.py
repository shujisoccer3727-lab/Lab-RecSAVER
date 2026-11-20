"""Launch existing stage12 runner with a persistent log and detached process."""
from pathlib import Path
import datetime, json, os, subprocess, sys

out=Path(__file__).resolve().parents[1]
state=out/'background_process.json'
if state.exists():
    old=json.loads(state.read_text(encoding='utf-8'))
    try:
        os.kill(old['pid'],0)
    except ProcessLookupError:
        pass
    else:
        raise SystemExit('Existing background PID is still present; inspect before launching again.')
stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
with (out/'execution_events.jsonl').open('a',encoding='utf-8') as f:
    f.write(json.dumps(dict(time=stamp,kind='resume_after_interruption',fact='No prior runner process or raw/result files found; prior termination cause unknown. Resume without changing frozen code, prompts, cases, seeds or parameters.'))+'\n')
log=(out/'execution.log').open('ab',buffering=0)
p=subprocess.Popen([sys.executable,'-u',str(out/'code/run.py'),'--phase','stage12'],cwd=out.parents[1],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
record=dict(pid=p.pid,started_at=stamp,phase='stage12',log='execution.log',command=[sys.executable,str(out/'code/run.py'),'--phase','stage12'])
state.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record))
