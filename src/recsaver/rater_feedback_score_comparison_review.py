"""CPU-only集計。内容判定は別の明示的なAI確認記録を使用。"""
import json
import re
import numpy as np
import pandas as pd
from . import rater_feedback_score_comparison_mvp as ex


def analyze(first=False):
    config=ex.setup()
    rows=ex.records()
    out=ex.OUT
    targets=pd.read_csv(out/'target_manifest.csv').set_index('target_id')
    main=pd.read_csv(out/'pilot_targets.csv').target_id.tolist()
    old={r['target_id']:r for r in ex.core.read(out/'previous_reflection.jsonl')}
    grounded={r['target_id']:r for r in ex.core.read(out/'previous_grounded.jsonl')}
    frame=ex.core.previous.data()
    ids=ex.FIVE if first else pd.read_csv(out/'execution_order.csv').target_id.tolist()
    rubric=(ex.ROOT/'rubrics/ellipse_overall_rubric.md').read_text(encoding='utf-8')
    report=['# 指定5例の先行確認' if first else '# 全32件の旧版・新版照合資料',
            'AI予備確認用。人手評価未実施。固定30件と追加確認2件を区別。4816:2・3453:1には旧reflection出力が存在しないため、grounded v2と比較し、旧reflectionは未実行と明記。',rubric]
    numeric=[]
    for tid in ids:
        r=rows.get(tid)
        report.extend([f'## {tid} ({"main30" if tid in main else "supplemental2"})',f'Gold（事後）={targets.loc[tid,"gold_overall"]}',
                       '### Target Essay',str(frame.loc[tid,'Text']),'### History K=3',ex.core.format_history(frame.loc[grounded[tid]['history_ids']]),
                       '### 旧grounded v2',json.dumps({k:grounded[tid][k] for k in ['predicted_overall','rater_tendency','reasoning']},ensure_ascii=False,indent=2),
                       '### 旧reflection',json.dumps({k:old[tid][k] for k in ['predicted_overall','rater_tendency','reasoning']},ensure_ascii=False,indent=2) if tid in old else 'この対象の旧reflectionは未実行。今回再生成していない。',
                       '### 新出力',json.dumps(r,ensure_ascii=False,indent=2) if r else '未実行',
                       '### 確認欄','A:4要素 / B:双方scoreと理由 / C:差の具体性 / D:一致説明 / E:参考値の相対性 / F:採点者宛 / G:本文と履歴の根拠: 未評価'])
        if r and r['parse_success']:
            found=re.findall(r'(?<!\d)[1-5](?!\d)',r['comparison_feedback'])
            expected={str(r[k]) for k in ex.SCORE_FIELDS}
            numeric.append({'target_id':tid,'scope':'main30' if tid in main else 'supplemental2',
                            'predicted_overall':r['predicted_overall'],'rubric_reference_overall':r['rubric_reference_overall'],
                            'feedback_numbers':json.dumps(found),'numeric_score_coverage':expected.issubset(found),
                            'extra_numbers_require_review':bool(set(found)-expected)})
    filename='first_five_review.md' if first else 'review_all_32.md'
    (out/filename).write_text('\n\n'.join(report),encoding='utf-8')
    if first:
        print('First-five comparison materials saved')
        return
    pd.DataFrame(numeric).to_csv(out/'feedback_score_audit.csv',index=False)
    valid=[t for t in main if t in rows and rows[t]['parse_success']]
    common=[t for t in valid if old[t]['parse_success']]
    summaries=[]
    for label,source in [('previous_reflection',old),('grounded_v2',grounded),('new_score_comparison',rows)]:
        if common:
            summaries.append({'Condition':label,'N':len(common),**ex.core.previous.metrics(targets.loc[common].gold_overall.to_numpy(),np.array([source[t]['predicted_overall'] for t in common]))})
    pd.DataFrame(summaries).to_csv(out/'prediction_summary.csv',index=False)
    distribution=[{'score':score,'count':sum(rows[t]['rubric_reference_overall']==score for t in valid),'N':len(valid)} for score in range(1,6)]
    pd.DataFrame(distribution).to_csv(out/'rubric_reference_distribution.csv',index=False)
    distances=[abs(rows[t]['predicted_overall']-rows[t]['rubric_reference_overall']) for t in valid]
    attempts=[a for t in main if t in rows for a in rows[t]['attempts']]
    tokens=[a['output_tokens'] for a in attempts]
    summary={'main_requested':30,'main_attempted':sum(t in rows for t in main),'main_schema_valid':len(valid),
             'supplemental_attempted':sum(t in rows for t in ex.FIVE if t not in main),
             'supplemental_schema_valid':sum(t in rows and rows[t]['parse_success'] for t in ex.FIVE if t not in main),
             'equal_scores':distances.count(0),'different_scores':sum(d>0 for d in distances),
             'difference_1':distances.count(1),'difference_2_or_more':sum(d>=2 for d in distances),
             'main_retry_total':sum(rows[t].get('retry_count',0) for t in main if t in rows),
             'main_length_finishes':sum(a['finish_reason']=='length' for a in attempts),
             'main_output_tokens_min_median_max':[min(tokens),float(np.median(tokens)),max(tokens)] if tokens else None,
             'reference_is_not_independent_rubric_only_prediction':True}
    ex.core.save(out/'summary.json',summary)
    text=f'''# 採点者への評価差フィードバック：Prompt再改訂MVP

## 1. 変更・維持した箇所

Promptと最小限の8フィールドschema/parserを変更。モデル・生成設定・seed・本人履歴K=3（本文/Overall/6 Traits）・Rubric・対象Essay・Gold除外は継承。
同一モデルの1段階生成で2スコアを出力。Rubric-onlyの別実行、比較LLM、Profile事前生成はない。
参考値は履歴を閲覧済みの同一LLMによる解釈であり、履歴から独立した予測でも絶対的正解でもない。
既存と同じJSON失敗時retry上限1を継承し、追加の推論ステージは導入していない。
固定30件を維持し、ユーザー承認により4816:2と3453:1を追加確認用2件として別集計。先に指定5例を実行・確認し、その後残り27件を実行。
指定されたoutputs/rater_feedback_prompt_mvp/は存在せず、実在する旧版outputs/rater_tendency_reflection_mvp_30/を使用。

## 2. 新Prompt全文

```text
{ex.PROMPT.read_text(encoding='utf-8')}
```

## 3. 固定30件の実行結果

```json
{json.dumps(summary,ensure_ascii=False,indent=2)}
```

```
{pd.DataFrame(summaries).to_csv(index=False)}
```
30件の結果を統計的性能改善の証明と解釈しない。

## 4. 2つのOverallの比較

summary.jsonとrubric_reference_distribution.csv。参考スコアとGoldの比較は実施せず、Goldは生成後の条件付き予測評価と資料化のみ。

## 5–7. 差異・一致・問題例

review_all_32.mdに元Essay・履歴・Rubric・前後出力を併記。first_five_review.mdに先行5件を保存。
内容妥当性とフィールド出力率を区別する。独立した人手評価は未実施。追加のAI内容確認はcontent_review.csvとcontent_assessment.mdに記録する。

## 8. 発表候補

指定5件の未編集比較フィードバックと日本語訳はpresentation_examples_bilingual.mdに保存予定。旧reflectionがない追加2件は旧grounded v2との比較に限定。

## 9. Integrity audit

integrity_audit.csv: 32件の入力同一性・Gold改変不変性・同一Essay排除を検査。
experiment_config.json: 旧Prompt/Config/Predictionを含む入力SHA256。実行後に再照合。
feedback_score_audit.csv: フィードバック内の数字を検出。ラベルへの対応や内容の一致はcontent_review.csvでも確認。
参考値はモデルraw出力からparse。PromptにはGold/Target Traitsが入力されず、Goldを出力フィールドにコピーする処理もない。
生成値がGoldと偶然一致することとコピーは異なる。Gold非混入は一致率ではなく入力経路と改変不変性で検査。
git_status_before/after.txtを保存。

## 10. 共通995件への拡張に必要な作業

今回のPilot後は停止。承認前に拡張しない。
既存grounded v2の有効995対象を固定し、同じ履歴・本文・RubricをSHA256照合。Prompt/schema/configを凍結してcheckpoint再開を維持。
Pilotの同一条件出力のみ再利用し、失敗件数・除外理由を保持。2スコアと文章の整合監査と内容評価を拡張する。
Rubric参考値は独立したRubric-only条件と呼ばず、因果的な履歴効果や採点者の偏りを断定しない。
実装根拠: rater_feedback_score_comparison_mvp.setup（入力固定/監査）、parse（8項目検査）、run（既存方式の生成）; rater_feedback_score_comparison_review.analyze（CPU集計）。
'''
    (out/'report.md').write_text(text,encoding='utf-8')
    ex.core.verify()
    ex.core.status('git_status_after')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    analyze('--first5' in sys.argv)
