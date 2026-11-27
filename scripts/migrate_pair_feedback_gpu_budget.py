"""Record operational GPU memory revision without replacing successful requests."""
import argparse
import shutil
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save, sha, now

ap = argparse.ArgumentParser()
ap.add_argument('phase', choices=['backup', 'verify'])
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
rev = out / 'revisions/gpu_memory_090'
if args.phase == 'backup':
    assert not rev.exists()
    rev.mkdir(parents=True)
    for name in ['manifest.json', 'status.json', 'progress.json', 'interruption.json', 'environment.json']:
        if (out / name).exists():
            shutil.copy2(out / name, rev / name)
    hashes = {str(f.relative_to(out)): sha(f) for f in out.glob('stage*/*/raw.txt')}
    attempts = {str(f.relative_to(out)): read(f) for f in out.glob('stage*/*/attempt.json') if read(f).get('state') != 'completed'}
    save(rev / 'output_snapshot.json', hashes)
    save(rev / 'interrupted_requests.json', attempts)
    save(rev / 'memory_evidence.json', dict(time=now(), source='Windows GPU performance counters, read-only',
        adapter_dedicated_bytes=50562289664, adapter_shared_bytes=1938046976, adapter_committed_bytes=52686057472,
        wsl_process_dedicated_bytes=50031849472, wsl_process_shared_bytes=1900019712,
        measured_batch_seconds=385, policy='Reduce vLLM GPU memory utilization from 0.9 to 0.8; preserve all completed outputs, model, prompts, seeds, sampling and token limits. No process belonging to another job was changed.'))
    (out / 'manifest.json').rename(rev / 'manifest_before_reprepare.json')
    print('Saved outputs:', len(hashes), 'interrupted:', len(attempts))
else:
    old, new = read(rev / 'manifest.json'), read(out / 'manifest.json')
    assert old['fixed_targets'] == new['fixed_targets'] and old['heldout'] == new['heldout']
    hashes = read(rev / 'output_snapshot.json')
    assert all(sha(out / f) == h for f, h in hashes.items())
    save(out / 'gpu_budget_revision.json', dict(time=now(), previous_version=old['version'], version=new['version'],
         old_gpu_memory_utilization=0.9, gpu_memory_utilization=0.8, fixed_selection_unchanged=True,
         prior_raw_outputs_unchanged=len(hashes), prompts_model_sampling_seeds_limits_unchanged=True,
         limitation='Operational allocation and GPU scheduling changed; bitwise equivalence across fresh runs is not claimed.'))
    print('Verified prior outputs:', len(hashes))
