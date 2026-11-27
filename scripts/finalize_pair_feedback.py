"""Freeze output provenance and check every Stage 4 quote/score and balanced Stage 5 set."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save, sha, now, table

ap = argparse.ArgumentParser()
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
m = read(out / 'manifest.json')
targets = {t['key']: t for t in m['fixed_targets']}
by_rater_id = {(t['rater_id'], t['target']['essay_id']): t for t in targets.values()}
excluded = set(read(out / 'exclusion_manifest.json')['excluded_essay_ids'])
checks = []


def check(name, ok, detail=''):
    checks.append(dict(name=name, passed=bool(ok), detail=detail))


check('frozen_sources', all(sha(ROOT / p) == h for p, h in m['source_sha256'].items()))
final_summary = []
for row in read(out / 'summary.json'):
    folder = out / 'stage5' / row['rater_id']
    result = read(folder / 'result.json') if (folder / 'result.json').exists() else {}
    render = read(folder / 'render_checks.json') if (folder / 'render_checks.json').exists() else {}
    state = ('rendered' if (folder / 'feedback.txt').exists() else 'insufficient_evidence' if (folder / 'skip.json').exists()
             else 'strict_json_failed' if result and not result.get('json_valid') else 'schema_failed' if result and not result.get('schema_valid')
             else 'render_failed' if render else 'unrun')
    final_summary.append(dict(row, stage5_status=state, stage5_executed=(folder / 'raw.txt').exists(),
                             stage5_json_pass=bool(result.get('json_valid')), stage5_schema_pass=bool(result.get('schema_valid')),
                             stage5_render_pass=bool(render.get('pass_')), stage5_failure_reason='; '.join(result.get('errors', []))))
    if state not in ['rendered', 'insufficient_evidence']:
        (folder / 'processing_failure.txt').write_text('Feedback rendering did not complete: ' + state + '. ' + '; '.join(result.get('errors', []))
            + '\nThe original output is preserved. No repair or regeneration was performed.\n', encoding='utf-8')
save(out / 'final_summary.json', final_summary)
table(out / 'final_summary.csv', final_summary)
for f in (out / 'stage4').glob('*/observations.json'):
    t = targets[f.parent.name]
    inp = read(f.parent / 'input.json')
    catalog = {s['span_id']: s for s in inp['evidence_spans']}
    observations = read(f)
    check(f.parent.name + ':max2', len(observations) <= 2)
    for o in observations:
        original = t['target']
        expected = original['Overall'] if o['dimension'] == 'Overall' else original['Traits'][o['dimension']]
        quotes = [original['text'][catalog[s]['start']:catalog[s]['end']] for s in o['evidence_span_ids']]
        check(o['observation_key'] + ':quote_and_recorded_score', quotes == o['quotes'] and expected == o['observed_score'])
eq = read(out / 'equalization.json')
for p in eq:
    selected = p['selected']
    check(p['pair_id'] + ':balanced', len({len(ids) for ids in selected.values()}) == 1 and all(len(ids) == p['M'] for ids in selected.values()))
    for rater, ids in selected.items():
        folder = out / 'stage5' / rater
        if not ids:
            check(rater + ':M0', (folder / 'skip.json').exists())
            continue
        inp = read(folder / 'input_3b.json')
        check(rater + ':input_matches', inp == read(folder / 'input.json') and inp['accepted_target_ids'] == ids and not (set(ids) & excluded))
        ranks = [by_rater_id[rater, eid]['fixed_rank'] for eid in ids]
        check(rater + ':fixed_order', ranks == sorted(ranks))
        rubric = read(out / 'rubric.json')
        check(rater + ':official_descriptors', all(e['descriptor'] == rubric['scores'][str(e['score_band'])][e['dimension']] for e in inp['rubric_entries']))
        check(rater + ':distinct_essay_count', len(set(ids)) == p['M'])
        if (folder / 'render_checks.json').exists() and read(folder / 'render_checks.json')['pass_']:
            result = read(folder / 'render_checks.json')
            check(rater + ':display_unedited', (folder / 'feedback.txt').read_text(encoding='utf-8') == result['feedback_paragraph'] + '\n')
output_hashes = {}
costs = {}
request_manifest = []
old_allocation_path = out / 'revisions/gpu_memory_090/output_snapshot.json'
old_allocation = set(read(old_allocation_path)) if old_allocation_path.exists() else set()
previous_excluded = read(out / 'mask_revision_v11.json').get('excluded_previous_smoke_candidates', []) if (out / 'mask_revision_v11.json').exists() else []
for stage in [1, 3, 4, 5]:
    actual = []
    for f in (out / f'stage{stage}').glob('*/generation.json'):
        g = read(f)
        scope = 'diagnostic_only' if '__smoke' in f.parent.name or (stage == 3 and f.parent.name in previous_excluded) else 'comparison'
        allocation = 0.9 if str((f.parent / 'raw.txt').relative_to(out)) in old_allocation else cfg['model']['gpu_memory_utilization']
        actual.append(dict(key=f.parent.name, scope=scope, gpu_memory_utilization=allocation, **g))
    for f in (out / f'stage{stage}').glob('*/input.json'):
        folder = f.parent
        generation = read(folder / 'generation.json') if (folder / 'generation.json').exists() else None
        scope = 'diagnostic_only' if '__smoke' in folder.name or (stage == 3 and folder.name in previous_excluded) else 'comparison'
        request_manifest.append(dict(stage=stage, key=folder.name, scope=scope,
            input_path=str(f.relative_to(out)), input_sha256=sha(f),
            rendered_chat_sha256=sha(folder / 'rendered_chat.txt') if (folder / 'rendered_chat.txt').exists() else None,
            sampling=read(folder / 'sampling.json') if (folder / 'sampling.json').exists() else None,
            generation=generation,
            gpu_memory_utilization=(0.9 if str((folder / 'raw.txt').relative_to(out)) in old_allocation else cfg['model']['gpu_memory_utilization']),
            state='completed' if (folder / 'result.json').exists() else 'terminal_failure' if (folder / 'error.json').exists() else 'prepared_or_interrupted',
            result=read(folder / 'result.json') if (folder / 'result.json').exists() else None))
    costs[str(stage)] = dict(actual_saved_requests=len(actual), comparison_requests=sum(g['scope'] == 'comparison' for g in actual),
                            diagnostic_requests=sum(g['scope'] == 'diagnostic_only' for g in actual),
                            prompt_tokens=sum(g['prompt_tokens'] for g in actual), output_tokens=sum(g['output_tokens'] for g in actual),
                            truncated=sum(g['finish_reason'] == 'length' for g in actual),
                            allocation_request_counts={str(v): sum(g['gpu_memory_utilization'] == v for g in actual) for v in sorted({g['gpu_memory_utilization'] for g in actual})})
interrupted_count = sum(len(read(p)) for p in (out / 'revisions').glob('*/interrupted_requests.json'))
save(out / 'request_manifest.json', dict(version=cfg['version'], requests=request_manifest, source_manifest_sha256=sha(out / 'manifest.json')))
save(out / 'cost_summary.json', dict(stages=costs, interrupted_requests_without_saved_output=interrupted_count,
     interrupted_token_counts='Unavailable; interrupted batch returned no persisted output. No successful saved request was regenerated.'))
for f in sorted(out.rglob('*')):
    if f.is_file() and f.name in ['raw.txt', 'parsed.json', 'input.json', 'input_3b.json', 'feedback.txt', 'sampling.json', 'generation.json']:
        output_hashes[str(f.relative_to(out))] = sha(f)
save(out / 'output_provenance.json', dict(time=now(), files_sha256=output_hashes,
     rubric_source=dict(path=cfg['rubric_path'], sha256=sha(ROOT / cfg['rubric_path'])),
     implementation_sources=m['source_sha256'],
     reporting_scripts_sha256={str(p.relative_to(ROOT)): sha(p) for p in (ROOT / 'scripts').glob('*pair_feedback*.py')},
     semantic_support='Separate provisional review; no Stage 6 model.'))
table(out / 'final_integrity_checks.csv', checks)
save(out / 'final_integrity.json', dict(time=now(), passed=all(c['passed'] for c in checks),
     checks=len(checks), failures=[c for c in checks if not c['passed']], output_files=len(output_hashes)))
print(read(out / 'final_integrity.json'))
assert all(c['passed'] for c in checks)
