"""Fixed-input inline tendency predictions only; no reference generation or evaluation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'configs/human_score_disagreement_rater_tendency_inline.yaml'
PILOT_ROWS = (6788, 7114, 7366)
TRAITS = ('Cohesion', 'Syntax', 'Vocabulary', 'Phraseology', 'Grammar', 'Conventions')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def atomic(path, value, jsonl=False):
    tmp = path.with_suffix(path.suffix + '.tmp')
    content = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in value) if jsonl else json.dumps(value, ensure_ascii=False, indent=2)
    tmp.write_text(content, encoding='utf-8')
    os.replace(tmp, path)


def journal(path, record):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def recover(path):
    if not path.exists():
        return []
    lines = path.read_bytes().splitlines(keepends=True)
    result = []
    offset = 0
    for index, line in enumerate(lines):
        try:
            result.append(json.loads(line))
        except (ValueError, UnicodeDecodeError):
            if index != len(lines) - 1:
                raise ValueError(f'Corrupt journal at line {index + 1}')
            path.with_name(path.name + f'.partial-{time.time_ns()}').write_bytes(line)
            with path.open('r+b') as f:
                f.truncate(offset)
        offset += len(line)
    return result


def render(template, *, rubric, history_text, essay):
    # Deliberately accepts no target score, traits, pair gap, or old prediction.
    return template.format(overall_rubric=rubric, rating_history=history_text, target_essay=essay)


def validate(raw, item):
    errors = []
    checks = {}
    try:
        obj = json.loads(raw.strip())
    except ValueError as exc:
        return None, [f'invalid_json: {exc}'], checks
    if not isinstance(obj, dict) or set(obj) != {'predicted_overall', 'reasoning'}:
        return obj, ['expected_exactly_two_keys'], checks
    if type(obj['predicted_overall']) is not int or not 1 <= obj['predicted_overall'] <= 5:
        errors.append('score_not_integer_1_to_5')
    reason = obj['reasoning']
    if not isinstance(reason, str) or not reason.strip():
        return obj, errors + ['reasoning_not_nonempty_string'], checks
    if '\n' in reason.strip() or '\r' in reason.strip() or reason.lstrip().startswith(('{', '[', '- ', '* ')):
        errors.append('reasoning_not_single_prose_paragraph')
    cited = re.findall(r'\b\d+:\d+\b', reason)
    checks['cited_history_ids'] = list(dict.fromkeys(cited))
    if set(cited) - set(item['history_ids']):
        errors.append('history_id_outside_input')
    # The prompt specifies this unambiguous form for recorded Overall assertions.
    assertions = re.findall(r'\b(\d+:\d+)\s*\(Overall\s+(\d+)\)', reason, re.I)
    known = {h['target_id']: int(h['Overall']) for h in item['history']}
    checks['history_overall_assertions'] = assertions
    for hid, score in assertions:
        if hid not in known or known[hid] != int(score):
            errors.append('incorrect_recorded_history_overall')
    quotes = re.findall(r'"([^"\n]+)"|“([^”\n]+)”', reason)
    quotes = [a or b for a, b in quotes]
    target_quotes = [q for q in quotes if q in item['essay']]
    history_quotes = [q for q in quotes if any(q in h['Text'] for h in item['history'])]
    correction_pairs = re.findall(r'(?:"([^"\n]+)"|“([^”\n]+)”)\s+(?:instead of|rather than)\s+(?:"([^"\n]+)"|“([^”\n]+)”)', reason)
    corrections = [dict(observed=a or b, proposed=c or d) for a, b, c, d in correction_pairs if (a or b) in item['essay']]
    proposed = {r['proposed'] for r in corrections}
    # A proposed replacement is explicitly not claimed to be a quotation from the essay.
    unmatched = [q for q in quotes if q not in target_quotes and q not in history_quotes and q not in proposed]
    checks.update(exact_target_quotes=target_quotes, unmatched_quotes=unmatched,
                  explicitly_proposed_corrections=corrections,
                  insufficient_evidence_explicit='insufficient evidence for a rater-specific tendency' in reason.lower())
    if len(set(target_quotes)) < 2:
        errors.append('fewer_than_two_distinct_exact_target_quotes')
    if unmatched:
        errors.append('quotation_not_found_in_supplied_essays')
    # No automated semantic judgment is presented as a human rating.
    return obj, list(dict.fromkeys(errors)), checks


def prepare(config):
    source = ROOT / config['source_dir']
    out = ROOT / config['output_dir']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'cases').mkdir(exist_ok=True)
    pairs = read_jsonl(source / 'extracted_pairs.jsonl')
    original = read_jsonl(source / 'prepared_targets.jsonl')
    template = (ROOT / config['template']).read_text(encoding='utf-8')
    rubric = (source / 'rubric_used.md').read_text(encoding='utf-8')
    by_id = {r['target_id']: r for r in original}
    assert len(by_id) == len(original), 'Duplicate source target ID'
    unavailable = {r['target_id']: r['failure_reason'] for r in csv.DictReader((source / 'unavailable_targets.csv').open(encoding='utf-8'))}
    inputs = {}
    meta = {}
    pilot = []
    seen_pairs = set()
    for pair in pairs:
        identity = (pair['essay_key'], *sorted((pair['rater_a'], pair['rater_b'])))
        assert identity not in seen_pairs
        seen_pairs.add(identity)
        assert pair['gap'] == abs(pair['actual_a'] - pair['actual_b']) in (2, 3)
        for side in ('a', 'b'):
            tid = pair['target_' + side]
            meta[tid] = dict(target_id=tid, rater_id=pair['rater_' + side])
            if any(row in pair['source_row_ids'] for row in PILOT_ROWS):
                if tid not in pilot:
                    pilot.append(tid)
            if tid not in by_id:
                assert tid in unavailable, f'Unexplained unavailable target: {tid}'
                continue
            r = by_id[tid]
            assert r['target_rater'] == pair['rater_' + side]
            assert r['essay'] == pair['essay'], 'Noncanonical target essay'
            assert r['rubric'].strip() == rubric.strip()
            history = r['history']
            assert len(history) == 3
            assert r['history_ids'] == [h['target_id'] for h in history]
            assert all(h['rater_id'] == r['target_rater'] for h in history)
            assert all(h['essay_key'] != pair['essay_key'] and h['Filename'] not in pair['filename_aliases'] for h in history)
            blocks = []
            for n, h in enumerate(history, 1):
                traits = '\n'.join(f'{t}: {int(h[t])}' for t in TRAITS)
                blocks.append(f"[History {n}; ID={h['target_id']}]\nEssay:\n{h['Text']}\n\nOverall: {int(h['Overall'])}\n\nTrait Scores:\n{traits}")
            assert '\n\n---\n\n'.join(blocks) == r['history_text']
            item = dict(target_id=tid, rater_id=r['target_rater'], essay=r['essay'],
                        rubric=r['rubric'], history=history, history_ids=r['history_ids'], history_text=r['history_text'])
            item['prompt'] = render(template, rubric=item['rubric'], history_text=item['history_text'], essay=item['essay'])
            item['input_hash'] = digest(item)
            if tid in inputs:
                assert inputs[tid] == item, 'Same target ID with inconsistent input'
            inputs[tid] = item
    assert len(pilot) == 6
    source_hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in
                     ('extracted_pairs.jsonl', 'prepared_targets.jsonl', 'rubric_used.md', 'unavailable_targets.csv')}
    fingerprint = digest(dict(config=config, template=template, source_hashes=source_hashes,
                              implementation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              generator_implementation=hashlib.sha256((ROOT / 'src/recsaver/model.py').read_bytes()).hexdigest()))
    manifest = out / 'manifest.json'
    if manifest.exists():
        assert json.loads(manifest.read_text(encoding='utf-8'))['fingerprint'] == fingerprint, 'Configuration/input/code changed: use a new output directory'
    else:
        atomic(manifest, dict(fingerprint=fingerprint, config=config, source_hashes=source_hashes,
                             created_at=datetime.now(timezone.utc).isoformat(), pilot_target_ids=pilot,
                             source_exclusions=unavailable, scope='prediction_only', source_inputs_validated=True))
        atomic(out / 'inputs.jsonl', list(inputs.values()), jsonl=True)
        (out / 'template_used.txt').write_text(template, encoding='utf-8')
        (out / 'rubric_used.md').write_text(rubric, encoding='utf-8')
    return out, pairs, inputs, meta, unavailable, pilot, fingerprint


def materialize(out, pairs, inputs, meta, unavailable, pilot, config, fingerprint):
    attempts = recover(out / 'attempts.jsonl')
    latest = {}
    for row in attempts:
        assert row['fingerprint'] == fingerprint
        latest[row['target_id']] = row
    records = {}
    for tid, m in meta.items():
        record = dict(m, history_ids=inputs[tid]['history_ids'] if tid in inputs else [],
                      predicted_overall=None, reasoning=None, raw_output=None, status='unprocessed', failure_reasons=[])
        if tid in unavailable:
            record.update(status='excluded', failure_reasons=[unavailable[tid]])
        elif tid in latest:
            record.update(latest[tid])
        records[tid] = record
    atomic(out / 'predictions.jsonl', list(records.values()), jsonl=True)
    for p in pairs:
        sections = [f"# {p['case_id']}", f"Essay ID: {p['essay_id']} | human Overall gap: {p['gap']}",
                    '## Target essay', p['essay'], '## Shared rubric', p['rubric'] if 'rubric' in p else (out / 'rubric_used.md').read_text(encoding='utf-8')]
        for side in ('a', 'b'):
            tid = p['target_' + side]
            r = records[tid]
            sections.extend([f"## {r['rater_id']} — target {tid}", f"Human Overall: {p['actual_' + side]} | predicted Overall: {r['predicted_overall']} | status: {r['status']}",
                             '### Generated reasoning (complete original text)', r['reasoning'] if isinstance(r['reasoning'], str) else json.dumps(r['reasoning']),
                             '### Ordered historical inputs', inputs[tid]['history_text'] if tid in inputs else '(source excluded)',
                             '### Validation / failure details', json.dumps(r.get('validation', {}), ensure_ascii=False),
                             json.dumps(r['failure_reasons'], ensure_ascii=False)])
            if r['status'] == 'failed':
                sections.extend(['### Raw failed output', '```text', r['raw_output'] or '', '```'])
        sections.extend(['## Interpretation', 'These are model-generated predictions and tentative descriptions, not the human raters’ actual thoughts. No reference reasons, self-verification, similarity evaluation, or corrective intervention were run. A smaller predicted gap is not evidence of improved human agreement.',
                         '## Human review (unfilled)', '- Differences in focus/judgment: ', '- Explanations unsupported by essay/history: ', '- Judgments to revisit against rubric: ', '- Likely useful for reducing disagreement (likely / unclear / unlikely): ', '- Basis for this judgment: '])
        (out / 'cases' / (p['case_id'] + '.md')).write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    counts = {}
    for gap in (3, 2):
        selected = [p for p in pairs if p['gap'] == gap]
        tids = {p['target_' + side] for p in selected for side in ('a', 'b')}
        target_counts = {s: sum(records[t]['status'] == s for t in tids) for s in ('success', 'failed', 'excluded', 'unprocessed')}
        pair_counts = dict.fromkeys(('success', 'failed', 'excluded', 'unprocessed'), 0)
        for p in selected:
            statuses = [records[p['target_' + side]]['status'] for side in ('a', 'b')]
            status = next((s for s in ('excluded', 'failed', 'unprocessed') if s in statuses), 'success')
            pair_counts[status] += 1
        counts[str(gap)] = dict(essay_count=len({p['essay_key'] for p in selected}), pair_count=len(selected),
                               generation_target_count=len(tids), target_status=target_counts, pair_status=pair_counts)
    timings = recover(out / 'timings.jsonl')
    gen = [r for r in timings if r['kind'] == 'generation']
    seconds = sum(r['seconds'] for r in gen)
    n = sum(r['request_count'] for r in gen)
    remaining = sum(r['status'] == 'unprocessed' for r in records.values())
    atomic(out / 'run_summary.json', dict(fingerprint=fingerprint, updated_at=datetime.now(timezone.utc).isoformat(),
          by_gap=counts, total_unique_targets=len(records), total_feasible_targets=len(inputs),
          template=config['template'], model=config['model'], generation=config['generation'], config=config,
          pilot_target_ids=pilot, pilot_structural_success=all(records[t]['status'] == 'success' for t in pilot),
          initialization_seconds=sum(r['seconds'] for r in timings if r['kind'] == 'initialization'),
          generation_seconds=seconds, generated_attempts=n, seconds_per_attempt=seconds/n if n else None,
          remaining_estimated_seconds=remaining*seconds/n if n else None,
          eta_assumptions='Completed batch mean per attempt; excludes future retries, reporting overhead and future initialization; GPU sharing may change speed.',
          time_cap_enforced=False, timing_records=timings,
          method_changes=['New inline tendency prompt; no old prediction reused', '768 output tokens versus old disagreement prediction 384',
                          'GPU fraction 0.38, CPU weight offload 6 GiB, eager execution, max 2 concurrent sequences due to other GPU workloads',
                          'Same canonical essays, ordered K=3 histories, rubric and Qwen2.5-32B model',
                          'Prediction only: no reference generation, self-verification or similarity'],
          pair_status_precedence=['excluded', 'failed', 'unprocessed', 'success']))
    return records, attempts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('prepare', 'pilot', 'all', 'report'), default='pilot')
    args = parser.parse_args()
    import yaml
    config = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    out, pairs, inputs, meta, unavailable, pilot, fingerprint = prepare(config)
    records, attempts = materialize(out, pairs, inputs, meta, unavailable, pilot, config, fingerprint)
    if args.stage in ('prepare', 'report'):
        return
    if args.stage == 'all':
        review = json.loads((out / 'pilot_review.json').read_text(encoding='utf-8'))
        assert review['fingerprint'] == fingerprint and review['passed'], 'Pilot content review required'
    chosen = pilot if args.stage == 'pilot' else list(dict.fromkeys(
        [p['target_' + s] for gap in (3, 2) for p in pairs if p['gap'] == gap for s in ('a', 'b')]))
    pending = [t for t in chosen if t in inputs and records[t]['status'] != 'success' and
               sum(r['target_id'] == t for r in attempts) < config['max_attempts']]
    if not pending:
        print('No pending eligible targets', flush=True)
        return
    from .reasoning_eval_v1 import EvaluationGenerator
    start = time.perf_counter()
    generator = EvaluationGenerator(config)
    journal(out / 'timings.jsonl', dict(kind='initialization', seconds=time.perf_counter()-start, stage=args.stage))
    print('GPU initialized', flush=True)
    while pending:
        batch = pending[:config['batch_size']]
        pending = pending[config['batch_size']:]
        jobs = []
        for tid in batch:
            item = inputs[tid]
            attempt = sum(r['target_id'] == tid for r in attempts) + 1
            seed = int(digest([config['seed'], tid, attempt])[:8], 16) % (2**31)
            tokens = len(generator.tokenizer.apply_chat_template([dict(role='user', content=item['prompt'])], tokenize=True, add_generation_prompt=True))
            job = dict(target_id=tid, prompt=item['prompt'], seed=seed, prompt_tokens=tokens, attempt=attempt)
            if tokens + config['generation']['max_tokens'] > config['model']['max_model_len']:
                row = dict(meta[tid], fingerprint=fingerprint, input_hash=item['input_hash'], history_ids=item['history_ids'],
                           predicted_overall=None, reasoning=None, raw_output='', status='failed', attempt=attempt,
                           failure_reasons=['context_limit_exceeded_without_truncation'], validation={}, prompt_tokens=tokens)
                journal(out / 'attempts.jsonl', row)
                attempts.append(row)
                continue
            jobs.append(job)
        if not jobs:
            records, attempts = materialize(out, pairs, inputs, meta, unavailable, pilot, config, fingerprint)
            continue
        start = time.perf_counter()
        try:
            raw_outputs = generator.generate(jobs, config['generation'])
        except Exception as exc:
            journal(out / 'runtime_errors.jsonl', dict(target_ids=[j['target_id'] for j in jobs], error=repr(exc)))
            raise
        elapsed = time.perf_counter()-start
        journal(out / 'timings.jsonl', dict(kind='generation', stage=args.stage, seconds=elapsed,
                request_count=len(jobs), target_ids=[j['target_id'] for j in jobs],
                input_tokens=sum(j['prompt_tokens'] for j in jobs),
                output_tokens=sum(len(generator.tokenizer.encode(r)) for r in raw_outputs)))
        assert len(raw_outputs) == len(jobs)
        for job, raw in zip(jobs, raw_outputs):
            tid = job['target_id']
            obj, errors, checks = validate(raw, inputs[tid])
            row = dict(meta[tid], fingerprint=fingerprint, input_hash=inputs[tid]['input_hash'], history_ids=inputs[tid]['history_ids'],
                       predicted_overall=obj.get('predicted_overall') if isinstance(obj, dict) else None,
                       reasoning=obj.get('reasoning') if isinstance(obj, dict) else None,
                       raw_output=raw, status='failed' if errors else 'success', failure_reasons=errors,
                       validation=checks, seed=job['seed'], attempt=job['attempt'], prompt_tokens=job['prompt_tokens'],
                       generation_batch_seconds=elapsed, timestamp=datetime.now(timezone.utc).isoformat())
            journal(out / 'attempts.jsonl', row)
            attempts.append(row)
            print(f"{tid} {row['status']} {errors}", flush=True)
            if errors and job['attempt'] < config['max_attempts']:
                pending.append(tid)
        records, attempts = materialize(out, pairs, inputs, meta, unavailable, pilot, config, fingerprint)
    print('Stage complete', args.stage, flush=True)


if __name__ == '__main__':
    main()
