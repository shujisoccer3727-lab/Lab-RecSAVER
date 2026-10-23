"""Fixed-target trait-free MVP. CPU preparation/analysis and separate gated GPU run."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
import subprocess
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/rater_profile_mvp_1000'
BASE = ROOT / 'outputs/full_prediction_experiment'
CONDITIONS = ['A_current_trait_history', 'B_traitfree_direct_correct',
              'B_traitfree_direct_wrong', 'B_nohistory_rubric',
              'C_traitfree_joint_profile', 'D_twostage_correct_profile',
              'D_twostage_wrong_profile']
NEW = [c for c in CONDITIONS if c not in (CONDITIONS[0], CONDITIONS[3])]
TRAITS = ['Cohesion', 'Syntax', 'Vocabulary', 'Phraseology', 'Grammar', 'Conventions']
PROMPTS = {
    'direct': 'traitfree_direct_prediction.txt',
    'joint': 'traitfree_joint_profile_prediction.txt',
    'profile': 'rater_profile_generation_traitfree_mvp_1000.txt',
    'prediction': 'profile_based_prediction_traitfree_mvp_1000.txt',
}
PAIRS = [(CONDITIONS[1], CONDITIONS[0]), (CONDITIONS[1], CONDITIONS[2]),
         (CONDITIONS[1], CONDITIONS[3]), (CONDITIONS[4], CONDITIONS[1]),
         (CONDITIONS[5], CONDITIONS[6]), (CONDITIONS[5], CONDITIONS[1])]


def read(path):
    if not path.exists():
        return []
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed(*parts):
    return int(hashlib.sha256(':'.join(map(str, (20261012, *parts))).encode()).hexdigest()[:8], 16)


def data():
    frame = pd.read_csv(ROOT / 'data/processed/rater_essay_wide.csv', low_memory=False)
    frame['target_id'] = frame.source_row_id.astype(int).astype(str) + ':' + frame.rater_position.astype(int).astype(str)
    assert not frame.target_id.duplicated().any()
    return frame.set_index('target_id', drop=False)


def history(frame, ids):
    # Explicit whitelist: trait scores and other metadata cannot reach the formatter.
    return [{'id': i, 'essay': str(frame.loc[i, 'Text']), 'overall': int(frame.loc[i, 'Overall'])} for i in ids]


@lru_cache(maxsize=1)
def texts():
    rubric = (ROOT / 'rubrics/ellipse_overall_rubric.md').read_text(encoding='utf-8')
    structured = json.loads((ROOT / 'rubrics/ellipse_rubric_structured.json').read_text(encoding='utf-8'))
    # Verbatim descriptors at all levels, identified as common criteria, never observed scores.
    aspects = {'analytic_rubric': {score: {t: row[t] for t in TRAITS}
                                  for score, row in structured['scores'].items()},
               'key_terms_and_definitions': structured['key_terms_and_definitions']}
    templates = {k: (ROOT / 'prompts/en' / v).read_text(encoding='utf-8') for k, v in PROMPTS.items()}
    return rubric, json.dumps(aspects, ensure_ascii=False, indent=2), templates


def render(kind, frame, tid=None, ids=(), rater_id=None, profile=None):
    rubric, aspects, templates = texts()
    return templates[kind].format(rubric=rubric, aspects=aspects,
                                  history=json.dumps(history(frame, ids), ensure_ascii=False),
                                  target=str(frame.loc[tid, 'Text']) if tid else '',
                                  rater_id=rater_id, profile=json.dumps(profile, ensure_ascii=False))


def fixed():
    targets = pd.read_csv(OUT / 'common_targets_1000.csv')
    manifest = {r['target_id']: r for r in read(OUT / 'target_history_manifest.jsonl')}
    profiles = pd.read_csv(OUT / 'profiles/profile_history_manifest.csv')
    assignments = pd.read_csv(OUT / 'wrong_profile_assignments.csv').set_index('target_id').wrong_profile_rater.to_dict()
    return targets, manifest, profiles, assignments


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'experiment_config.json').exists():
        verify_inputs()
        print('Preparation already exists; verified fingerprints, did not resample.')
        return
    common_path = ROOT / 'outputs/full_prediction_main_results/common_targets.csv'
    common = pd.read_csv(common_path)
    assert len(common) == 17725 and not common.target_id.duplicated().any()
    common['sampling_stratum'] = common.gold_overall.astype(str) + '|' + common.target_rater
    counts = common.groupby('sampling_stratum', sort=True).size()
    quota = counts * 1000 / len(common)
    allocated = np.floor(quota).astype(int)
    remainder = (quota - allocated).sort_values(ascending=False, kind='stable')
    allocated.loc[remainder.index[:1000 - allocated.sum()]] += 1
    rng = np.random.default_rng(20261012)
    selected = []
    for stratum, group in common.groupby('sampling_stratum', sort=True):
        selected.extend(rng.choice(group.index.to_numpy(), allocated[stratum], replace=False))
    targets = common.loc[selected, ['target_id', 'source_row_id', 'target_rater', 'gold_overall', 'sampling_stratum']].sort_values('target_id')
    assert len(targets) == 1000
    targets.to_csv(OUT / 'common_targets_1000.csv', index=False)
    pd.DataFrame({'population_n': counts, 'ideal_n': quota, 'sample_n': allocated}).to_csv(OUT / 'sampling_strata.csv')
    frame = data()
    original = {r['target_id']: r for r in read(BASE / 'target_manifest.jsonl')}
    rows = [original[t] for t in targets.target_id]
    jsonl(OUT / 'target_history_manifest.jsonl', rows)
    sources = set(targets.source_row_id)
    filenames = set(frame.loc[targets.target_id, 'Filename'].dropna().astype(str))
    exact = set(frame.loc[targets.target_id, 'Text'].astype(str))
    valid = frame.Overall.isin(range(1, 6)) & frame.Text.notna() & frame.Text.astype(str).str.strip().ne('')
    audit, profile_rows, availability = [], [], []
    for rater in sorted(targets.target_rater.unique()):
        own = frame.loc[valid & frame.rater_id.eq(rater)]
        eligible = own.loc[~own.source_row_id.isin(sources)]
        # Also protect identical filenames/text occurring under a different source ID.
        clean = eligible.loc[~eligible.Filename.astype(str).isin(filenames) & ~eligible.Text.astype(str).isin(exact)]
        availability.append({'rater_id': rater, 'valid_essay_overall_n': len(own),
                             'after_target_source_exclusion_n': len(eligible), 'after_all_overlap_exclusion_n': len(clean)})
        ids = random.Random(seed('profile-history', rater)).sample(sorted(clean.index), min(20, len(clean)))
        for i in ids:
            h = frame.loc[i]
            profile_rows.append({'rater_id': rater, 'history_id': i, 'source_row_id': int(h.source_row_id),
                                 'Filename': h.Filename, 'overall': int(h.Overall), 'selection_seed': seed('profile-history', rater)})
    avail = pd.DataFrame(availability)
    avail.to_csv(OUT / 'profile_history_availability.csv', index=False)
    (OUT / 'profiles').mkdir(exist_ok=True)
    pd.DataFrame(profile_rows).to_csv(OUT / 'profiles/profile_history_manifest.csv', index=False)
    maximum = int(avail.after_all_overlap_exclusion_n.min())
    raters = sorted(targets.target_rater.unique())
    assignments = [{'target_id': t.target_id, 'target_rater': t.target_rater,
                    'wrong_profile_rater': random.Random(seed('wrong-profile', t.target_id)).choice([r for r in raters if r != t.target_rater])}
                   for t in targets.itertuples()]
    pd.DataFrame(assignments).to_csv(OUT / 'wrong_profile_assignments.csv', index=False)
    for t in targets.itertuples():
        actual = frame.loc[t.target_id]
        assert actual.Overall == t.gold_overall and actual.rater_id == t.target_rater and actual.source_row_id == t.source_row_id
        for label in ['correct', 'wrong']:
            ids = original[t.target_id][label + '_history_ids']
            hs = frame.loc[ids]
            audit.append({'scope': label, 'target_id': t.target_id, 'source_overlap': int(hs.source_row_id.eq(t.source_row_id).sum()),
                          'filename_overlap': int(hs.Filename.eq(actual.Filename).sum()),
                          'exact_text_overlap': int(hs.Text.eq(actual.Text).sum()),
                          'rater_violation': int(hs.rater_id.nunique() != 1 or
                              (hs.rater_id.iloc[0] != t.target_rater if label == 'correct' else hs.rater_id.iloc[0] == t.target_rater)),
                          'history_size_violation': int(len(ids) != 3), 'gold_mismatch': 0})
    pd.DataFrame(audit).to_csv(OUT / 'history_overlap_audit.csv', index=False)
    for condition, filename in [(CONDITIONS[0], 'predictions_correct_k3_rubric.jsonl'),
                                (CONDITIONS[3], 'predictions_k0_rubric.jsonl')]:
        predictions = {r['target_id']: r for r in read(BASE / filename)}
        reused_digest = sha(BASE / filename)
        reused = []
        for t in targets.itertuples():
            r = predictions[t.target_id]
            assert r['parse_success'] and r['gold_overall'] == t.gold_overall and r['predicted_overall'] in range(1, 6)
            if condition == CONDITIONS[0]:
                assert r['history_ids'] == original[t.target_id]['correct_history_ids']
            reused.append({'target_id': t.target_id, 'source_row_id': t.source_row_id, 'target_rater': t.target_rater,
                           'gold_overall': t.gold_overall, 'condition': condition,
                           'predicted_overall': r['predicted_overall'], 'reasoning': r['prediction_reasoning'],
                           'parse_success': True, 'retry_count': r['retry_count'],
                           'reused_from': str((BASE / filename).relative_to(ROOT)), 'reused_sha256': reused_digest})
        jsonl(OUT / 'predictions' / (condition + '.jsonl'), reused)
    paths = [common_path, ROOT / 'data/processed/rater_essay_wide.csv', BASE / 'target_manifest.jsonl',
             BASE / 'predictions_correct_k3_rubric.jsonl', BASE / 'predictions_k0_rubric.jsonl',
             ROOT / 'rubrics/ellipse_overall_rubric.md', ROOT / 'rubrics/ellipse_rubric_structured.json',
             *[ROOT / 'prompts/en' / p for p in PROMPTS.values()],
             OUT / 'common_targets_1000.csv', OUT / 'target_history_manifest.jsonl',
             OUT / 'profiles/profile_history_manifest.csv', OUT / 'wrong_profile_assignments.csv']
    config = {'sampling_seed': 20261012, 'profile_history_seed': 20261012, 'wrong_profile_seed': 20261012,
              'seed_derivation': 'SHA256 of base seed, role/condition, target/rater, attempt; first 32 bits',
              'population_n': 17725, 'target_n': 1000, 'conditions': CONDITIONS, 'profile_k': 20,
              'maximum_common_profile_k': maximum,
              'model': {'model_id': 'Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4', 'quantization': 'gptq_marlin',
                        'tensor_parallel_size': 1, 'max_model_len': 8192, 'gpu_memory_utilization': .90},
              'generation': {'temperature': .2, 'top_p': .8, 'max_tokens': 384},
              'profile_max_tokens': 768, 'max_parse_retries': 3,
              'bootstrap': {'samples': 2000, 'seed': 20260914, 'method': 'paired percentile, target_id unit'},
              'prompts': PROMPTS, 'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in paths},
              'profile_history_eligibility': 'Valid Overall and nonempty text; no Trait-score validity restriction. All selected target sources, filenames and exact texts excluded.',
              'profile_token_reason': 'Eight descriptive fields plus arrays, rater ID and explicit evidence citations exceed a reliable 384-token budget; profile-only max_tokens=768.',
              'status': 'prepared; inference not performed'}
    dump(OUT / 'experiment_config.json', config)
    rubric, aspects, _ = texts()
    (OUT / 'rubric_definitions_used.md').write_text('# Sources\n\nrubrics/ellipse_overall_rubric.md\n\n' + rubric +
       '\n\nrubrics/ellipse_rubric_structured.json (six analytic descriptors at all levels and key_terms_and_definitions, verbatim)\n\n```json\n' + aspects + '\n```\n', encoding='utf-8')
    structural_audit()
    print(f'Fixed N=1000, raters={len(raters)}, maximum common PROFILE_K={maximum}; requested K=20')


def verify_inputs():
    config = json.loads((OUT / 'experiment_config.json').read_text(encoding='utf-8-sig'))
    for p, digest in config['input_sha256'].items():
        assert sha(ROOT / p) == digest, f'Input changed: {p}'
    return config


def structural_audit():
    targets, manifest, profiles, assignments = fixed()
    frame = data()
    overlap = pd.read_csv(OUT / 'history_overlap_audit.csv')
    results = []
    for key in ['source_overlap', 'filename_overlap', 'exact_text_overlap', 'rater_violation', 'history_size_violation', 'gold_mismatch']:
        results.append({'check': 'k3_' + key, 'failures': int(overlap[key].sum()), 'status': 'pass' if overlap[key].sum() == 0 else 'fail'})
    sources = set(targets.source_row_id)
    failures = int(profiles.source_row_id.isin(sources).sum())
    results.append({'check': 'profile_history_target_source_overlap', 'failures': failures, 'status': 'pass' if not failures else 'fail'})
    results.append({'check': 'wrong_profile_is_self', 'failures': sum(assignments[t.target_id] == t.target_rater for t in targets.itertuples()), 'status': 'pass'})
    # Metamorphic check: replacing ALL score/metadata columns of a target leaves its rendered prompt identical;
    # replacing historical Trait scores leaves trait-free direct/joint/profile prompts identical.
    sentinel = frame.copy()
    sentinel[TRAITS] = 'FORBIDDEN_TRAIT_SENTINEL'
    target_failures = trait_failures = 0
    prompts = []
    for t in targets.itertuples():
        for c, kind, label in [(CONDITIONS[1], 'direct', 'correct'), (CONDITIONS[2], 'direct', 'wrong'), (CONDITIONS[4], 'joint', 'correct')]:
            ids = manifest[t.target_id][label + '_history_ids']
            p = render(kind, frame, t.target_id, ids)
            trait_failures += int(p != render(kind, sentinel, t.target_id, ids))
            mutated = sentinel.copy(deep=False)
            # Copy the Overall column before assigning to preserve the shared frame.
            mutated = mutated.assign(Overall=sentinel.Overall.copy())
            mutated.loc[t.target_id, 'Overall'] = -999
            target_failures += int(p != render(kind, mutated, t.target_id, ids))
            if len(prompts) < 15:
                prompts.append({'target_id': t.target_id, 'condition': c, 'prompt': p})
    for rater, group in profiles.groupby('rater_id'):
        ids = group.history_id.tolist()
        trait_failures += int(render('profile', frame, ids=ids, rater_id=rater) != render('profile', sentinel, ids=ids, rater_id=rater))
    results.extend([{'check': 'traitfree_prompts_invariant_to_historical_trait_scores', 'failures': trait_failures, 'status': 'pass' if trait_failures == 0 else 'fail'},
                    {'check': 'prediction_prompts_invariant_to_target_gold_and_traits', 'failures': target_failures, 'status': 'pass' if target_failures == 0 else 'fail'},
                    {'check': 'all_seven_prediction_target_sets_and_gold', 'failures': None, 'status': 'pending_inference'},
                    {'check': 'token_context_fit', 'failures': None, 'status': 'pending_tokenizer_audit'}])
    jsonl(OUT / 'prompt_audit_samples.jsonl', prompts)
    pd.DataFrame(results).to_csv(OUT / 'integrity_audit.csv', index=False)


def parse(raw, profile=False, condition=None):
    text = raw.strip()
    fence = re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    value = json.loads(text)
    assert isinstance(value, dict)
    if profile:
        p = value['profile']
        assert isinstance(value['rater_id'], str) and isinstance(p['overall_scoring_tendency'], str)
        assert set(p['evaluation_aspects']) == {t.lower() for t in TRAITS}
        assert all(isinstance(v, str) for v in p['evaluation_aspects'].values())
        assert isinstance(p['other_observed_patterns'], list) and isinstance(p['uncertainties'], list)
    else:
        assert type(value['predicted_overall']) is int and value['predicted_overall'] in range(1, 6)
        assert isinstance(value['reasoning'], str) and value['reasoning'].strip()
        if condition == CONDITIONS[4]:
            assert isinstance(value['rater_tendency'], list) and value['rater_tendency']
            assert all(isinstance(v, str) for v in value['rater_tendency'])
        if condition in CONDITIONS[5:]:
            assert isinstance(value['used_profile_tendencies'], list)
            assert all(isinstance(v, str) for v in value['used_profile_tendencies'])
    return value


def reparse_profiles():
    path = OUT / 'profiles/rater_profiles.jsonl'
    rows = read(path)
    archive = OUT / 'profiles/rater_profiles_pre_fence_repair.jsonl'
    if not archive.exists():
        archive.write_bytes(path.read_bytes())
    recovered = []
    audit = []
    for row in rows:
        success = None
        for attempt, raw in enumerate(row['raw_model_output_attempts']):
            try:
                value = parse(raw, profile=True)
                assert value['rater_id'] == row['rater_id']
                success = dict(row, **value, parse_success=True, selected_valid_attempt=attempt,
                               parse_repair='Removed Markdown JSON fence only; selected earliest schema-valid attempt; original attempts preserved')
                break
            except (ValueError, AssertionError, KeyError, TypeError):
                pass
        recovered.append(success if success else row)
        audit.append({'rater_id': row['rater_id'], 'before_success': row['parse_success'],
                      'after_success': bool(success), 'selected_valid_attempt': success['selected_valid_attempt'] if success else None,
                      'generation_retries_performed': row['retry_count']})
    jsonl(path, recovered)
    pd.DataFrame(audit).to_csv(OUT / 'profiles/profile_parse_repair_audit.csv', index=False)
    print(f'Recovered {sum(r["parse_success"] for r in recovered)}/{len(rows)} profiles without regeneration')


def token_audit():
    config = verify_inputs()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'], local_files_only=True)
    frame = data()
    targets, manifest, ph, _ = fixed()
    rows = []
    def record(identity, condition, prompt, output_budget):
        count = len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True, add_generation_prompt=True))
        context = config.get('profile_max_model_len', 8192) if condition == 'profile_generation' else 8192
        rows.append({'identity': identity, 'condition': condition, 'prompt_tokens': count,
                     'output_budget': output_budget, 'max_model_len': context, 'context_fit': count + output_budget <= context})
    for rater, group in ph.groupby('rater_id', sort=True):
        record(rater, 'profile_generation', render('profile', frame, ids=group.history_id.tolist(), rater_id=rater), 768)
    for t in targets.itertuples():
        for c, kind, label in [(CONDITIONS[1], 'direct', 'correct'), (CONDITIONS[2], 'direct', 'wrong'), (CONDITIONS[4], 'joint', 'correct')]:
            record(t.target_id, c, render(kind, frame, t.target_id, manifest[t.target_id][label + '_history_ids']), 384)
    result = pd.DataFrame(rows)
    result.to_csv(OUT / 'prompt_token_audit.csv', index=False)
    audit = pd.read_csv(OUT / 'integrity_audit.csv')
    failures = int((~result.context_fit).sum())
    audit.loc[audit.check.eq('token_context_fit'), ['failures', 'status']] = [failures, 'fail' if failures else 'pass']
    audit.to_csv(OUT / 'integrity_audit.csv', index=False)
    print(result.groupby('condition').agg(N=('context_fit', 'size'), max_prompt_tokens=('prompt_tokens', 'max'), context_failures=('context_fit', lambda x: int((~x).sum()))).to_string())
    return failures


def run(mode):
    config = verify_inputs()
    if not (OUT / 'prompt_token_audit.csv').exists():
        token_audit()
    integrity = pd.read_csv(OUT / 'integrity_audit.csv')
    assert not integrity.status.eq('fail').any(), 'Design integrity failure: do not change histories silently'
    assert config['maximum_common_profile_k'] >= 20, 'PROFILE_K shortage: report availability, require design decision'
    if mode == 'profiles':
        ready = {r['rater_id']: r for r in read(OUT / 'profiles/rater_profiles.jsonl')}
        _, _, ph, _ = fixed()
        if all(r in ready and ready[r]['parse_success'] for r in ph.rater_id.unique()):
            print('All 27 profiles already schema-valid; reused, no GPU/model load or generation.', flush=True)
            return
    if mode == 'full':
        gate = json.loads((OUT / 'dry_run/dry_run_gate.json').read_text(encoding='utf-8'))
        assert gate['passed'], 'Full inference requires successful dry-run'
        assert gate['fingerprint'] == sha(OUT / 'experiment_config.json')
    # Avoid colliding with an unrelated GPU job. No process is stopped.
    gpu = subprocess.run(['/usr/lib/wsl/lib/nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
                         capture_output=True, text=True, check=True)
    assert max(int(v) for v in gpu.stdout.split()) < 4000, 'GPU occupied: wait or supply a separate compatible GPU; no unrelated job was stopped'
    from .model import VLLMGenerator
    from vllm import SamplingParams
    runtime = dict(config, model=dict(config['model']))
    if mode == 'profiles':
        runtime['model']['max_model_len'] = config['profile_max_model_len']
    generator = VLLMGenerator(runtime)
    frame = data()
    targets, manifest, ph, assignments = fixed()
    destination = OUT / 'dry_run' if mode == 'dry' else OUT
    destination.mkdir(exist_ok=True)
    profile_path = OUT / 'profiles/rater_profiles.jsonl'
    generated = {r['rater_id']: r for r in read(profile_path)}

    def generate_batch(jobs, condition, profile=False):
        limit = config['profile_max_tokens'] if profile else 384
        context = config['profile_max_model_len'] if profile else 8192
        work = []
        for prompt, identity in jobs:
            tokens = generator.tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True, add_generation_prompt=True)
            assert len(tokens) + limit <= context, f'Context overflow {identity}/{condition}: {len(tokens)}+{limit}'
            formatted = generator.tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False, add_generation_prompt=True)
            work.append({'identity': identity, 'prompt': prompt, 'formatted': formatted,
                         'prompt_tokens': len(tokens), 'attempts': [], 'seeds': []})
        results = {}
        for attempt in range(config['max_parse_retries'] + 1):
            pending = [w for w in work if w['identity'] not in results]
            if not pending:
                break
            params = []
            for w in pending:
                request_seed = seed(condition, w['identity'], attempt)
                w['seeds'].append(request_seed)
                params.append(SamplingParams(temperature=.2, top_p=.8, max_tokens=limit, seed=request_seed))
            outputs = generator.llm.generate([w['formatted'] for w in pending], params, use_tqdm=False)
            for w, result in zip(pending, outputs):
                output = result.outputs[0]
                w['attempts'].append(output.text)
                try:
                    value = parse(output.text, profile, condition)
                    if profile:
                        assert value['rater_id'] == w['identity']
                    results[w['identity']] = dict(value, parse_success=True, retry_count=attempt,
                        generation_seeds=w['seeds'], raw_model_output_attempts=w['attempts'],
                        prompt=w['prompt'], prompt_tokens=w['prompt_tokens'], output_tokens=len(output.token_ids))
                except (ValueError, KeyError, AssertionError, TypeError):
                    pass
        for w in work:
            if w['identity'] not in results:
                results[w['identity']] = dict(parse_success=False, retry_count=config['max_parse_retries'],
                    generation_seeds=w['seeds'], raw_model_output_attempts=w['attempts'],
                    prompt=w['prompt'], prompt_tokens=w['prompt_tokens'])
        return [results[identity] for _, identity in jobs]

    def append(path, row):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
            f.flush()

    if mode == 'profiles':
        groups = {r: g.history_id.tolist() for r, g in ph.groupby('rater_id', sort=True)}
        pending = [r for r in groups if r not in generated or not generated[r]['parse_success']]
        for start in range(0, len(pending), 3):
            batch = pending[start:start + 3]
            jobs = [(render('profile', frame, ids=groups[r], rater_id=r), r) for r in batch]
            for rater, record in zip(batch, generate_batch(jobs, 'profile', True)):
                record.update(rater_id=rater, history_ids=groups[rater])
                append(profile_path, record)
                print('profile', rater, record['parse_success'], flush=True)
        latest = {r['rater_id']: r for r in read(profile_path)}
        assert all(r in latest and latest[r]['parse_success'] for r in groups), 'One or more Profile JSONs failed validation; inspect saved raw outputs'
        return
    assert all(r in generated and generated[r]['parse_success'] for r in ph.rater_id.unique()), 'Generate all profiles first'
    subset = targets.head(5) if mode == 'dry' else targets
    completed = {}
    for c in NEW:
        saved = {r['target_id']: r for r in read(destination / 'predictions' / (c + '.jsonl'))}
        if mode == 'full' and not saved:
            saved = {r['target_id']: r for r in read(OUT / 'dry_run/predictions' / (c + '.jsonl'))}
        completed[c] = sum(r['parse_success'] for r in saved.values())
    baseline_completed = sum(completed.values())
    prediction_started = time.monotonic()
    for c in NEW:
        path = destination / 'predictions' / (c + '.jsonl')
        previous = {r['target_id']: r for r in read(path)}
        if mode == 'full' and not previous:
            dry_rows = read(OUT / 'dry_run/predictions' / (c + '.jsonl'))
            jsonl(path, dry_rows)
            previous = {r['target_id']: r for r in dry_rows}
        jobs, metadata = [], []
        for t in subset.itertuples():
            if t.target_id in previous and previous[t.target_id]['parse_success']:
                continue
            m = manifest[t.target_id]
            ids, profile_rater = [], None
            if c in [CONDITIONS[1], CONDITIONS[2], CONDITIONS[4]]:
                label = 'wrong' if c == CONDITIONS[2] else 'correct'
                ids = m[label + '_history_ids']
                prompt = render('joint' if c == CONDITIONS[4] else 'direct', frame, t.target_id, ids)
            else:
                profile_rater = assignments[t.target_id] if c == CONDITIONS[6] else t.target_rater
                prompt = render('prediction', frame, t.target_id, profile=generated[profile_rater]['profile'])
            jobs.append((prompt, t.target_id))
            metadata.append(dict(target_id=t.target_id, source_row_id=t.source_row_id, target_rater=t.target_rater,
                                 gold_overall=t.gold_overall, condition=c, history_ids=ids, profile_rater=profile_rater))
        for start in range(0, len(jobs), 10):
            batch_started = time.monotonic()
            for meta, record in zip(metadata[start:start + 10], generate_batch(jobs[start:start + 10], c)):
                record.update(meta)
                append(path, record)
                completed[c] += int(record['parse_success'])
            print(c, 'completed', min(start + 10, len(jobs)) + len(previous), '/', len(subset), flush=True)
            elapsed = time.monotonic() - prediction_started
            processed = sum(completed.values()) - baseline_completed
            remaining = len(subset) * len(NEW) - sum(completed.values())
            estimated_seconds = remaining * elapsed / processed if processed >= 20 else None
            now = datetime.now(ZoneInfo('Asia/Tokyo'))
            dump(destination / 'prediction_progress.json', {'updated_at': now.isoformat(),
                'phase': mode, 'completed_by_condition': completed, 'new_prediction_successes': sum(completed.values()),
                'total_requested': len(subset) * len(NEW), 'last_batch_seconds': time.monotonic() - batch_started,
                'measured_predictions_per_hour': processed * 3600 / elapsed if elapsed else None,
                'estimated_remaining_seconds': estimated_seconds,
                'estimated_inference_finish_jst': (now + timedelta(seconds=estimated_seconds)).isoformat() if estimated_seconds is not None else None,
                'eta_note': 'Extrapolated from this run; retries, condition changes and other GPU jobs can change completion time; analysis follows inference.'})
    if mode == 'dry':
        success = all({r['target_id']: r for r in read(destination / 'predictions' / (c + '.jsonl'))}[t]['parse_success']
                      for c in NEW for t in subset.target_id)
        dump(destination / 'dry_run_gate.json', {'passed': success, 'n_per_condition': 5,
                                               'fingerprint': sha(OUT / 'experiment_config.json'),
                                               'structural_integrity_passed': True})
    else:
        analyze()


def metrics(gold, pred):
    difference = pred - gold
    observed = np.mean(difference ** 2)
    expected = np.mean(gold ** 2) + np.mean(pred ** 2) - 2 * np.mean(gold) * np.mean(pred)
    return {'Accuracy': float(np.mean(difference == 0)), 'MAE': float(np.mean(abs(difference))),
            'RMSE': float(np.sqrt(observed)), 'QWK': float(1 - observed / expected) if expected else float('nan')}


def final_integrity(records):
    config = verify_inputs()
    frame = data()
    targets, manifest, ph, assignments = fixed()
    profiles = {r['rater_id']: r for r in read(OUT / 'profiles/rater_profiles.jsonl')}
    audit = pd.read_csv(OUT / 'integrity_audit.csv')
    target_set = set(targets.target_id)
    golds = targets.set_index('target_id').gold_overall.to_dict()
    failures = sum(set(rows) != target_set for rows in records.values())
    failures += sum(row['gold_overall'] != golds[tid] for rows in records.values() for tid, row in rows.items())
    audit.loc[audit.check.eq('all_seven_prediction_target_sets_and_gold'), ['failures', 'status']] = [failures, 'pass' if not failures else 'pending_inference']
    checks = []
    def check(name, count, pending=False):
        checks.append({'check': name, 'failures': count, 'status': 'pending_inference' if pending else ('fail' if count else 'pass')})
    ts = frame.loc[targets.target_id]
    hs = frame.loc[ph.history_id]
    check('profile_global_target_filename_overlap', int(hs.Filename.isin(set(ts.Filename)).sum()))
    check('profile_global_target_exact_text_overlap', int(hs.Text.isin(set(ts.Text)).sum()))
    check('profile_fixed_K20_single_rater', sum(len(g) != 20 or not frame.loc[g.history_id, 'rater_id'].eq(r).all() for r, g in ph.groupby('rater_id')))
    actual_prompt_failures = score_invariance_failures = raw_history_failures = context_failures = 0
    mutated = frame.copy()
    mutated[TRAITS] = 'FORBIDDEN_TRAIT_SENTINEL'
    for c in NEW:
        for tid, row in records[c].items():
            if c in CONDITIONS[5:]:
                rater = assignments[tid] if c == CONDITIONS[6] else row['target_rater']
                p = profiles[rater]['profile']
                expected = render('prediction', frame, tid, profile=p)
                alternate = render('prediction', mutated, tid, profile=p)
                actual_prompt_failures += int(row['profile_rater'] != rater)
                raw_history_failures += int(bool(row['history_ids']))
            else:
                ids = manifest[tid]['wrong_history_ids' if c == CONDITIONS[2] else 'correct_history_ids']
                kind = 'joint' if c == CONDITIONS[4] else 'direct'
                expected = render(kind, frame, tid, ids)
                alternate = render(kind, mutated, tid, ids)
                actual_prompt_failures += int(row['history_ids'] != ids)
            actual_prompt_failures += int(row['prompt'] != expected)
            score_invariance_failures += int(expected != alternate)
            original = mutated.at[tid, 'Overall']
            mutated.at[tid, 'Overall'] = -999
            if c in CONDITIONS[5:]:
                alternate = render('prediction', mutated, tid, profile=p)
            else:
                alternate = render(kind, mutated, tid, ids)
            score_invariance_failures += int(expected != alternate)
            mutated.at[tid, 'Overall'] = original
            context_failures += int(row['prompt_tokens'] + 384 > 8192)
    for rater, row in profiles.items():
        ids = ph.loc[ph.rater_id.eq(rater), 'history_id'].tolist()
        expected = render('profile', frame, ids=ids, rater_id=rater)
        actual_prompt_failures += int(row['prompt'] != expected or row['history_ids'] != ids)
        score_invariance_failures += int(expected != render('profile', mutated, ids=ids, rater_id=rater))
        context_failures += int(row['prompt_tokens'] + 768 > config['profile_max_model_len'])
    pending = any(not records[c] for c in NEW)
    check('saved_prompt_matches_whitelisted_render', actual_prompt_failures, pending)
    check('saved_prompts_invariant_to_target_gold_traits_and_history_traits', score_invariance_failures, pending)
    check('D_predictions_raw_history_absent', raw_history_failures, pending)
    check('actual_saved_prompt_context_fit', context_failures, pending)
    check('input_fingerprints_unchanged', 0)
    replace = {row['check'] for row in checks}
    audit = pd.concat([audit.loc[~audit.check.isin(replace)], pd.DataFrame(checks)], ignore_index=True)
    audit.to_csv(OUT / 'integrity_audit.csv', index=False)
    assert not audit.status.eq('fail').any(), 'Post-inference integrity failure: report without selectively excluding targets'


def analyze():
    verify_inputs()
    targets, _, _, _ = fixed()
    records = {c: {r['target_id']: r for r in read(OUT / 'predictions' / (c + '.jsonl'))} for c in CONDITIONS}
    common = [t for t in targets.target_id if all(t in records[c] and records[c][t]['parse_success'] for c in CONDITIONS)]
    golds = targets.set_index('target_id').gold_overall
    summaries, distributions = [], []
    for c in CONDITIONS:
        rows = records[c]
        assert not set(rows) - set(targets.target_id)
        for tid, row in rows.items():
            assert row['gold_overall'] == golds[tid]
        ids = [tid for tid in targets.target_id if tid in rows and rows[tid]['parse_success']]
        m = metrics(golds.loc[ids].to_numpy(int), np.array([rows[tid]['predicted_overall'] for tid in ids])) if ids else {k: None for k in ['Accuracy', 'MAE', 'RMSE', 'QWK']}
        summaries.append({'condition': c, 'scope': 'available_only', 'N': len(ids),
                          'missing': 1000 - len(rows), 'parse_errors': sum(not r['parse_success'] for r in rows.values()),
                          'retry_count': sum(r['retry_count'] for r in rows.values()), **m})
        if common:
            m = metrics(golds.loc[common].to_numpy(int), np.array([rows[tid]['predicted_overall'] for tid in common]))
            summaries.append({'condition': c, 'scope': 'common_all_seven', 'N': len(common), **m})
        for scope, use_ids in [('available_only', ids), ('common_all_seven', common)]:
            for score in range(1, 6):
                count = sum(rows[tid]['predicted_overall'] == score for tid in use_ids)
                distributions.append({'condition': c, 'scope': scope, 'N': len(use_ids), 'score': score,
                                      'count': count, 'percentage': 100 * count / len(use_ids) if use_ids else None})
    pd.DataFrame(summaries).to_csv(OUT / 'condition_summary.csv', index=False)
    pd.DataFrame(distributions).to_csv(OUT / 'prediction_distribution.csv', index=False)
    comparisons, cis = [], []
    if common:
        gold = golds.loc[common].to_numpy(int)
        preds = {c: np.array([records[c][t]['predicted_overall'] for t in common]) for c in CONDITIONS}
        samples = {(a, b, k): [] for a, b in PAIRS for k in metrics(gold, gold)}
        rng = np.random.default_rng(20260914)
        for _ in range(2000):
            indices = rng.integers(0, len(common), len(common))
            ms = {c: metrics(gold[indices], p[indices]) for c, p in preds.items()}
            for a, b in PAIRS:
                for k in ms[a]:
                    samples[a, b, k].append(ms[a][k] - ms[b][k])
        for a, b in PAIRS:
            ma, mb = metrics(gold, preds[a]), metrics(gold, preds[b])
            for k in ma:
                row = {'left': a, 'right': b, 'difference_direction': a + ' - ' + b, 'metric': k,
                       'N': len(common), 'difference': ma[k] - mb[k], 'left_better_when': 'positive' if k in ('Accuracy', 'QWK') else 'negative'}
                comparisons.append(row)
                lo, hi = np.quantile(samples[a, b, k], [.025, .975])
                cis.append(dict(row, ci_lower=lo, ci_upper=hi, samples=2000, seed=20260914, method='paired percentile'))
    pd.DataFrame(comparisons, columns=['left', 'right', 'difference_direction', 'metric', 'N', 'difference', 'left_better_when']).to_csv(OUT / 'pairwise_comparison.csv', index=False)
    pd.DataFrame(cis, columns=['left', 'right', 'difference_direction', 'metric', 'N', 'difference', 'left_better_when', 'ci_lower', 'ci_upper', 'samples', 'seed', 'method']).to_csv(OUT / 'paired_bootstrap_ci.csv', index=False)
    final_integrity(records)
    profile_analysis(records)
    report(summaries, cis, len(common))
    status = subprocess.run(['git', 'status', '--short'], cwd=ROOT, capture_output=True, text=True)
    (OUT / 'git_status_after.txt').write_text(status.stdout, encoding='utf-8')
    (OUT / 'git_status_after.stderr.txt').write_text(status.stderr, encoding='utf-8')
    finalizer = OUT / 'build_final_report.py'
    if len(common) == 1000 and finalizer.exists():
        import runpy
        runpy.run_path(str(finalizer), run_name='__main__')


def profile_analysis(records):
    def tfidf_cosine(documents):
        # Smoothed document IDF, count TF, L2 normalization; no additional model/package.
        counts = [Counter(re.findall(r'\b\w\w+\b', text.lower())) for text in documents]
        vocabulary = sorted(set().union(*(set(c) for c in counts)))
        matrix = np.array([[c[word] for word in vocabulary] for c in counts], dtype=float)
        if not vocabulary:
            return np.zeros((len(documents), len(documents)))
        matrix *= np.log((1 + len(documents)) / (1 + (matrix > 0).sum(axis=0))) + 1
        norm = np.linalg.norm(matrix, axis=1, keepdims=True)
        matrix = np.divide(matrix, norm, out=np.zeros_like(matrix), where=norm != 0)
        return matrix @ matrix.T
    profiles = {r['rater_id']: r for r in read(OUT / 'profiles/rater_profiles.jsonl') if r.get('parse_success')}
    rows = []
    if len(profiles) > 1:
        ids = sorted(profiles)
        matrix = tfidf_cosine([json.dumps(profiles[i]['profile']) for i in ids])
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                rows.append({'rater_a': ids[i], 'rater_b': ids[j], 'tfidf_cosine': matrix[i, j]})
    pd.DataFrame(rows, columns=['rater_a', 'rater_b', 'tfidf_cosine']).to_csv(OUT / 'profiles/profile_similarity.csv', index=False)
    joint = [r for r in records[CONDITIONS[4]].values() if r.get('parse_success')]
    stability = []
    for rater in sorted({r['target_rater'] for r in joint}):
        group = [r for r in joint if r['target_rater'] == rater]
        if len(group) > 1:
            matrix = tfidf_cosine([' '.join(r['rater_tendency']) for r in group])
            values = matrix[np.triu_indices(len(group), 1)]
            stability.append({'rater_id': rater, 'N': len(group), 'mean_within_rater_cosine': values.mean(), 'min_within_rater_cosine': values.min()})
    pd.DataFrame(stability, columns=['rater_id', 'N', 'mean_within_rater_cosine', 'min_within_rater_cosine']).to_csv(OUT / 'profiles/joint_profile_stability.csv', index=False)
    frame = data()
    review = ['# Profile grounding: 人手確認用、正しさの判定は未実施\n',
              'Trait scoreは入力されていません。以下の全文履歴とOverallを照合し、特にGrammar/Vocabularyの根拠・反例・rubricの言い換えを確認してください。\n']
    chosen = sorted(profiles, key=lambda r: ('grammar' not in json.dumps(profiles[r]['profile']).lower(), r))[:3]
    for rater in chosen:
        p = profiles[rater]
        review.extend([f'## {rater}\n', '```json\n' + json.dumps(p['profile'], ensure_ascii=False, indent=2) + '\n```\n'])
        for h in history(frame, p['history_ids']):
            review.extend([f"### History {h['id']}; Overall={h['overall']}\n", h['essay'] + '\n'])
    if not chosen:
        review.append('Profile生成は未実行です。実在しないProfile例は記載しません。\n')
    (OUT / 'profiles/profile_examples_for_manual_review.md').write_text('\n'.join(review), encoding='utf-8')


def report(summaries, cis, n):
    config = verify_inputs()
    text = ['# Trait-free Rater Profile MVP（1,000 fixed targets）\n',
            '**状態：' + ('全条件の推論完了' if n == 1000 else '未完了。全7条件共通の評価N=' + str(n)) + '**\n',
            '## 目的\nEssay本文＋Overallに採点者固有の予測情報が含まれるか、自然言語Profileへの明示化・圧縮が未知Essayの予測に有用かを検証する。\n',
            '## 対象抽出\n最新版5条件共通N=17,725からGold Overall×target_raterで比例配分。floor後の残数は小数部分が大きい層に配分（同率は層名順）。NumPy default_rng(20261012)で各層から無作為抽出、target_id順に固定。sampling_strata.csvに配分を保存。\n',
            '## 条件\nA: 既存本人K=3本文＋Overall＋6 Trait scores、Overall rubric、Target本文。既存予測再利用。\n'
            'B_correct/B_wrong: 同じmanifestの本人／他者K=3本文＋Overall、Overall rubric、6観点rubric定義、Target本文。predicted_overall＋reasoning。\n'
            'B_nohistory: 既存Rubric Only予測再利用。6観点の別ブロックを追加しておらず、履歴なしbaselineとして扱う。\n'
            'C: B_correctと同じ入力、rater_tendency＋predicted_overall＋reasoning。\n'
            'D_correct/D_wrong: Overall rubric、6観点rubric定義、本人／他者Profile、Target本文。raw履歴なし。predicted_overall＋reasoning＋used_profile_tendencies。\n',
            '## Trait除去・rubric\n新規history formatterはid/essay/overallのみをホワイトリストで渡す。Profile historyも同様。Target入力はTextのみ。'
            'rubrics/ellipse_rubric_structured.jsonの全レベル6観点記述とkey_terms_and_definitionsをそのまま使用（新作文なし）。内容はrubric_definitions_used.md参照。共通rubricのレベル番号は観測Trait scoreではない。\n',
            '## Profile履歴\nPROFILE_K=20。全target sourceを全rater候補から除外、同じFilename・exact textも除外。'
            f"共通利用可能最大K={config['maximum_common_profile_k']}。件数はprofile_history_availability.csv参照。"
            '候補は有効Overall＋非空本文、Traitの有効性では絞らない。固定seedからrater別seedを導出して固定抽出。\n',
            '## モデルと生成\nQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、vLLM、gptq_marlin。Prediction engineのmax_model_len=8192。'
            'Profile生成専用engineのmax_model_len=16384（2026-10-12にユーザーが明示承認）。Profile engine終了後にPrediction engineをロードする。'
            'Prediction: temperature=.2/top_p=.8/max_tokens=384。Profileのみ768 tokens：8つの記述欄、配列と根拠IDを含むため。'
            'request seedはbase seed＋condition＋target/rater＋attemptのSHA256。parse retry最大3回、履歴の短縮・対象除外はしない。\n',
            '## 現在の指標（available_onlyは7条件比較に使用不可）\n',
            '```csv\n' + pd.DataFrame(summaries).to_csv(index=False) + '```\n',
            '## 予測分布\nprediction_distribution.csv参照。Score 3 concentrationは全条件共通集合で比較し、MAE改善だけで成功と判断しない。未実行条件の分布は未取得。\n',
            '## Paired比較・95% CI\n差はleft - right。Accuracy/QWKは正、MAE/RMSEは負がleft優位。'
            'target単位paired percentile bootstrap、2000回、seed=20260914。両条件・全比較に同じindexを使用。'
            '同一sourceの複数raterは独立targetとして扱い、essay/rater cluster CIは本MVPでは実施しない。\n',
            '```csv\n' + pd.DataFrame(cis).to_csv(index=False) + '```\n' if cis else '全7条件の成功共通targetがないため差とCIは未算出。\n',
            '## Profile評価\n本人／他者Profileの予測性能でutilityを評価する。profile_similarity.csvはTF-IDF cosineによる表層的多様性、'
            'joint_profile_stability.csvは同rater内傾向文の類似度。異なるK=3履歴による変動とtargetによる変動は分離できない。'
            '人手grounding確認資料はprofiles/profile_examples_for_manual_review.md。人手での正しさの判定は自動実行しない。\n',
            '## Integrity\nintegrity_audit.csv、history_overlap_audit.csv、input SHA256を参照。構造的auditと推論後auditを区別する。'
            '当初GPUは別研究Ministralジョブで使用中だったが、その後空きを確認。既存ジョブは停止せず、別モデルへ変更しない。'
            'K=20のProfile生成は変更前に27件すべて8,192-token上限を超えた（最大15,451＋768）。'
            'Profile生成のみcontextを16,384へ拡張することをユーザーが承認、再auditでは全27件が上限内。変更前auditはprompt_token_audit_8192.csvに保存。\n',
            '## Parser修復\n初回Profile生成はMarkdown JSON fenceを厳密JSONパーサーが受理せず、各raterで不要な3回retryが発生した。'
            '2026-10-14にfenceだけを除去するパーサーへ修正し、全27 Profileを保存済み応答から復旧した。'
            '各raterの最初のschema-valid attemptを採用し、内容・スコアは変更していない。'
            '元応答・全attemptはrater_profiles_pre_fence_repair.jsonlとrater_profiles.jsonlに保存。'
            'profile_parse_repair_audit.csvに採用attemptと実際のretryを記録。\n',
            '## 解釈\n全7条件共通結果が揃うまではTrait-free本人履歴の優位性、Joint Profileの影響、Two-stage Profile utilityは判断できない。'
            '本人が他者より高性能なら、本文とOverallの対応に固有予測情報が含まれる可能性を述べられる。'
            'AとBはTrait除去に加え共通Trait定義の明示も異なるため、完全な単一要因比較ではない。\n',
            '## 現時点で主張できないこと\nLLMが真の人間認知過程を再現した、Profileが真の採点方針である、特定TraitがOverallに因果的に影響する、とは主張しない。'
            'target bootstrapは複数比較補正を含まず、探索的MVPとして解釈する。\n',
            '## 再実行\nリポジトリroot、WSL qwen3で以下を実行。GPU使用中はrunが明示的に拒否する。\n'
            '```bash\npython -m src.recsaver.rater_profile_mvp_1000 prepare\npython -m src.recsaver.rater_profile_mvp_1000 token-audit\npython -m src.recsaver.rater_profile_mvp_1000 profiles\npython -m src.recsaver.rater_profile_mvp_1000 dry\npython -m src.recsaver.rater_profile_mvp_1000 full\npython -m src.recsaver.rater_profile_mvp_1000 analyze\n```\n',
            '## 作成・変更ファイル\n新規src/recsaver/rater_profile_mvp_1000.py、4つの新規prompt（experiment_config.json参照）、'
            'outputs/rater_profile_mvp_1000/以下。既存研究コード・data・既存experiment outputは変更していない。'
            'git_status_before.txtには作業前からの3つのmodifiedと既存untrackedを記録、git_status_after.txtで今回分を確認可能。\n']
    (OUT / 'report.md').write_text('\n'.join(text), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'token-audit', 'reparse-profiles', 'profiles', 'dry', 'full', 'analyze'])
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare()
    elif args.phase == 'analyze':
        analyze()
    elif args.phase == 'token-audit':
        token_audit()
    elif args.phase == 'reparse-profiles':
        reparse_profiles()
    else:
        run(args.phase)
