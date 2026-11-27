"""CPU-only audit and reporting, with no essay text in the check table."""
import argparse
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import (read, save, table, sha, normalized, digest,
                                       load_dataset, DIMS, number, model_essay, generation_seed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    cfg = read(args.config)
    out = ROOT / cfg['output_dir']
    manifest = read(out / 'manifest.json')
    _, rows, _ = load_dataset(cfg)
    invalid = []
    for r in rows:
        bad = [d for d in DIMS if number(r[d]) is None]
        if bad or not r['Text'].strip() or not r['rater_id']:
            invalid.append(dict(source_row_id=r['source_row_id'], rater_position=r['rater_position'],
                                rater_id=r['rater_id'], invalid_dimensions=';'.join(bad),
                                missing_dimensions=';'.join(d for d in DIMS if r[d] == ''),
                                missing_text=not bool(r['Text'].strip()), missing_rater=not bool(r['rater_id'])))
    table(out / 'excluded_invalid_records.csv', invalid)
    excluded = set(read(out / 'exclusion_manifest.json')['excluded_essay_ids'])
    checks = []

    def check(name, passed, **detail):
        checks.append(dict(name=name, passed=bool(passed), detail=json.dumps(detail, ensure_ascii=False)))

    check('frozen_sources', all(sha(ROOT / p) == h for p, h in manifest['source_sha256'].items()))
    check('120_targets', len(manifest['fixed_targets']) == 120)
    check('20_per_rater', all(c['selected'] == cfg['history_count'] for c in manifest['history_counts']))
    check('5_comparison_essays', len(excluded) == 5)
    check('expected_rows_and_empty_kaggle', all(r['expected_row_matches'] and not r['text_id_kaggle']
                                             for c in manifest['heldout'] for r in c['records']))
    for t in manifest['fixed_targets']:
        source_rows = [next(r for r in rows if r['source_row_id'] == s['source_row_id'] and r['rater_position'] == s['rater_position'])
                       for s in [t['source']] + t['history_sources']]
        actual = [model_essay(r) for r in source_rows]
        check(t['key'] + ':raw_text_and_scores', actual == [t['target']] + t['history'])
        check(t['key'] + ':K3_and_exclusions', len(t['history']) == 3 and len({x['essay_id'] for x in actual}) == 4
              and all(x['essay_id'] not in excluded for x in actual)
              and all(r['rater_id'] == t['rater_id'] for r in source_rows))
    requests = []
    excluded_reconstructions = set(read(out / 'mask_revision_v11.json').get('excluded_previous_smoke_candidates', [])) if (out / 'mask_revision_v11.json').exists() else set()
    for stage in [1, 3, 4, 5]:
        for f in sorted((out / f'stage{stage}').glob('*/input.json')):
            p = read(f)
            context = read(f.parent / 'context_check.json')
            requests.append(dict(stage=stage, key=f.parent.name, prompt_tokens=context['prompt_tokens'],
                                 output_budget=context['output_budget'], fits=context['fits'],
                                 raw=(f.parent / 'raw.txt').exists(), result=(f.parent / 'result.json').exists(),
                                 error=(f.parent / 'error.json').exists()))
            if stage in [1, 3]:
                expected_keys = {'rater_id', 'rubric', 'score_specification', 'history', 'target'}
                if stage == 3:
                    expected_keys.add('reference_analysis')
                check(f.parent.name + f':stage{stage}:payload_contract', set(p) == expected_keys)
                check(f.parent.name + f':stage{stage}:score_isolation',
                      len(p['history']) == 3 and (stage == 1 or set(p['target']) == {'essay_id', 'text'})
                      and 'observed_score_alignment' not in p)
                check(f.parent.name + f':stage{stage}:excluded',
                      p['target']['essay_id'] not in excluded and all(h['essay_id'] not in excluded for h in p['history']))
                if stage == 3:
                    mask_dir = out / 'stage2' / f.parent.name
                    audit = read(mask_dir / 'audit.json')
                    current_safe = audit['automatic_pass'] and p['reference_analysis'] == read(mask_dir / 'masked_analysis.json')
                    check(f.parent.name + ':stage3:current_safe_or_explicitly_excluded_history',
                          current_safe or f.parent.name in excluded_reconstructions,
                          scope='excluded_prior_smoke' if f.parent.name in excluded_reconstructions else 'comparison')
            elif stage == 4:
                check(f.parent.name + ':stage4:score_and_rationale_free',
                      set(p) == {'target_essay_id', 'target_text', 'evidence_spans', 'dimension_names'} and p['target_essay_id'] not in excluded)
            else:
                check(f.parent.name + ':stage5:excluded', not (set(p['accepted_target_ids']) & excluded)
                      and not ({o['target_essay_id'] for o in p['verified_observations']} & excluded))
    check('all_contexts_fit', all(r['fits'] for r in requests))
    pair_stats = []
    valid = [r for r in rows if all(number(r[d]) is not None for d in DIMS) and r['Text'].strip()]
    for pair in cfg['pairs']:
        left, right = pair['raters']
        by_id = {}
        for r in valid:
            if r['rater_id'] in [left, right]:
                by_id.setdefault(r['essay_id'], {})[r['rater_id']] = r
        common = [g for g in by_id.values() if left in g and right in g]
        pair_stats.append(dict(pair_id=pair['pair_id'], common=len(common),
                               gap3=sum(abs(g[left]['Overall'] - g[right]['Overall']) == 3 for g in common),
                               gap2=sum(abs(g[left]['Overall'] - g[right]['Overall']) == 2 for g in common)))
    tests = unittest.defaultTestLoader.loadTestsFromName('tests.test_pair_feedback')
    result = unittest.TextTestRunner(verbosity=1).run(tests)
    check('mask_and_contract_regressions', result.wasSuccessful(), tests=result.testsRun)
    table(out / 'cpu_audit_checks.csv', checks)
    table(out / 'request_inventory.csv', requests)
    save(out / 'cpu_validation.json', dict(passed=all(c['passed'] for c in checks), check_count=len(checks),
                                          regression_tests=result.testsRun, pair_stats=pair_stats,
                                          invalid_records=len(invalid),
                                          excluded_prior_smoke_reconstruction_ids=sorted(excluded_reconstructions),
                                          requests=len(requests), failures=[c for c in checks if not c['passed']]))
    print(json.dumps(read(out / 'cpu_validation.json'), ensure_ascii=False, indent=2))
    assert all(c['passed'] for c in checks)


if __name__ == '__main__':
    main()
