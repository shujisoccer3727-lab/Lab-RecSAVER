"""固定1,000対象のjoint tendency実験。GPU依存はrun内だけで読み込む。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import rater_profile_mvp_1000 as previous
from .history import format_history

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/rater_tendency_joint_mvp_1000'
OLD = ROOT / 'outputs/rater_profile_mvp_1000'
BASE = ROOT / 'outputs/full_prediction_experiment'
PROMPT = ROOT / 'prompts/en/rater_tendency_joint_prediction.txt'
SEED = 20260914
FIELDS = ('essay_evidence', 'tendency_connection', 'scoring_explanation')


def read(path):
    return previous.read(path)


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    previous.dump(temporary, value)
    temporary.replace(path)


def status(name):
    result = subprocess.run(['git', 'status', '--porcelain=v1'], cwd=ROOT, capture_output=True)
    (OUT / (name + '.txt')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(result.stderr)
    assert result.returncode == 0


def render(frame, tid, ids):
    # Target metadata/scores never enter the formatter. History is exactly A's K=3.
    return PROMPT.read_text(encoding='utf-8').format(
        overall_rubric=(ROOT / 'rubrics/ellipse_overall_rubric.md').read_text(encoding='utf-8'),
        rating_history=format_history(frame.loc[ids]), target_essay=str(frame.loc[tid, 'Text']))


def verify():
    config = json.loads((OUT / 'experiment_config.json').read_text(encoding='utf-8'))
    for path, digest in config['input_sha256'].items():
        assert previous.sha(ROOT / path) == digest, f'Input changed: {path}'
    return config


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / 'experiment_config.json').exists():
        verify()
        return
    if not (OUT / 'git_status_before.txt').exists():
        status('git_status_before')
    targets = pd.read_csv(OLD / 'common_targets_1000.csv')
    assert len(targets) == 1000 and targets.target_id.is_unique
    manifests = {r['target_id']: r for r in read(OLD / 'target_history_manifest.jsonl')}
    original = {r['target_id']: r for r in read(BASE / 'target_manifest.jsonl')}
    baseline = {r['target_id']: r for r in read(BASE / 'predictions_correct_k3_rubric.jsonl')}
    reused = {r['target_id']: r for r in read(OLD / 'predictions/A_current_trait_history.jsonl')}
    oldconfig = json.loads((OLD / 'experiment_config.json').read_text(encoding='utf-8-sig'))
    frame = previous.data()
    baseline_digest = previous.sha(BASE / 'predictions_correct_k3_rubric.jsonl')
    audit = []
    for t in targets.itertuples():
        m, b, a = manifests[t.target_id], baseline[t.target_id], reused[t.target_id]
        ids = m['correct_history_ids']
        h, target = frame.loc[ids], frame.loc[t.target_id]
        assert m == original[t.target_id]
        assert ids == b['history_ids'] and len(ids) == len(set(ids)) == 3
        assert b['predicted_overall'] == a['predicted_overall'] and b['prediction_reasoning'] == a['reasoning']
        assert a['reused_sha256'] == baseline_digest
        assert target.Overall == t.gold_overall == b['gold_overall'] == a['gold_overall']
        assert target.source_row_id == t.source_row_id == m['source_row_id']
        assert target.rater_id == t.target_rater == m['target_rater'] == a['target_rater']
        assert h.rater_id.eq(t.target_rater).all()
        assert not h.source_row_id.eq(target.source_row_id).any()
        assert not h.Filename.eq(target.Filename).any() and not h.Text.eq(target.Text).any()
        # Gold perturbation verifies that only allowed target text reaches the prompt.
        prompt = render(frame, t.target_id, ids)
        assert b['rater_id'] == t.target_rater
        assert prompt.split('[Official Overall Scoring Rubric]\n', 1)[1] == b['prompt'].split('[Official Overall Scoring Rubric]\n', 1)[1]
        modified = frame.loc[[t.target_id] + ids].copy()
        modified.loc[t.target_id, ['Overall', *previous.TRAITS]] = -999
        assert render(modified, t.target_id, ids) == prompt
        audit.append({'target_id': t.target_id, 'baseline_identical': True, 'history_identical': True,
                      'no_essay_overlap': True, 'gold_perturbation_invariant': True})
    (OUT / 'target_manifest.csv').write_bytes((OLD / 'common_targets_1000.csv').read_bytes())
    previous.jsonl(OUT / 'target_history_manifest.jsonl', [manifests[t] for t in targets.target_id])
    previous.jsonl(OUT / 'baseline_A.jsonl', [reused[t] for t in targets.target_id])
    pd.DataFrame(audit).to_csv(OUT / 'integrity_audit.csv', index=False)
    # Proportional Gold quotas with a seeded preference for underrepresented raters.
    counts = targets.groupby('gold_overall').size()
    quota = counts * 30 / len(targets)
    allocated = np.floor(quota).astype(int)
    extra = (quota - allocated).sort_values(ascending=False, kind='stable').index[:30-int(allocated.sum())]
    allocated.loc[extra] += 1
    rng, selected, used = np.random.default_rng(SEED), [], {}
    for gold, group in targets.groupby('gold_overall', sort=True):
        remaining = list(rng.permutation(group.index))
        for _ in range(int(allocated[gold])):
            index = min(remaining, key=lambda i: used.get(targets.loc[i, 'target_rater'], 0))
            selected.append(index)
            rater = targets.loc[index, 'target_rater']
            used[rater] = used.get(rater, 0) + 1
            remaining.remove(index)
    targets.loc[selected].to_csv(OUT / 'pilot_targets.csv', index=False)
    paths = [OLD / 'common_targets_1000.csv', OLD / 'target_history_manifest.jsonl',
             OLD / 'predictions/A_current_trait_history.jsonl', OLD / 'experiment_config.json',
             BASE / 'predictions_correct_k3_rubric.jsonl', BASE / 'target_manifest.jsonl',
             ROOT / 'data/processed/rater_essay_wide.csv', ROOT / 'rubrics/ellipse_overall_rubric.md',
             ROOT / 'prompts/en/rubric_based_prediction.txt', PROMPT,
             OUT / 'target_manifest.csv', OUT / 'pilot_targets.csv', OUT / 'target_history_manifest.jsonl',
             Path(__file__)]
    config = {'model': oldconfig['model'], 'generation': {'temperature': .2, 'top_p': .8, 'max_tokens': 768},
              'baseline_max_tokens': 384, 'max_parse_retries': 1, 'seed': SEED,
              'pilot_selection': 'Gold proportional largest-remainder quotas; seeded shuffle; prefer least selected rater',
              'bootstrap': {'samples': 2000, 'seed': SEED, 'method': 'paired percentile'},
              'full_run_requires': 'Explicit user approval after pilot, recorded in approval.json with config_sha256',
              'input_sha256': {str(p.relative_to(ROOT)): previous.sha(p) for p in paths}}
    save(OUT / 'experiment_config.json', config)
    (OUT / 'predictions.jsonl').touch(exist_ok=True)
    analyze()


def parse(raw, ids):
    text = raw.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    value = json.loads(text)
    assert set(value) == {'predicted_overall', 'rater_tendency', 'reasoning'}
    assert type(value['predicted_overall']) is int and value['predicted_overall'] in range(1, 6)
    tendency, reasoning = value['rater_tendency'], value['reasoning']
    assert set(tendency) == {'description', 'supporting_history_ids', 'uncertainty'}
    assert set(reasoning) == set(FIELDS)
    assert all(isinstance(x, str) and x.strip() for x in [tendency['description'], tendency['uncertainty'], *reasoning.values()])
    cited = tendency['supporting_history_ids']
    assert isinstance(cited, list) and all(isinstance(x, str) and x in ids for x in cited)
    assert len(cited) == len(set(cited))
    return value


def records():
    # Every completed target, including exhausted failures, is checkpointed once.
    from .full_prediction_experiment import recover_jsonl
    rows = recover_jsonl(OUT / 'predictions.jsonl')
    assert len({r['target_id'] for r in rows}) == len(rows)
    assert all(r['config_sha256'] == previous.sha(OUT / 'experiment_config.json') for r in rows)
    return {r['target_id']: r for r in rows}


def run(full=False):
    config = verify()
    if full:
        approval = json.loads((OUT / 'approval.json').read_text(encoding='utf-8'))
        assert approval['approved'] is True and approval['config_sha256'] == previous.sha(OUT / 'experiment_config.json')
        assert len(set(pd.read_csv(OUT / 'pilot_targets.csv').target_id) & records().keys()) == 30
    gpu = subprocess.run(['/usr/lib/wsl/lib/nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True)
    assert max(map(int, gpu.stdout.split())) < 4000, 'GPU occupied; existing jobs were left running'
    from .model import VLLMGenerator
    from .full_prediction_experiment import append_jsonl
    from vllm import SamplingParams
    generator = VLLMGenerator(config)
    frame = previous.data()
    manifests = {r['target_id']: r for r in read(OUT / 'target_history_manifest.jsonl')}
    targets = pd.read_csv(OUT / ('target_manifest.csv' if full else 'pilot_targets.csv'))
    completed = records()
    started = time.monotonic()
    for tid in targets.target_id:
        if tid in completed:
            continue
        ids = manifests[tid]['correct_history_ids']
        prompt = render(frame, tid, ids)
        chat = [{'role': 'user', 'content': prompt}]
        tokens = generator.tokenizer.apply_chat_template(chat, tokenize=True, add_generation_prompt=True)
        formatted = generator.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        record = {'target_id': tid, 'history_ids': ids, 'prompt': prompt, 'prompt_tokens': len(tokens),
                  'config_sha256': previous.sha(OUT / 'experiment_config.json'), 'parse_success': False, 'attempts': []}
        if len(tokens) + config['generation']['max_tokens'] > config['model']['max_model_len']:
            record['failure_reason'] = 'context_overflow; no text truncated'
        else:
            for attempt in range(config['max_parse_retries'] + 1):
                seed = int(hashlib.sha256(f'{SEED}:{tid}:{attempt}'.encode()).hexdigest()[:8], 16)
                output = generator.llm.generate([formatted], SamplingParams(**config['generation'], seed=seed), use_tqdm=False)[0].outputs[0]
                record['attempts'].append({'raw': output.text, 'output_tokens': len(output.token_ids),
                                           'finish_reason': output.finish_reason, 'seed': seed})
                try:
                    record.update(parse(output.text, ids), parse_success=True)
                    break
                except (ValueError, AssertionError, TypeError, KeyError) as error:
                    record['failure_reason'] = f'invalid_json_schema_or_history_id: {type(error).__name__}'
            record['retry_count'] = len(record['attempts']) - 1
            if record['parse_success']:
                record.pop('failure_reason', None)
        append_jsonl(OUT / 'predictions.jsonl', record)
        completed[tid] = record
        save(OUT / 'progress.json', {'completed': len(completed), 'phase': 'full' if full else 'pilot', 'elapsed_seconds': time.monotonic()-started})
        print(tid, record['parse_success'], len(completed), flush=True)
    analyze()


def analyze():
    config = verify()
    targets = pd.read_csv(OUT / 'target_manifest.csv').set_index('target_id')
    pilot = pd.read_csv(OUT / 'pilot_targets.csv')
    baseline = {r['target_id']: r for r in read(OUT / 'baseline_A.jsonl')}
    generated = records()
    common = sorted(t for t, r in generated.items() if r['parse_success'] and baseline[t]['parse_success'])
    summaries, comparisons = [], []
    if common:
        gold = targets.loc[common].gold_overall.to_numpy()
        a = np.array([baseline[t]['predicted_overall'] for t in common])
        b = np.array([generated[t]['predicted_overall'] for t in common])
        for name, pred in [('A', a), ("A'", b)]:
            summaries.append({'Condition': name, 'N': len(common), **previous.metrics(gold, pred)})
        rng = np.random.default_rng(SEED)
        draws = {k: [] for k in previous.metrics(gold, a)}
        for _ in range(2000):
            ix = rng.integers(0, len(common), len(common))
            ma, mb = previous.metrics(gold[ix], a[ix]), previous.metrics(gold[ix], b[ix])
            for key in draws:
                draws[key].append(mb[key]-ma[key])
        for key, values in draws.items():
            finite = np.asarray(values)[np.isfinite(values)]
            bounds = np.percentile(finite, [2.5, 97.5]) if len(finite) else [None, None]
            comparisons.append({'metric': key, 'N': len(common), 'difference_Aprime_minus_A': summaries[1][key]-summaries[0][key],
                                'ci_lower': bounds[0], 'ci_upper': bounds[1], 'valid_bootstrap_draws': len(finite)})
    pd.DataFrame(summaries, columns=['Condition','N','Accuracy','MAE','RMSE','QWK']).to_csv(OUT / 'prediction_summary.csv', index=False)
    pd.DataFrame(comparisons, columns=['metric','N','difference_Aprime_minus_A','ci_lower','ci_upper','valid_bootstrap_draws']).to_csv(OUT / 'paired_comparison.csv', index=False)
    distribution = [{'Condition': name, 'score': score, 'N_common': len(common),
                     'count': sum((baseline[t] if name == 'A' else generated[t])['predicted_overall'] == score for t in common)}
                    for name in ['A', "A'"] for score in range(1,6)]
    pd.DataFrame(distribution).to_csv(OUT / 'prediction_distribution.csv', index=False)
    valid = [r for r in generated.values() if r['parse_success']]
    counts = {'json_parse_success': len(valid), 'rater_tendency': len(valid),
              'supporting_history_ids': sum(bool(r['rater_tendency']['supporting_history_ids']) for r in valid),
              'insufficient_evidence_explicit_phrase': sum('insufficient evidence' in json.dumps(r['rater_tendency']).lower() for r in valid),
              **{key: sum(bool(r['reasoning'][key]) for r in valid) for key in FIELDS}}
    pd.DataFrame([{'element': k, 'count': v, 'attempted_targets': len(generated),
                   'rate': v/len(generated) if generated else None} for k,v in counts.items()]).to_csv(OUT / 'reasoning_structure_summary.csv', index=False)
    failed = [{'target_id': t, 'reason': r.get('failure_reason')} for t,r in generated.items() if not r['parse_success']]
    pd.DataFrame(failed, columns=['target_id','reason']).to_csv(OUT / 'excluded_targets.csv', index=False)
    frame = previous.data()
    manifests = {r['target_id']:r for r in read(OUT / 'target_history_manifest.jsonl')}
    review = ['# Pilot全30件の比較資料', '人手評価は未実施。各項目を履歴・Essay・Rubricと照合して記入してください。',
              '確認軸: Tendency Grounding / Essay Grounding / Tendency Connection / Score Consistency。',
              (ROOT / 'rubrics/ellipse_overall_rubric.md').read_text(encoding='utf-8')]
    for tid in pilot.target_id:
        r = generated.get(tid)
        review.extend([f'## {tid}', f'Gold: {targets.loc[tid,"gold_overall"]}; A: {baseline[tid]["predicted_overall"]}',
                       '### Target Essay', str(frame.loc[tid,'Text']), '### K=3 History',
                       format_history(frame.loc[manifests[tid]['correct_history_ids']]), '### A reasoning', baseline[tid]['reasoning'],
                       "### A' input", r['prompt'] if r else render(frame, tid, manifests[tid]['correct_history_ids']),
                       "### A' output", json.dumps(r, ensure_ascii=False, indent=2) if r else '未実行',
                       '### 人手確認欄', 'Tendency Grounding: 未評価\n\nEssay Grounding: 未評価\n\nTendency Connection: 未評価\n\nScore Consistency: 未評価\n\nRubric言い換え・一般的すぎる傾向・留保・履歴整合性の懸念: 未評価'])
    (OUT / 'reasoning_review_examples.md').write_text('\n\n'.join(review), encoding='utf-8')
    attempts = [a for r in generated.values() for a in r['attempts']]
    pilot_done = sum(t in generated for t in pilot.target_id)
    report = f'''# Pilot report

状態: {pilot_done}/30 targets checkpointed; valid JSON/schema {len(valid)}/{len(generated)} attempted targets.
Full 1,000件は未承認。Pilot完了後に停止し、明示承認を得る。

設定: {json.dumps(config['generation'])}; max_model_len=8192; K=3; English.
Aのmax_tokens=384に対し、長いJSON用に768を初期候補として選択。最終推奨は実測後に判断。
選択: {config['pilot_selection']}; seed={SEED}。対象IDとGold/raterはpilot_targets.csv。

出力token数: {[a['output_tokens'] for a in attempts]}
length終了attempt数: {sum(a['finish_reason']=='length' for a in attempts)} / {len(attempts)}
retry総数: {sum(r.get('retry_count',0) for r in generated.values())}
失敗・除外: {json.dumps(failed, ensure_ascii=False)}

integrity_audit.csv: 1,000件の既存A再利用・履歴一致・重複Essay排除・Gold改変不変性を確認。
参照IDはparse()で提供済みK=3内に限定。全入出力・人手確認欄: reasoning_review_examples.md。
構造の出力率は内容の正しさを示さない。人手評価は未実施。
'''
    (OUT / 'pilot_report.md').write_text(report, encoding='utf-8')
    headings = ['実験目的', "AとA'の入力・出力の違い", 'Pilotの結果', '最終Promptと生成設定',
                '共通1,000件のOverall予測性能', "AとA'の統計的比較", '予測Overall分布',
                '新しい採点理由の出力例', '評価傾向と履歴との整合性', 'Rec-SAVER評価の再利用可能性',
                'Integrity audit', '主張できること・現時点で主張できないこと', '次の研究課題']
    bodies = ['評価履歴から評価傾向と個別Essayの理由を同時生成する初期検証。',
              '入力は本人履歴K=3（本文・Overall・6 Traits）、Overall rubric、Target Essay。出力のみ拡張。Profile生成なし。',
              report, 'prompts/en/rater_tendency_joint_prediction.txt; experiment_config.json。最終設定はPilot後に確定。',
              f'現在の共通有効予測数={len(common)}。1,000件本実験は承認待ち。prediction_summary.csv。',
              'paired_comparison.csv。2,000 paired percentile bootstrap、seed=20260914。pilot段階の値を本実験結果と扱わない。',
              'prediction_distribution.csv（両条件で有効な共通対象のみ）。', 'reasoning_review_examples.md（全30件）。',
              '人手確認は未実施。構造集計はreasoning_structure_summary.csv。',
              'outputs/reasoning_eval_v1/verified_reference_pool.jsonlは対象・履歴ID・rubric・参照検証条件の個別照合が必要。既存評価値は転記しない。Essay固有reasoningのみ比較し、rater_tendencyは別に履歴整合性を確認。追加処理は参照の交差集合抽出、理由3要素の文章化、既存metric再計算。所要時間は環境・対象数の実測がなく未推定。',
              'integrity_audit.csvおよびexperiment_config.jsonのSHA256。git_status_before/after.txt。',
              '生成・履歴による裏付け・予測への因果的利用・本人の真の判断理由・フィードバックによる分散低減は別の主張。未実測の有効性は主張できない。',
              'Pilotの内容確認、最終設定の承認、本実験、独立した人手評価、必要に応じたRec-SAVER追加評価。']
    (OUT / 'report.md').write_text('\n\n'.join(f'## {i}. {h}\n\n{b}' for i,(h,b) in enumerate(zip(headings,bodies),1)), encoding='utf-8')
    status('git_status_after')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare','pilot','analyze','full'])
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare()
    elif args.phase == 'analyze':
        analyze()
    else:
        run(full=args.phase == 'full')


if __name__ == '__main__':
    main()
