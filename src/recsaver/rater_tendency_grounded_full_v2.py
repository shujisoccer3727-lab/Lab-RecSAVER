"""承認済みv2本実験。独立プロセスで起動し、終了状態を永続化。"""
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from . import rater_tendency_grounded_pilot_v2 as revision


def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()


def main():
    core, out = revision.core, revision.OUT
    revision.setup()
    if '--launch' in sys.argv:
        state_path = out / 'full_execution_status.json'
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if state.get('status') in ['launching','running']:
                try:
                    os.kill(state['pid'], 0)
                except ProcessLookupError:
                    pass
                else:
                    raise RuntimeError('Full experiment already running')
        pilot = out / 'pilot_predictions_snapshot.jsonl'
        if not pilot.exists():
            pilot.write_bytes((out / 'predictions.jsonl').read_bytes())
        core.save(out / 'approval.json', {'approved': True,
                  'config_sha256':core.previous.sha(out / 'experiment_config.json'),
                  'authorization':'2026-10-18 user: これで1000件を実行してみてください！', 'recorded_at':now()})
        with (out / 'full_execution.log').open('a',encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable,'-u','-m','src.recsaver.rater_tendency_grounded_full_v2'],
                        cwd=core.ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                        start_new_session=True)
        core.save(state_path, {'status':'launching','pid':process.pid,'launched_at':now()})
        print(f'Launched PID={process.pid}',flush=True)
        return
    state = {'status':'running','pid':os.getpid(),'started_at':now()}
    core.save(out / 'full_execution_status.json', state)
    try:
        core.run(full=True)
        rows = core.records()
        assert len(rows) == 1000
        state.update(status='completed',attempted=len(rows),valid=sum(r['parse_success'] for r in rows.values()))
    except BaseException:
        state.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        state['ended_at'] = now()
        core.save(out / 'full_execution_status.json',state)


if __name__ == '__main__':
    main()
