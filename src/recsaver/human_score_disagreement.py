"""人間採点者間の大きな点差を対象とする、再開可能な探索実験。

既存の履歴選択・プロンプト・リーク検査・自己検証・理由指標を再利用する。
人手確認欄は機械判定で埋めず、生成物からバイアス是正を結論しない。
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import difflib
import gc
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

import pandas as pd
import yaml

from .config import load_config, project_path
from .data import TRAITS, VALID
from .full_prediction_experiment import sample_correct
from .history import format_history
from .parsing import parse_prediction
from .reasoning_eval_v1 import (EvaluationGenerator, append_record, atomic_json, generate,
                               recover_log, request_seed, sha, summarize, token_count,
                               verification_prompt)
from .utils import read_jsonl, write_jsonl


NOTICE = ('参照理由は実Overallを条件としてLLMが生成した説明であり、採点者本人の実際の思考を示すものではありません。'
          '自己検証通過は説明の正しさを保証しません。予測点差の縮小や理由の生成だけで、'
          '採点者バイアスの是正・人間採点者間の点差縮小・フィードバックの効果は結論できません。')
REVIEW = ['着目点・判断の違い', '本文や履歴に裏付けられない説明', 'ルーブリックに照らして再確認すべき判断',
          '点差の縮小に役立ちそうか', '判断根拠', '評価者', '評価日']


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def selected_jsonl(path, ids):
    if not path.exists():
        return []
    with path.open(encoding='utf-8') as stream:
        return [r for line in stream if line.strip() for r in [json.loads(line)] if r.get('target_id') in ids]


def new_generator(config):
    # 元実験との比較用モデル設定を保ち、GPU共有時の確保量だけを分離する。
    runtime=dict(config,model=dict(config['model'],gpu_memory_utilization=config['runtime_gpu_memory_utilization']))
    return EvaluationGenerator(runtime)


def extract(raw):
    """Filenameを同一エッセイとし、本文の版違いを監査する。

    完全重複は統合し、同一本文×採点者のスコア矛盾は黙って選ばず停止する。
    """
    from ..transform_data import create_rater_essay_wide
    wide = create_rater_essay_wide(raw)
    wide['target_id'] = wide.apply(lambda r: f'{int(r.source_row_id)}:{int(r.rater_position)}', axis=1)
    wide['essay_key'] = wide.Filename.astype(str).map(digest)
    canonical_text={}
    canonical_row={}
    for filename,group in raw.groupby('Filename',sort=False):
        texts=group.Text.tolist()
        if len(set(texts))>1 and any(difflib.SequenceMatcher(None,texts[0],t).ratio()<.90 for t in texts[1:]):
            raise ValueError(f'Filename collision with unrelated texts needs manual resolution: {filename}')
        # 監査した10組は空白・匿名化の版違い。後方の匿名化済みレコードを共通入力にする。
        canonical_text[filename]=texts[-1]
        canonical_row[filename]=int(group.index[-1])
    wide['canonical_text']=wide.Filename.map(canonical_text)
    duplicate_audit = []
    rows = []
    for (_, rater), group in wide.groupby(['essay_key', 'rater_id'], sort=False):
        if len(group) > 1:
            same = len(group[['Overall']].drop_duplicates()) == 1
            traits_same = len(group[TRAITS].drop_duplicates()) == 1
            duplicate_audit.append(dict(essay_key=group.essay_key.iloc[0], rater_id=rater,
                                        target_ids=group.target_id.tolist(), identical_overall=same,identical_traits=traits_same,
                                        original_records=group[['target_id','Overall',*TRAITS]].to_dict('records'),
                                        action='keep_last_same_overall; preserve_trait_differences_in_audit' if same else 'conflict_requires_resolution'))
        rows.append(group.iloc[-1])
    if any(not r['identical_overall'] for r in duplicate_audit):
        raise ValueError(f'同一エッセイ×採点者の矛盾: {duplicate_audit}')
    canonical = pd.DataFrame(rows)
    pairs, excluded = [], []
    for essay_key, group in canonical.groupby('essay_key', sort=False):
        for (_, a), (_, b) in itertools.combinations(group.sort_values('rater_id').iterrows(), 2):
            record = dict(case_id=f"essay_{int(a.source_row_id):05d}__{a.rater_id}__{b.rater_id}",
                          essay_key=essay_key, essay_id=str(a.Filename), filename_aliases=sorted(group.Filename.astype(str).unique()),
                          source_row_ids=sorted(map(int, wide[wide.essay_key.eq(essay_key)].source_row_id.unique())),
                          canonical_text_source_row_id=canonical_row[a.Filename],
                          target_a=a.target_id, target_b=b.target_id, rater_a=a.rater_id, rater_b=b.rater_id,
                          actual_a=None if pd.isna(a.Overall) else float(a.Overall),
                          actual_b=None if pd.isna(b.Overall) else float(b.Overall),
                          essay= canonical_text[a.Filename], rater_count=len(group))
            if a.Overall not in VALID or b.Overall not in VALID:
                record['exclusion_reason'] = 'Overall missing/zero/outside integer 1..5'
                excluded.append(record)
            else:
                record.update(actual_a=int(a.Overall), actual_b=int(b.Overall), gap=int(abs(a.Overall-b.Overall)))
                if record['gap'] in (2, 3):
                    pairs.append(record)
    pairs.sort(key=lambda p: (-p['gap'], p['case_id']))
    return wide, pairs, excluded, duplicate_audit


def eligible_history(wide, target):
    """本人のみ。本文・Filename・非欠損kaggle IDの別名も対象から除外する。"""
    valid = wide.Overall.isin(VALID) & wide[TRAITS].isin(VALID).all(axis=1)
    pool = wide[valid & wide.Text.notna() & wide.Text.astype(str).str.strip().ne('')].copy()
    exclude = pool.essay_key.eq(target.essay_key) | pool.Filename.eq(target.Filename)
    if pd.notna(target.text_id_kaggle):
        exclude |= pool.text_id_kaggle.eq(target.text_id_kaggle)
    pool = pool[~exclude].drop_duplicates(['essay_key', 'rater_id'], keep='last')
    return pool


def prepare(config, tokenizer):
    root = Path(config['_root']); out = project_path(config, config['output_dir']); out.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(project_path(config, config['data']['raw_path']), low_memory=False)
    wide, pairs, excluded, duplicates = extract(raw)
    # rawから作った値と既存processedの対応を実測で検証する。
    processed = pd.read_csv(project_path(config, config['data']['processed_path']), low_memory=False)
    cols = ['source_row_id','rater_position','Filename','Text','rater_id','Overall',*TRAITS]
    pd.testing.assert_frame_equal(wide[cols], processed[cols], check_dtype=False)
    source_md = json.loads(project_path(config, config['source_metadata']).read_text(encoding='utf-8'))
    if source_md['model'] != config['model'] or source_md['history_seed'] != config['history_seed']:
        raise ValueError('Prediction model/history seed differs from JIMA full experiment')
    if source_md['generation_config'] != config['generation']['prediction']:
        raise ValueError('Prediction sampling differs')
    for name in ['dataset','rubric','rubric_prompt','parser']:
        if sha(root/source_md['source_paths'][name]) != source_md['source_sha256'][name]:
            raise ValueError(f'Source prediction provenance changed: {name}')
    ids = {p[k] for p in pairs for k in ['target_a','target_b']}
    predictions = {r['target_id']:r for r in selected_jsonl(project_path(config, config['source_predictions']), ids)}
    manifest = {r['target_id']:r for r in selected_jsonl(project_path(config, config['source_manifest']), ids)}
    rubric = project_path(config, config['rubric_path']).read_text(encoding='utf-8')
    templates = {k:project_path(config,config[k]).read_text(encoding='utf-8') for k in
                 ['prediction_prompt','reference_prompt','self_verification_prompt']}
    if '{gold_overall}' in templates['self_verification_prompt'] or '{predicted_overall}' in templates['self_verification_prompt']:
        raise ValueError('verification contains target score field')
    indexed = wide.set_index('target_id', drop=False)
    items, unavailable, audit = [], [], []
    ordered = list(dict.fromkeys(p[k] for p in pairs for k in ['target_a','target_b']))
    for tid in ordered:
        target = indexed.loc[tid]
        try:
            # 既存の対象フィルタを維持し、除外時も抽出ペアは残す。
            if not all(target[t] in VALID for t in TRAITS):
                raise ValueError('target_trait_profile_invalid_under_existing_preprocessing')
            pool = eligible_history(wide, target)
            groups = {r:g for r,g in pool.groupby('rater_id')}
            if target.rater_id not in groups:
                raise ValueError('history_insufficient: no valid rater history')
            history = sample_correct(groups, target, config['history_size'], config['history_seed'])
            if history is None:
                raise ValueError('history_insufficient: fewer than K=3')
            history_ids = history.target_id.tolist()
            text = format_history(history)
            # targetの実スコア/Trait/相手のスコアをrendererに渡さない。
            prompt = templates['prediction_prompt'].format(overall_rubric=rubric, rating_history=text, target_essay=target.canonical_text)
            old = predictions.get(tid)
            reusable = bool(old and old['parse_success'] and old['condition']=='correct_k3_overall_rubric'
                            and old['rater_id']==target.rater_id and old['gold_overall']==int(target.Overall)
                            and old['history_ids']==history_ids and old['prompt']==prompt
                            and manifest[tid]['correct_history_ids']==history_ids)
            item = dict(target_id=tid, target_rater=target.rater_id, gold_overall=int(target.Overall),
                        essay_key=target.essay_key, essay=target.canonical_text, rubric=rubric, history_ids=history_ids,
                        history_text=text, history=history[cols+['target_id','essay_key']].to_dict('records'),
                        prediction= dict(old, reused=True, reused_from=config['source_predictions']) if reusable else None,
                        prediction_prompt=prompt)
            item['reference_prompt'] = templates['reference_prompt'].format(overall_rubric=rubric, rating_history=text,
                                                                           target_essay=item['essay'], gold_overall=item['gold_overall'])
            item['reference_prompt_tokens'] = token_count(tokenizer, item['reference_prompt'])
            item['verification_base_tokens'] = token_count(tokenizer, verification_prompt(templates['self_verification_prompt'], item, ''))
            if (token_count(tokenizer,prompt)+config['generation']['prediction']['max_tokens']>config['model']['max_model_len'] or
                item['reference_prompt_tokens']+config['generation']['reference']['max_tokens']>config['model']['max_model_len'] or
                item['verification_base_tokens']+config['generation']['reference']['max_tokens']+16+
                    config['generation']['verification']['max_tokens']>config['model']['max_model_len']):
                raise ValueError('context_overflow_no_truncation')
            items.append(item)
            audit.append(dict(target_id=tid, history_ids=history_ids, prediction_reused=reusable,
                              target_essay_excluded=True, target_filename_excluded=True, correct_rater=True,
                              prediction_gold_and_traits_not_rendered=True, verification_gold_field_absent=True,
                              history_count=len(history), history_changed_from_existing=not reusable))
        except ValueError as exc:
            unavailable.append(dict(target_id=tid, failure_reason=str(exc)))
    collisions=[]
    for filename,g in raw[raw.Filename.duplicated(False)].groupby('Filename'):
        texts=g.Text.tolist()
        collisions.append(dict(Filename=str(filename),rows=g.index.tolist(),distinct_texts=g.Text.nunique(),
                               text_similarity=difflib.SequenceMatcher(None,*texts).ratio() if len(texts)==2 else None,
                               canonical_text_source_row_id=int(g.index[-1]),
                               action='same_essay_anonymization_whitespace_variants; latest_text_used_for_both_raters; all_aliases_excluded_from_history'))
    gap_all = Counter(abs(int(r.Overall_1)-int(r.Overall_2)) for r in raw.itertuples()
                      if pd.notna(r.Overall_1) and pd.notna(r.Overall_2))
    audit_data=dict(raw_rows=len(raw), unique_texts=raw.Text.nunique(), unique_filenames=raw.Filename.nunique(),
                    filename_collisions=collisions, essay_rater_duplicates=duplicates,
                    essays_with_three_or_more_raters=int((wide.groupby('essay_key').rater_id.nunique()>=3).sum()),
                    missing_rater_records=int(wide.rater_id.isna().sum()),
                    invalid_overall_records=int((~wide.Overall.isin(VALID)).sum()),
                    invalid_trait_records=int((~wide[TRAITS].isin(VALID).all(axis=1)).sum()),
                    raw_row_gap_distribution_including_invalid=dict(gap_all),
                    gaps={str(g):dict(essays=len({p['essay_key'] for p in pairs if p['gap']==g}),
                                     pairs=sum(p['gap']==g for p in pairs)) for g in [3,2]},
                    expected_counts=dict(gap3_approx=15,gap2_approx=215),
                    identity_policy='Filename identity; 10 duplicate Filename text variants manually inspected (whitespace/anonymization); latest variant used for all raters; same-essay aliases excluded from history',
                    score_policy='pair extraction: both Overall integer 1..5; histories/eligible targets: existing Overall+all Traits integer 1..5',
                    target_preprocessing_failures=unavailable)
    atomic_json(out/'data_audit.json',audit_data)
    write_jsonl(out/'extracted_pairs.jsonl', pairs)
    write_jsonl(out/'excluded_invalid_overall_pairs.jsonl', excluded)
    pd.DataFrame([{k:v for k,v in p.items() if k!='essay'} for p in pairs]).to_csv(out/'extracted_pairs.csv',index=False)
    pd.DataFrame(unavailable,columns=['target_id','failure_reason']).to_csv(out/'unavailable_targets.csv',index=False)
    pd.DataFrame(audit).to_csv(out/'input_integrity_audit.csv',index=False)
    (out/'rubric_used.md').write_text(rubric,encoding='utf-8')
    paths={k:config[k] for k in ['source_metadata','source_predictions','source_manifest','rubric_path','prediction_prompt',
                                'reference_prompt','self_verification_prompt']}
    paths.update(raw=config['data']['raw_path'],processed=config['data']['processed_path'],
                 implementation='src/recsaver/human_score_disagreement.py',parser='src/recsaver/parsing.py',
                 leakage='src/recsaver/reference_audit.py',generation='src/recsaver/reasoning_eval_v1.py',
                 metrics='src/recsaver/reasoning_eval_metrics.py',history='src/recsaver/full_prediction_experiment.py')
    hashes={k:sha(root/v) for k,v in paths.items()}
    clean={k:v for k,v in config.items() if not k.startswith('_')}
    fingerprint=digest(json.dumps(dict(config=clean,hashes=hashes),sort_keys=True))
    if (out/'metadata.json').exists():
        md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
        if md['fingerprint']!=fingerprint:
            raise ValueError('resume input/config/code changed; use separate output directory')
    else:
        md=dict(timestamp=datetime.now(timezone.utc).isoformat(), fingerprint=fingerprint, model=config['model'],
                source_paths=paths,source_sha256=hashes,status='prepared',target_count=len(items),
                prediction_reused_count=sum(i['prediction'] is not None for i in items),
                generation_config=config['generation'],notice=NOTICE)
        atomic_json(out/'metadata.json',md)
    (out/'resolved_config.yaml').write_text(yaml.safe_dump(clean,sort_keys=False),encoding='utf-8')
    write_jsonl(out/'prepared_targets.jsonl',items)
    print(json.dumps(audit_data['gaps']), 'prepared',len(items),'unavailable',len(unavailable),
          'prediction_reused',sum(i['prediction'] is not None for i in items),flush=True)
    return out,items,pairs,unavailable,templates['self_verification_prompt']


def reuse_references(config,items,out,template,tokenizer):
    """出力と入力・設定を比較し、一致する候補の全試行と検証履歴を再利用する。"""
    if (out/'reference_reuse_audit.json').exists():
        return
    by_id={i['target_id']:i for i in items}; ids=set(by_id)
    existing={r['target_id'] for r in recover_log(out/'reference_candidates.jsonl')}
    imported=[]; decisions=[]
    for source in config['reference_sources']:
        directory=project_path(config,source)
        resolved=yaml.safe_load((directory/'resolved_config.yaml').read_text(encoding='utf-8'))
        match=(resolved['model']==config['model'] and resolved['generation']==
               {k:config['generation'][k] for k in ['reference','verification']} and
               resolved['seed']==config['seed'] and all(resolved[k]==config[k] for k in
               ['history_size','num_reference_candidates','max_reference_retries','max_verification_parse_retries']))
        md=json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
        source_ok=all(sha(project_path(config,p))==md['source_sha256'][k] for k,p in md['source_paths'].items())
        decisions.append(dict(source=source,settings_match=match,source_hashes_match=source_ok))
        if not match or not source_ok:
            continue
        refs=selected_jsonl(directory/'reference_candidates.jsonl',ids-existing)
        verifs=selected_jsonl(directory/'self_verification_results.jsonl',ids-existing)
        for tid in sorted({r['target_id'] for r in refs}):
            item=by_id[tid]; rr=[r for r in refs if r['target_id']==tid]; vv=[v for v in verifs if v['target_id']==tid]
            if not all(r['prompt']==item['reference_prompt'] and r['history_ids']==item['history_ids'] and
                       r['gold_overall']==item['gold_overall'] and r['target_rater']==item['target_rater'] and
                       r['seed']==request_seed(config,'reference',tid,r['candidate_index'],r['attempt_index']) for r in rr):
                continue
            candidates={(r['candidate_index'],r['attempt_index']):r for r in rr}
            if not all(v['prompt']==verification_prompt(template,item,candidates[(v['candidate_index'],v['reference_attempt_index'])]['reference_reasoning'])
                       and v['seed']==request_seed(config,'verification',tid,v['candidate_index'],v['attempt_index']) for v in vv):
                continue
            for name,records in [('reference_candidates.jsonl',rr),('self_verification_results.jsonl',vv)]:
                for r in records:
                    append_record(out/name,dict(r,reused_from=source,reused=True))
            imported.append(tid);existing.add(tid)
    atomic_json(out/'reference_reuse_audit.json',dict(source_decisions=decisions,imported_targets=imported))


def ensure_predictions(config,items,out,generator):
    saved={p['target_id']:p for p in recover_log(out/'predictions.jsonl')}
    for item in items:
        tid=item['target_id']
        if tid in saved:
            item['prediction']=saved[tid];continue
        if item['prediction'] is None:
            generator=generator or new_generator(config)
            attempts=[];parsed=None;error=None
            for attempt in [1,2]:
                job=dict(prompt=item['prediction_prompt'], seed=request_seed(config,'prediction',tid,0,attempt))
                raw=generator.generate([job],config['generation']['prediction'])[0];attempts.append(dict(job,raw_model_output=raw))
                try:
                    parsed=parse_prediction(raw);break
                except (ValueError,TypeError) as exc:
                    error=str(exc)
            pred=parsed['predicted_overall'] if parsed else None
            item['prediction']=dict(target_id=tid,rater_id=item['target_rater'],gold_overall=item['gold_overall'],
                 predicted_overall=pred,prediction_reasoning=parsed['reasoning'] if parsed else '',parse_success=parsed is not None,
                 parse_error=None if parsed else error,absolute_error=abs(pred-item['gold_overall']) if pred is not None else None,
                 history_ids=item['history_ids'],prompt=item['prediction_prompt'],attempts=attempts,reused=False)
        append_record(out/'predictions.jsonl',item['prediction'])
    return generator


def compute_metrics(config,items,out):
    from .reasoning_eval_metrics import MetricEngine, METRICS
    pool=read_jsonl(out/'verified_reference_pool.jsonl');by_id={i['target_id']:i for i in items}
    previous=recover_log(out/'metric_pairs.jsonl')
    done={(r['target_id'],r['candidate_index']) for r in previous}
    pending=[r for r in pool if (r['target_id'],r['candidate_index']) not in done and
             by_id[r['target_id']]['prediction']['parse_success']]
    if pending:
        engine=MetricEngine(config)
        for start in range(0,len(pending),config['metrics']['batch_size']):
            batch=pending[start:start+config['metrics']['batch_size']]
            scores=engine.score([by_id[r['target_id']]['prediction']['prediction_reasoning'] for r in batch],
                                [r['reference_reasoning'] for r in batch])
            for r,score in zip(batch,scores):
                row=dict(target_id=r['target_id'],candidate_index=r['candidate_index'],**score)
                append_record(out/'metric_pairs.jsonl',row);previous.append(row)
        atomic_json(out/'metric_metadata.json',engine.metadata)
    pd.DataFrame(previous,columns=['target_id','candidate_index',*METRICS]).to_csv(out/'reasoning_metrics_by_reference.csv',index=False)


def report(config,out,items,pairs,unavailable):
    refs=read_jsonl(out/'reference_candidates.jsonl');vs=read_jsonl(out/'self_verification_results.jsonl')
    pool=read_jsonl(out/'verified_reference_pool.jsonl');metric=read_jsonl(out/'metric_pairs.jsonl')
    completed={r['target_id']:r for r in pd.read_csv(out/'target_reference_summary.csv').to_dict('records')} if (out/'target_reference_summary.csv').exists() else {}
    missing={r['target_id']:r['failure_reason'] for r in unavailable};by_id={i['target_id']:i for i in items}
    all_targets={}
    for tid in {p[k] for p in pairs for k in ['target_a','target_b']}:
        item=by_id.get(tid);c=completed.get(tid,{})
        accepted=[r for r in pool if r['target_id']==tid]
        attempts=[r for r in refs if r['target_id']==tid]
        verification=[v for v in vs if v['target_id']==tid]
        p=item['prediction'] if item else None
        status=('unavailable' if not item else 'pending' if not p else 'prediction_failed' if not p['parse_success'] else
                'completed' if c.get('completed') else 'pending')
        failure=missing.get(tid)
        if not failure and not accepted:
            failure=('not_processed_yet' if status=='pending' else 'prediction_parse_failure' if status=='prediction_failed' else
                     'no_leakage_free_candidate' if not any(r['accepted_as_leakage_free'] for r in attempts) else
                     'verification_parse_failure' if not any(v['parse_success'] for v in verification) else 'self_verification_score_mismatch')
        all_targets[tid]=dict(target_id=tid,status=status,failure_reason=failure,prediction=p,
                 history=item['history'] if item else [],history_text=item['history_text'] if item else None,
                 reference_candidates=attempts,self_verifications=verification,verified_references=accepted,
                 verified_count=len(accepted),reasoning_metrics=[m for m in metric if m['target_id']==tid])
    write_jsonl(out/'target_results.jsonl',list(all_targets.values()))
    case_dir=out/'cases';case_dir.mkdir(exist_ok=True);pair_rows=[];index=[]
    def block(value):
        # Essay/model output may contain markdown fences; use an appropriately long delimiter.
        text=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)
        fence='`'*(max([len(x) for x in __import__('re').findall(r'`+',text)]+[2])+1)
        return f'{fence}\n{text}\n{fence}\n'
    for pair in pairs:
        a,b=all_targets[pair['target_a']],all_targets[pair['target_b']]
        pa,pb=a['prediction'],b['prediction']
        pred_a=pa['predicted_overall'] if pa and pa['parse_success'] else None
        pred_b=pb['predicted_overall'] if pb and pb['parse_success'] else None
        row={k:v for k,v in pair.items() if k!='essay'}
        row.update(predicted_a=pred_a,predicted_b=pred_b,
                   signed_error_a=pred_a-pair['actual_a'] if pred_a is not None else None,
                   signed_error_b=pred_b-pair['actual_b'] if pred_b is not None else None,
                   absolute_error_a=abs(pred_a-pair['actual_a']) if pred_a is not None else None,
                   absolute_error_b=abs(pred_b-pair['actual_b']) if pred_b is not None else None,
                   predicted_gap=abs(pred_a-pred_b) if pred_a is not None and pred_b is not None else None,
                   status_a=a['status'],status_b=b['status'],verified_a=a['verified_count'],verified_b=b['verified_count'],
                   failure_a=a['failure_reason'],failure_b=b['failure_reason'],
                   processing_status='success' if a['status']==b['status']=='completed' else
                       'failed' if any(t['status'] in ['unavailable','prediction_failed'] for t in [a,b]) else 'pending',
                   reference_acquisition='both' if a['verified_count'] and b['verified_count'] else
                       'one' if a['verified_count'] or b['verified_count'] else 'neither')
        pair_rows.append(row)
        lines=[f"# {pair['case_id']}\n",NOTICE,'\n## エッセイと人間の採点\n',
               block({k:pair[k] for k in ['essay_id','essay_key','filename_aliases','source_row_ids','rater_a','actual_a','rater_b','actual_b','gap']}),
               block(pair['essay']), '\n## 共通ルーブリック\n','[使用したルーブリック全文](../rubric_used.md)\n',
               '\n## 処理概要\n',block(row)]
        for label,target in [('A',a),('B',b)]:
            lines += [f'\n## 採点者 {label}: {pair["rater_"+label.lower()]}\n',
                      f"状態: {target['status']} / 参照理由取得数: {target['verified_count']} / 失敗理由: {target['failure_reason']}\n",
                      '\n### 使用した本人の履歴（全文・実スコア・Trait）\n',block(target['history_text'] or '利用不可'),
                      '\n### 実スコアを与えない予測Overall・予測理由\n',
                      block({k:target['prediction'].get(k) for k in ['predicted_overall','prediction_reasoning','parse_success','reused','reused_from']}
                            if target['prediction'] else None),
                      '\n### 実スコア条件付き参照理由候補・全再試行・リーク検査\n']
            # 全試行を掲載する。promptも元のjournalで確認できる。
            for r in target['reference_candidates']:
                lines.append(block({k:v for k,v in r.items() if k!='prompt'}))
            lines += ['\n### 自己検証の全試行\n']
            for v in target['self_verifications']:
                lines.append(block({k:x for k,x in v.items() if k!='prompt'}))
            lines += ['\n### 検証済み参照理由（すべて）\n',block(target['verified_references']),
                      '\n### 予測理由と各検証済み参照理由の既存指標\n',block(target['reasoning_metrics'])]
            if target['reasoning_metrics']:
                from .reasoning_eval_metrics import METRICS
                lines.append(block({m:{'mean':sum(r[m] for r in target['reasoning_metrics'])/len(target['reasoning_metrics']),
                                       'max':max(r[m] for r in target['reasoning_metrics'])} for m in METRICS}))
        lines += ['\n## 人手確認欄（未評価）\n',
                  '記入は human_review.csv に保存してください。このレポートの再生成時もCSVの記入内容は維持します。\n',
                  '\n- 両者の着目点・判断の違い：\n- 本文や履歴に裏付けられない説明：\n- ルーブリックに照らして再確認すべき判断：\n',
                  '- 点差の縮小に役立ちそうか：[ ] 役立ちそう / [ ] 判断できない / [ ] 役立ちにくい\n- 上記の判断根拠：\n']
        (case_dir/(pair['case_id']+'.md')).write_text('\n'.join(lines),encoding='utf-8')
        index.append(f"- [{pair['case_id']}](cases/{pair['case_id']}.md) — {pair['gap']}点差、実 {pair['actual_a']} / {pair['actual_b']}、参照理由 {a['verified_count']} / {b['verified_count']}")
    write_jsonl(out/'pair_results.jsonl',pair_rows)
    frame=pd.DataFrame(pair_rows);frame.to_csv(out/'pair_results.csv',index=False)
    review_path=out/'human_review.csv'
    if not review_path.exists():
        pd.DataFrame([dict(case_id=p['case_id'],gap=p['gap'],**{k:'' for k in REVIEW}) for p in pairs]).to_csv(review_path,index=False,encoding='utf-8-sig')
    summaries=[]
    for gap in [3,2]:
        part=frame[frame.gap==gap]
        valid=part[part.predicted_gap.notna()]
        summaries.append(dict(gap=gap,essays=int(part.essay_key.nunique()),pairs=len(part),
            processing_success=int(part.processing_status.eq('success').sum()),processing_failed=int(part.processing_status.eq('failed').sum()),
            processing_pending=int(part.processing_status.eq('pending').sum()),
            reference_both=int(part.reference_acquisition.eq('both').sum()),reference_one=int(part.reference_acquisition.eq('one').sum()),
            reference_neither=int(part.reference_acquisition.eq('neither').sum()),
            mae_a=float(part.absolute_error_a.mean()),mae_b=float(part.absolute_error_b.mean()),
            predicted_gap_mean=float(valid.predicted_gap.mean()) if len(valid) else None,
            predicted_gap_distribution={str(k):int(v) for k,v in valid.predicted_gap.value_counts().items()},
            predicted_gap_smaller=int(valid.predicted_gap.lt(gap).sum()),
            signed_error_a_distribution={str(k):int(v) for k,v in part.signed_error_a.value_counts().items()},
            signed_error_b_distribution={str(k):int(v) for k,v in part.signed_error_b.value_counts().items()}))
    atomic_json(out/'summary.json',dict(by_gap=summaries,notice=NOTICE,all_human_reviews_unfilled_by_llm=True))
    pd.DataFrame(summaries).to_csv(out/'summary_by_gap.csv',index=False)
    data_audit=json.loads((out/'data_audit.json').read_text(encoding='utf-8'))
    counts='、'.join(f"{s['gap']}点差{s['essays']}エッセイ・{s['pairs']}ペア" for s in summaries)
    lines=['# 人間採点者間の点差を対象とする探索実験\n',NOTICE,
           '\n## 対象・設定・既存実験との整合性\n',
           'rawを再集計。有効Overallは整数1～5。対象はエッセイ本文×異なる採点者の順序なしペア。'
           f'{counts}（期待値15/215とは不一致。実測値を採用）。'
           'Filename重複10組は本文差分を確認し、空白・匿名化の版違いとして同一エッセイに統合。'
           '両者の入力は後方の匿名化済み本文に統一し、履歴ではすべての同一エッセイ版を除外。'
           f"3名以上の採点があるエッセイは全体で{data_audit['essays_with_three_or_more_raters']}件。"
           '同一採点者の重複1組はOverall一致・Trait不一致を記録し、後方レコードを代表として使用。'
           '詳細は[data_audit.json](data_audit.json)、[抽出一覧](extracted_pairs.csv)を参照。\n',
           'JIMAと同じQwen2.5-32B-Instruct-GPTQ-Int4、GPTQ Marlin、履歴K=3、本人の履歴をseed=20260814で抽出。'
           '英語の既存Overallルーブリック・既存3プロンプトを使用。対象本文・Filename・非欠損kaggle IDを全採点者の履歴候補から除外。'
           '対象の実Trait/実Overall/相手の点数は予測入力に含めない。自己検証は対象の実スコアを含めない。\n',
           '予測・参照生成: temperature=.2, top_p=.8, max_tokens=384。自己検証: .2/.8/64。'
           '参照理由3枠、枠ごと最大5生成試行。スコア開示があれば除外・再生成し、文章の恣意的な削除はしない。'
           '検証のparse失敗は1回再試行、再構成スコアが実スコアと一致すれば採用。'
           '理由生成/検証seed=20260916はreasoning_eval_largeに一致。設定・履歴・プロンプト・元ファイルのhashが一致した既存出力を再利用。\n',
           f"GPUメモリ利用率: {config['runtime_gpu_memory_utilization']}（既存 {config['model']['gpu_memory_utilization']}）。モデル・生成条件の変更なし。\n",
           '変更は点差による対象選択、別名も含む履歴除外、両者の比較レポート・未記入人手評価欄の追加。'
           '対象Traitが無効な場合は既存前処理に合わせ実験対象から外し、ペア一覧には失敗理由を残す。\n',
           '\n## 集計\n', 'A/Bは採点者ID順で、高得点/低得点の順ではありません。処理成功は参照生成・検証の所定試行が完了した状態で、参照取得成功とは別です。\n',
           block(summaries), '\n## 人が次に確認する点\n',
           '両者の実スコア条件付き参照理由をすべて比較し、着目点の違い、本文・履歴の裏付け、ルーブリック上の再確認点を記入してください。'
           '予測理由は実スコアなしの別出力です。人手評価は未実施です。'
           '役立ちそうかの選択肢は「役立ちそう／判断できない／役立ちにくい」です。'
           '実際の効果を調べるには、別途採点者による再確認・再採点が必要です。\n',
           '\n## 再開・出力\n',
           '`python -m src.recsaver.human_score_disagreement --stage all` で既存設定を検証して未処理から再開。'
           'journalは各試行でflush/fsync。変更された入力・コード・設定での混在を拒否します。'
           'reference_candidates.jsonl/self_verification_results.jsonlに生出力・入力・seed・失敗理由、'
           'prepared_targets.jsonlに履歴と予測入力、target_results.jsonlに対象別全結果、pair_results.jsonl/CSVにペア別結果を保存。'
           '理由指標はBLEU・ROUGE-1 F1・METEOR・BERTScore F1（roberta-large、17層、IDF/再スケールなし）。各参照と平均・最大を提示します。\n',
           '\n[人手記入用CSV](human_review.csv) / [集計CSV](summary_by_gap.csv) / [対象別結果](target_results.jsonl)\n',
           '\n## ケース別比較レポート\n',*index]
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    return all_targets


def run(config,stage):
    from filelock import FileLock
    from transformers import AutoTokenizer
    out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
    with FileLock(str(out/'.run.lock'),timeout=0):
        tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True)
        out,items,pairs,unavailable,template=prepare(config,tok)
        if stage=='prepare':
            return
        if stage=='report':
            predictions={p['target_id']:p for p in recover_log(out/'predictions.jsonl')}
            for i in items:i['prediction']=predictions.get(i['target_id'],i['prediction'])
            report(config,out,items,pairs,unavailable);return
        reuse_references(config,items,out,template,tok)
        if stage=='evaluate':
            predictions={p['target_id']:p for p in recover_log(out/'predictions.jsonl')}
            for i in items:i['prediction']=predictions.get(i['target_id'],i['prediction'])
            compute_metrics(config,items,out);report(config,out,items,pairs,unavailable);return
        generator=None
        pilot=pairs[:config['pilot_pairs']]
        phases=[('pilot_gap3',pilot),('all_gap3',[p for p in pairs if p['gap']==3]),('all_gap2',pairs)]
        for name,active in phases:
            if stage=='pilot' and name!='pilot_gap3':break
            ids={p[k] for p in active for k in ['target_a','target_b']}
            phase_items=[i for i in items if i['target_id'] in ids]
            generator=ensure_predictions(config,phase_items,out,generator)
            write_jsonl(out/'prepared_targets.jsonl',items)
            selected=[i for i in phase_items if i['prediction']['parse_success']]
            atomic_json(out/'execution_status.json',dict(phase=name,status='running',timestamp=datetime.now(timezone.utc).isoformat()))
            # 同一モデルをフェーズ間で維持し、既存generateのjournal/retry/verificationを使う。
            if generator is None:
                from .reasoning_eval_v1 import reference_jobs, verify_jobs
                refs=recover_log(out/'reference_candidates.jsonl');verifs=recover_log(out/'self_verification_results.jsonl')
                if reference_jobs(config,selected,refs) or verify_jobs(config,selected,refs,verifs,template,tok):
                    generator=new_generator(config)
            generate(config,selected,template,out,generator=generator)
            results=report(config,out,items,pairs,unavailable)
            checks=dict(phase=name,case_count=len(active),all_available_targets_completed=all(
                results[tid]['status']=='completed' for tid in ids if tid in {i['target_id'] for i in items}),
                reports_exist=all((out/'cases'/(p['case_id']+'.md')).exists() for p in active),
                human_review_columns_blank=bool(pd.read_csv(out/'human_review.csv')[REVIEW].isna().all().all()))
            atomic_json(out/(name+'_validation.json'),checks)
            if not checks['all_available_targets_completed'] or not checks['reports_exist']:
                raise RuntimeError(f'Phase structural gate failed: {checks}')
            print('PHASE COMPLETED',name,flush=True)
        # vLLMとBERTScoreは別プロセスにしてGPUメモリを確実に解放する。
        atomic_json(out/'execution_status.json',dict(phase='generation',status='pilot_completed' if stage=='pilot' else 'completed',
                                                      timestamp=datetime.now(timezone.utc).isoformat()))
        if stage=='all':
            print('Generation complete. Run --stage evaluate in a fresh process.',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',default='configs/human_score_disagreement.yaml')
    p.add_argument('--stage',choices=['prepare','pilot','generate','evaluate','report','all'],default='all')
    args=p.parse_args();config=load_config(args.config)
    try:
        if args.stage=='all':
            # 各GPUモデルの終了を待ち、少数例の指標・出力確認後に全件へ進む。
            for stage in ['pilot','evaluate','generate','evaluate']:
                subprocess.run([sys.executable,'-m','src.recsaver.human_score_disagreement',
                                '--config',args.config,'--stage',stage],check=True,cwd=config['_root'])
        else:
            run(config,args.stage)
    except Exception as exc:
        out=project_path(config,config['output_dir']);out.mkdir(parents=True,exist_ok=True)
        append_record(out/'execution_failures.jsonl',dict(timestamp=datetime.now(timezone.utc).isoformat(),
                                                        stage=args.stage,error_type=type(exc).__name__,error=str(exc)))
        raise


if __name__=='__main__':
    main()
