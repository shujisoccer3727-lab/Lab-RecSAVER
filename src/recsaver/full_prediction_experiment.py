"""Resumable full-scale prediction for the four fixed pilot conditions."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

from .config import load_config, project_path
from .data import load_valid_data
from .history import _stable_seed, format_history
from .model import VLLMGenerator
from .parsing import parse_prediction
from .utils import read_jsonl


FILES = {
    'k0': 'predictions_k0.jsonl',
    'k0_overall_rubric': 'predictions_k0_rubric.jsonl',
    'wrong_k3_overall_rubric': 'predictions_wrong_k3_rubric.jsonl',
    'correct_k3_overall_rubric': 'predictions_correct_k3_rubric.jsonl',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def append_jsonl(path, value):
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False) + '\n')
        stream.flush(); os.fsync(stream.fileno())


def recover_jsonl(path):
    if not path.exists():
        return []
    data = path.read_bytes(); pieces = data.splitlines(keepends=True); offset = 0
    for index, piece in enumerate(pieces):
        try:
            json.loads(piece)
        except (ValueError, UnicodeDecodeError):
            if index != len(pieces)-1:
                raise ValueError(f'Corrupt non-tail JSONL record: {path}:{index+1}')
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


def valid_frame(config):
    base = load_valid_data(config)
    text_ok = base.Text.notna() & base.Text.astype(str).str.strip().ne('')
    return base.loc[text_ok].copy(), len(base), int((~text_ok).sum())


def sample_correct(groups, target, size, seed):
    pool = groups[target.rater_id]
    pool = pool[pool.source_row_id != target.source_row_id]
    if len(pool) < size:
        return None
    indices = list(pool.index)
    random.Random(_stable_seed(seed, target.target_id)).shuffle(indices)
    return pool.loc[indices[:size]].copy()


def sample_wrong(groups, target, size, seed):
    eligible = []
    for rater, group in groups.items():
        if rater == target.rater_id:
            continue
        available = group[group.source_row_id != target.source_row_id]
        if len(available) >= size:
            eligible.append(rater)
    if not eligible:
        return None, None
    rater = random.Random(_stable_seed(seed, f'wrong-rater:{target.target_id}')).choice(sorted(eligible))
    pool = groups[rater]; pool = pool[pool.source_row_id != target.source_row_id]
    indices = list(pool.index)
    random.Random(_stable_seed(seed, f'wrong-history:{target.target_id}:{rater}')).shuffle(indices)
    return rater, pool.loc[indices[:size]].copy()


def render(condition, target, correct, wrong, templates, rubric):
    if condition == 'k0':
        return templates['zero'].format(history=format_history(target.to_frame().T.iloc[:0]), target_essay=target.Text)
    history = target.to_frame().T.iloc[:0]
    if condition == 'correct_k3_overall_rubric':
        history = correct
    elif condition == 'wrong_k3_overall_rubric':
        history = wrong
    return templates['rubric'].format(overall_rubric=rubric, rating_history=format_history(history), target_essay=target.Text)


def build_manifest(config, tokenizer):
    frame, score_valid_total, missing_text = valid_frame(config)
    groups = {rater: group for rater, group in frame.groupby('rater_id', sort=True)}
    templates = {'zero': project_path(config, config['zero_shot_prompt']).read_text(encoding='utf-8'),
                 'rubric': project_path(config, config['rubric_prompt']).read_text(encoding='utf-8')}
    rubric = project_path(config, config['rubric_path']).read_text(encoding='utf-8')
    size = config['history_size']; rows = []
    availability = {c: 0 for c in config['conditions']}; overflow = {c: 0 for c in config['conditions']}
    leakage = 0; history_failures = {'correct': 0, 'wrong': 0}
    for _, target in frame.sort_values('target_id').iterrows():
        correct = sample_correct(groups, target, size, config['history_seed'])
        wrong_rater, wrong = sample_wrong(groups, target, size, config['wrong_rater_seed'])
        if correct is None: history_failures['correct'] += 1
        if wrong is None: history_failures['wrong'] += 1
        condition_available = {}
        token_counts = {}
        for condition in config['conditions']:
            structurally_available = condition not in ('correct_k3_overall_rubric',) or correct is not None
            structurally_available &= condition not in ('wrong_k3_overall_rubric',) or wrong is not None
            if not structurally_available:
                condition_available[condition] = False; token_counts[condition] = None; continue
            prompt = render(condition, target, correct, wrong, templates, rubric)
            # Target blocks contain only raw essay text; scores are never formatted there.
            assert target.Text in prompt
            count = len(tokenizer.apply_chat_template([{'role':'user','content':prompt}], tokenize=True, add_generation_prompt=True))
            fits = count + config['generation']['max_tokens'] <= config['model']['max_model_len']
            condition_available[condition] = fits; token_counts[condition] = count
            availability[condition] += int(fits); overflow[condition] += int(not fits)
        if correct is not None:
            leakage += int(target.source_row_id in set(correct.source_row_id) or
                           not correct.rater_id.eq(target.rater_id).all() or len(correct) != size)
        if wrong is not None:
            leakage += int(target.source_row_id in set(wrong.source_row_id) or wrong.rater_id.nunique() != 1 or
                           wrong.rater_id.iloc[0] == target.rater_id or len(wrong) != size)
        rows.append({'target_id':target.target_id, 'source_row_id':int(target.source_row_id), 'target_rater':target.rater_id,
                     'gold_overall':int(target.Overall),
                     'correct_history_ids':correct.target_id.tolist() if correct is not None else [],
                     'wrong_history_ids':wrong.target_id.tolist() if wrong is not None else [],
                     'wrong_rater':wrong_rater, 'condition_available':condition_available, 'prompt_tokens':token_counts})
    common = sum(all(r['condition_available'][c] for c in config['conditions']) for r in rows)
    audit = pd.DataFrame([
        {'item':'valid_score_samples', 'count':score_valid_total}, {'item':'missing_or_empty_text', 'count':missing_text},
        {'item':'valid_total_samples', 'count':len(frame)}, {'item':'k0_eligible', 'count':availability['k0']},
        {'item':'k0_overall_rubric_eligible', 'count':availability['k0_overall_rubric']},
        {'item':'correct_k3_eligible', 'count':availability['correct_k3_overall_rubric']},
        {'item':'wrong_k3_eligible', 'count':availability['wrong_k3_overall_rubric']},
        {'item':'common_comparison_targets', 'count':common}, {'item':'target_history_leakage_failures', 'count':leakage},
        {'item':'correct_history_count_failures', 'count':history_failures['correct']},
        {'item':'wrong_history_count_failures', 'count':history_failures['wrong']},
        *[{'item':f'{c}_context_overflows', 'count':overflow[c]} for c in config['conditions']]])
    return frame, rows, audit


def input_fingerprint(config):
    paths = {'dataset':config['data']['processed_path'], 'rubric':config['rubric_path'],
             'zero_shot_prompt':config['zero_shot_prompt'], 'rubric_prompt':config['rubric_prompt'],
             'parser':'src/recsaver/parsing.py'}
    hashes = {key:sha(project_path(config, path)) for key,path in paths.items()}
    clean = {key:value for key,value in config.items() if not key.startswith('_')}
    fingerprint = hashlib.sha256(json.dumps({'config':clean, 'hashes':hashes}, sort_keys=True).encode()).hexdigest()
    return paths, hashes, clean, fingerprint


def initialize(config, tokenizer):
    out = project_path(config, config['output_dir']); out.mkdir(parents=True, exist_ok=True)
    paths, hashes, clean, fingerprint = input_fingerprint(config)
    metadata_path = out / 'metadata.json'
    if metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        if metadata['fingerprint'] != fingerprint:
            raise ValueError('Config or input changed; choose another output_dir')
        manifest = recover_jsonl(out / 'target_manifest.jsonl')
        audit = pd.read_csv(out / 'dataset_audit.csv')
        print(f'Reused validated manifest: {len(manifest)} targets', flush=True)
        return out, manifest, audit
    _, manifest, audit = build_manifest(config, tokenizer)
    for row in manifest:
        append_jsonl(out / 'target_manifest.jsonl', row)
    audit.to_csv(out / 'dataset_audit.csv', index=False)
    common = sum(all(row['condition_available'][c] for c in config['conditions']) for row in manifest)
    try:
        gpu = subprocess.run(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        gpu = 'unknown'
    metadata = {'experiment_name':config['experiment_name'], 'timestamp':datetime.now(timezone.utc).isoformat(),
                'git_commit':subprocess.run(['git','rev-parse','HEAD'],cwd=config['_root'],capture_output=True,text=True).stdout.strip(),
                'model':config['model'], 'quantization':config['model']['quantization'], 'GPU':gpu,
                'generation_config':config['generation'], 'target_count':len(manifest), 'common_target_count':common,
                'target_seed':config['target_seed'], 'target_seed_note':'No target sampling: deterministic target_id order over all eligible rows',
                'history_seed':config['history_seed'], 'wrong_rater_seed':config['wrong_rater_seed'],
                'generation_seed':config['generation_seed'], 'bootstrap_seed':config['bootstrap_seed'],
                'source_paths':paths, 'source_sha256':hashes, 'rubric_path':config['rubric_path'],
                'rubric_sha256':hashes['rubric'], 'prompt_paths':[config['zero_shot_prompt'],config['rubric_prompt']],
                'prompt_sha256':[hashes['zero_shot_prompt'],hashes['rubric_prompt']],
                'dataset_path':config['data']['processed_path'], 'dataset_sha256':hashes['dataset'],
                'resume':config['resume'], 'skip_completed':config['skip_completed'], 'fingerprint':fingerprint,
                'condition_order':config['conditions'], 'status':'audit_complete'}
    atomic_json(metadata_path, metadata)
    (out / 'resolved_config.yaml').write_text(yaml.safe_dump(clean, sort_keys=False), encoding='utf-8')
    print(audit.to_string(index=False), flush=True)
    return out, manifest, audit


def generation_seed(config, condition, target_id, attempt):
    value = f"{config['generation_seed']}:{condition}:{target_id}:{attempt}"
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:4], 'big')


class SeededGenerator:
    def __init__(self, config):
        self.base = VLLMGenerator(config); self.tokenizer = self.base.tokenizer

    def generate(self, jobs, parameters):
        from vllm import SamplingParams
        prompts = [self.tokenizer.apply_chat_template([{'role':'user','content':j['prompt']}], tokenize=False,
                                                       add_generation_prompt=True) for j in jobs]
        params = [SamplingParams(n=1, seed=j['seed'], **parameters) for j in jobs]
        return [item.outputs[0].text for item in self.base.llm.generate(prompts, params, use_tqdm=True)]


def prepare_jobs(config, condition, manifest, frame, templates, rubric, completed):
    indexed = frame.set_index('target_id', drop=False); jobs = []
    for row in manifest:
        tid = row['target_id']
        if tid in completed or not row['condition_available'][condition]:
            continue
        target = indexed.loc[tid]
        correct = indexed.loc[row['correct_history_ids']] if row['correct_history_ids'] else None
        wrong = indexed.loc[row['wrong_history_ids']] if row['wrong_history_ids'] else None
        prompt = render(condition, target, correct, wrong, templates, rubric)
        jobs.append({'target_id':tid, 'target':target, 'prompt':prompt, 'prompt_tokens':row['prompt_tokens'][condition],
                     'history':correct if condition == 'correct_k3_overall_rubric' else wrong if condition == 'wrong_k3_overall_rubric' else frame.iloc[:0],
                     'wrong_rater':row['wrong_rater']})
    return jobs


def run(config, condition=None, runtime_batch_size=None):
    if condition and condition not in config['conditions']:
        raise ValueError(condition)
    generator = SeededGenerator(config)
    out, manifest, _ = initialize(config, generator.tokenizer)
    frame, _, _ = valid_frame(config)
    templates = {'zero':project_path(config,config['zero_shot_prompt']).read_text(encoding='utf-8'),
                 'rubric':project_path(config,config['rubric_prompt']).read_text(encoding='utf-8')}
    rubric = project_path(config,config['rubric_path']).read_text(encoding='utf-8')
    batch_size = runtime_batch_size or config['batch_size']
    metadata_path = out / 'metadata.json'; metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata.setdefault('runtime_batch_sizes', [])
    if batch_size not in metadata['runtime_batch_sizes']:
        metadata['runtime_batch_sizes'].append(batch_size); atomic_json(metadata_path, metadata)
    selected = [condition] if condition else config['conditions']
    for current in selected:
        path = out / FILES[current]; records = recover_jsonl(path); completed = {r['target_id'] for r in records}
        if len(completed) != len(records):
            raise ValueError(f'Duplicate completed target in {path}')
        jobs = prepare_jobs(config,current,manifest,frame,templates,rubric,completed)
        print(f'{current}: completed={len(completed)} pending={len(jobs)}', flush=True)
        for offset in range(0,len(jobs),batch_size):
            chunk = jobs[offset:offset+batch_size]
            requests = [dict(job, seed=generation_seed(config,current,job['target_id'],1)) for job in chunk]
            tick=time.perf_counter(); raw_outputs=generator.generate(requests,config['generation']); batch_seconds=time.perf_counter()-tick
            for job,raw in zip(chunk,raw_outputs):
                attempts=[raw]; error=None; parsed={'predicted_overall':None,'reasoning':''}; total_time=batch_seconds/len(chunk)
                for attempt in range(1,config['max_parse_retries']+2):
                    try:
                        parsed=parse_prediction(raw,True); error=None; break
                    except Exception as exc:
                        error=f'{type(exc).__name__}: {exc}'
                        if attempt <= config['max_parse_retries']:
                            retry=dict(job,seed=generation_seed(config,current,job['target_id'],attempt+1),prompt=job['prompt'])
                            started=time.perf_counter(); raw=generator.generate([retry],config['generation'])[0]
                            total_time += time.perf_counter()-started; attempts.append(raw)
                target=job['target']; pred=parsed['predicted_overall']; gold=int(target.Overall); history=job['history']
                record={'target_id':job['target_id'],'source_row_id':int(target.source_row_id),'rater_id':target.rater_id,
                        'condition':current,'K':len(history),'wrong_rater_id':job['wrong_rater'] if current.startswith('wrong') else None,
                        'gold_overall':gold,'predicted_overall':pred,'exact_correct':pred==gold if pred is not None else None,
                        'absolute_error':abs(pred-gold) if pred is not None else None,'squared_error':(pred-gold)**2 if pred is not None else None,
                        'prediction_reasoning':parsed['reasoning'],'history_ids':history.target_id.tolist(),
                        'history_rater_ids':history.rater_id.tolist(),'prompt_tokens':job['prompt_tokens'],
                        'output_tokens':len(generator.tokenizer.encode(raw,add_special_tokens=False)),'context_fit':True,
                        'parse_success':pred is not None,'retry_count':len(attempts)-1,'parse_error':error,
                        'inference_time_seconds':total_time,'raw_model_output':raw,'raw_model_output_attempts':attempts,
                        'prompt':job['prompt'],'generation_seeds':[generation_seed(config,current,job['target_id'],i+1) for i in range(len(attempts))]}
                append_jsonl(path,record); records.append(record)
            atomic_json(out/'progress.json',{'timestamp':datetime.now(timezone.utc).isoformat(),'condition':current,
                        'completed':len(records),'expected':sum(r['condition_available'][current] for r in manifest)})
            print(f'{current}: {len(records)}/{sum(r["condition_available"][current] for r in manifest)}',flush=True)
        from .full_prediction_analysis import analyze
        analyze(config, allow_partial=True)
    from .full_prediction_analysis import analyze
    analyze(config, allow_partial=False)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--config',default='configs/full_prediction_experiment.yaml')
    parser.add_argument('--stage',choices=['audit','run','analyze'],default='audit'); parser.add_argument('--condition',choices=list(FILES))
    parser.add_argument('--runtime-batch-size',type=int,help='Operational scheduler batch; does not alter prompts, generation parameters, or request seeds')
    args=parser.parse_args(); config=load_config(args.config)
    from filelock import FileLock
    out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    with FileLock(str(out/'.run.lock'),timeout=0):
        if args.stage=='analyze':
            from .full_prediction_analysis import analyze; analyze(config,allow_partial=True)
        elif args.stage=='audit':
            from transformers import AutoTokenizer
            tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True); initialize(config,tok)
        else:
            run(config,args.condition,args.runtime_batch_size)


if __name__=='__main__':
    main()
