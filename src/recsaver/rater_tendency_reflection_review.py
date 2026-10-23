"""CPU集計と全30件の比較資料。表現検出は正しさの評価ではない。"""
import json
import re
import numpy as np
import pandas as pd
from . import rater_tendency_reflection_mvp as experiment


def review():
    experiment.setup()
    core, out = experiment.core, experiment.OUT
    config = core.verify()
    rows = core.records()
    targets = pd.read_csv(out/'pilot_targets.csv').set_index('target_id')
    old = {r['target_id']:r for r in core.read(out/'grounded_v2_baseline.jsonl')}
    common = sorted(t for t,r in rows.items() if r['parse_success'] and old[t]['parse_success'])
    summaries=[]
    if common:
        gold=targets.loc[common].gold_overall.to_numpy()
        for label, source in [('grounded_v2',old),('reflection',rows)]:
            summaries.append({'Condition':label,'N':len(common),**core.previous.metrics(gold,np.array([source[t]['predicted_overall'] for t in common]))})
    pd.DataFrame(summaries).to_csv(out/'grounded_v2_comparison.csv',index=False)
    frame=core.previous.data()
    artifacts=['# 全30件の旧版・振り返り版比較','人手評価は未実施。英文は無編集。Rubric、Essay、履歴、Gold、双方の出力を併記する。',
               (core.ROOT/'rubrics/ellipse_overall_rubric.md').read_text(encoding='utf-8')]
    checks=[]
    for tid in targets.index:
        r=rows.get(tid)
        artifacts.extend([f'## {tid}',f'Gold={targets.loc[tid,"gold_overall"]}', '### Target Essay',str(frame.loc[tid,'Text']),
                          '### History K=3',core.format_history(frame.loc[old[tid]['history_ids']]),
                          '### grounded v2',json.dumps({k:old[tid][k] for k in ['predicted_overall','rater_tendency','reasoning']},ensure_ascii=False,indent=2),
                          '### reflection input and output',json.dumps(r,ensure_ascii=False,indent=2) if r else '未実行',
                          '### 人手確認欄','履歴根拠 / Essay根拠 / Rubricとの関係 / 不確実性の整合性 / 振り返りの具体性 / 偏り等の断定有無: 未評価'])
        if r and r['parse_success']:
            text=' '.join(r['reasoning'].values())
            checks.append({'target_id':tid,'rubric_mention':bool(re.search('rubric',text,re.I)),
                'reflection_wording':bool(re.search(r'consider|reflect|review|recheck|check|revisit|ensure|you may|you might',r['reasoning']['scoring_explanation'],re.I)),
                'no_discrepancy_wording':bool(re.search(r'no clear discrepancy|no discrepancy|no clear deviation',text,re.I)),
                'bias_or_fairness_wording_for_review':bool(re.search(r'biased|unfair|bias',text,re.I))})
    pd.DataFrame(checks).to_csv(out/'reflection_structure_checks.csv',index=False)
    (out/'review_all_30.md').write_text('\n\n'.join(artifacts),encoding='utf-8')
    attempts=[a for r in rows.values() for a in r['attempts']]
    tokens=[a['output_tokens'] for a in attempts]
    summary={'attempted':len(rows),'schema_valid':sum(r['parse_success'] for r in rows.values()),
             'retries':sum(r.get('retry_count',0) for r in rows.values()),
             'length_finish_attempts':sum(a['finish_reason']=='length' for a in attempts),
             'output_tokens_min_median_max':[min(tokens),float(np.median(tokens)),max(tokens)] if tokens else None,
             'score_changes_vs_grounded_v2':sum(rows[t]['predicted_overall']!=old[t]['predicted_overall'] for t in common),
             'wording_presence_counts':{k:sum(r[k] for r in checks) for k in checks[0] if k!='target_id'} if checks else {}}
    core.save(out/'reflection_summary.json',summary)
    text=f'''# ルーブリック比較・振り返り情報のPrompt拡張MVP

同じ固定30件でgrounded v2と比較。変更はPrompt本文と出力先だけ。
既存のrun/render/parse/VLLMGenerator、JSON構造、モデル、入力K=3、Overallと6 Traits、履歴ID、Rubric、対象Essay、Gold除外を維持。
temperature=.2、top_p=.8、max_tokens=768、max_model_len=8192、generation seedも同じ。
生成された1つのJSONのtendency_connectionにRubricとの関係、scoring_explanationに建設的な振り返りを求めた。
別スコア・別LLM・Profile事前生成・追加推論ステージはなし。既存と同じJSON失敗時retry上限1のみ維持。

## 実行結果

```json
{json.dumps(summary,ensure_ascii=False,indent=2)}
```

grounded_v2_comparison.csv:
```
{pd.DataFrame(summaries).to_csv(index=False)}
```

## 読み方

reflection_structure_checks.csvは表現の有無の機械検査であり、内容の正しさや有用性を保証しない。
全30件の比較と人手評価欄はreview_all_30.md。人手評価は未実施。
小規模な同一対象での出力変更の影響を確認したもので、採点者の真の思考過程や偏り、振り返りによる改善を実証しない。

## 根拠と再現

Prompt: prompts/en/rater_tendency_joint_prediction_reflection_mvp.txt。
実装: rater_tendency_reflection_mvp.setup/main（既存core.runを呼ぶ）。
integrity_audit.csvは全30件の入力部分同一性とGold改変不変性。experiment_config.jsonのSHA256を実行後も確認。
既存Prompt・Config・Predictionは上書きせず、比較に既存結果を再利用。
再開: python -m src.recsaver.rater_tendency_reflection_mvp launch。
'''
    (out/'report.md').write_text(text,encoding='utf-8')
    core.status('git_status_after')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    review()
