"""自己検証済み参照推論のフィードバック予備検証。既存結果は読取専用。"""
from __future__ import annotations
import argparse
import collections
import csv
import hashlib
import json
import re
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]


def now():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def read(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as f:
        return [json.loads(s) for s in f if s.strip()]


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def append(path, obj):
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')
        f.flush()


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def locate(text, quote):
    """Unicode code-point offsets, zero-based/end-exclusive; lines one-based."""
    if not isinstance(quote, str) or not quote:
        return []
    result = []
    start = 0
    while True:
        pos = text.find(quote, start)
        if pos < 0:
            return result
        result.append({'start': pos, 'end': pos + len(quote),
                       'line_start': text.count('\n', 0, pos) + 1,
                       'line_end': text.count('\n', 0, pos + len(quote)) + 1})
        start = pos + 1


def prepare(cfg, out):
    import yaml
    from .history import format_history
    import pandas as pd
    src = ROOT / cfg['source_dir']
    old = yaml.safe_load((ROOT / cfg['source_config']).read_text())
    rubric_text = (ROOT / old['rubric_path']).read_text(encoding='utf-8')
    structured = json.loads((ROOT / cfg['rubric_structured']).read_text())
    rubric = {f'Overall.S{s}': v['Overall'] for s, v in structured['scores'].items()}
    for value in rubric.values():
        assert value in rubric_text, 'Overall rubric transcription mismatch'
    pool = read(src / 'verified_reference_pool.jsonl')
    candidates = {(r['target_id'], r['candidate_index'], r['attempt_index']): r
                  for r in read(src / 'reference_candidates.jsonl')}
    verifications = read(src / 'self_verification_results.jsonl')
    verified = {}
    for v in verifications:
        key = (v['target_id'], v['candidate_index'], v['reference_attempt_index'])
        if v.get('verified') and v.get('parse_success'):
            verified[key] = v
    wide = csv_rows(ROOT / old['data']['processed_path'])
    raw = csv_rows(ROOT / cfg['raw_path'])
    by_id = {f"{r['source_row_id']}:{r['rater_position']}": r for r in wide}
    ref_template = (ROOT / old['reference_prompt']).read_text(encoding='utf-8')
    ver_template = (ROOT / old['self_verification_prompt']).read_text(encoding='utf-8')
    checks, joined = [], []
    for p in pool:
        try:
            key = (p['target_id'], p['candidate_index'], p['attempt_index'])
            w = by_id[p['target_id']]
            r = raw[int(w['source_row_id'])]
            position = w['rater_position']
            assert w['Text'] == r['Text'], 'raw/processed text mismatch'
            assert w['rater_id'] == r[f'Rater_{position}'].strip() == p['target_rater'], 'actual rater mismatch'
            assert int(w['Overall']) == int(r[f'Overall_{position}']) == p['gold_overall'], 'Overall mismatch'
            assert w['Filename'] == r['Filename'] and w['text_id_kaggle'] == r['text_id_kaggle']
            assert p['verified'] is True and p['reconstructed_overall'] == p['gold_overall']
            v = verified[key]
            assert v['reconstructed_overall'] == p['gold_overall']
            assert v['history_ids'] == p['history_ids'] and len(p['history_ids']) == 3
            history = [by_id[h] for h in p['history_ids']]
            assert all(h['rater_id'] == w['rater_id'] and h['source_row_id'] != w['source_row_id'] for h in history)
            # 当時のformatterでpromptを再構成し、対象と履歴を取り違えていないことを確認。
            hf = pd.DataFrame(history)
            for c in ['Overall','Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']:
                hf[c] = hf[c].astype(int)
            hf['target_id'] = p['history_ids']
            hist_text = format_history(hf)
            args = dict(overall_rubric=rubric_text, rating_history=hist_text, target_essay=w['Text'])
            assert v['prompt'] == ver_template.format(**args, reference_reasoning=p['reference_reasoning']), 'verification prompt mismatch'
            c = candidates.get(key)
            if c:
                assert c['accepted_as_leakage_free'] and c['reference_reasoning'] == p['reference_reasoning']
                assert c['prompt'] == ref_template.format(**args, gold_overall=p['gold_overall']), 'reference prompt mismatch'
            unique = w['text_id_kaggle'] or w['Filename'] or digest(w['Text'])
            joined.append(dict(p, target_text=w['Text'], source_row_id=int(w['source_row_id']),
                               filename=w['Filename'], text_id_kaggle=w['text_id_kaggle'], unique_essay_key=unique,
                               candidate_journal_present=c is not None,
                               candidate_provenance='candidate journal' if c else 'verified pool + exact self-verification prompt; generation journal absent',
                               history=[dict(target_id=h, text=by_id[h]['Text'], overall=int(by_id[h]['Overall'])) for h in p['history_ids']]))
            checks.append(dict(target_id=p['target_id'], candidate_index=p['candidate_index'], ok=True,
                               candidate_journal_present=c is not None))
        except Exception as e:
            checks.append(dict(target_id=p['target_id'], candidate_index=p['candidate_index'], ok=False, error=str(e)))
    save(out / 'source_checks.json', checks)
    # 同一答案の複数候補・重複source行を独立履歴として数えない。
    unique_rows = {}
    for row in sorted(joined, key=lambda x: (x['candidate_index'], x['attempt_index'], x['target_id'])):
        unique_rows.setdefault((row['target_rater'], row['unique_essay_key']), row)
    groups = collections.defaultdict(list)
    for r in unique_rows.values():
        groups[r['target_rater']].append(r)
    counts = {k: len(v) for k, v in sorted(groups.items())}
    eligible = [k for k in groups if len(groups[k]) >= cfg['min_essays_per_rater']]
    rank = lambda kind, value: digest(f"{cfg['seed']}:{kind}:{value}")
    raters = sorted(eligible, key=lambda r: (rank('rater', r), r))[:cfg['max_raters']]
    selected = [r for k in raters for r in sorted(groups[k], key=lambda x: (rank('essay', x['target_id']), x['target_id']))[:cfg['max_essays_per_rater']]]
    for r in selected:
        r['selection_rank'] = rank('essay', r['target_id'])
    selection = dict(seed=cfg['seed'], rule=cfg['selection'], available_unique_essays_by_rater=counts,
                     selected_raters=raters, selected_target_ids=[r['target_id'] for r in selected],
                     source_pool_rows=len(pool), audited_pool_rows=len(joined),
                     rejected_pool_rows=sum(not c['ok'] for c in checks),
                     sample_role='動作と出力内容の確認用。代表性を持つ評価標本ではない。')
    save(out / 'selection.json', selection)
    save(out / 'inputs.json', selected)
    save(out / 'rubric.json', rubric)
    paths = [ROOT / cfg['source_config'], ROOT / cfg['raw_path'], ROOT / old['data']['processed_path'],
             ROOT / old['reference_prompt'], ROOT / old['self_verification_prompt'], ROOT / old['rubric_path'],
             ROOT / cfg['rubric_structured'], *[src / n for n in ['verified_reference_pool.jsonl', 'reference_candidates.jsonl', 'self_verification_results.jsonl','metadata.json','integrity_checks.json']]]
    save(out / 'provenance.json', dict(timestamp=now(), source_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
         confirmed=['Overall score-conditioned reference reasoning', 'verification reconstructs rationale score, not evidence validity',
                    'actual IDs from raw Rater_1/Rater_2 values', 'raw logical row index + position target ID',
                    'exact target text and historical prompt reconstruction', 'Overall rubric MD matches stored structured transcription'],
         not_confirmed=['Source DOCX ELL_Rubrics (1).docx is absent; official transcription authenticity cannot be independently checked against original DOCX',
                        'Human rater true reasoning; actual trait weights; semantic correctness of generated rationales'],
         original_model=old['model'], original_generation=old['generation'],
         original_prompt_paths=[old['reference_prompt'], old['self_verification_prompt']]))
    return old


def validate_a(obj, item):
    assert isinstance(obj.get('claims'), list) and len(obj['claims']) <= 3
    for i, c in enumerate(obj['claims']):
        assert c['scope'] in ['target','history','uncertain']
        assert c['semantic_support'] in ['supported','uncertain','unsupported']
        assert c['direction'] in ['positive','negative','mixed','unclear']
        for field in ['feature','rationale_claim','semantic_explanation','overall_relation','limitations']:
            assert isinstance(c[field], str)
        assert isinstance(c['quotes'], list)
        c['evidence_id'] = f"{item['target_id']}.E{i+1}"
        c['target_id'] = item['target_id']
        c['rationale_span_verified'] = bool(c['rationale_claim']) and c['rationale_claim'] in item['reference_reasoning']
        c['quote_checks'] = [dict(quote=q, occurrences=locate(item['target_text'], q)) for q in c['quotes']]
        c['quotes_verified'] = bool(c['quote_checks']) and all(q['occurrences'] for q in c['quote_checks'])
        c['usable_for_synthesis'] = bool(c['scope']=='target' and c['semantic_support']=='supported' and c['quotes_verified'] and c['rationale_span_verified'])
        c['semantic_validation'] = 'model-assessed; not independently human-validated'
    return obj


def evidence_map(a_rows):
    return {c['evidence_id']: c for row in a_rows for c in row['claims']}


def apply_review(a_rows, review):
    """原出力を保持し、明示した証拠不足のレビューだけを反映する。"""
    for c in evidence_map(a_rows).values():
        override = review.get('overrides', {}).get(c['evidence_id'])
        if override:
            assert override['semantic_support'] in ['uncertain','unsupported'], 'Review may only conservatively downgrade'
            c['model_semantic_support'] = c['semantic_support']
            c['semantic_support'] = override['semantic_support']
            c['review_reason'] = override['reason']
            c['reviewer'] = review['reviewer']
            c['usable_for_synthesis'] = False
            c['limitations'] += ' / Review: ' + override['reason']
    return a_rows


def validate_b(obj, evidence, target_ids):
    assert isinstance(obj['patterns'], list) and len(obj['patterns']) <= 2
    seen = set()
    for p in obj['patterns']:
        assert p['pattern_id'] not in seen
        seen.add(p['pattern_id'])
        ids = p['support_evidence_ids']
        assert all(e in evidence and evidence[e]['usable_for_synthesis'] for e in ids), 'B uses ineligible evidence'
        assert len({evidence[e]['target_id'] for e in ids}) >= 2, 'B needs 2 distinct target essays'
        assert all(e in evidence for e in p['counterexample_evidence_ids'])
        assert set(p['non_applicable_target_ids']) <= set(target_ids)
        for k in ['inferred_tendency','evaluation_score_relation','unknowns']:
            assert p[k]
    assert 'undetermined' in obj and 'cross_essay_review' in obj
    return obj


def validate_c(obj, evidence, b, rubric):
    assert [e['number'] for e in obj['elements']] == [1,2,3,4,5], 'five elements required'
    patterns = {p['pattern_id'] for p in b['patterns']}
    relations = {r['relation_id'] for r in obj['relations']}
    assert len(relations) == len(obj['relations']) and relations
    for r in obj['relations']:
        assert not r['pattern_id'] or r['pattern_id'] in patterns
        assert r['rubric_id'] in rubric
        assert r['condition_quote'] and r['condition_quote'] in rubric[r['rubric_id']], 'rubric condition not verbatim'
        assert r['evidence_ids'] and all(e in evidence and evidence[e]['usable_for_synthesis'] for e in r['evidence_ids'])
        for k in ['evidence_to_condition','judgment_to_condition','interpretation_or_missing_evidence','next_check']:
            assert r[k], f'missing relation explanation {k}'
    for e in obj['elements']:
        assert e['text']
        assert all(x in evidence and evidence[x]['usable_for_synthesis'] for x in e['evidence_ids'])
        assert set(e['rubric_ids']) <= set(rubric)
        assert set(e['pattern_ids']) <= patterns
        assert set(e['relation_ids']) <= relations
    assert obj['elements'][3]['relation_ids'] and obj['elements'][4]['relation_ids']
    assert set(obj['elements'][4]['relation_ids']) <= set(obj['elements'][3]['relation_ids']), '5 must follow 4'
    for rid in obj['elements'][0]['rubric_ids']:
        assert rubric[rid] in obj['elements'][0]['text'], 'element 1 must retain full rubric description'
    return obj


class Runner:
    def __init__(self, cfg, out, old):
        self.cfg, self.out, self.old = cfg, out, old
        self.runtime_model = dict(old['model'], max_model_len=cfg.get('runtime_model_max_len', old['model']['max_model_len']))
        self.generator = None

    def call(self, stage, key, payload, validator):
        template = (ROOT / f'prompts/en/rater_feedback_pilot_{stage}_v1.txt').read_text(encoding='utf-8')
        base = template + json.dumps(payload, ensure_ascii=False)
        fingerprint = digest(base + json.dumps(dict(version=self.cfg['version'], model=self.old['model'],
            seed=self.cfg['seed'], parameters=dict(self.cfg['generation'], max_tokens=self.cfg['max_output_tokens'][stage])), sort_keys=True))
        dest = self.out / stage / f"{key.replace(':','_')}.json"
        if dest.exists():
            prior = json.loads(dest.read_text())
            assert prior['fingerprint'] == fingerprint, 'input or prompt changed: use a new output_dir'
            return prior['result']
        if self.generator is None:
            # 他実験のGPU使用中は新しいモデルをロードしない。プロセス情報・認証情報は読まない。
            import subprocess
            gpu = subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
                                 capture_output=True, text=True, check=True)
            free = int(gpu.stdout.strip().splitlines()[0])
            if free < 24000:
                append(self.out / 'calls.jsonl', dict(stage=stage, key=key, timestamp=now(), status='failed',
                    error=f'GPU memory.free={free} MiB; 24000 MiB required before Qwen initialization; no model call'))
                raise RuntimeError('GPU busy; resume when free. Existing processes are not modified.')
            try:
                from .model import VLLMGenerator
                self.generator = VLLMGenerator(dict(self.old, model=self.runtime_model))
            except BaseException:
                append(self.out / 'calls.jsonl', dict(stage=stage, key=key, timestamp=now(), status='failed',
                    error='model initialization failed', traceback=traceback.format_exc()))
                raise
        error = ''
        for attempt in range(self.cfg['validation_retries'] + 1):
            prompt = base if not error else base + '\nPrevious response failed validation: ' + error + '\nReturn corrected full JSON. Do not invent evidence.'
            params = dict(self.cfg['generation'], max_tokens=self.cfg['max_output_tokens'][stage],
                          seed=int(digest(f"{self.cfg['seed']}:{stage}:{key}:{attempt}")[:8], 16))
            record = dict(stage=stage, key=key, attempt=attempt, timestamp=now(), fingerprint=fingerprint,
                          model=self.runtime_model, source_model=self.old['model'], sampling_parameters=params, prompt=prompt)
            start = time.monotonic()
            try:
                tokens = len(self.generator.tokenizer.apply_chat_template([{'role':'user','content':prompt}], tokenize=True, add_generation_prompt=True))
                record['prompt_tokens'] = tokens
                assert tokens + params['max_tokens'] <= self.runtime_model['max_model_len'], 'context limit exceeded; no truncation applied'
                raw = self.generator.generate([prompt], params)[0][0]
                record['raw_output'] = raw
                clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip())
                result = validator(json.loads(clean))
                record.update(status='ok', elapsed_seconds=time.monotonic()-start)
                append(self.out / 'calls.jsonl', record)
                save(dest, dict(fingerprint=fingerprint, result=result, timestamp=now()))
                print(stage, key, 'ok', flush=True)
                return result
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
                record.update(status='failed', error=error, elapsed_seconds=time.monotonic()-start)
                append(self.out / 'calls.jsonl', record)
                print(stage, key, error, flush=True)
        raise RuntimeError(f'{stage} {key}: {error}; failed outputs retained in calls.jsonl')

    def rater(self, rater, inputs, rubric):
        rows = [r for r in inputs if r['target_rater'] == rater]
        a = []
        for item in rows:
            payload = {k:item[k] for k in ['target_id','target_text','gold_overall','reference_reasoning','history_ids']}
            a.append(dict(target_id=item['target_id'], gold_overall=item['gold_overall'],
                          **self.call('A', item['target_id'], payload, lambda x: validate_a(x, item))))
        review_path = self.out / 'semantic_review.json'
        if review_path.exists():
            a = apply_review(a, json.loads(review_path.read_text()))
            save(self.out / 'A_reviewed' / f'{rater}.json', a)
        evidence = evidence_map(a)
        # 重複するquote_checks内の原文などを除き、意味的判断と留保は保持。
        fields = ['evidence_id','target_id','rationale_claim','feature','direction','quotes','semantic_support',
                  'semantic_explanation','overall_relation','limitations','usable_for_synthesis']
        compact = [{k:c[k] for k in fields if c['usable_for_synthesis'] or k not in ['quotes','semantic_explanation','overall_relation']}
                   for c in evidence.values()]
        summary = dict(rater_id=rater, observed_scores={r['target_id']:r['gold_overall'] for r in rows}, evidence=compact,
                       history_and_unassessed=[dict(target_id=r['target_id'], history_separation=r.get('history_separation',''),
                           unassessed_claims=r.get('unassessed_claims','')) for r in a])
        b = self.call('B', rater, summary, lambda x: validate_b(x, evidence, [r['target_id'] for r in rows]))
        # 原文全文ではなく確認済み引用と監査結果を渡す。Aの不適格証拠はCに渡さない。
        payload = dict(rater_id=rater, observed_scores={r['target_id']:r['gold_overall'] for r in rows},
                       synthesis=b, evidence={c['evidence_id']:c for c in compact if c['usable_for_synthesis']}, official_overall_rubric=rubric)
        c = self.call('C', rater, payload, lambda x: validate_c(x, evidence, b, rubric))
        return dict(rater_id=rater, target_count=len(rows), observed_scores=payload['observed_scores'], A=a, B=b, C=c)


