"""Real pairwise metrics, retaining the MVP BLEU/ROUGE definitions."""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from .config import load_config, project_path
from .phase3_reasoning_eval import tokens, sentence_bleu, rouge1_f1
from .utils import read_jsonl

METRICS = ['bleu', 'rouge1_f1', 'meteor', 'bertscore_f1']


def resources(config, download=False):
    import nltk
    from huggingface_hub import snapshot_download
    if download:
        nltk.download('wordnet', raise_on_error=True)
        nltk.download('omw-1.4', raise_on_error=True)
    from nltk.corpus import wordnet
    wordnet.ensure_loaded()
    return snapshot_download(config['metrics']['bertscore_model'], local_files_only=not download,
                             allow_patterns=['config.json', 'tokenizer.json', 'tokenizer_config.json',
                                             'vocab.json', 'merges.txt', 'model.safetensors'])


class MetricEngine:
    def __init__(self, config):
        import torch
        from bert_score import BERTScorer
        torch.set_num_threads(4)
        m = config['metrics']; self.settings = m
        path = resources(config)
        self.scorer = BERTScorer(model_type=path, num_layers=m['bertscore_layers'],
                                idf=m['bertscore_idf'], rescale_with_baseline=m['bertscore_rescale_with_baseline'],
                                use_fast_tokenizer=m['bertscore_use_fast_tokenizer'], device=m['device'])
        self.metadata = dict(m, model_revision=Path(path).name, bertscore_hash=self.scorer.hash,
                             bleu_definition='MVP sentence BLEU-4, add-one smoothing for every n-gram order, lower-case regex word tokens',
                             rouge_definition='MVP unigram multiset F1, lower-case regex word tokens',
                             meteor_definition='NLTK single_meteor_score; same word tokens, default Porter stemmer/WordNet; alpha=.9 beta=3 gamma=.5',
                             aggregation='per-reference pairs; per-target max and mean; macro-average over covered targets only')

    def score(self, hypotheses, references):
        from nltk.translate.meteor_score import single_meteor_score
        if not hypotheses:
            return []
        for text in hypotheses + references:
            if len(self.scorer._tokenizer.encode(text, truncation=False)) > self.scorer._tokenizer.model_max_length:
                raise ValueError('BERTScore context overflow; silent truncation is prohibited')
        _, _, f1 = self.scorer.score(hypotheses, references, batch_size=self.settings['batch_size'])
        return [dict(bleu=sentence_bleu(h, r), rouge1_f1=rouge1_f1(h, r),
                     meteor=single_meteor_score(tokens(r), tokens(h)), bertscore_f1=float(b))
                for h, r, b in zip(hypotheses, references, f1.tolist())]


