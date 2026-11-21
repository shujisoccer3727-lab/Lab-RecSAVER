from pathlib import Path
import subprocess,sys,json,os
out=Path(__file__).resolve().parents[1]
if (out/'process.json').exists():
    pid=json.loads((out/'process.json').read_text())['pid']
    try:os.kill(pid,0)
    except ProcessLookupError:pass
    else:raise SystemExit('Worker already exists')
with (out/'execution.log').open('ab',buffering=0) as log:
    child=subprocess.Popen([sys.executable,'-u',str(out/'code/run.py'),'--phase','worker'],cwd=out.parents[1],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
(out/'process.json').write_text(json.dumps(dict(pid=child.pid))+'\n');print(child.pid)
