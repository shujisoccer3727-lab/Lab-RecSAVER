"""固定済みの全件target/historyを再利用する、RubricなしK=3実験。"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone

import pandas as pd
import yaml

from .config import load_config, project_path
from .data import TRAITS
from .history import format_history
from .parsing import parse_prediction
from .full_prediction_experiment import (
    SeededGenerator, append_jsonl, atomic_json, generation_seed, recover_jsonl,
    sha, valid_frame,
)

CONDITION = 'correct_k3_no_rubric'
REFERENCE = 'correct_k3_overall_rubric'
PREDICTIONS = 'predictions_correct_k3_no_rubric.jsonl'


def read_records(path):
    """既存実験のファイルは回復処理も含めて一切変更しない。"""
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def output_path(config):
    out = project_path(config, config['output_dir']).resolve()
    for key in ('target_source', 'history_assignment_source'):
        source = project_path(config, config[key]).resolve()
        require(out != source and source not in out.parents and out not in source.parents,
                'Output must be separate from reference experiment')
    return out


def render_raw(template, target, history):
    # Only Text from the target can reach the formatter; all scores come from history.
    return template.format(history=format_history(history), target_essay=target.Text)


def validate_row(row, record, target, history, rubric_template, rubric):
    tid = row['target_id']
    require(record['target_id'] == tid == target.target_id, f'Target order/ID mismatch: {tid}')
    require(row['source_row_id'] == record['source_row_id'] == int(target.source_row_id), f'Source mismatch: {tid}')
    require(row['target_rater'] == record['rater_id'] == target.rater_id, f'Rater mismatch: {tid}')
    require(row['gold_overall'] == record['gold_overall'] == int(target.Overall), f'Gold mismatch: {tid}')
    require(record['condition'] == REFERENCE, f'Reference condition mismatch: {tid}')
    require(row['correct_history_ids'] == record['history_ids'] == history.target_id.tolist(), f'History IDs/order mismatch: {tid}')
    require(len(history) == 3 and history.target_id.nunique() == 3 and record['K'] == 3, f'History size mismatch: {tid}')
    require(history.rater_id.eq(target.rater_id).all() and record['history_rater_ids'] == history.rater_id.tolist(), f'History rater mismatch: {tid}')
    require(target.source_row_id not in set(history.source_row_id) and tid not in set(history.target_id)
            and not history.Text.eq(target.Text).any(), f'Target leakage: {tid}')
    expected = rubric_template.format(overall_rubric=rubric, rating_history=format_history(history), target_essay=target.Text)
    require(record['prompt'] == expected, f'Saved prompt / essay / historical scores mismatch: {tid}')
    require(record['context_fit'] and row['condition_available'][REFERENCE], f'Reference audit failure: {tid}')


def audit(config, tokenizer):
    """Samplingを呼ばず、保存された実際のpromptまで全件照合する。"""
    out = output_path(config)
    source = project_path(config, config['target_source'])
    history_source = project_path(config, config['history_assignment_source'])
    require(source.resolve() == history_source.resolve(), 'Targets and history must use the same source')
    metadata = json.loads((source/'metadata.json').read_text(encoding='utf-8'))
    old_config = yaml.safe_load((source/'resolved_config.yaml').read_text(encoding='utf-8'))
    require(config['condition'] == CONDITION and config['history_size'] == 3, 'Only raw correct K=3 is allowed')
    require(config['resume'] and config['skip_completed'], 'Resume must remain enabled')
    for key in ('model', 'generation', 'generation_seed', 'history_seed', 'max_parse_retries'):
        require(config[key] == old_config[key], f'Configuration mismatch: {key}')
    require(config['model'] == metadata['model'] and config['generation'] == metadata['generation_config'], 'Metadata model/generation mismatch')
    paths = {'dataset': project_path(config, config['data']['processed_path']),
             'zero_shot_prompt': project_path(config, config['prediction_prompt']),
             'parser': project_path(config, 'src/recsaver/parsing.py'),
             'rubric_prompt': project_path(config, old_config['rubric_prompt']),
             'rubric': project_path(config, old_config['rubric_path'])}
    hashes = {key: sha(path) for key, path in paths.items()}
    require(hashes['zero_shot_prompt'] == config['expected_prompt_sha256'], 'Requested prompt SHA mismatch')
    for key, value in hashes.items():
        require(value == metadata['source_sha256'][key], f'Reference SHA mismatch: {key}')
    source_files = ['metadata.json', 'resolved_config.yaml', 'dataset_audit.csv', 'target_manifest.jsonl',
                    'predictions_correct_k3_rubric.jsonl', 'predictions_k0.jsonl']
    source_hashes = {name: sha(source/name) for name in source_files}
    clean = {k:v for k,v in config.items() if not k.startswith('_')}
    fingerprint = hashlib.sha256(json.dumps([clean, hashes, source_hashes], sort_keys=True).encode()).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    if (out/'metadata.json').exists():
        previous = json.loads((out/'metadata.json').read_text(encoding='utf-8'))
        require(previous['fingerprint'] == fingerprint, 'Resume input/config changed')
    manifest = read_records(source/'target_manifest.jsonl')
    reference = read_records(source/'predictions_correct_k3_rubric.jsonl')
    k0 = read_records(source/'predictions_k0.jsonl')
    ids = [r['target_id'] for r in manifest]
    require(len(ids) == len(set(ids)) == metadata['target_count'] == 17731, 'Target count/uniqueness mismatch')
    require(ids == [r['target_id'] for r in reference] == [r['target_id'] for r in k0], 'Reference target order mismatch')
    old_audit = pd.read_csv(source/'dataset_audit.csv').set_index('item')['count']
    require(int(old_audit['target_history_leakage_failures']) == 0 and int(old_audit['correct_history_count_failures']) == 0, 'Existing audit has failures')
    frame, _, _ = valid_frame(config)
    require(frame.target_id.is_unique, 'Dataset target IDs are not unique')
    indexed = frame.set_index('target_id', drop=False)
    template = paths['zero_shot_prompt'].read_text(encoding='utf-8')
    rubric_template = paths['rubric_prompt'].read_text(encoding='utf-8')
    rubric = paths['rubric'].read_text(encoding='utf-8')
    jobs, audits = [], []
    for position, (row, saved, baseline) in enumerate(zip(manifest, reference, k0)):
        target = indexed.loc[row['target_id']]
        history = indexed.loc[row['correct_history_ids']]
        validate_row(row, saved, target, history, rubric_template, rubric)
        require(baseline['gold_overall'] == int(target.Overall) and baseline['rater_id'] == target.rater_id
                and baseline['source_row_id'] == int(target.source_row_id), f'K0 identity mismatch: {target.target_id}')
        require(baseline['prompt'] == render_raw(template, target, frame.iloc[:0]), f'K0 target essay mismatch: {target.target_id}')
        prompt = render_raw(template, target, history)
        altered = target.copy()
        for name in ['Overall', *TRAITS]:
            altered[name] = 'TARGET_SCORE_SENTINEL'
        require(prompt == render_raw(template, altered, history), f'Target score leakage: {target.target_id}')
        count = len(tokenizer.apply_chat_template([{'role':'user', 'content':prompt}], tokenize=True, add_generation_prompt=True))
        fits = count + config['generation']['max_tokens'] <= config['model']['max_model_len']
        jobs.append({'target_id': target.target_id, 'target':target, 'history':history, 'prompt':prompt, 'prompt_tokens':count})
        audits.append({'target_order':position, 'target_id':target.target_id, 'target_rater':target.rater_id,
                       'history_ids':json.dumps(history.target_id.tolist()), 'history_count':len(history),
                       'history_ids_order_match':True, 'saved_reference_prompt_match':True,
                       'history_rater_match':True, 'target_leakage':False, 'gold_leakage':False,
                       'target_trait_leakage':False, 'prompt_tokens':count, 'context_fit':fits})
        if (position+1) % 1000 == 0:
            print(f'Audit: {position+1}/{len(manifest)}', flush=True)
    audit_frame = pd.DataFrame(audits)
    audit_frame.to_csv(out/'history_assignment_audit.csv', index=False)
    overflow = int((~audit_frame.context_fit).sum())
    pd.DataFrame([{'item':k, 'count':v} for k,v in {
        'target_count':len(ids), 'rater_count':audit_frame.target_rater.nunique(), 'history_exact_matches':len(ids),
        'target_order_matches':len(ids), 'target_leakage':0, 'gold_leakage':0, 'target_trait_leakage':0,
        'context_overflows':overflow, 'prompt_sha_match':1, 'existing_audit_match':1}.items()]).to_csv(out/'dataset_audit.csv',index=False)
    require(overflow == 0, f'Context overflow: {overflow}; no truncation or target removal allowed')
    if not (out/'metadata.json').exists():
        gpu = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'], capture_output=True,text=True).stdout.strip()
        atomic_json(out/'metadata.json', dict(experiment_name=config['experiment_name'], timestamp=datetime.now(timezone.utc).isoformat(),
            git_commit=subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),
            model=config['model'], quantization=config['model']['quantization'], GPU=gpu,
            generation_config=config['generation'], generation_seed=config['generation_seed'],
            generation_seed_policy='Existing condition-specific SHA256(base_seed:condition:target_id:attempt); new condition name gives distinct draws',
            target_count=len(ids), common_target_count=None, history_size=3, history_seed=config['history_seed'],
            history_assignment_source=config['history_assignment_source'], target_source=config['target_source'],
            prompt_path=config['prediction_prompt'], prompt_sha256=hashes['zero_shot_prompt'],
            dataset_path=config['data']['processed_path'], dataset_sha256=hashes['dataset'],
            source_sha256=hashes, reference_file_sha256=source_hashes, fingerprint=fingerprint,
            resume=True, skip_completed=True, status='audit_complete',
            comparison_limitation='Required zero-shot and rubric templates also differ in framing/instructions; not a literal rubric-text-only edit.'))
    (out/'resolved_config.yaml').write_text(yaml.safe_dump(clean,sort_keys=False),encoding='utf-8')
    print(f'Audit complete: {len(ids)} exact histories; overflow={overflow}', flush=True)
    return out, jobs


def validate_completed(records, jobs, config):
    require(len(records) <= len(jobs), 'Too many resumed records')
    for record, job in zip(records, jobs):
        target = job['target']
        require(record['target_id'] == job['target_id'] and record['condition'] == CONDITION
                and record['prompt'] == job['prompt'] and record['history_ids'] == job['history'].target_id.tolist()
                and record['gold_overall'] == int(target.Overall) and record['rater_id'] == target.rater_id
                and record['prompt_tokens'] == job['prompt_tokens'], 'Resume record identity/order mismatch')
        require(record['generation_seeds'] == [generation_seed(config, CONDITION, job['target_id'], i+1)
                for i in range(len(record['raw_model_output_attempts']))], 'Resume generation seed mismatch')


def progress(out, records, expected):
    seconds = sum(r['inference_time_seconds'] for r in records)
    mean = seconds/len(records) if records else None
    atomic_json(out/'progress.json', dict(timestamp=datetime.now(timezone.utc).isoformat(), selected_targets=expected,
        status='inference_complete' if len(records)==expected else 'running',
        completed_targets=len(records), parse_success=sum(r['parse_success'] for r in records),
        parse_errors=sum(not r['parse_success'] for r in records), elapsed_seconds=seconds,
        elapsed_seconds_definition='Cumulative measured generation time, including retries, across resumes',
        estimated_remaining_seconds=mean*(expected-len(records)) if mean is not None else None,
        mean_inference_seconds=mean))


def wait_for_gpu(config, out):
    """他ジョブを変更せず、指定メモリ予算を利用できるまで待機。"""
    while True:
        result = subprocess.run(['nvidia-smi','--query-gpu=memory.total,memory.used',
                                 '--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
        total, used = map(int,result.stdout.strip().splitlines()[0].split(','))
        processes = subprocess.run(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],
                                   capture_output=True,text=True,check=True).stdout.strip()
        if not processes and total-used >= total*config['model']['gpu_memory_utilization']:
            print('GPU available; starting full CPU re-audit before inference',flush=True)
            return
        status_path = out/'progress.json'
        status = json.loads(status_path.read_text(encoding='utf-8')) if status_path.exists() else {}
        status.update(status='waiting_for_gpu',timestamp=datetime.now(timezone.utc).isoformat(),
                      gpu_memory_total_mib=total,gpu_memory_used_mib=used,gpu_compute_pids=processes.splitlines(),
                      selected_targets=17731,estimated_remaining_seconds=None)
        status.setdefault('completed_targets',0)
        status.setdefault('parse_success',0)
        status.setdefault('parse_errors',0)
        status.setdefault('elapsed_seconds',0)
        status.setdefault('mean_inference_seconds',None)
        atomic_json(status_path,status)
        metadata_path = out/'metadata.json'
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            metadata['status'] = 'waiting_for_gpu'
            atomic_json(metadata_path,metadata)
        print(f'Waiting for GPU: {used}/{total} MiB; compute PIDs={processes!r}',flush=True)
        time.sleep(60)


def run(config, out, jobs):
    path = out/PREDICTIONS
    records = recover_jsonl(path)
    validate_completed(records, jobs, config)
    progress(out, records, len(jobs))
    if len(records) < len(jobs):
        generator = SeededGenerator(config)  # 全件CPU監査を通過した後にのみGPUを初期化。
        metadata = json.loads((out/'metadata.json').read_text(encoding='utf-8'))
        metadata['status'] = 'running'
        atomic_json(out/'metadata.json', metadata)
        for offset in range(len(records), len(jobs), config['batch_size']):
            chunk = jobs[offset:offset+config['batch_size']]
            requests = [dict(job,seed=generation_seed(config,CONDITION,job['target_id'],1)) for job in chunk]
            tick = time.perf_counter()
            outputs = generator.generate(requests, config['generation'])
            seconds = time.perf_counter()-tick
            require(len(outputs) == len(chunk), 'Generator output count mismatch')
            for job, raw in zip(chunk, outputs):
                attempts, error, parsed = [raw], None, {'predicted_overall':None,'reasoning':''}
                elapsed = seconds/len(chunk)
                for attempt in range(1, config['max_parse_retries']+2):
                    try:
                        parsed = parse_prediction(raw, True)
                        error = None
                        break
                    except Exception as exc:
                        error = f'{type(exc).__name__}: {exc}'
                        if attempt <= config['max_parse_retries']:
                            tick = time.perf_counter()
                            raw = generator.generate([dict(job,seed=generation_seed(config,CONDITION,job['target_id'],attempt+1))],config['generation'])[0]
                            elapsed += time.perf_counter()-tick
                            attempts.append(raw)
                target, history = job['target'], job['history']
                pred, gold = parsed['predicted_overall'], int(target.Overall)
                record = dict(target_id=job['target_id'],source_row_id=int(target.source_row_id),rater_id=target.rater_id,
                    condition=CONDITION,K=3,gold_overall=gold,predicted_overall=pred,
                    exact_correct=pred==gold if pred is not None else None,
                    absolute_error=abs(pred-gold) if pred is not None else None,
                    squared_error=(pred-gold)**2 if pred is not None else None,
                    prediction_reasoning=parsed['reasoning'], history_ids=history.target_id.tolist(),
                    history_rater_ids=history.rater_id.tolist(),prompt_tokens=job['prompt_tokens'],
                    output_tokens=len(generator.tokenizer.encode(raw,add_special_tokens=False)),context_fit=True,
                    parse_success=pred is not None,retry_count=len(attempts)-1,parse_error=error,
                    inference_time_seconds=elapsed,raw_model_output=raw,raw_model_output_attempts=attempts,
                    prompt=job['prompt'],generation_seeds=[generation_seed(config,CONDITION,job['target_id'],i+1) for i in range(len(attempts))])
                append_jsonl(path, record)
                records.append(record)
            progress(out, records, len(jobs))
            print(f'{CONDITION}: {len(records)}/{len(jobs)}', flush=True)
    from .full_history_only_analysis import analyze
    analyze(config)
    status = json.loads((out/'progress.json').read_text(encoding='utf-8'))
    status['status'] = 'completed'
    atomic_json(out/'progress.json',status)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/full_history_only_experiment.yaml')
    parser.add_argument('--stage',choices=['audit','run','analyze'],default='audit')
    parser.add_argument('--wait-for-gpu',action='store_true',help='Wait for existing GPU jobs to exit; never stop them')
    args = parser.parse_args()
    config = load_config(args.config)
    out = output_path(config)
    out.mkdir(parents=True,exist_ok=True)
    from filelock import FileLock
    with FileLock(str(out/'.run.lock'),timeout=0):
        if args.stage == 'analyze':
            from .full_history_only_analysis import analyze
            analyze(config)
        else:
            if args.stage == 'run' and args.wait_for_gpu:
                wait_for_gpu(config,out)
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True)
            out, jobs = audit(config, tokenizer)
            if args.stage == 'run':
                run(config, out, jobs)


if __name__ == '__main__':
    main()