def evaluate(config):
    start = time.perf_counter(); out = project_path(config, config['output_dir'])
    summary = pd.read_csv(out / 'target_reference_summary.csv')
    completed = summary[summary.completed].copy()
    pool = read_jsonl(out / 'verified_reference_pool.jsonl')
    prediction_condition = config.get('prediction_condition', 'raw_k3_with_rubric')
    predictions = {r['target_id']: r for r in read_jsonl(project_path(config, config['source_predictions']))
                   if r['condition'] == prediction_condition}
    pool = [r for r in pool if r['target_id'] in set(completed.target_id)]
    engine = MetricEngine(config)
    pairs = []
    scores = engine.score([predictions[r['target_id']]['prediction_reasoning'] for r in pool],
                          [r['reference_reasoning'] for r in pool])
    for reference, score in zip(pool, scores):
        pairs.append(dict(target_id=reference['target_id'], candidate_index=reference['candidate_index'], **score))
    pair_frame = pd.DataFrame(pairs, columns=['target_id', 'candidate_index', *METRICS])
    pair_frame.to_csv(out / 'reasoning_metrics_by_reference.csv', index=False)
    pair_frame.to_csv(out / 'reasoning_metrics_pairwise.csv', index=False)
    rows = []
    for row in completed.to_dict('records'):
        p = predictions[row['target_id']]
        values = pair_frame[pair_frame.target_id == row['target_id']]
        result = dict(target_id=row['target_id'], target_rater=p['rater_id'], gold_overall=p['gold_overall'],
                      predicted_overall=p['predicted_overall'], prediction_correct=p['exact_correct'],
                      absolute_score_error=p['absolute_error'], verified_reference_count=len(values),
                      metric_status='evaluated' if len(values) else 'no_verified_reference')
        for metric in METRICS:
            for agg in ['max', 'mean']:
                result[metric+'_'+agg] = float(getattr(values[metric], agg)()) if len(values) else np.nan
        rows.append(result)
    by_target = pd.DataFrame(rows)
    by_target.to_csv(out / 'reasoning_metrics_by_target.csv', index=False)
    columns = [m+'_'+a for m in METRICS for a in ['max', 'mean']]
    covered = by_target[by_target.verified_reference_count > 0]
    pd.DataFrame([{'metric': m, 'aggregation': a, 'n': len(covered), 'macro_mean': covered[m+'_'+a].mean()}
                  for m in METRICS for a in ['max', 'mean']]).to_csv(out / 'reasoning_metrics_summary.csv', index=False)
    for key, filename in [('prediction_correct', 'prediction_correctness_comparison.csv'),
                          ('score_error_group', 'score_error_comparison.csv')]:
        by_target['score_error_group'] = by_target.absolute_score_error.map(lambda x: str(x) if x < 2 else '>=2')
        groups = []
        for label, group in by_target.groupby(key):
            valid = group[group.verified_reference_count > 0]
            groups.append({key: label, 'targets_total': len(group), 'targets_evaluated': len(valid),
                           'coverage_rate': len(valid)/len(group), **valid[columns].mean().to_dict()})
        pd.DataFrame(groups).to_csv(out / filename, index=False)
    diversity = []
    for tid in completed.target_id:
        refs = [r for r in pool if r['target_id'] == tid]
        for a, b in itertools.combinations(refs, 2):
            left, right = set(tokens(a['reference_reasoning'])), set(tokens(b['reference_reasoning']))
            diversity.append({'target_id': tid, 'candidate_a': a['candidate_index'], 'candidate_b': b['candidate_index'],
                              'reasoning_a':a['reference_reasoning'], 'reasoning_b':b['reference_reasoning'],
                              'lexical_jaccard': len(left & right)/len(left | right) if left | right else 1.0,
                              'exact_duplicate': a['reference_reasoning'].strip() == b['reference_reasoning'].strip()})
    diversity_frame=pd.DataFrame(diversity, columns=['target_id','candidate_a','candidate_b','reasoning_a','reasoning_b',
                                                     'lexical_jaccard','exact_duplicate'])
    if len(diversity_frame) and config.get('metrics',{}).get('include_reference_bertscore',False):
        diversity_frame['bertscore_similarity']=[x['bertscore_f1'] for x in engine.score(
            diversity_frame.reasoning_a.tolist(),diversity_frame.reasoning_b.tolist())]
    diversity_frame.drop(columns=['reasoning_a','reasoning_b']).to_csv(out / 'reference_diversity.csv', index=False)
    engine.metadata.update(metric_seconds=time.perf_counter()-start, evaluated_targets=len(covered),
                           completed_targets=len(completed), pair_count=len(pairs))
    (out / 'metric_metadata.json').write_text(json.dumps(engine.metadata, indent=2), encoding='utf-8')
    metadata_path = out / 'metadata.json'
    if metadata_path.exists():
        from .reasoning_eval_v1 import atomic_json
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        metadata.update(status='completed' if len(completed) == config['num_targets'] else 'partial_evaluated',
                        reasoning_evaluation=engine.metadata)
        atomic_json(metadata_path, metadata)
    print(f'Metrics: {len(covered)}/{len(completed)} targets, {len(pairs)} pairs', flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--config', default='configs/reasoning_eval_v1.yaml')
    parser.add_argument('--setup', action='store_true'); args = parser.parse_args(); config = load_config(args.config)
    if args.setup:
        print(resources(config, download=True))
    else:
        evaluate(config)


if __name__ == '__main__':
    main()
