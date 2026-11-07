"""最終結果の入力条件・試行・全件処理・指標・人手未記入を独立に監査する。"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pandas as pd
from src.recsaver.config import load_config
from src.recsaver.data import VALID
from src.recsaver.human_score_disagreement import REVIEW
from src.recsaver.parsing import parse_reasoning, parse_prediction
from src.recsaver.reference_audit import leakage_audit
from src.recsaver.reasoning_eval_v1 import atomic_json, reference_jobs, verify_jobs, verification_prompt, sha
from src.recsaver.utils import read_jsonl,write_jsonl


def main():
    config=load_config('configs/human_score_disagreement.yaml');out=ROOT/config['output_dir']
    pairs=read_jsonl(out/'extracted_pairs.jsonl')
    items=read_jsonl(out/'prepared_targets.jsonl');by_id={r['target_id']:r for r in items}
    predictions={p['target_id']:p for p in read_jsonl(out/'predictions.jsonl')}
    targets={r['target_id']:r for r in read_jsonl(out/'target_results.jsonl')}
    refs=read_jsonl(out/'reference_candidates.jsonl');vs=read_jsonl(out/'self_verification_results.jsonl')
    pool=read_jsonl(out/'verified_reference_pool.jsonl');metrics=read_jsonl(out/'metric_pairs.jsonl')
    results=pd.read_csv(out/'pair_results.csv')
    md=json.loads((out/'metadata.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/path)==md['source_sha256'][k] for k,path in md['source_paths'].items())
    assert len(pairs)==len(results)==results.case_id.nunique()
    assert len({(r['essay_key'],*sorted([r['rater_a'],r['rater_b']])) for r in pairs})==len(pairs)
    assert set(targets)=={p[k] for p in pairs for k in ['target_a','target_b']}
    assert all(r['actual_a'] in VALID and r['actual_b'] in VALID and r['rater_a']!=r['rater_b'] and
               abs(r['actual_a']-r['actual_b'])==r['gap'] for r in pairs)
    rubric=(out/'rubric_used.md').read_text(encoding='utf-8')
    template=(ROOT/config['self_verification_prompt']).read_text(encoding='utf-8')
    ptemplate=(ROOT/config['prediction_prompt']).read_text(encoding='utf-8')
    rtemplate=(ROOT/config['reference_prompt']).read_text(encoding='utf-8')
    for item in items:
        tid=item['target_id'];p=predictions[tid]
        assert targets[tid]['status']=='completed'
        assert len(item['history'])==3 and len({r['essay_key'] for r in item['history']})==3
        assert all(r['essay_key']!=item['essay_key'] and r['rater_id']==item['target_rater'] for r in item['history'])
        assert p['history_ids']==item['history_ids'] and p['prompt']==ptemplate.format(
            overall_rubric=rubric,rating_history=item['history_text'],target_essay=item['essay'])
        assert item['reference_prompt']==rtemplate.format(overall_rubric=rubric,rating_history=item['history_text'],
                                                        target_essay=item['essay'],gold_overall=item['gold_overall'])
        assert p['parse_success'] and p['absolute_error']==abs(p['predicted_overall']-item['gold_overall'])
    for pair in pairs:
        for k in ['target_a','target_b']:
            if k in pair and pair[k] in by_id:assert by_id[pair[k]]['essay']==pair['essay']
        assert (out/'cases'/(pair['case_id']+'.md')).exists()
    refs_by_key={(r['target_id'],r['candidate_index'],r['attempt_index']):r for r in refs}
    assert len(refs_by_key)==len(refs)
    assert len({(v['target_id'],v['candidate_index'],v['attempt_index']) for v in vs})==len(vs)
    for r in refs:
        item=by_id[r['target_id']]
        assert r['prompt']==item['reference_prompt'] and r['history_ids']==item['history_ids']
        audit=leakage_audit(r['reference_reasoning'],r['raw_model_output'],item['gold_overall'])
        assert all(r[k]==v for k,v in audit.items())
        assert r['accepted_as_leakage_free']==(r['parse_success'] and not audit['leaked'] and not audit['other_score_disclosure'])
        assert 1<=r['attempt_index']<=5
        if r['parse_success']:assert parse_reasoning(r['raw_model_output'])==r['reference_reasoning']
    latest={}
    for v in vs:
        item=by_id[v['target_id']]
        r=refs_by_key[v['target_id'],v['candidate_index'],v['reference_attempt_index']]
        assert v['prompt']==verification_prompt(template,item,r['reference_reasoning'])
        assert v['verified']==(v['reconstructed_overall']==item['gold_overall'])
        if v['parse_success']:assert parse_prediction(v['raw_model_output'],False)['predicted_overall']==v['reconstructed_overall']
        assert 1<=v['attempt_index']<=2
        latest[v['target_id'],v['candidate_index']]=v
    expected_pool={(r['target_id'],r['candidate_index']) for r in refs if r['accepted_as_leakage_free'] and
                   latest.get((r['target_id'],r['candidate_index']),{}).get('verified')}
    assert expected_pool=={(r['target_id'],r['candidate_index']) for r in pool}
    assert expected_pool=={(r['target_id'],r['candidate_index']) for r in metrics}
    assert len(metrics)==len(expected_pool)
    assert all(all(math.isfinite(m[k]) for k in ['bleu','rouge1_f1','meteor','bertscore_f1']) for m in metrics)
    assert pd.read_csv(out/'human_review.csv')[REVIEW].isna().all().all()
    assert results.processing_status.isin(['success','failed']).all()
    assert not reference_jobs(config,items,refs)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(config['model']['model_id'],local_files_only=True)
    assert not verify_jobs(config,items,refs,vs,template,tok)
    slot_failures=Counter()
    for tid,target in targets.items():
        slots=[]
        for slot in [1,2,3]:
            attempts=[r for r in refs if r['target_id']==tid and r['candidate_index']==slot]
            accepted=[r for r in attempts if r['accepted_as_leakage_free']]
            v=latest.get((tid,slot))
            reason=(target['failure_reason'] if target['status']=='unavailable' else
                    None if v and v['verified'] else
                    'generation_parse_failed_all_attempts' if attempts and all(not r['parse_success'] for r in attempts) else
                    'no_leakage_free_candidate_within_five_attempts' if not accepted else
                    'verification_parse_failed_after_retry' if v and not v['parse_success'] else
                    'reconstructed_score_did_not_match_actual')
            slots.append(dict(candidate_index=slot,generation_attempts=len(attempts),
                              verified=bool(v and v['verified']),failure_reason=reason,
                              reconstructed_overall=v['reconstructed_overall'] if v else None))
            if reason:slot_failures[reason]+=1
        target['reference_slots']=slots
    write_jsonl(out/'target_results.jsonl',list(targets.values()))
    for pair in pairs:
        with (out/'cases'/(pair['case_id']+'.md')).open('a',encoding='utf-8') as stream:
            stream.write('\n## 参照理由の枠ごとの取得・未取得理由\n\n')
            for label in ['a','b']:
                tid=pair['target_'+label]
                stream.write(f'\n採点者 {label.upper()} ({pair["rater_"+label]})\n\n```json\n')
                stream.write(json.dumps(targets[tid]['reference_slots'],ensure_ascii=False,indent=2)+'\n```\n')
            correction=out/'reference_text_fix/migration.json'
            if correction.exists():
                changed=set(json.loads(correction.read_text(encoding='utf-8'))['affected_targets'])
                if {pair['target_a'],pair['target_b']}&changed:
                    stream.write('\n## 本文版の整合性修正の記録\n\n'
                        '初回の参照生成が元の本文版を用いていたため、共通の匿名化済み本文で該当採点者側のみ再生成・再検証・再評価しました。'
                        '本文が不一致だった旧結果は現行集計に含めず、削除せずに隔離して保存しています。\n\n'
                        '[修正対象と隔離件数](../reference_text_fix/migration.json) / '
                        '[旧参照候補の全試行](../reference_text_fix/reference_candidates.jsonl.quarantined.jsonl) / '
                        '[旧自己検証](../reference_text_fix/self_verification_results.jsonl.quarantined.jsonl)\n')
    metric_df=pd.DataFrame(metrics)
    from src.recsaver.reasoning_eval_metrics import METRICS
    per_target=metric_df.groupby('target_id')[METRICS].agg(['mean','max'])
    per_target.columns=['_'.join(c) for c in per_target.columns]
    per_target.to_csv(out/'reasoning_metrics_by_target.csv')
    metric_summaries=[];rater_summaries=[];score_distributions=[]
    for gap in [3,2]:
        ids={p[k] for p in pairs if p['gap']==gap for k in ['target_a','target_b']}
        available=[dict(target_id=tid,rater_id=by_id[tid]['target_rater'],gold=by_id[tid]['gold_overall'],
                        predicted=predictions[tid]['predicted_overall'],error=predictions[tid]['absolute_error'])
                   for tid in ids if tid in by_id]
        frame=pd.DataFrame(available)
        for rater,g in frame.groupby('rater_id'):
            rater_summaries.append(dict(gap=gap,rater_id=rater,n=len(g),mae=float(g.error.mean()),
                                       mean_signed_error=float((g.predicted-g.gold).mean()),exact_accuracy=float(g.error.eq(0).mean())))
        for series in ['gold','predicted']:
            counts=frame[series].value_counts()
            for score in range(1,6):score_distributions.append(dict(gap=gap,series=series,score=score,count=int(counts.get(score,0))))
        covered=per_target[per_target.index.isin(ids)]
        for column in covered:
            metric_summaries.append(dict(gap=gap,metric=column,n=len(covered),macro_mean=float(covered[column].mean())))
    pd.DataFrame(rater_summaries).to_csv(out/'prediction_error_by_rater.csv',index=False)
    pd.DataFrame(score_distributions).to_csv(out/'prediction_score_distribution.csv',index=False)
    pd.DataFrame(metric_summaries).to_csv(out/'reasoning_metrics_summary.csv',index=False)
    validation=dict(timestamp=datetime.now(timezone.utc).isoformat(),all_checks_passed=True,
                    pairs=len(pairs),targets=len(targets),processed_targets=len(items),
                    unavailable_targets=[k for k,v in targets.items() if v['status']=='unavailable'],
                    predictions_reused=sum(p.get('reused',False) for p in predictions.values()),
                    new_predictions=sum(not p.get('reused',False) for p in predictions.values()),
                    runtime_model=dict(config['model'],gpu_memory_utilization=config['runtime_gpu_memory_utilization']),
                    runtime_batch_size=config['batch_size'],
                    reference_attempts=len(refs),verification_attempts=len(vs),verified_reference_count=len(pool),
                    metric_pairs=len(metrics),reference_attempts_reused=sum(r.get('reused',False) for r in refs),
                    reference_slot_failure_counts=dict(slot_failures),
                    remaining_reference_jobs=0,remaining_verification_jobs=0,human_evaluation='not_performed',
                    duplicate_pair_count=0,all_target_essay_aliases_excluded=True,score_inputs_audited=True,
                    packages={n:importlib.metadata.version(n) for n in ['vllm','torch','transformers','pandas','nltk','bert-score']},
                    model_cache_revision=tok.init_kwargs.get('_commit_hash'),
                    gpu=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],
                                       capture_output=True,text=True).stdout.strip())
    atomic_json(out/'integrity_validation.json',validation)
    md.update(status='completed_with_exclusions' if validation['unavailable_targets'] else 'completed',
              completed_at=validation['timestamp'],validation=validation,runtime_model=validation['runtime_model'])
    atomic_json(out/'metadata.json',md)
    atomic_json(out/'execution_status.json',dict(phase='finished',status=md['status'],timestamp=validation['timestamp']))
    with (out/'report.md').open('a',encoding='utf-8') as stream:
        stream.write('\n## 最終整合性確認\n\n')
        stream.write(f"{len(pairs)}ペアのレポート、{len(items)}対象の処理、全{len(pool)}検証済み参照理由への指標計算を確認しました。\n\n")
        stream.write('[最終監査](integrity_validation.json) / [採点者別予測誤差](prediction_error_by_rater.csv) / '
                     '[スコア分布](prediction_score_distribution.csv) / [理由指標集計](reasoning_metrics_summary.csv)\n')
        stream.write('\n最終監査・枠別の失敗理由も含めた一括再開は `bash scripts/run_human_score_disagreement.sh`。'
                     '段階別に再開した場合は最後に `python scripts/validate_human_score_disagreement.py` を実行してください。\n')
        stream.write('\nチャットの接続から独立して実行する場合は `bash scripts/start_human_disagreement_detached.sh`。'
                     'tmuxセッション `recsaver-human-disagreement`、runner_exit_code.txt、run.logで稼働と終了コードを確認できます。\n')
        stream.write(f"\n運用設定: 生成・検証のスケジューラバッチ数を既存reasoning_eval_largeの10から{config['batch_size']}へ変更しました。"
                     '各リクエストの入力・モデル・サンプリングパラメータ・seedは維持しています。'
                     '途中のメモリ確保量・バッチ数の変更とシリアライズ修正はmetadata.jsonの移行記録および各保存ログを参照してください。\n')
        stream.write('\nseedの区別: 再利用予測はfull_prediction_experimentの基準seed=20260814と既存の条件別規則を保持しています。'
                     '新規予測は追加実験のrequest_seed規則（基準seed=20260916、stage=prediction）、'
                     '参照生成・自己検証はreasoning_eval_largeと同じrequest_seed規則（基準seed=20260916）です。'
                     '新規予測のseed規則は既存全件予測と異なります。実際のリクエストseedは全試行に保存しています。'
                     '再利用判定はモデルID・量子化・文脈長・入力・履歴・生成パラメータの一致を検証し、参照理由はseedも照合しています。'
                     'GPU確保量とバッチ数は運用差として分離しており、異なるバッチ構成でのビット単位の再現は保証しません。\n')
        if (out/'reference_text_fix/migration.json').exists():
            stream.write('\n最終監査の本文照合で、匿名化の版が複数ある3ケース・4採点者側に参照入力の版不一致を検出しました。'
                         '参照生成も予測・自己検証と同じ共通本文を使うよう修正し、該当対象の参照・検証・指標だけを再実行して再監査しました。'
                         '旧30生成試行・11検証試行・11指標は削除せず隔離し、現行集計から除外しました。'
                         '[修正・隔離の記録](reference_text_fix/migration.json)を参照してください。\n')
        stream.write('\nraw行内での暫定3点差15件のうち8件は無効Overallを含み、有効は7件でした。'
                     'raw行内の2点差258件のうち7件は無効Overallを含み、有効251件です。'
                     '同一Filenameの版を対応づけた別行間の採点者ペアが1件加わり、2点差は252ペアとなりました。'
                     '最大4点差の1件も無効Overallを含むため除外しています。\n')
    print(json.dumps(validation,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
