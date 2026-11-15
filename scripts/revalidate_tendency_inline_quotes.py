"""One-time validator-only migration: preserve raw generations and all scientific inputs."""
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timezone

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.human_score_disagreement_rater_tendency_inline import (
    CONFIG, atomic, digest, journal, materialize, prepare, read_jsonl, recover, validate)


def main():
    config = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    out = ROOT / config['output_dir']
    old = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    assert old['config'] == config, 'Cannot migrate changed generation settings'
    old_inputs = read_jsonl(out / 'inputs.jsonl')
    old_template = (out / 'template_used.txt').read_text(encoding='utf-8')
    assert old_template == (ROOT / config['template']).read_text(encoding='utf-8')
    attempts = recover(out / 'attempts.jsonl')
    assert all(r['fingerprint'] == old['fingerprint'] for r in attempts)
    backup = out / ('validation_update_backup_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    backup.mkdir()
    for name in ('attempts.jsonl', 'predictions.jsonl', 'run_summary.json', 'timings.jsonl', 'run.log', 'template_used.txt'):
        if (out / name).exists():
            shutil.copy2(out / name, backup / name)
    (out / 'manifest.json').rename(backup / 'manifest.json')
    out, pairs, inputs, meta, unavailable, pilot, fingerprint = prepare(config)
    new = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    assert new['source_hashes'] == old['source_hashes']
    assert {r['target_id']: r['input_hash'] for r in old_inputs} == {t: r['input_hash'] for t, r in inputs.items()}
    changed = []
    for row in attempts:
        obj, errors, checks = validate(row['raw_output'], inputs[row['target_id']])
        row['original_fingerprint'] = row['fingerprint']
        row['original_validation'] = row['validation']
        row['original_failure_reasons'] = row['failure_reasons']
        row['original_status'] = row['status']
        row['fingerprint'] = fingerprint
        row['status'] = 'failed' if errors else 'success'
        row['failure_reasons'] = errors
        row['validation'] = checks
        row['validator_only_recheck'] = True
        if row['status'] != row['original_status']:
            changed.append(row['target_id'])
    atomic(out / 'attempts.jsonl', attempts, jsonl=True)
    materialize(out, pairs, inputs, meta, unavailable, pilot, config, fingerprint)
    atomic(out / 'validator_update.json', dict(
        reason='Explicitly proposed spelling corrections are not purported source quotations.',
        old_fingerprint=old['fingerprint'], new_fingerprint=fingerprint,
        changed_status_target_ids=changed, backup_directory=str(backup.relative_to(ROOT)),
        unchanged_raw_outputs=True, unchanged_prompts_histories_and_generation_settings=True,
        cancelled_retry_note='The in-flight three-request retry batch was stopped before returning. Its unreturned outputs and unmeasured elapsed time are not counted as completed generations.',
        interpretation='Assistant/code validation update, not human evaluation. No reasoning text was edited.'))
    print(json.dumps(dict(changed_status_target_ids=changed, fingerprint=fingerprint), indent=2))


if __name__ == '__main__':
    main()
