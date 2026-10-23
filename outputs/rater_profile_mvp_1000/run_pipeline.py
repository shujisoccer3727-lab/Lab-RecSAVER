"""Persistently run the authorized stages; save timestamps, logs and exit codes."""
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]


def timestamp():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()


def save(value):
    temporary = OUT / 'execution_status.tmp.json'
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(OUT / 'execution_status.json')


def pipeline():
    state = {'started_at': timestamp(), 'status': 'running', 'stages': []}
    for phase in ['profiles', 'dry', 'full']:
        entry = {'phase': phase, 'started_at': timestamp(), 'status': 'running', 'log': f'{phase}.log'}
        state['stages'].append(entry)
        state['current_phase'] = phase
        save(state)
        if phase in ('dry', 'full'):
            while True:
                gpu = subprocess.run(['/usr/lib/wsl/lib/nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                                     capture_output=True, text=True, check=True)
                used = max(int(v) for v in gpu.stdout.split())
                if used < 4000:
                    break
                entry['status'] = 'waiting_for_gpu'
                entry['last_gpu_check'] = timestamp()
                entry['gpu_memory_used_mib'] = used
                state['current_phase'] = phase + '_waiting_for_gpu'
                save(state)
                time.sleep(30)
            entry['status'] = 'running'
            entry['gpu_available_at'] = timestamp()
            state['current_phase'] = phase
            save(state)
        with (OUT / entry['log']).open('a', encoding='utf-8') as log:
            log.write(f'\n=== {entry["started_at"]} {phase} ===\n')
            log.flush()
            code = subprocess.call([sys.executable, '-u', '-m', 'src.recsaver.rater_profile_mvp_1000', phase],
                                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        entry.update(status='completed' if code == 0 else 'failed', exit_code=code, ended_at=timestamp())
        if code:
            state.update(status='failed', ended_at=timestamp())
            save(state)
            return code
        save(state)
    state.update(status='completed', ended_at=timestamp())
    save(state)
    return 0


if __name__ == '__main__':
    if '--launch' in sys.argv:
        state_path = OUT / 'execution_status.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if state.get('status') == 'running':
                raise RuntimeError('Already marked running: inspect process before launching another pipeline')
            archive = OUT / ('execution_status_previous_' + datetime.now().strftime('%Y%m%dT%H%M%S') + '.json')
            archive.write_bytes(state_path.read_bytes())
        with (OUT / 'pipeline.log').open('a', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve())], cwd=ROOT,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        (OUT / 'pipeline_pid.txt').write_text(str(process.pid) + '\n', encoding='utf-8')
        print(f'Launched pipeline PID={process.pid}; status: {OUT / "execution_status.json"}', flush=True)
    else:
        sys.exit(pipeline())
