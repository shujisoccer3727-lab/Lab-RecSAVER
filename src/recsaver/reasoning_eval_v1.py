"""Fixed-input Rec-SAVER evaluation with durable attempts and resumable stages."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import time
from datetime import datetime, timezone

import pandas as pd
import yaml

from .config import load_config, project_path
from .history import format_history
from .model import VLLMGenerator
from .overall_rubric_ablation import prepare as original_prepare
from .parsing import parse_reasoning, parse_prediction
from .reference_audit import leakage_audit, quality_warnings
from .utils import read_jsonl, write_jsonl


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def append_record(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n'); stream.flush(); os.fsync(stream.fileno())


def recover_log(path):
    """Only an incomplete trailing record may be repaired; preserve its bytes."""
    if not path.exists():
        return []
    data = path.read_bytes(); pieces = data.splitlines(keepends=True); offset = 0
    for index, piece in enumerate(pieces):
        try:
            json.loads(piece)
        except (ValueError, UnicodeDecodeError):
            if index != len(pieces)-1:
                raise ValueError(f'Corrupt non-tail journal record: {path}:{index+1}')
            archive = path.with_name(path.name + f'.partial-{time.time_ns()}')
            archive.write_bytes(piece)
            with path.open('r+b') as stream:
                stream.truncate(offset)
            break
        offset += len(piece)
    if path.stat().st_size and not path.read_bytes().endswith(b'\n'):
        with path.open('ab') as stream:
            stream.write(b'\n')
    return read_jsonl(path)


def token_count(tokenizer, prompt):
    return len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True, add_generation_prompt=True))


def verification_prompt(template, item, reasoning):
    # No gold/predicted score argument is accepted by this renderer.
    return template.format(overall_rubric=item['rubric'], rating_history=item['history_text'],
                           target_essay=item['essay'], reference_reasoning=reasoning)


def prepare(config, tokenizer):
    meta = json.loads(project_path(config, config['source_metadata']).read_text(encoding='utf-8'))
    predictions = [r for r in read_jsonl(project_path(config, config['source_predictions'])) if r['condition'] == 'raw_k3_with_rubric']
    assert [r['target_id'] for r in predictions] == meta['target_ids']
    assert config['model'] == meta['model']
    assert config['generation']['reference'] == meta['generation_config']
    assert config['seed'] == meta['target_seed'] == meta['history_seed']
    assert config['history_size'] == 3
    assert 0 < config['num_targets'] <= len(predictions)
    original = dict(config, source_metadata=config['history_metadata'], source_predictions=config['history_predictions'],
                    generation=meta['generation_config'])
    history_meta, _, prepared = original_prepare(original, tokenizer)
    assert history_meta['target_ids'] == meta['target_ids']
    assert sha(project_path(config, config['rubric_path'])) == meta['rubric_sha256']
    assert sha(project_path(config, config['prediction_prompt'])) == meta['prediction_prompt_sha256']
    reference_template = project_path(config, config['reference_prompt']).read_text(encoding='utf-8')
    verify_template = project_path(config, config['self_verification_prompt']).read_text(encoding='utf-8')
    assert '{gold_overall}' not in verify_template and '{predicted_overall}' not in verify_template
    rubric = project_path(config, config['rubric_path']).read_text(encoding='utf-8')
    wanted = predictions[:config['num_targets']]; by_id = {r['target_id']: r for r in wanted}; items = []
    for prepared_item in prepared:
        if prepared_item['condition'] != 'raw_k3_with_rubric':
            continue
        target = prepared_item['target']; tid = target.target_id
        if tid not in by_id:
            continue
        prediction = by_id[tid]; history = prepared_item['history']
        assert prediction['prompt'] == prepared_item['prompt']
        assert prediction['rater_id'] == target.rater_id and prediction['gold_overall'] == int(target.Overall)
        assert prediction['history_ids'] == history.target_id.tolist() and len(history) == 3
        assert history.rater_id.eq(target.rater_id).all() and target.Text not in history.Text.tolist()
        assert prediction['parse_success'] and prediction['prediction_reasoning']
        item = dict(target_id=tid, target_rater=target.rater_id, gold_overall=int(target.Overall),
                    history_ids=history.target_id.tolist(), history_text=format_history(history), rubric=rubric,
                    essay=target.Text, prediction=prediction)
        item['reference_prompt'] = reference_template.format(overall_rubric=rubric, rating_history=item['history_text'],
                                                             target_essay=item['essay'], gold_overall=item['gold_overall'])
        item['reference_prompt_tokens'] = token_count(tokenizer, item['reference_prompt'])
        item['verification_base_tokens'] = token_count(tokenizer, verification_prompt(verify_template, item, ''))
        assert item['reference_prompt_tokens'] + config['generation']['reference']['max_tokens'] <= config['model']['max_model_len']
        assert item['verification_base_tokens'] + config['generation']['reference']['max_tokens'] + 16 + config['generation']['verification']['max_tokens'] <= config['model']['max_model_len']
        items.append(item)
    assert [i['target_id'] for i in items] == [p['target_id'] for p in wanted]
    return items, verify_template


def initialize(config, items):
    out = project_path(config, config['output_dir']); out.mkdir(parents=True, exist_ok=True)
    paths = {key: config[key] for key in ['source_metadata', 'source_predictions', 'history_metadata', 'history_predictions',
                                        'rubric_path', 'prediction_prompt', 'reference_prompt', 'self_verification_prompt']}
    paths['parser'] = 'src/recsaver/parsing.py'; paths['dataset'] = config['data']['processed_path']
    hashes = {key: sha(project_path(config, path)) for key, path in paths.items()}
    clean_config = {key:value for key,value in config.items() if not key.startswith('_')}
    fingerprint = hashlib.sha256(json.dumps({'config': clean_config, 'hashes': hashes}, sort_keys=True).encode()).hexdigest()
    metadata_path = out / 'metadata.json'
    if metadata_path.exists():
        md = json.loads(metadata_path.read_text(encoding='utf-8'))
        if md['fingerprint'] != fingerprint:
            raise ValueError('Resume config/input changed; use a separate output_dir')
    else:
        md = dict(experiment_name=config['experiment_name'], timestamp=datetime.now(timezone.utc).isoformat(),
                  git_commit=subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=config['_root'], capture_output=True, text=True).stdout.strip(),
                  model=config['model'], quantization=config['model']['quantization'], generation_config=config['generation'],
                  prediction_generation_config=config['generation']['reference'], target_seed=config['seed'], history_seed=config['seed'],
                  seed_policy='SHA256(base seed, stage, target ID, candidate slot, attempt); independent per request and resume-stable',
                  retry_policy='Reference: five total attempts per slot including initial; verification: one parse retry; no retry for score mismatch',
                  target_ids=[i['target_id'] for i in items], history_ids={i['target_id']:i['history_ids'] for i in items},
                  source_paths=paths, source_sha256=hashes, fingerprint=fingerprint,
                  prediction_inference_count=0, status='validated',
                  GPU=subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'], capture_output=True, text=True).stdout.strip(),
                  packages={name:importlib.metadata.version(name) for name in ['vllm', 'torch', 'transformers', 'nltk', 'bert-score']})
        atomic_json(metadata_path, md)
        (out / 'resolved_config.yaml').write_text(yaml.safe_dump(clean_config, sort_keys=False), encoding='utf-8')
    pd.DataFrame([{'target_id': i['target_id'], 'target_rater': i['target_rater'], 'history_ids': json.dumps(i['history_ids']),
                   'history_size': 3, 'same_prediction_input': True, 'correct_rater': True, 'target_excluded': True,
                   'overall_rubric_only': True, 'verification_gold_field_absent': True, 'reference_prompt_tokens': i['reference_prompt_tokens'],
                   'verification_base_tokens': i['verification_base_tokens'], 'reserved_reference_tokens': 400,
                   'context_fit': True} for i in items]).to_csv(out / 'dry_validation.csv', index=False)
    print(f'Structural validation: {len(items)} targets passed', flush=True)
    return out


def request_seed(config, stage, tid, candidate, attempt):
    key = f"{config['seed']}:{stage}:{tid}:{candidate}:{attempt}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big')


class EvaluationGenerator:
    def __init__(self, config):
        self.base = VLLMGenerator(config)
        self.tokenizer = self.base.tokenizer

    def generate(self, jobs, parameters):
        from vllm import SamplingParams
        prompts = [self.tokenizer.apply_chat_template([{'role':'user','content':j['prompt']}], tokenize=False,
                                                       add_generation_prompt=True) for j in jobs]
        params = [SamplingParams(n=1, seed=j['seed'], **parameters) for j in jobs]
        outputs = self.base.llm.generate(prompts, params, use_tqdm=True)
        return [o.outputs[0].text for o in outputs]


def reference_jobs(config, items, attempts):
    jobs = []
    for item in items:
        for slot in range(1, config['num_reference_candidates']+1):
            prior = [r for r in attempts if r['target_id'] == item['target_id'] and r['candidate_index'] == slot]
            if any(r['accepted_as_leakage_free'] for r in prior) or len(prior) >= config['max_reference_retries']:
                continue
            attempt = len(prior)+1
            jobs.append(dict(target_id=item['target_id'], candidate_index=slot, attempt_index=attempt,
                             seed=request_seed(config, 'reference', item['target_id'], slot, attempt),
                             prompt=item['reference_prompt'], prompt_tokens=item['reference_prompt_tokens']))
    return jobs


def verify_jobs(config, items, references, verifications, template, tokenizer):
    jobs = []; by_id = {i['target_id']: i for i in items}
    for reference in references:
        if not reference['accepted_as_leakage_free'] or reference['target_id'] not in by_id:
            continue
        tid, slot = reference['target_id'], reference['candidate_index']
        prior = [v for v in verifications if v['target_id'] == tid and v['candidate_index'] == slot]
        if any(v['parse_success'] for v in prior) or len(prior) >= 1+config['max_verification_parse_retries']:
            continue
        # Only the candidate text, not gold-bearing metadata, enters the renderer.
        prompt = verification_prompt(template, by_id[tid], reference['reference_reasoning'])
        count = token_count(tokenizer, prompt)
        if count + config['generation']['verification']['max_tokens'] > config['model']['max_model_len']:
            raise ValueError(f'Verification context overflow: {tid}/{slot}; no truncation')
        attempt = len(prior)+1
        jobs.append(dict(target_id=tid, candidate_index=slot, attempt_index=attempt,
                         reference_attempt_index=reference['attempt_index'],
                         seed=request_seed(config, 'verification', tid, slot, attempt), prompt=prompt, prompt_tokens=count))
    return jobs


def summarize(config, items, references, verifications, out):
    latest = {(v['target_id'], v['candidate_index']): v for v in verifications}
    pool = []
    for reference in references:
        verification = latest.get((reference['target_id'], reference['candidate_index']))
        if reference['accepted_as_leakage_free'] and verification and verification['verified']:
            pool.append({key:reference[key] for key in ['target_id', 'target_rater', 'candidate_index', 'attempt_index',
                                                       'gold_overall', 'reference_reasoning', 'history_ids']} |
                        {'reconstructed_overall': verification['reconstructed_overall'], 'verified': True})
    write_jsonl(out / 'verified_reference_pool.jsonl', pool)
    rows = []
    for item in items:
        tid = item['target_id']; refs = [r for r in references if r['target_id'] == tid]
        accepted = [r for r in refs if r['accepted_as_leakage_free']]
        reference_done = all(any(r['accepted_as_leakage_free'] for r in refs if r['candidate_index'] == slot)
                             or sum(r['candidate_index'] == slot for r in refs) >= config['max_reference_retries']
                             for slot in range(1, config['num_reference_candidates']+1))
        verification_done = all((tid, r['candidate_index']) in latest and
                                (latest[(tid, r['candidate_index'])]['parse_success'] or
                                 latest[(tid, r['candidate_index'])]['attempt_index'] >= 1+config['max_verification_parse_retries'])
                                for r in accepted)
        rows.append(dict(target_id=tid, target_rater=item['target_rater'], candidate_count=len(refs),
                         leakage_free_count=len(accepted), verified_count=sum(r['target_id'] == tid for r in pool),
                         missing_leakage_free_count=config['num_reference_candidates']-len(accepted),
                         completed=reference_done and verification_done))
    frame = pd.DataFrame(rows); frame.to_csv(out / 'target_reference_summary.csv', index=False)
    audit_columns = ['target_id', 'candidate_index', 'attempt_index', 'leaked', 'leakage_reason', 'other_score_disclosure',
                     'other_score_reason', 'accepted_as_leakage_free', 'parse_success', 'parse_error']
    pd.DataFrame(references).reindex(columns=audit_columns).to_csv(out / 'leakage_audit.csv', index=False)
    warnings = [dict(target_id=r['target_id'], candidate_index=r['candidate_index'], attempt_index=r['attempt_index'],
                     warning=w, formal_metric=False) for r in references for w in quality_warnings(r['reference_reasoning'])]
    pd.DataFrame(warnings, columns=['target_id', 'candidate_index', 'attempt_index', 'warning', 'formal_metric']).to_csv(out / 'quality_warnings.csv', index=False)
    done = frame[frame.completed]
    atomic_json(out / 'coverage_summary.json', {'targets_total': len(frame), 'completed_targets': len(done),
                'targets_with_verified_reference': int((frame.verified_count > 0).sum()),
                'coverage_rate': float((frame.verified_count > 0).mean()),
                'mean_verified_refs_per_target': float(frame.verified_count.mean()), 'median_verified_refs_per_target': float(frame.verified_count.median()),
                'verified_refs_distribution': {str(n): int((frame.verified_count == n).sum()) for n in range(config['num_reference_candidates']+1)},
                'note': 'Unfinished targets remain in denominator; consult completed_targets for partial runs'})
    atomic_json(out / 'progress.json', {'timestamp': datetime.now(timezone.utc).isoformat(),
                'completed_targets': done.target_id.tolist(), 'reference_attempts': len(references), 'verification_attempts': len(verifications)})
    md = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    md.update(status='generation_completed' if len(done) == len(items) else 'partial', completed_targets=len(done),
              reference_attempts=len(references), verification_attempts=len(verifications),
              reference_gpu_seconds=sum(r['inference_seconds'] for r in references),
              verification_gpu_seconds=sum(r['inference_seconds'] for r in verifications),
              reference_parse_errors=sum(not r['parse_success'] for r in references),
              verification_parse_errors=sum(not r['parse_success'] for r in verifications), context_errors=0)
    atomic_json(out / 'metadata.json', md)


def generate(config, items, template, out, limit=None, generator=None, summarize_fn=summarize):
    refs = recover_log(out / 'reference_candidates.jsonl')
    verifications = recover_log(out / 'self_verification_results.jsonl')
    active = items[:limit] if limit else items
    by_id = {i['target_id']: i for i in items}
    summarize_fn(config, items, refs, verifications, out)
    # Lazy model loading: a fully completed resume performs zero generation calls.
    for stage in ['reference', 'verification']:
        while True:
            if stage == 'reference':
                jobs = reference_jobs(config, active, refs)
            else:
                if generator is None and not any(r['accepted_as_leakage_free'] for r in refs):
                    break
                if generator is None:
                    from transformers import AutoTokenizer
                    tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'], local_files_only=True)
                else:
                    tokenizer = generator.tokenizer
                jobs = verify_jobs(config, active, refs, verifications, template, tokenizer)
            if not jobs:
                break
            generator = generator or EvaluationGenerator(config)
            chunk = jobs[:config['batch_size']]
            tick = time.perf_counter(); outputs = generator.generate(chunk, config['generation'][stage]); duration = time.perf_counter()-tick
            assert len(outputs) == len(chunk)
            for job, raw in zip(chunk, outputs):
                item = by_id[job['target_id']]
                record = dict(job, raw_model_output=raw, target_rater=item['target_rater'], history_ids=item['history_ids'],
                              gold_overall=item['gold_overall'], inference_seconds=duration/len(chunk), parse_error=None,
                              sampling_parameters=dict(config['generation'][stage], seed=job['seed']))
                if stage == 'reference':
                    try:
                        reasoning = parse_reasoning(raw); record['parse_success'] = True
                    except (ValueError, TypeError) as exc:
                        reasoning = ''; record.update(parse_success=False, parse_error=str(exc))
                    record.update(reference_reasoning=reasoning, **leakage_audit(reasoning, raw, item['gold_overall']))
                    record['accepted_as_leakage_free'] = record['parse_success'] and not record['leaked'] and not record['other_score_disclosure']
                    append_record(out / 'reference_candidates.jsonl', record); refs.append(record)
                else:
                    try:
                        pred = parse_prediction(raw, require_reasoning=False)['predicted_overall']; record['parse_success'] = True
                    except (ValueError, TypeError) as exc:
                        pred = None; record.update(parse_success=False, parse_error=str(exc))
                    record.update(reconstructed_overall=pred, verified=pred == item['gold_overall'])
                    append_record(out / 'self_verification_results.jsonl', record); verifications.append(record)
            summarize_fn(config, items, refs, verifications, out)
            print(f'{stage}: reference attempts={len(refs)}, verification attempts={len(verifications)}', flush=True)
    summarize_fn(config, items, refs, verifications, out)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', default='configs/reasoning_eval_v1.yaml')
    parser.add_argument('--stage', choices=['validate', 'generate', 'evaluate'], default='validate')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(); config = load_config(args.config)
    out = project_path(config, config['output_dir']); out.mkdir(parents=True, exist_ok=True)
    from filelock import FileLock
    with FileLock(str(out / '.run.lock'), timeout=0):
        if args.stage == 'evaluate':
            resolved = yaml.safe_load((out / 'resolved_config.yaml').read_text(encoding='utf-8'))
            if resolved != {k:v for k,v in config.items() if not k.startswith('_')}:
                raise ValueError('Evaluation config differs from this run')
            metadata = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
            for key, path in metadata['source_paths'].items():
                if sha(project_path(config, path)) != metadata['source_sha256'][key]:
                    raise ValueError(f'Evaluation source changed: {key}')
            from .reasoning_eval_metrics import evaluate
            evaluate(config)
            return
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'], local_files_only=True)
        items, template = prepare(config, tokenizer); initialize(config, items)
        if args.stage == 'generate':
            generate(config, items, template, out, args.limit)


if __name__ == '__main__':
    main()