def report(out, results):
    titles = ['ルーブリックの基準','複数エッセイに共通する評価傾向','傾向が表れた箇所','基準と実際の採点の関係','次の採点で確認する点']
    lines = ['# 採点者フィードバック予備検証', '', '既存の自己検証済み・観測Overall条件付き参照推論のみを使用。最終実験ではなく、代表性・有効性・バイアス是正効果を評価しない。',
             '', '引用の文字列一致は機械検査。意味的支持はモデルによる暫定評価であり、人間による妥当性確認ではない。元ルーブリックDOCXは不在。保存済みOverall原文を主照合先とし、観点別得点・重みは復元しない。', '']
    all_claims = []
    for result in results:
        evidence = evidence_map(result['A'])
        all_claims.extend(evidence.values())
        lines += [f"## {result['rater_id']}", '', f"対象答案数: {result['target_count']}。観測Overall分布: {dict(sorted(collections.Counter(result['observed_scores'].values()).items()))}", '',
                  '対象ID・Overall: ' + json.dumps(result['observed_scores'], ensure_ascii=False), '', '### フィードバック', '']
        for e in result['C']['elements']:
            lines += [e['text'], '']
        lines += ['### 要素・証拠・基準の対応', '', '|要素|該当部分|証拠ID|基準ID|傾向ID|関係ID|', '|---|---|---|---|---|---|']
        for e in result['C']['elements']:
            text = e['text'].replace('|','\\|').replace('\n','<br>')
            lines.append(f"|{e['number']} {titles[e['number']-1]}|{text}|{', '.join(e['evidence_ids'])}|{', '.join(e['rubric_ids'])}|{', '.join(e['pattern_ids'])}|{', '.join(e['relation_ids'])}|")
        lines += ['', '### 条件と判断の照合・次回確認', '']
        for r in result['C']['relations']:
            lines += [f"- {r['relation_id']} / {r['rubric_id']} / {r['condition_quote']}", f"  - 証拠: {', '.join(r['evidence_ids'])}。{r['evidence_to_condition']}",
                      f"  - 評価判断: {r['judgment_to_condition']}", f"  - 解釈差・不足: {r['interpretation_or_missing_evidence']}", f"  - 次回: {r['next_check']}"]
        lines += ['', '### 支持例・反例・判断できない点', '', result['B']['cross_essay_review'], '', result['B']['undetermined']]
        for p in result['B']['patterns']:
            lines += ['', f"- {p['pattern_id']}: {p['inferred_tendency']}", f"  - 支持: {p['support_evidence_ids']}", f"  - 反例: {p['counterexample_evidence_ids']}。非該当: {p['non_applicable_target_ids']}", f"  - 不明: {p['unknowns']}"]
        lines += ['', '### 個別証拠の監査', '']
        for c in evidence.values():
            lines += [f"- {c['evidence_id']} ({c['scope']}, {c['semantic_support']}, 統合利用={c['usable_for_synthesis']}): {c['feature']}",
                      f"  - 参照推論: {c['rationale_claim']}", f"  - 意味的支持の暫定判断: {c['semantic_explanation']}", f"  - 留保: {c['limitations']}"]
            for q in c['quote_checks']:
                lines += [f"  - 原文引用: {json.dumps(q['quote'],ensure_ascii=False)} / 位置: {q['occurrences']}"]
        lines += ['', result['C']['limits'], '']
    calls = read(out / 'calls.jsonl')
    stats = dict(timestamp=now(), completed_raters=len(results), target_count=sum(r['target_count'] for r in results),
                 extracted_claims=len(all_claims), semantic_support_counts=dict(collections.Counter(c['semantic_support'] for c in all_claims)),
                 scope_counts=dict(collections.Counter(c['scope'] for c in all_claims)),
                 usable_claims=sum(c['usable_for_synthesis'] for c in all_claims),
                 invalid_quote_count=sum(not q['occurrences'] for c in all_claims for q in c['quote_checks']),
                 quote_count=sum(len(c['quote_checks']) for c in all_claims),
                 rationale_span_failures=sum(not c['rationale_span_verified'] for c in all_claims),
                 failed_calls=sum(c['status']=='failed' for c in calls), successful_calls=sum(c['status']=='ok' for c in calls),
                 interpretation='Claim rates describe at most three model-extracted claims per essay; not all rationale assertions or human validity rates.')
    save(out / 'checks.json', stats)
    save(out / 'feedback.json', results)
    lines += ['## 検査集計', '', '```json', json.dumps(stats, ensure_ascii=False, indent=2), '```', '',
              '## 次回の個別理由生成プロンプト改善案', '',
              '- 対象答案と入力履歴の主張を別フィールドに分け、各主張に対象IDを必須化する。',
              '- 評価特徴、原文引用、位置、評価方向、観測Overallとの定性的関係を構造化する。',
              '- ルーブリックの該当条件IDと程度・頻度・伝達阻害の範囲を明示し、短い引用で全体判断を代用させない。',
              '- 支持例に加えて反例・解釈差・不足を要求し、本文から確認できない主張は保留させる。',
              '- 得点再構成の自己検証に加えて、引用一致検査と独立した意味的支持の評価を設ける。',
              '- 観測得点を与えた事後説明の性質と、採点者固有性を比較していない制約を保持する。', '']
    (out / 'report.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['prepare','pilot','remaining','report'])
    parser.add_argument('--config', default='configs/rater_feedback_pilot.json')
    args = parser.parse_args()
    cfg = json.loads((ROOT / args.config).read_text())
    out = ROOT / cfg['output_dir']
    out.mkdir(parents=True, exist_ok=True)
    import yaml
    old = yaml.safe_load((ROOT / cfg['source_config']).read_text())
    if args.phase == 'prepare' or not (out / 'inputs.json').exists():
        if (out / 'resolved_config.json').exists():
            assert json.loads((out / 'resolved_config.json').read_text())['pilot_config'] == cfg
        old = prepare(cfg, out)
        save(out / 'resolved_config.json', dict(pilot_config=cfg, source_config=old, timestamp=now(), python=sys.version))
        for path in [Path(__file__), ROOT / args.config, *[ROOT / f'prompts/en/rater_feedback_pilot_{s}_v1.txt' for s in 'ABC']]:
            shutil.copy2(path, out / path.name)
        print('Prepared', out, flush=True)
    if args.phase == 'prepare':
        return
    inputs = json.loads((out / 'inputs.json').read_text())
    rubric = json.loads((out / 'rubric.json').read_text())
    selection = json.loads((out / 'selection.json').read_text())
    raters = selection['selected_raters']
    if args.phase == 'remaining':
        assert (out / 'pilot_review.json').exists(), 'Review first rater before expansion'
        assert json.loads((out / 'pilot_review.json').read_text())['proceed'], 'pilot review did not authorize expansion'
    runner = Runner(cfg, out, old)
    state = dict(phase=args.phase, started_at=now(), status='running')
    save(out / 'status.json', state)
    try:
        if args.phase != 'report':
            for rater in (raters[:1] if args.phase == 'pilot' else raters[1:]):
                result = runner.rater(rater, inputs, rubric)
                save(out / 'results' / f'{rater}.json', result)
        results = [json.loads((out / 'results' / f'{r}.json').read_text()) for r in raters if (out / 'results' / f'{r}.json').exists()]
        report(out, results)
        state.update(status='completed', completed_raters=[r['rater_id'] for r in results])
    except BaseException:
        state.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        state['ended_at'] = now()
        save(out / 'status.json', state)


if __name__ == '__main__':
    main()
