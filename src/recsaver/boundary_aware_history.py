"""Fixed-input boundary instruction ablation; never sample or rerun the baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone

import pandas as pd
import yaml

from .config import load_config, project_path
from .full_rubric_ablation import load_sources
from .model import VLLMGenerator
from .overall_rubric_ablation import prepare as prepare_overall, summarize
from .parsing import parse_prediction
from .utils import write_jsonl


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(config, tokenizer):
    meta, prior = load_sources(config)
    existing = project_path(config, config['existing_prompt']).read_text(encoding='utf-8')
    boundary = project_path(config, config['boundary_prompt']).read_text(encoding='utf-8')
    # Reuse the original data/history/rubric loader and context accounting.
    original = dict(config, source_metadata=config['history_metadata'],
                    source_predictions=config['history_predictions'], prediction_prompt=config['existing_prompt'])
    history_meta, history_prior, prepared = prepare_overall(original, tokenizer)
    assert meta['target_ids'] == history_meta['target_ids']
    assert len(meta['target_ids']) == len(set(meta['target_ids'])) == config['num_targets'] == 100
    assert config['history_size'] == 3
    assert config['model'] == meta['model']
    assert config['generation'] == meta['generation_config']
    assert config['seed'] == meta['target_seed'] == meta['history_seed']
    assert sha(project_path(config, config['rubric_path'])) == meta['rubric_sha256']
    assert sha(project_path(config, config['existing_prompt'])) == meta['prediction_prompt_sha256']
    # Everything from the rubric header onwards must remain byte-for-byte equal as text.
    marker = '[Official Overall Scoring Rubric]'
    assert boundary.split(marker, 1)[1] == existing.split(marker, 1)[1]
    rows = [r for r in prior.values() if r['condition'] == 'raw_k3_with_rubric']
    assert [r['target_id'] for r in rows] == meta['target_ids']
    items, baseline, checks = [], [], []
    for item in prepared:
        if item['condition'] != 'raw_k3_with_rubric':
            continue
        target = item['target']; tid = target.target_id
        old = prior[(tid, 'raw_k3_with_rubric')]
        assert old['prompt'] == item['prompt'], f'original input mismatch: {tid}'
        assert old['history_ids'] == history_prior[(tid, 3)]['history_ids'] == item['history'].target_id.tolist()
        assert len(item['history']) == 3 and item['history'].rater_id.eq(target.rater_id).all()
        assert target.Text not in item['history'].Text.tolist()
        assert old['rater_id'] == target.rater_id and old['gold_overall'] == int(target.Overall)
        assert old['parse_success']
        prompt = boundary.split(marker, 1)[0] + marker + item['prompt'].split(marker, 1)[1]
        # Target scores are never formatted: only the unchanged raw essay is inserted.
        assert prompt.split('<TARGET_ESSAY>\n', 1)[1] == target.Text + '\n</TARGET_ESSAY>\n'
        tokens = len(tokenizer.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=True, add_generation_prompt=True))
        fit = tokens + config['generation']['max_tokens'] <= config['model']['max_model_len']
        items.append(dict(item, prompt=prompt, prompt_tokens=tokens, context_fit=fit, condition=config['new_condition']))
        baseline.append(dict(old, condition=config['baseline_condition'], reused=True))
        checks.append({'target_id': tid, 'target_rater': target.rater_id, 'history_ids': json.dumps(old['history_ids']),
                       'history_count': 3, 'same_target_order': True, 'same_history_order': True,
                       'same_input_sections': True, 'same_rubric': True, 'same_model_generation': True,
                       'same_parser': True, 'no_target_score_leakage': True, 'no_target_in_history': True,
                       'correct_rater_only': True, 'overall_rubric_only': True,
                       'prompt_tokens': tokens, 'reserved_output_tokens': 384, 'context_fit': fit})
    assert [x['target'].target_id for x in items] == meta['target_ids']
    out = project_path(config, config['output_dir']); out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(checks).to_csv(out / 'dry_run_conditions.csv', index=False)
    if not all(x['context_fit'] for x in items):
        raise ValueError('Context overflow: no truncation or inference allowed')
    return meta, baseline, items


def analyze(config, baseline, records, out):
    a, b = config['baseline_condition'], config['new_condition']
    summary = summarize(baseline + records, out, [a, b], [(a, b)], 'boundary_aware_summary.csv')
    (out / 'paired_comparisons.csv').rename(out / 'paired_comparison.csv')
    old = {r['target_id']: r for r in baseline}
    transitions, examples = [], []
    for new in records:
        prev = old[new['target_id']]
        if not new['parse_success'] or prev['predicted_overall'] == new['predicted_overall']:
            continue
        row = {'target_id': new['target_id'], 'target_rater': new['rater_id'], 'gold': new['gold_overall'],
               'existing_prediction': prev['predicted_overall'], 'boundary_prediction': new['predicted_overall'],
               'existing_error': prev['absolute_error'], 'boundary_error': new['absolute_error'],
               'transition': f"{prev['predicted_overall']} -> {new['predicted_overall']}"}
        transitions.append(row)
        examples.append(dict(row, existing_reasoning=prev['prediction_reasoning'], boundary_reasoning=new['prediction_reasoning']))
    columns = ['target_id', 'target_rater', 'gold', 'existing_prediction', 'boundary_prediction', 'existing_error', 'boundary_error', 'transition']
    pd.DataFrame(transitions, columns=columns).to_csv(out / 'score_transitions.csv', index=False)
    # Deterministic coverage: include both focal transitions before filling to ten.
    selected = []
    for label in ['3 -> 2', '3 -> 4']:
        selected.extend([r for r in examples if r['transition'] == label][:5])
    selected += [r for r in examples if r not in selected][:10-len(selected)]
    (out / 'reasoning_examples.json').write_text(json.dumps({'selection': 'First up to five per focal transition, then target order; exploratory, not representative', 'examples': selected}, indent=2), encoding='utf-8')
    counts = []
    for label in ['3 -> 2', '3 -> 4']:
        group = [r for r in transitions if r['transition'] == label]
        counts.append({'transition': label, 'n': len(group), 'toward_gold': sum(r['boundary_error'] < r['existing_error'] for r in group),
                       'away_from_gold': sum(r['boundary_error'] > r['existing_error'] for r in group),
                       'same_error': sum(r['boundary_error'] == r['existing_error'] for r in group)})
    pd.DataFrame(counts).to_csv(out / 'score_transition_summary.csv', index=False)
    patterns = {'history_explicitly_referenced': r'\bhistor\w*|\bpast\b|\bprevious\w*|\brater\b|\bexample\w*',
                'rubric_explicitly_referenced': r'\brubric\b|\bdescriptor\w*|\bscoring criteri\w*',
                'neighboring_score_comparison_present': r'\b(?:rather than|instead of|compared (?:with|to)|unlike|whereas|higher|lower|neighbor\w*|boundary|boundaries|but not)\b'}
    audit = []
    for r in records:
        reason = r['prediction_reasoning']
        flags = {key: bool(re.search(pattern, reason, re.I)) for key, pattern in patterns.items()}
        # Require two explicitly numbered, adjacent score levels as well as contrast language.
        scores = {int(x) for x in re.findall(r'\b(?:score|level|rating)\s*(?:of\s*)?([1-5])\b', reason, re.I)}
        flags['neighboring_score_comparison_present'] &= any(x+1 in scores for x in scores)
        audit.append(dict(target_id=r['target_id'], **flags))
    pd.DataFrame(audit).to_csv(out / 'reasoning_usage_per_target.csv', index=False)
    pd.DataFrame([{'heuristic': key, 'count': sum(r[key] for r in audit), 'n': len(audit),
                   'rate': sum(r[key] for r in audit)/len(audit), 'pattern': pattern,
                   'formal_metric': False} for key, pattern in patterns.items()]).to_csv(out / 'reasoning_usage_summary.csv', index=False)
    raters = pd.read_csv(out / 'rater_summary.csv').pivot(index='rater_id', columns='condition', values=['n', 'accuracy', 'mae'])
    d = raters['mae'][b] - raters['mae'][a]
    pd.DataFrame([{'criterion': 'MAE (exploratory)', 'boundary_better': int((d < 0).sum()), 'same': int((d == 0).sum()),
                   'boundary_worse': int((d > 0).sum())}]).to_csv(out / 'rater_comparison_summary.csv', index=False)
    return summary


def execute(config, dry_run=False):
    from transformers import AutoTokenizer
    start = time.perf_counter()
    out = project_path(config, config['output_dir'])
    if (out / 'boundary_aware_predictions.jsonl').exists():
        raise FileExistsError('Refusing to overwrite existing predictions or repeat inference')
    tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'], local_files_only=True)
    meta, baseline, items = prepare(config, tokenizer)
    md = {'experiment_name': config['experiment_name'], 'timestamp': datetime.now(timezone.utc).isoformat(),
          'status': 'dry_run_passed', 'git_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=config['_root'], capture_output=True, text=True).stdout.strip(),
          'model': config['model'], 'quantization': config['model']['quantization'], 'generation_config': config['generation'],
          'target_seed': meta['target_seed'], 'history_seed': meta['history_seed'], 'target_ids': meta['target_ids'],
          'history_ids': {r['target_id']: r['history_ids'] for r in baseline}, 'new_inference_budget': 100,
          'parse_retries': 0, 'parse_retry_note': 'No retries to honor exactly 100 new generations',
          'output_format': 'Existing two-key JSON; parser unchanged',
          'mean_ae_difference_definition': 'Existing AE minus Boundary AE; positive means improvement',
          'max_prompt_tokens': max(x['prompt_tokens'] for x in items)}
    for key in ['rubric_path', 'existing_prompt', 'boundary_prompt']:
        name = key.removesuffix('_path')
        md[name + '_path'] = config[key]; md[name + '_sha256'] = sha(project_path(config, config[key]))
    md['parser_sha256'] = sha(project_path(config, 'src/recsaver/parsing.py'))
    md['source_predictions_sha256'] = sha(project_path(config, config['source_predictions']))
    md['GPU'] = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'], capture_output=True, text=True).stdout.strip()
    (out / 'metadata.json').write_text(json.dumps(md, indent=2), encoding='utf-8')
    (out / 'resolved_config.yaml').write_text(yaml.safe_dump({k:v for k,v in config.items() if not k.startswith('_')}, sort_keys=False), encoding='utf-8')
    print(f"Dry run: {len(items)}/100 passed; max prompt tokens={md['max_prompt_tokens']}", flush=True)
    if dry_run:
        return
    gen = VLLMGenerator(config)
    records = []
    for offset in range(0, len(items), config['batch_size']):
        chunk = items[offset:offset+config['batch_size']]
        tick = time.perf_counter(); outputs = gen.generate([x['prompt'] for x in chunk], config['generation'])
        per = (time.perf_counter()-tick)/len(chunk)
        assert len(outputs) == len(chunk)
        for item, values in zip(chunk, outputs):
            raw = values[0]; error = None
            try:
                parsed = parse_prediction(raw, True)
            except ValueError as exc:
                parsed = {'predicted_overall': None, 'reasoning': ''}; error = str(exc)
            t = item['target']; pred = parsed['predicted_overall']; gold = int(t.Overall)
            records.append({'target_id': t.target_id, 'source_row_id': int(t.source_row_id), 'rater_id': t.rater_id,
                            'condition': config['new_condition'], 'K': 3, 'gold_overall': gold, 'predicted_overall': pred,
                            'exact_correct': pred == gold if pred is not None else None,
                            'absolute_error': abs(pred-gold) if pred is not None else None,
                            'squared_error': (pred-gold)**2 if pred is not None else None,
                            'prediction_reasoning': parsed['reasoning'], 'history_ids': item['history'].target_id.tolist(),
                            'history_rater_ids': item['history'].rater_id.tolist(), 'prompt_tokens': item['prompt_tokens'],
                            'output_tokens': len(gen.tokenizer.encode(raw, add_special_tokens=False)), 'context_fit': True,
                            'parse_success': pred is not None, 'retry_count': 0, 'parse_error': error,
                            'inference_time_seconds': per, 'raw_model_output': raw, 'raw_model_output_attempts': [raw],
                            'prompt': item['prompt'], 'reused': False})
        write_jsonl(out / 'boundary_aware_predictions.jsonl', records)
        print(f'Completed {len(records)}/100', flush=True)
    md.update(status='completed', new_inference_count=len(records), elapsed_seconds=time.perf_counter()-start,
              inference_seconds=sum(r['inference_time_seconds'] for r in records), parse_errors=sum(not r['parse_success'] for r in records), context_overflows=0)
    (out / 'metadata.json').write_text(json.dumps(md, indent=2), encoding='utf-8')
    print(analyze(config, baseline, records, out).to_string(index=False))


def report(config):
    """Render saved results without loading a model or regenerating predictions."""
    out = project_path(config, config['output_dir'])
    md = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    assert md['status'] == 'completed' and md['new_inference_count'] == 100
    labels = {config['baseline_condition']: 'Existing', config['new_condition']: 'Boundary-aware', 'gold': 'Gold'}

    def read(name):
        return pd.read_csv(out / name).replace(labels)

    def table(frame):
        def cell(value):
            if isinstance(value, float):
                return f'{value:.4f}'
            return str(value).replace('|', '\\|').replace('\n', ' ')
        return '\n'.join(['| ' + ' | '.join(map(str, frame.columns)) + ' |',
                          '| ' + ' | '.join(['---'] * len(frame.columns)) + ' |'] +
                         ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in frame.itertuples(index=False, name=None)])

    summary = read('boundary_aware_summary.csv')
    paired = read('paired_comparison.csv')
    distribution = read('prediction_distribution.csv').pivot(index='score', columns='series', values='rate').reset_index()
    distribution = distribution[['score', 'Gold', 'Existing', 'Boundary-aware']]
    distribution.iloc[:, 1:] *= 100
    raters = read('rater_summary.csv').pivot(index='rater_id', columns='condition', values=['n', 'accuracy', 'mae'])
    raters.columns = [f'{c} {metric}' for metric, c in raters.columns]
    examples = json.loads((out / 'reasoning_examples.json').read_text(encoding='utf-8'))
    transitions = read('score_transitions.csv')
    lines = ['# Rec-SAVER AES: Boundary-aware History Prompt Ablation',
             '## 実験条件',
             '同じOverall Rubric・Correct-rater Raw History K=3・Target Essayの100件。Existingは保存済みraw_k3_with_rubricを再利用し、新規生成はBoundary-awareの100件のみ。',
             'ユーザー承認により既存と同じJSONのreasoning / predicted_overallを使用。parserは変更していない。Reasoningは簡潔な採点根拠のみ。',
             '```yaml\n' + yaml.safe_dump({'model': md['model'], 'generation': md['generation_config'], 'target_seed': md['target_seed'], 'history_seed': md['history_seed'], 'GPU': md['GPU']}, sort_keys=False).strip() + '\n```',
             'Target/historyは再samplingせず、同じ順序で10件ずつ処理した。生成seedは共通VLLMGeneratorの既定値0を使用。保存済みExistingと新規条件の乱数系列・バッチ構成が完全に対応することまでは保証しない（Existing実験はK=0/K=3を交互に生成）。単一実行の比較であり、反復実験による安定性は未検証。',
             '## Performance', table(summary[['condition', 'n', 'exact_accuracy', 'mae', 'rmse', 'qwk']]),
             '## Metric delta', 'Boundary-aware minus Existing。Accuracy/QWKは正、MAE/RMSEは負が改善。',
             table(paired[['accuracy_delta', 'mae_delta', 'rmse_delta', 'qwk_delta']]),
             '## Paired comparison', '同一targetの絶対誤差を比較。Mean/Median AE differenceはExisting minus Boundary-aware（正が改善）。',
             table(paired[['improved_targets', 'unchanged_targets', 'worsened_targets', 'mean_ae_difference', 'median_ae_difference']]),
             '## Prediction distribution', '単位：%。', table(distribution),
             '## Score collapse', table(read('score_collapse_summary.csv')),
             '## Score transitions', f'予測が変化した{len(transitions)}件すべてをscore_transitions.csvに保存。',
             table(transitions.groupby('transition').size().reset_index(name='n')),
             table(read('score_transition_summary.csv')),
             '## Rater別傾向', '探索的結果。better/same/worseはraterごとのMAEで判定し、各raterのnに注意する。',
             table(read('rater_comparison_summary.csv')), table(raters.reset_index()),
             '## Boundary-aware Reasoning examples',
             '変化したtargetから3→2と3→4を各最大5件、残りはtarget順で補完。代表性を保証する抽出ではない。以下は保存された簡潔な説明の原文。']
    for row in examples['examples']:
        lines.extend([f"### {row['target_id']} / rater {row['target_rater']} / Gold {row['gold']} / {row['transition']}",
                      '**Existing:** ' + row['existing_reasoning'], '**Boundary-aware:** ' + row['boundary_reasoning']])
    lines.extend(['## History utilization簡易監査',
                  'Keyword-based heuristicであり正式評価ではない。rater/example等への言及は具体的な履歴比較を保証せず、暗黙の比較は検出できない。隣接比較は対比語に加えて明示的な隣接score番号2つを要求するため、取りこぼしがある。',
                  table(read('reasoning_usage_summary.csv')[['heuristic', 'count', 'n', 'rate']]),
                  '## Leakage checks',
                  '全100件で保存済みExisting Promptを元データから再構成し完全一致を確認。両条件のRubricヘッダー以降の全入力部分も一致。TargetブロックはEssay本文のみで、Gold Overall/Target Trait scoresを挿入していない。',
                  'target/history ID・順序・history size=3・history rater=target raterを検証。targetのsource rowと同じessay本文を履歴から排除していることを確認。Overall RubricのSHA-256も既存metadataと一致。Full Rubric、Key Terms、Profile、Wrong Historyの追加なし。',
                  '## Context / parse errors',
                  f"Context overflow: {md['context_overflows']}。最大prompt {md['max_prompt_tokens']} + 384 = {md['max_prompt_tokens'] + 384} <= 8192。切り詰めなし。Parse errors: {md['parse_errors']}。再推論0件。",
                  '## 実行時間',
                  f"生成処理合計: {md['inference_seconds']:.2f}秒。dry run・model初期化を含む計測区間: {md['elapsed_seconds']:.2f}秒（集計・レポート作成は含まない）。",
                  '## 再現性と成果物',
                  'metadata.jsonに実行時刻、git commit、GPU、seed、全target/history ID、Rubric/両Prompt/parser/既存予測のSHA-256、generation設定を保存。resolved_config.yamlとdry_run_conditions.csvを併記。',
                  '実行: `python -m src.recsaver.boundary_aware_history`。レポート再作成のみ: `python -m src.recsaver.boundary_aware_history --report-only`。既存予測がある状態の推論再実行は拒否する。'])
    interpretation = out / 'interpretation.md'
    if interpretation.exists():
        lines.append(interpretation.read_text(encoding='utf-8'))
    (out / 'report.md').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/boundary_aware_history.yaml')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--report-only', action='store_true')
    args = parser.parse_args()
    config = load_config(args.config)
    if args.report_only:
        report(config)
    else:
        execute(config, args.dry_run)
        if not args.dry_run:
            report(config)


if __name__ == '__main__':
    main()
