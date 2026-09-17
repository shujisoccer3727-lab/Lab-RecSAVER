"""Report and integrity validation for persisted Reasoning Evaluation V1 results."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone

import pandas as pd

from .config import load_config, project_path
from .parsing import parse_prediction
from .reference_audit import leakage_audit, quality_warnings
from .utils import read_jsonl


def table(frame):
    def value(x):
        return f'{x:.4f}' if isinstance(x, float) else str(x).replace('|', '\\|')
    return '\n'.join(['| ' + ' | '.join(frame.columns) + ' |', '| ' + ' | '.join(['---']*len(frame.columns)) + ' |'] +
                     ['| ' + ' | '.join(value(x) for x in row) + ' |' for row in frame.itertuples(index=False, name=None)])


def validate_saved(config, require_complete=False):
    from .reasoning_eval_v1 import verification_prompt, reference_jobs, verify_jobs
    from .history import format_history
    from .data import load_valid_data
    out = project_path(config, config['output_dir'])
    md = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    for key, path in md['source_paths'].items():
        assert hashlib.sha256(project_path(config, path).read_bytes()).hexdigest() == md['source_sha256'][key], key
    source = {r['target_id']:r for r in read_jsonl(project_path(config, config['source_predictions'])) if r['condition'] == 'raw_k3_with_rubric'}
    frame = load_valid_data(config).set_index('target_id', drop=False)
    rubric = project_path(config, config['rubric_path']).read_text(encoding='utf-8')
    template = project_path(config, config['self_verification_prompt']).read_text(encoding='utf-8')
    references = read_jsonl(out / 'reference_candidates.jsonl'); verification = read_jsonl(out / 'self_verification_results.jsonl')
    accepted = {(r['target_id'],r['candidate_index']):r for r in references if r['accepted_as_leakage_free']}
    assert len({(r['target_id'],r['candidate_index'],r['attempt_index']) for r in references}) == len(references)
    assert len({(r['target_id'],r['candidate_index'],r['attempt_index']) for r in verification}) == len(verification)
    for r in references + verification:
        p = source[r['target_id']]
        assert r['history_ids'] == p['history_ids'] and r['target_rater'] == p['rater_id']
        assert r['prompt_tokens'] + r['sampling_parameters']['max_tokens'] <= 8192
    for v in verification:
        r = accepted[(v['target_id'],v['candidate_index'])]
        audit = leakage_audit(r['reference_reasoning'], r['raw_model_output'], r['gold_overall'])
        assert not audit['leaked'] and not audit['other_score_disclosure']
        p = source[v['target_id']]; target = frame.loc[v['target_id']]
        item = {'rubric': rubric, 'essay': target.Text, 'history_text': format_history(frame.loc[p['history_ids']])}
        assert v['prompt'] == verification_prompt(template, item, r['reference_reasoning'])
        assert v['verified'] == (v['reconstructed_overall'] == p['gold_overall'])
        if v['parse_success']:
            assert parse_prediction(v['raw_model_output'], False)['predicted_overall'] == v['reconstructed_overall']
    summary = pd.read_csv(out / 'target_reference_summary.csv')
    assert summary.target_id.tolist() == md['target_ids']
    if require_complete:
        assert summary.completed.all() and len(summary) == config['num_targets']
        metrics = pd.read_csv(out / 'reasoning_metrics_by_target.csv')
        assert metrics.target_id.tolist() == md['target_ids']
        assert metrics.verified_reference_count.tolist() == summary.verified_count.tolist()
        assert metrics.loc[metrics.verified_reference_count > 0].filter(regex='_(max|mean)$').notna().all().all()
        assert metrics.loc[metrics.verified_reference_count == 0].filter(regex='_(max|mean)$').isna().all().all()
        stubs = [{'target_id': tid} for tid in md['target_ids']]
        assert not reference_jobs(config, stubs, references)
        assert not verify_jobs(config, stubs, references, verification, template, None)
        pool = read_jsonl(out / 'verified_reference_pool.jsonl')
        latest = {(v['target_id'], v['candidate_index']): v for v in verification}
        expected = {key for key, v in latest.items() if v['verified']}
        assert {(r['target_id'], r['candidate_index']) for r in pool} == expected
        assert len(pool) == len(expected) == int(summary.verified_count.sum())
        pairs = pd.read_csv(out / 'reasoning_metrics_by_reference.csv')
        assert len(pairs) == len(pool)
    return {'source_hashes_unchanged': True, 'prediction_regenerations': 0, 'verification_gold_input_absent': True,
            'context_fit': True, 'unique_attempt_keys': True, 'completed_targets': int(summary.completed.sum()),
            'no_pending_generation_requests': True if require_complete else None}


def report(config, require_complete=False):
    out = project_path(config, config['output_dir']); checks = validate_saved(config, require_complete)
    (out / 'integrity_checks.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
    md = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    metric_md = json.loads((out / 'metric_metadata.json').read_text(encoding='utf-8'))
    refs = read_jsonl(out / 'reference_candidates.jsonl'); verifications = read_jsonl(out / 'self_verification_results.jsonl')
    latest = {(r['target_id'],r['candidate_index']):r for r in verifications}
    free = [r for r in refs if r['accepted_as_leakage_free']]; verified = read_jsonl(out / 'verified_reference_pool.jsonl')
    summary = pd.read_csv(out / 'target_reference_summary.csv'); completed = summary[summary.completed]
    read = lambda filename: pd.read_csv(out / filename)
    diversity = read('reference_diversity.csv')
    warnings = pd.DataFrame([dict(target_id=r['target_id'], candidate_index=r['candidate_index'], attempt_index=r['attempt_index'],
                                  warning=w, formal_metric=False) for r in refs for w in quality_warnings(r['reference_reasoning'])],
                            columns=['target_id','candidate_index','attempt_index','warning','formal_metric'])
    warnings.to_csv(out / 'quality_warnings.csv', index=False)
    source = read('reasoning_metrics_by_target.csv')
    predictions = [r for r in read_jsonl(project_path(config, config['source_predictions'])) if r['condition'] == 'raw_k3_with_rubric']
    leaks = sum(r['leaked'] for r in refs)
    generated = pd.DataFrame([dict(total_generated_attempts=len(refs), gold_leakage_count=leaks,
                                 gold_leakage_rate=leaks/len(refs) if refs else 0,
                                 other_score_disclosures=sum(r['other_score_disclosure'] for r in refs),
                                 retry_attempts=sum(r['attempt_index'] > 1 for r in refs), leakage_free_candidates=len(free),
                                 initial_leakage_free_candidates=sum(r['attempt_index'] == 1 for r in free),
                                 retry_recovered_candidates=sum(r['attempt_index'] > 1 for r in free),
                                 targets_recovered_from_zero_initial_free=len({r['target_id'] for r in free} -
                                                                             {r['target_id'] for r in free if r['attempt_index'] == 1}),
                                 targets_short_of_three=int((completed.leakage_free_count < 3).sum()))])
    generated.to_csv(out / 'reference_generation_summary.csv', index=False)
    verified_table = pd.DataFrame([dict(candidates_submitted=len(latest), verification_attempts=len(verifications),
                                      verified_candidates=len(verified), verification_pass_rate=len(verified)/len(latest) if latest else 0)])
    coverage = pd.DataFrame([dict(targets_total=len(summary), completed_targets=len(completed),
                                 targets_with_verified_reference=int((summary.verified_count > 0).sum()),
                                 coverage_rate=float((summary.verified_count > 0).mean()),
                                 mean_verified_refs_per_target=summary.verified_count.mean(), median_verified_refs_per_target=summary.verified_count.median())])
    distribution = pd.DataFrame([{'verified_reference_count':n, 'targets':int((summary.verified_count == n).sum())} for n in range(4)])
    gold_by_id = {p['target_id']:p['gold_overall'] for p in predictions}
    gold_coverage = summary.assign(gold_overall=summary.target_id.map(gold_by_id)).groupby('gold_overall').agg(
        n=('target_id','size'), completed_targets=('completed','sum'),
        targets_with_reference=('verified_count', lambda s: int((s > 0).sum())),
        mean_verified_refs=('verified_count','mean')).reset_index()
    gold_coverage['coverage_rate'] = gold_coverage.targets_with_reference / gold_coverage.n
    gold_coverage.to_csv(out / 'coverage_by_gold.csv', index=False)
    performance = pd.read_csv(project_path(config, config['prediction_source']) / 'overall_rubric_summary.csv')
    performance = performance[performance.condition == 'raw_k3_with_rubric'][['condition', 'n', 'exact_accuracy', 'mae', 'rmse', 'qwk']]
    lines = ['# Rec-SAVER AES: Reasoning Evaluation V1', '## Experiment setup',
             'Correct-rater K=3 + Overall Rubric + Existing Promptの保存済みPrediction Reasoningを固定。新規Prediction生成は0件。ReferenceとSelf-verificationのみ新規生成。',
             '```json\n' + json.dumps({'model':md['model'], 'generation':md['generation_config'], 'seed':config['seed'], 'GPU':md['GPU']}, indent=2) + '\n```',
             'Referenceは3候補枠。各枠は初回を含め最大5 attempt（追加retryは最大4）。Goldまたは他のnumeric scoreを採点文脈で明示した候補は不採用として再生成する。Score不一致のSelf-verificationは再試行せず、parse失敗だけ最大1回retry。',
             '## Prediction source', str(config['source_predictions']), table(performance),
             '## Reference generation', table(generated), '## Self-verification', table(verified_table),
             '## Coverage', table(coverage), table(distribution), 'Gold score別の補助集計：', table(gold_coverage),
             '未完了targetがある場合、coverageは未完了を含む設定target数を分母とする。Reasoning metricsは完了かつverified referenceが1件以上あるtargetのみで計算。未coverage targetは0点に置換せずNaNを保存。',
             '## Reasoning quality', table(read('reasoning_metrics_summary.csv')),
             '各referenceとのscoreをreasoning_metrics_by_reference.csvに保存。max/meanはtarget内referenceに対する集約、その後のmacro_meanは対象target間の平均。どちらを主要指標にするかは未決定。',
             'BLEUは既存MVPのsentence BLEU-4（全n-gram次数でadd-one smoothing）、ROUGE-1は既存の単語multiset F1を再利用。どちらも小文字化regex word tokenを使う。METEORにも同じtokenを渡し、NLTK既定stemmer/WordNetを使用。',
             'BERTScoreはroberta-largeの17層、IDFなし、baseline rescalingなし、slow tokenizer。モデルrevisionと実装version、hashをmetric_metadata.jsonに保存。BERTScoreの入力上限も検査し、黙示的な切り詰めを行わない。',
             '実装参照：[BERTScore公式](https://github.com/Tiiiger/bert_score)、[NLTK METEOR API](https://www.nltk.org/api/nltk.translate.meteor_score.html)。',
             '## Correct vs Incorrect prediction', table(read('prediction_correctness_comparison.csv')),
             '## Score-error analysis', table(read('score_error_comparison.csv')),
             '探索的比較であり、因果関係を意味しない。Coverageと各groupのnが異なる場合の選択効果にも注意する。',
             '## Reference diversity', table(pd.DataFrame([dict(targets_with_multiple_refs=diversity.target_id.nunique(),
                 reference_pairs=len(diversity), mean_lexical_jaccard=diversity.lexical_jaccard.mean(),
                 median_lexical_jaccard=diversity.lexical_jaccard.median(), exact_duplicate_pairs=int(diversity.exact_duplicate.sum()),
                 pairs_jaccard_ge_09=int((diversity.lexical_jaccard >= .9).sum()))])),
             'Jaccardは語集合の重なりであり、意味的な多様性を保証しない。類似度の高いreferenceによるmax集約の上昇もあり得るため、reference数と両集約を併記する。',
             '## Quality warnings', f'属性推測のkeyword warning: {len(warnings)}件。検出0件でもhallucinationが存在しない保証ではない。',
             '## Parse/context errors', table(pd.DataFrame([dict(reference_parse_errors=md['reference_parse_errors'],
                 verification_parse_errors=md['verification_parse_errors'], context_errors=md['context_errors'],
                 max_reference_prompt_plus_budget=max((r['prompt_tokens']+r['sampling_parameters']['max_tokens'] for r in refs), default=0),
                 max_verification_prompt_plus_budget=max((r['prompt_tokens']+r['sampling_parameters']['max_tokens'] for r in verifications), default=0))])),
             'Goldを入力するのはReference生成のみ。Self-verification PromptはGold引数を受け取らないrendererで作り、保存済み全verificationをGoldなしで再構成して一致を検査。履歴・Rubricに含まれる数字は既存の入力として維持している。',
             '## GPU inference time', f"Reference生成: {md['reference_gpu_seconds']:.2f}秒。Self-verification: {md['verification_gpu_seconds']:.2f}秒。合計: {md['reference_gpu_seconds']+md['verification_gpu_seconds']:.2f}秒（モデル初期化を除く、3-target dry run分を含む）。Metric処理: {metric_md['metric_seconds']:.2f}秒（BERTScoreモデル初期化を含む）。",
             '## 解釈上の限界',
             'Verifiedはモデルが条件付き生成した説明からGoldを再構成できたという自己整合性であり、人間によるGold Reasoningではない。同じモデルがReference生成・検証を担い、両段階が同じRubricとEssayを参照するため、共通の表現・判断傾向が一致を高める可能性がある。Reasoning metricはこの参照poolへの類似度であり、事実性・履歴忠実性・採点妥当性を単独で保証しない。',
             '## 再開と再現',
             'reference_candidates.jsonlとself_verification_results.jsonlはattemptごとにappend/fsyncする正本。config・入力hashが同じ場合のみ再開し、採用済み候補と検証済み候補をskip。末尾の不完全JSONは退避して復旧する。バッチ途中で未保存だったrequestのみ同じseedで再実行可能。完了済みtargetを再生成しない。',
             '3-target確認: `python -m src.recsaver.reasoning_eval_v1 --stage generate --limit 3`。続いて`--stage evaluate`。100-target再開: `--stage generate`、続いて`--stage evaluate`。レポート/整合性検査: `python -m src.recsaver.reasoning_eval_report --require-complete`。',
             'configのnum_targetsは固定source manifestのprefix数として変更できる。将来のdataset全件への拡張は別の固定prediction manifestと別output_dirを使う。今回は既存100件のみ。']
    notes = out / 'interpretation.md'
    if notes.exists():
        lines.append(notes.read_text(encoding='utf-8'))
    (out / 'report.md').write_text('\n\n'.join(lines)+'\n', encoding='utf-8')
    selected = []
    covered_ids = set(source[source.verified_reference_count > 0].target_id)
    for correct in [True, False]:
        for prediction in [p for p in predictions if p['exact_correct'] == correct and p['target_id'] in covered_ids][:3]:
            selected.append({'target_id':prediction['target_id'], 'gold_overall':prediction['gold_overall'],
                             'predicted_overall':prediction['predicted_overall'], 'prediction_reasoning':prediction['prediction_reasoning'],
                             'verified_references':[r['reference_reasoning'] for r in verified if r['target_id'] == prediction['target_id']]})
    (out / 'reasoning_examples.json').write_text(json.dumps({'selection':'first up to three covered targets per correctness group',
                                                          'examples':selected}, ensure_ascii=False, indent=2), encoding='utf-8')
    from .reasoning_eval_v1 import atomic_json
    md.update(report_timestamp=datetime.now(timezone.utc).isoformat(), integrity_checks=checks,
              evaluation_code_sha256={name:hashlib.sha256(project_path(config, 'src/recsaver/'+name).read_bytes()).hexdigest()
                                      for name in ['reasoning_eval_v1.py','reference_audit.py','reasoning_eval_metrics.py','reasoning_eval_report.py']})
    atomic_json(out / 'metadata.json', md)
    print(json.dumps(checks), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', default='configs/reasoning_eval_v1.yaml')
    parser.add_argument('--require-complete', action='store_true'); args = parser.parse_args()
    report(load_config(args.config), args.require_complete)


if __name__ == '__main__':
    main()
