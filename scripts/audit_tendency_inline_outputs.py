"""CPU-only consistency audit; does not assess the truth of generated explanations."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.human_score_disagreement_rater_tendency_inline import validate, atomic, read_jsonl


def main():
    out = ROOT / 'outputs/human_score_disagreement_rater_tendency_inline'
    source = ROOT / 'outputs/human_score_disagreement'
    inputs = {r['target_id']: r for r in read_jsonl(out / 'inputs.jsonl')}
    source_inputs = {r['target_id']: r for r in read_jsonl(source / 'prepared_targets.jsonl')}
    predictions = read_jsonl(out / 'predictions.jsonl')
    pairs = read_jsonl(source / 'extracted_pairs.jsonl')
    by_id = {r['target_id']: r for r in predictions}
    errors = []
    if len(by_id) != len(predictions):
        errors.append('duplicate_prediction_target_ids')
    expected = {p['target_' + s] for p in pairs for s in ('a', 'b')}
    if expected != set(by_id):
        errors.append('target_universe_mismatch')
    for tid, item in inputs.items():
        old = source_inputs[tid]
        for key in ('essay', 'history_ids', 'history', 'history_text', 'rubric'):
            if item[key] != old[key]:
                errors.append(f'{tid}:changed_{key}')
        if set(item) != {'target_id', 'rater_id', 'essay', 'rubric', 'history', 'history_ids', 'history_text', 'prompt', 'input_hash'}:
            errors.append(f'{tid}:unexpected_input_fields')
        record = by_id[tid]
        if record['status'] == 'success':
            obj, invalid, _ = validate(record['raw_output'], item)
            if invalid:
                errors.append(f'{tid}:invalid_success:{invalid}')
            elif obj['predicted_overall'] != record['predicted_overall'] or obj['reasoning'] != record['reasoning']:
                errors.append(f'{tid}:raw_output_snapshot_mismatch')
    for p in pairs:
        report = (out / 'cases' / (p['case_id'] + '.md')).read_text(encoding='utf-8')
        for s in ('a', 'b'):
            tid = p['target_' + s]
            if tid in inputs and inputs[tid]['essay'] != p['essay']:
                errors.append(f'{tid}:pair_essay_mismatch')
            r = by_id[tid]
            if r['status'] == 'success' and r['reasoning'] not in report:
                errors.append(f'{tid}:reasoning_not_reproduced_in_report')
    counts = {status: sum(r['status'] == status for r in predictions) for status in ('success', 'failed', 'excluded', 'unprocessed')}
    audit = dict(all_consistency_checks_passed=not errors, errors=errors, pair_count=len(pairs),
                 target_count=len(predictions), status_counts=counts,
                 interpretation='Literal input/output consistency only; no human evaluation or explanation correctness guarantee.')
    atomic(out / 'integrity_validation.json', audit)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
