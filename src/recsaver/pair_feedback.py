"""Reproducible, resumable rater-pair experiment. CPU preparation has no GPU imports."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .pair_feedback_masking import mask_analysis
from .pair_feedback_contracts import a_schema, b_schema, gate_a, review_and_render

ROOT = Path(__file__).resolve().parents[2]
TRAITS = ['Cohesion', 'Syntax', 'Vocabulary', 'Phraseology', 'Grammar', 'Conventions']
DIMS = ['Overall'] + TRAITS


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat()


def digest(x):
    return hashlib.sha256(x.encode('utf-8')).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(path)


def table(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def normalized(text):
    # Only whitespace and line-break layout; never rewrite words/punctuation.
    return re.sub(r'\s+', ' ', text).strip()


def rank(cfg, purpose, rater, eid):
    return digest(f'{cfg["seed"]}:{purpose}:{rater}:{eid}')


def generation_seed(cfg, stage, key):
    return int(rank(cfg, f'stage{stage}', '', key)[:8], 16) % (2 ** 31)


def number(x):
    if isinstance(x, bool):
        return None
    try:
        f = float(x)
        return int(f) if f in range(1, 6) else None
    except (ValueError, TypeError):
        return None


def model_essay(row):
    return dict(essay_id=row['essay_id'], text=row['Text'], Overall=number(row['Overall']),
                Traits={t: number(row[t]) for t in TRAITS})


def load_dataset(cfg):
    import pandas as pd
    from src.transform_data import create_rater_essay_wide
    raw = pd.read_csv(ROOT / cfg['raw_path'], low_memory=False)
    wide = pd.read_csv(ROOT / cfg['wide_path'], low_memory=False)
    recreated = create_rater_essay_wide(raw)
    cols = ['source_row_id', 'rater_position', 'Filename', 'text_id_kaggle', 'Text', 'rater_id'] + DIMS
    pd.testing.assert_frame_equal(recreated[cols], wide[cols], check_dtype=False)
    rows = wide[cols].fillna('').to_dict('records')
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen = {}
    for i, r in enumerate(rows):
        r['text_hash'] = digest(normalized(r['Text'])) if r['Text'] else ''
        r['identity_tokens'] = ([('filename', str(r['Filename']))] if r['Filename'] else []) + \
            ([('kaggle', str(r['text_id_kaggle']))] if r['text_id_kaggle'] else []) + \
            ([('text', r['text_hash'])] if r['text_hash'] else [])
        for token in r['identity_tokens']:
            if token in seen:
                parent[find(i)] = find(seen[token])
            else:
                seen[token] = i
    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(find(i), []).append(r)
    collisions = []
    for group in groups.values():
        tokens = sorted({x for r in group for x in r['identity_tokens']})
        eid = 'essay_' + digest(json.dumps(tokens, ensure_ascii=False))[:24]
        for r in group:
            r['essay_id'] = eid
        hashes = sorted({r['text_hash'] for r in group})
        filenames = sorted({r['Filename'] for r in group})
        if len(hashes) > 1 or len(filenames) > 1:
            collisions.append(dict(essay_id=eid, filenames=filenames, text_hashes=hashes,
                                   source_row_ids=sorted({int(r['source_row_id']) for r in group}),
                                   policy='Transitive exclusion across all aliases; original text retained for each record; no word normalization.'))
    return raw, rows, collisions


def provenance(row):
    return {k: row[k] for k in ['essay_id', 'source_row_id', 'rater_position', 'rater_id',
                               'Filename', 'text_id_kaggle', 'text_hash']}


def prepare(cfg, out, config_path):
    raw, rows, collisions = load_dataset(cfg)
    valid = [r for r in rows if r['rater_id'] and r['Text'].strip() and all(number(r[t]) is not None for t in DIMS)]
    heldout = []
    excluded = set()
    for pair in cfg['pairs']:
        for case in pair['cases']:
            hits = [r for r in rows if r['Filename'] == case['filename']]
            if not hits:
                raise ValueError('Comparison Filename missing: ' + case['filename'])
            ids = {r['essay_id'] for r in hits}
            assert len(ids) == 1
            excluded |= ids
            scores = []
            for rater, overall in zip(pair['raters'], case['overall']):
                matches = [r for r in hits if r['rater_id'] == rater]
                assert matches and all(number(r['Overall']) == overall for r in matches)
                assert all(all(number(r[t]) is not None for t in DIMS) for r in matches)
                chosen = next((r for r in matches if int(r['source_row_id']) == case['source_row_id']), matches[0])
                scores.append(dict(**provenance(chosen), Overall=overall, Traits={t: number(chosen[t]) for t in TRAITS},
                                   expected_row_matches=int(chosen['source_row_id']) == case['source_row_id'],
                                   text_sha256=digest(chosen['Text'])))
            assert len({r['text_hash'] for r in hits}) == 1, 'Comparison texts differ beyond whitespace'
            heldout.append(dict(pair_id=pair['pair_id'], filename=case['filename'], expected_source_row_id=case['source_row_id'],
                                essay_id=next(iter(ids)), records=scores))
    pool = [r for r in valid if r['essay_id'] not in excluded]
    selected, targets, counts, duplicates = {}, [], [], []
    for pair in cfg['pairs']:
        for rater in pair['raters']:
            by_id = {}
            for r in pool:
                if r['rater_id'] == rater:
                    by_id.setdefault(r['essay_id'], []).append(r)
            canonical = []
            for eid, same in by_id.items():
                profiles = {tuple(number(r[t]) for t in DIMS) for r in same}
                if len(same) > 1:
                    duplicates.append(dict(essay_id=eid, rater_id=rater, records=[provenance(r) for r in same],
                                           profiles=sorted(profiles), action='quarantine conflicting score profiles' if len(profiles) > 1 else 'deterministic original-text hash selection'))
                if len(profiles) > 1:
                    continue
                canonical.append(min(same, key=lambda r: (digest(r['Text']), str(r['Filename']), int(r['rater_position']))))
            if cfg['timestamp_column'] is not None:
                raise ValueError('Timestamp selection needs independently verified event availability; no fallback allowed')
            ordered = sorted(canonical, key=lambda r: rank(cfg, 'history', rater, r['essay_id']))
            chosen = ordered[:cfg['history_count']]
            selected[rater] = chosen
            counts.append(dict(rater_id=rater, valid_distinct_other_essays=len(canonical), selected=len(chosen)))
            for order, target in enumerate(chosen):
                others = [r for r in chosen if r['essay_id'] != target['essay_id']]
                refs = sorted(others, key=lambda r: rank(cfg, 'reference:' + target['essay_id'], rater, r['essay_id']))[:cfg['reference_count']]
                assert len(refs) == cfg['reference_count']
                key = rater + '__' + target['essay_id']
                targets.append(dict(key=key, pair_id=pair['pair_id'], rater_id=rater, fixed_rank=order,
                                    target=model_essay(target), history=[model_essay(r) for r in refs],
                                    source=provenance(target), history_sources=[provenance(r) for r in refs],
                                    candidate_seeds={str(k): generation_seed(cfg, 1, key + f'__K{k}') for k in range(1, cfg['candidates'] + 1)}))
    rubric = read(ROOT / cfg['rubric_path'])
    assert all(str(b) in rubric['scores'] and all(d in rubric['scores'][str(b)] for d in DIMS) for b in range(1, 6))
    assert rubric.get('key_terms_and_definitions')
    specification = dict(valid_overall_values=list(range(1, 6)), valid_trait_values=list(range(1, 6)),
                         dimension_names=DIMS, increment=1,
                         relationship='Overall is the human holistic language proficiency judgment; no arithmetic or weighted relationship with Traits is defined.')
    files = [ROOT / cfg[k] for k in ['raw_path', 'wide_path', 'rubric_path']] + [ROOT / p for p in cfg['prompts'].values()]
    files += list((ROOT / 'src/recsaver').glob('pair_feedback*.py'))
    hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in files}
    manifest = dict(version=cfg['version'], config=cfg, source_sha256=hashes, config_sha256=sha(config_path),
                    baseline_commit=cfg['baseline_commit'], current_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    selection_policy='SHA256(seed:purpose:rater:stable component ID); score-blind ordering; no row/ID chronology',
                    interpretation='未使用エッセイを用いた事後的な事例分析', timestamp_evidence=cfg['timestamp_evidence'],
                    fixed_targets=targets, heldout=heldout, history_counts=counts)
    if (out / 'manifest.json').exists():
        assert read(out / 'manifest.json') == manifest, 'Frozen configuration, code or data changed; use a separate version/output directory'
    else:
        save(out / 'manifest.json', manifest)
    save(out / 'rubric.json', rubric)
    save(out / 'score_specification.json', specification)
    save(out / 'exclusion_manifest.json', dict(excluded_essay_ids=sorted(excluded), comparisons=heldout,
                                               excluded_records=[provenance(r) for r in rows if r['essay_id'] in excluded]))
    save(out / 'identity_audit.json', dict(collisions=collisions, duplicate_profiles=duplicates))
    save(out / 'dataset_audit.json', dict(raw_rows=len(raw), wide_rows=len(rows), valid_records=len(valid),
                                         raters=len({r['rater_id'] for r in valid}), raw_columns=list(raw.columns),
                                         raw_wide_equal=True, valid_definition='Nonempty original text, rater, integer Overall + all six Traits in 1..5',
                                         identity_definition='Connected components of exact Filename, nonempty kaggle ID, whitespace-normalized text SHA256',
                                         history_counts=counts))
    checks = []
    for t in targets:
        ids = [t['target']['essay_id']] + [h['essay_id'] for h in t['history']]
        ok = len(ids) == cfg['reference_count'] + 1 and len(set(ids)) == len(ids) and not (set(ids) & excluded)
        ok &= all(s['rater_id'] == t['rater_id'] for s in [t['source']] + t['history_sources'])
        assert ok
        checks.append(dict(key=t['key'], reference_count=len(t['history']), unique_and_excluded_safe=True,
                           raw_wide_equal=True, original_text_preserved=True, same_rater=True))
    table(out / 'cpu_input_checks.csv', checks)
    table(out / 'history_counts.csv', counts)
    return manifest


def no_duplicates(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError('Duplicate JSON key: ' + k)
        value[k] = v
    return value


def strict_json(text):
    value = json.loads(text, object_pairs_hook=no_duplicates,
                       parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
    if not isinstance(value, dict):
        raise ValueError('Expected one JSON object')
    return value


def schema(stage, value, payload, template):
    if stage == 4:
        return a_schema(value)
    if stage == 5:
        return b_schema(value)
    marker = 'RETURN FORMAT' if stage == 1 else 'REQUIRED JSON FIELDS'
    start = template.index('{\n', template.index(marker))
    example = json.JSONDecoder().raw_decode(template[start:])[0]
    errors = []

    def walk(v, ex, path):
        if isinstance(ex, dict):
            if not isinstance(v, dict):
                errors.append(path + ': expected object')
                return
            for k, e in ex.items():
                if k not in v:
                    errors.append(path + '/' + k + ': missing')
                else:
                    walk(v[k], e, path + '/' + k)
            if ex:
                errors.extend(path + '/' + k + ': unexpected' for k in set(v) - set(ex))
        elif isinstance(ex, list):
            if not isinstance(v, list):
                errors.append(path + ': expected array')
            elif ex:
                for i, item in enumerate(v):
                    walk(item, ex[0], path + '/' + str(i))
        elif isinstance(ex, str) and not isinstance(v, str):
            errors.append(path + ': expected string')
        elif ex is None and v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            errors.append(path + ': expected number/null')
    walk(value, example, '')
    if value.get('schema_version') != '1.0' or value.get('rater_id') != payload['rater_id'] or value.get('target_essay_id') != payload['target']['essay_id']:
        errors.append('version/rater/target identity mismatch')
    if stage == 1:
        if value.get('observed_score_alignment', {}).get('observed_target_scores') != {k: payload['target'][k] for k in ['Overall', 'Traits']}:
            errors.append('observed target profile not copied exactly')
        for p in value.get('score_free_analysis', {}).get('history_patterns', []):
            if p.get('status') not in ['recurring_in_supplied_history', 'single_case_hypothesis']:
                errors.append('invalid history status')
        if value.get('observed_score_alignment', {}).get('explanatory_status') not in ['supported_interpretation', 'partly_supported', 'insufficient']:
            errors.append('invalid explanatory status')
    else:
        status, score = value.get('status'), value.get('reconstructed_overall')
        if status not in ['estimated', 'insufficient_information', 'contaminated_input'] or (status == 'estimated' and number(score) is None) or (status != 'estimated' and score is not None):
            errors.append('invalid reconstruction status/value')
        supplied = {h['essay_id'] for h in payload['history']}
        if not set(value.get('used_history_essay_ids', [])) <= supplied:
            errors.append('unknown history reference')
    return errors


def valid(folder):
    return (folder / 'result.json').exists() and read(folder / 'result.json')['schema_valid']


def spans(text):
    result = []
    # Nonoverlapping source slices; original offsets and whitespace retained.
    for pindex, paragraph in enumerate(re.finditer(r'[^\r\n]+', text)):
        for sentence in re.finditer(r'[^.!?]+(?:[.!?]+|$)', paragraph.group()):
            a = paragraph.start() + sentence.start()
            b = paragraph.start() + sentence.end()
            if text[a:b].strip():
                result.append(dict(span_id=f'S{len(result) + 1}', paragraph_id=f'P{pindex + 1}', start=a, end=b, text=text[a:b]))
    return result


def base(out, target):
    return dict(rater_id=target['rater_id'], rubric=read(out / 'rubric.json'),
                score_specification=read(out / 'score_specification.json'), history=target['history'])


def inspect_mask(record, target):
    analysis = record['score_free_analysis']
    result = mask_analysis(analysis, target['history'], target['target'])
    audit = result['audit']
    history = {h['essay_id']: h for h in target['history']}
    for pattern in analysis['history_patterns']:
        support = pattern['support'] + pattern['counterevidence']
        for h in support:
            eid = h.get('history_essay_id')
            if eid not in history:
                audit['quarantine'].append(dict(kind='invalid_or_self_history_id', path=eid))
            elif 'relevant_observed_history_scores' in h:
                scores = h['relevant_observed_history_scores']
                actual = history[eid]
                if scores.get('Overall') is not None and scores['Overall'] != actual['Overall']:
                    audit['quarantine'].append(dict(kind='history_score_mismatch', path=eid))
                if any(actual['Traits'].get(k) != v for k, v in scores.get('Traits', {}).items()):
                    audit['quarantine'].append(dict(kind='history_trait_mismatch', path=eid))
    audit['automatic_pass'] = not audit['quarantine']
    audit['scope'] = 'Conservative mechanical input screen, not semantic support certification or human review.'
    return result


def candidate_decisions(cfg, out, targets):
    rows, accepted = [], []
    for target in targets:
        matched = []
        for k in range(1, cfg['candidates'] + 1):
            key = target['key'] + f'__K{k}'
            f1, fm, f3 = [out / s / key for s in ['stage1', 'stage2', 'stage3']]
            v = read(f3 / 'parsed.json') if valid(f3) else {}
            mask_pass = (fm / 'audit.json').exists() and read(fm / 'audit.json')['automatic_pass']
            match = bool(mask_pass and valid(f3) and v.get('status') == 'estimated' and v.get('reconstructed_overall') == target['target']['Overall'])
            reason = 'accepted' if match else 'stage1_invalid_or_unrun' if not valid(f1) else 'mask_quarantined' if not mask_pass else 'stage3_invalid_or_unrun' if not valid(f3) else 'stage3_' + v.get('status', 'invalid') if v.get('status') != 'estimated' else 'overall_mismatch'
            rows.append(dict(candidate_id=key, rater_id=target['rater_id'], essay_id=target['target']['essay_id'],
                             generated=(f1 / 'raw.txt').exists(), json_pass=(f1 / 'result.json').exists() and read(f1 / 'result.json')['json_valid'],
                             schema_pass=valid(f1), mask_pass=bool(mask_pass), reconstructed_overall=v.get('reconstructed_overall'),
                             exact_match=match, accepted=match, reason=reason))
            if match:
                matched.append(key)
        save(out / 'essay_decisions' / (target['key'] + '.json'), dict(accepted=bool(matched), accepted_candidates=matched))
        if matched:
            accepted.append(target)
    table(out / 'candidate_results.csv', rows)
    save(out / 'candidate_results.json', rows)
    return accepted, rows


def local_findings(out, accepted):
    findings = {}
    for target in accepted:
        f = out / 'stage4' / target['key']
        inp = read(f / 'input.json') if (f / 'input.json').exists() else None
        gate = gate_a(read(f / 'parsed.json'), inp) if inp and valid(f) else dict(top_errors=['Stage 4 invalid or unrun'], checks=[], passed_observations=[])
        save(f / 'source_checks.json', gate)
        observations = []
        for o in gate['passed_observations']:
            dim = o['dimension']
            score = target['target']['Overall'] if dim == 'Overall' else target['target']['Traits'][dim]
            observations.append(dict(o, observation_key=target['target']['essay_id'] + '::' + o['observation_id'],
                                     target_essay_id=target['target']['essay_id'], observed_score=score))
        save(f / 'observations.json', observations)
        if observations:
            findings.setdefault(target['rater_id'], []).append(dict(target=target, observations=observations))
    return findings


def integration_payload(out, rater, chosen):
    observations = [o for c in chosen for o in c['observations']]
    rubric = read(out / 'rubric.json')
    entries = [dict(rubric_ref_id=f'{d}:{b}', dimension=d, score_band=b, descriptor=rubric['scores'][str(b)][d])
               for d in DIMS for b in range(1, 6)]
    return dict(rater_id=rater, accepted_target_ids=[c['target']['target']['essay_id'] for c in chosen],
                verified_observations=observations, rubric_entries=entries,
                evidence_limitations=['These are retrospective cases from one fixed, score-blind history sample.',
                                     'Source matching confirms quotations and recorded scores, not semantic support.',
                                     'Only observations from at least two distinct essays may support a feature-to-evaluation pattern.',
                                     'A single essay permits local feedback only. Shared scores or features alone do not establish a scoring pattern.',
                                     'No access to the human rater\'s true reasons, numerical weights or causal effects; no rerating occurred.'])


def run(cfg, out, manifest, smoke=False):
    from .pair_feedback_gpu import Engine
    engine = Engine(cfg, out)
    targets = manifest['fixed_targets']
    if smoke:
        targets = [next(t for t in targets if t['rater_id'] == r) for r in manifest_raters(cfg)]
    save(out / 'status.json', dict(time=now(), status='smoke_running' if smoke else 'full_running'))
    jobs = [(t['key'] + f'__K{k}', dict(base(out, t), target=t['target'])) for t in targets for k in range(1, cfg['candidates'] + 1)]
    engine.run(1, jobs)
    jobs = []
    for t in targets:
        for k in range(1, cfg['candidates'] + 1):
            key = t['key'] + f'__K{k}'
            f1, fm = out / 'stage1' / key, out / 'stage2' / key
            if not valid(f1):
                continue
            record = read(f1 / 'parsed.json')
            mask = inspect_mask(record, t)
            save(fm / 'original_analysis.json', record['score_free_analysis'])
            save(fm / 'masked_analysis.json', mask['masked_analysis'])
            save(fm / 'audit.json', mask['audit'])
            if mask['audit']['automatic_pass']:
                payload = dict(base(out, t), target={k: t['target'][k] for k in ['essay_id', 'text']}, reference_analysis=mask['masked_analysis'])
                assert set(payload['target']) == {'essay_id', 'text'} and 'observed_score_alignment' not in payload
                jobs.append((key, payload))
    engine.run(3, jobs)
    accepted, _ = candidate_decisions(cfg, out, targets)
    engine.run(4, [(t['key'], dict(target_essay_id=t['target']['essay_id'], target_text=t['target']['text'],
                                 evidence_spans=spans(t['target']['text']), dimension_names=DIMS)) for t in accepted])
    findings = local_findings(out, accepted)
    if smoke:
        # Exercise Stage 5 and resumption without changing the full-run equalization.
        # Smoke Stage 5 gets its own namespace and never counts as final feedback.
        stage5(cfg, out, findings, engine, suffix='smoke')
    else:
        stage5(cfg, out, findings, engine)
    report(cfg, out, manifest)
    save(out / ('smoke_status.json' if smoke else 'status.json'), dict(time=now(), status='completed',
         scope='smoke_only' if smoke else 'Stage 1-5', stage6='excluded'))


def manifest_raters(cfg):
    return [r for p in cfg['pairs'] for r in p['raters']]


def stage5(cfg, out, findings, engine, suffix=''):
    jobs, alignment = [], []
    for pair in cfg['pairs']:
        left, right = pair['raters']
        n = min(len(findings.get(left, [])), len(findings.get(right, [])))
        m = min(n, cfg['stage5_max_essays_per_side'])
        ordered = {r: sorted(findings.get(r, []), key=lambda c: c['target']['fixed_rank']) for r in pair['raters']}
        # Preflight both sides at the same M; reduce equally and deterministically only for Stage 5 capacity.
        while m and any(not engine.fits(5, integration_payload(out, r, ordered[r][:m])) for r in pair['raters']):
            m -= 1
        alignment.append(dict(pair_id=pair['pair_id'], n_left=len(ordered[left]), n_right=len(ordered[right]),
                              natural_M=n, M=m, capacity_cap=m if m < n else None,
                              selected={r: [c['target']['target']['essay_id'] for c in ordered[r][:m]] for r in pair['raters']},
                              unused={r: [c['target']['target']['essay_id'] for c in ordered[r][m:]] for r in pair['raters']}))
        for r in pair['raters']:
            key = r + ('__' + suffix if suffix else '')
            if m == 0:
                save(out / 'stage5' / key / 'skip.json', dict(status='insufficient_evidence', M=0, reason='No equally sized source-checked essay set'))
                continue
            payload = integration_payload(out, r, ordered[r][:m])
            save(out / 'stage5' / key / 'input_3b.json', payload)
            jobs.append((key, payload))
    save(out / ('smoke_equalization.json' if suffix else 'equalization.json'), alignment)
    engine.run(5, jobs)
    for key, payload in jobs:
        folder = out / 'stage5' / key
        if valid(folder):
            result = review_and_render(read(folder / 'parsed.json'), payload)
            save(folder / 'render_checks.json', result)
            if result['pass_']:
                (folder / 'feedback.txt').write_text(result['feedback_paragraph'] + '\n', encoding='utf-8')


def report(cfg, out, manifest):
    targets = manifest['fixed_targets']
    accepted, candidates = candidate_decisions(cfg, out, targets)
    findings = local_findings(out, accepted)
    eq = read(out / 'equalization.json') if (out / 'equalization.json').exists() else []
    rows = []
    for r in manifest_raters(cfg):
        cr = [c for c in candidates if c['rater_id'] == r]
        f = out / 'stage5' / r
        alignment = next((e for e in eq if r in e['selected']), None)
        status = 'rendered_semantics_unreviewed' if (f / 'feedback.txt').exists() else 'insufficient_evidence' if (f / 'skip.json').exists() else 'invalid_or_unrun'
        rows.append(dict(rater_id=r, targets=sum(t['rater_id'] == r for t in targets), output_candidates=sum(c['generated'] for c in cr),
                         json_pass=sum(c['json_pass'] for c in cr), schema_pass=sum(c['schema_pass'] for c in cr), mask_pass=sum(c['mask_pass'] for c in cr),
                         exact_matches=sum(c['exact_match'] for c in cr), accepted_essays=sum(t['rater_id'] == r for t in accepted),
                         stage4_essays=len(findings.get(r, [])), stage5_M=alignment['M'] if alignment else None, stage5_status=status))
    table(out / 'summary.csv', rows)
    save(out / 'summary.json', rows)
    lines = ['# 採点者ペア比較実験', '', '未使用エッセイを用いた事後的な事例分析。3点差の事例を選んだ分析であり、本人の真の採点理由や再採点による点差縮小は検証していない。', '',
             '|採点者|対象|候補|JSON|マスク|完全一致|採用エッセイ|有効所見付き|統合M|状態|', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for row in rows:
        lines.append('|' + '|'.join(str(row[k]) for k in ['rater_id', 'targets', 'output_candidates', 'json_pass', 'mask_pass', 'exact_matches', 'accepted_essays', 'stage4_essays', 'stage5_M', 'stage5_status']) + '|')
    lines += ['', 'Stage 4の出典一致は意味的支持を保証しない。Stage 5は直接統合の生成内容を保持し、機械検査と意味内容のレビューを分ける。', '',
              '固定比較用5エッセイの本文と得点は生成入力へ渡していない。対応の確認は生成終了後の別監査に保存する。']
    (out / 'report_ja.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(rows, ensure_ascii=False, indent=2), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phase', choices=['prepare', 'smoke', 'run', 'report', 'tokens'])
    ap.add_argument('--config', type=Path, required=True)
    args = ap.parse_args()
    config_path = args.config.resolve()
    cfg = read(config_path)
    out = ROOT / cfg['output_dir']
    manifest = prepare(cfg, out, config_path)
    if args.phase in ['smoke', 'run']:
        run(cfg, out, manifest, smoke=args.phase == 'smoke')
    elif args.phase == 'report':
        report(cfg, out, manifest)
    elif args.phase == 'tokens':
        from .pair_feedback_gpu import Engine
        e = Engine(cfg, out)
        e.run(1, [(t['key'] + f'__K{k}', dict(base(out, t), target=t['target']))
                  for t in manifest['fixed_targets'] for k in range(1, cfg['candidates'] + 1)], dry=True)


if __name__ == '__main__':
    main()
