"""Explicit one-time audit revision; preserve outputs and the fixed selection."""
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
rev = out / 'revisions/mask_v1_0'
if args.phase == 'backup':
    assert not rev.exists()
    rev.mkdir(parents=True)
    for p in (ROOT / 'src/recsaver').glob('pair_feedback*.py'):
        shutil.copy2(p, rev / p.name)
    for name in ['manifest.json', 'candidate_results.json', 'candidate_results.csv', 'summary.json', 'summary.csv',
                 'smoke_status.json', 'status.json', 'interruption.json']:
        if (out / name).exists():
            shutil.copy2(out / name, rev / name)
    shutil.copytree(out / 'stage2', rev / 'stage2')
    hashes = {str(f.relative_to(out)): sha(f) for f in out.glob('stage*/*/raw.txt')}
    attempts = {str(f.relative_to(out)): read(f) for f in out.glob('stage*/*/attempt.json')
                if read(f).get('state') != 'completed'}
    save(rev / 'output_snapshot.json', hashes)
    save(rev / 'interrupted_requests.json', attempts)
    save(rev / 'revision_reason.json', dict(time=now(), reason='Native-like applied to a target uniquely identifies the top rubric band, even without a numeric score. Quarantine before reconstruction.',
        discovered_candidates=['rater_13__essay_17116345036926ef7a1d51d2__K2', 'rater_13__essay_3f4d5d459a296ccd2d5d0c8d__K1'],
        previous_smoke_reconstruction_note='One affected candidate was previously reconstructed in smoke; it did not match and was not accepted. Keep the historical output but exclude it under the corrected screen.',
        generation_changes='None: all inputs, seeds, model, prompts and output budgets remain fixed.', interrupted_request_count=len(attempts)))
    (out / 'manifest.json').rename(rev / 'manifest_before_reprepare.json')
    print('Backed up immutable outputs:', len(hashes), 'interrupted requests:', len(attempts))
else:
    old, new = read(rev / 'manifest.json'), read(out / 'manifest.json')
    assert old['fixed_targets'] == new['fixed_targets'] and old['heldout'] == new['heldout']
    hashes = read(rev / 'output_snapshot.json')
    changed = [f for f, h in hashes.items() if sha(out / f) != h]
    assert not changed
    save(out / 'mask_revision_v11.json', dict(time=now(), previous_version=old['version'], version=new['version'],
        fixed_targets_and_history_unchanged=True, raw_outputs_unchanged=len(hashes), generation_conditions_unchanged=True,
        prior_audit_location=str(rev.relative_to(out)), excluded_previous_smoke_candidates=['rater_13__essay_3f4d5d459a296ccd2d5d0c8d__K1']))
    print('Selection and all prior raw outputs preserved:', len(hashes))
