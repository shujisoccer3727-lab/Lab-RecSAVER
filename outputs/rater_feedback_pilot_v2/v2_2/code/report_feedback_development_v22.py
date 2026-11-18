"""生成原本を変えずに監査、短い本文、監査対応表を別表示する。"""
import collections
import json
import re
import shutil
from pathlib import Path
from src.recsaver.rater_feedback_development_v21 import ROOT,CONFIG,load,save,sha,now,IDS,masked_reason
from src.recsaver.rater_feedback_pilot_v2 import LEAK_PATTERNS
from src.recsaver.rater_feedback_development_v21 import DIRECT_SCORE_PATTERN
LEAK_PATTERNS=[*LEAK_PATTERNS,('unseparated_score_label',DIRECT_SCORE_PATTERN)]


CONFIG=ROOT/'configs/rater_feedback_development_v22.json'


def cell(value):
    return str(value).replace('|','\\|').replace('\n',' ')


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir']
    cause=load(out/'cause_analysis.json')
    trace=['# 旧版：個別主張から最終文章までの対応','',
        '最終文章の文単位IDは旧版に存在しないため、確定できない対応を不明として残す。', '',
        '|対象・候補・主張|元の個別判断|根拠span|自己検証一致|意味点検|統合の候補|公式条件|④⑤|最終文への正確な対応|',
        '|---|---|---|---|---|---|---|---|---|']
    for x in cause['claim_lineage']:
        c=x['original_claim'];review=c.get('grounding_review')
        trace.append('|'+'|'.join(cell(v) for v in [x['claim_id'],c['feature'],c['span_ids'],x['accepted'],
            (review or {}).get('support','未点検'),[p['pattern_id'] for p in x['pattern_nodes']],x['official_condition_ids'],
            [dict(issue=i['issue_id'],comparison=i['rubric_based_proposal'],next_action=i['next_action']) for i in x['comparison_nodes']],
            '不明（旧版は集約IDのみ）'])+'|')
    trace += ['','## 最終文章の主張ごとの棚卸し','',
        '|要素・文|旧版の文章|付与された候補・対象ID|原主張との対応|','|---|---|---|---|']
    for x in cause['final_sentence_inventory']:
        trace.append('|'+'|'.join(cell(v) for v in [f"{x['element']}-{x['sentence']}",x['text'],
            dict(patterns=x['available_pattern_ids'],targets=x['available_target_ids']),'不明：後付けの集約IDから文単位の対応は確定不可'])+'|')
    (out/'old_claim_lineage.md').write_text('\n'.join(trace)+'\n',encoding='utf-8')
    phase='three' if (out/'three_results.json').exists() else 'one'
    snapshot=load(out/f'{phase}_results.json') if (out/f'{phase}_results.json').exists() else None
    resolved=load(out/'resolved_config.json')
    source_changed=[p for p,h in resolved['source_sha256'].items() if sha(ROOT/p)!=h]
    old_changed=[p for p,h in load(out/'old_output_hashes.json').items() if sha(ROOT/p)!=h]
    errors=[];verification_checks=[]
    for p in (out/'stage_inputs'/'verify').glob('*.json'):
        x=load(p)
        assert set(x['target'])=={'essay_id','text'}
        assert all(set(h)=={'essay_id','text','overall'} for h in x['history'])
        assert all('traits' not in h and 'condition_ids' not in h for h in [x['target'],*x['history']])
        prose=[x['masked_reason'][k] for k in ['rationale','unexplained']]
        prose += [c[k] for c in x['masked_reason']['claims'] for k in ['feature','evaluation','overall_relation','trait_relation','limits']]
        hits=[dict(pattern=kind,text=m.group()) for text in prose for kind,pat in LEAK_PATTERNS for m in re.finditer(pat,text,re.I)]
        assert not hits,(p,hits)
        verification_checks.append(dict(path=p.relative_to(out).as_posix(),target_fields_exact=True,free_text_direct_scores_absent=True))
    calls=[json.loads(s) for s in (out/'calls.jsonl').read_text(encoding='utf-8').splitlines()] if (out/'calls.jsonl').exists() else []
    stages={stage:dict(calls=sum(c['stage']==stage for c in calls),success=sum(c['stage']==stage and c['status']=='ok' for c in calls),
        failed_attempts=sum(c['stage']==stage and c['status']!='ok' for c in calls)) for stage in cfg['max_tokens']}
    failures=[{k:c.get(k) for k in ['stage','key','attempt','status','error','raw_output']} for c in calls if c['status']!='ok']
    citations=0;sentences=0;lineage=[]
    if snapshot:
        items={i['target_id']:i for i in load(out/'inputs.json')}
        catalog=load(out/'conditions.json')
        for comparison in snapshot['comparisons'].values():
            for issue in (comparison or {}).get('relationships',[]):
                for span in issue['citations']:
                    assert items[issue['target_id']]['target']['text'][span['start']:span['end']]==span['text'];citations+=1
                assert issue['official_conditions']==[catalog[c] for c in issue['condition_ids']]
        for key,text in snapshot['texts'].items():
            if text is None: continue
            p=snapshot['text_payloads'][key]
            for s in text['sentences']:
                sentences+=1
                lineage.append(dict(topic_key=key,**s,
                    source_claims=[p['claims'][c] for c in s['claim_ids']],
                    issues=[p['issues'][i] for i in s['issue_ids']],
                    official_conditions=[p['conditions'][c] for c in s['condition_ids']]))
    assert not source_changed and not old_changed,(source_changed,old_changed)
    audit=dict(timestamp=now(),phase=phase,source_files_unchanged=True,all_old_output_hashes_unchanged=True,
        verification_payloads=verification_checks,exact_citations=citations,final_sentences_with_lineage=sentences,
        stage_calls=stages,failed_attempts=failures,
        limitation='Mechanical checks do not establish semantic correctness; Codex review is development review, not independent human evaluation.')
    save(out/'audit.json',audit);save(out/'sentence_lineage.json',lineage)
    review=load(out/'development_review.json') if (out/'development_review.json').exists() else dict(status='No new-output content review yet',findings=[])
    summary=load(out/f'{phase}_summary.json') if snapshot else dict(
        status=load(out/'status.json'),generated_candidates=0,verified_candidates=0,
        evidence_reviewed_claims=0,integrated_raters=0,comparison_outputs=0,feedback_texts=0,
        interruption='one_attempt_01.log ended at 11:38 during model loading; prior process absent; cause unknown',
        pending='New outputs and semantic review of the one-case run, then the fixed three-case run')
    runtime_status=load(out/'status.json')
    report=['# 採点者フィードバック修正版：開発3答案','','固定対象: rater_7、1514:1・1868:1・4902:1、B条件、履歴各3件・2候補。最終評価用標本ではない。', '',
        '## 現在の実行状況','', '```json',json.dumps(runtime_status,ensure_ascii=False,indent=2),'```','',
        '## 実施範囲','', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```','',
        '成功件数はJSONと参照の検査通過を表し、5要素の意味的充足や採点者への提示可否の認定ではない。内容上の未達は開発レビューに分けて記録する。','',
        '## 採点者向けの短い本文','']
    short=[]
    if snapshot:
        for key,text in snapshot['texts'].items():
            if text is None:
                report += [f'### {key}','','文章化は終端失敗。原出力を保持。',''];continue
            body='\n\n'.join(s['text'] for s in text['sentences'])
            report += [f'### {key}','',''+body,'']
            short += [f'## {key}','',body,'']
    if not short:
        short=['生成済みの採点者向け本文はまだありません。実行状態はstatus.json、ログはone_attempt_01.logを参照してください。']
        report += short+['']
    report += ['## 証拠・公式条件・④⑤の監査用対応表','',
        '|論点|要素|文章|個別主張|対象答案|比較論点|公式条件|',
        '|---|---|---|---|---|---|---|']
    for x in lineage:
        report.append('|'+'|'.join(cell(x[k]) for k in ['topic_key','element','text','claim_ids','source_target_ids','issue_ids','condition_ids'])+'|')
    if snapshot:
        report += ['','## 監査用原文・位置・基準全文','']
        evidence={e['span_id']:e for x in lineage for c in x['source_claims'] for e in c['evidence']}
        evidence.update({e['span_id']:e for x in lineage for i in x['issues'] for e in i['citations']})
        for sid,e in evidence.items():
            report += [f"- {sid} [{e['start']}:{e['end']}]：{json.dumps(e['text'],ensure_ascii=False)}"]
        criteria={c['condition_id']:c for x in lineage for c in x['official_conditions']}
        for cid,c in criteria.items():
            report += [f"- {cid}（{c['role']}）：{c['text']} 親段階全文：{c['parent_text']}"]
        report += ['','## 個別理由・候補整理・統合','',
            '```json',json.dumps(dict(groups=snapshot['essay_groups'],synthesis=snapshot['synthesis']),ensure_ascii=False,indent=2),'```']
    report += ['','## 新旧比較と残る問題','',
        '[原因調査表](cause_analysis.md)、[開発レビュー](development_review.json)、[新旧比較表](old_new_comparison.md)。', '',
        'Codexの点検は開発時のレビューであり、独立した人間評価ではない。研究上の制約はこの監査欄に分離し、短い本文で反復しない。','']
    (out/'feedback.md').write_text('開発用の生成原文。内容レビューで未達が残っており、採点者への提示用に妥当性を確認した完成稿ではない。\n\n'+'\n'.join(short),encoding='utf-8')
    (out/'report.md').write_text('\n'.join(report),encoding='utf-8')
    assessment=['# 修正版の所見','','## 完了範囲','', '```json',json.dumps(summary,ensure_ascii=False,indent=2),'```','',
        '## 開発レビュー','', '```json',json.dumps(review,ensure_ascii=False,indent=2),'```','',
        '## 機械検査','', '```json',json.dumps({k:v for k,v in audit.items() if k not in ['failed_attempts']},ensure_ascii=False,indent=2),'```','',
        '## 失敗記録','', '```json',json.dumps([{k:v for k,v in f.items() if k!='raw_output'} for f in failures],ensure_ascii=False,indent=2),'```','',
        '原出力はcalls.jsonl、各段階入力はstage_inputs、終端結果はstages。得点不一致を理由とした追加生成はしない。設定・コード・プロンプトの変更は別版にする。', '',
        '共通する文章特徴と評価判断候補は別に保存。3答案から共通評価が確定できなくても対象を増やさない。観点別基準だけによる局所判断はOverall全体を説明したと扱わない。', '',
        '旧版の引用符誤認は④で初めて確認。修正版で同じ誤りが再発しないことと、あらゆる引用判断が正しいことは別。点検対象にならなかった論点は未確認とする。', '',
        '公式ルーブリックの保存済み転記を用いた。元DOCXの独立確認はできていない。本人の真の理由、採点者固有性、実用性、有効性、バイアス是正効果は未検証。', '']
    (out/'assessment.md').write_text('\n'.join(assessment),encoding='utf-8')
    readme=f'''# 採点者フィードバック開発3答案・B条件（版2.1）

保存済み結果の範囲: **{phase}**。現在の実行状態: **{runtime_status['status']} / {runtime_status.get('scope','unknown')}**。
oneは1514:1のみであり、固定3答案の結果とは区別する。

現在読むファイル:
- `outputs/rater_feedback_pilot_v2/v2_2/report.md` — [本文・対応表](report.md)
- `outputs/rater_feedback_pilot_v2/v2_2/assessment.md` — [所見・失敗](assessment.md)
- [短いフィードバック](feedback.md)
- [原因調査](cause_analysis.md) / [旧主張の対応表](old_claim_lineage.md) / [全来歴JSON](cause_analysis.json)
- [新旧比較](old_new_comparison.md) / [開発レビュー](development_review.json)
- [機械監査](audit.json) / [文章ごとの内部参照](sentence_lineage.json)

指定3答案のみ。27答案への展開・最終評価設計・commit/pushはしない。旧出力は読み取り専用でハッシュ照合した。
入力・元データ照合はinputs.json/input_checks.json、選択はselection.json、設定とソースハッシュはresolved_config.json、コード・全プロンプトはcode/に保存。
生成原本・マスク・検証payload・中間結果・原出力・失敗はstage_inputs/、masks/、stages/、calls.jsonlに保持。生成設定はv1.6を維持、JSON制約は既存outlines、変更点はrevision_note.json。

再開コマンド（GPUが空いている場合のみ。既存処理は停止しない）:
```bash
# 上流は版2.1の同一入力・成功済み結果を再利用
# 1答案の内容点検とone_review.jsonの保存後:
python -c "import runpy; runpy.run_path('scripts/resume_feedback_v22.py',run_name='__main__')"
python -c "import runpy; runpy.run_path('scripts/report_feedback_development_v22.py',run_name='__main__')"
```
同一fingerprintの成功結果のみ再利用。得点不一致・終端失敗を追加候補生成で埋めない。共通傾向がなければ未確定として報告する。
'''
    (out/'README.md').write_text(readme,encoding='utf-8')
    archive=out/'code'
    paths=[Path(__file__),ROOT/'scripts/investigate_feedback_v2_cases.py',ROOT/'scripts/check_feedback_development_guidance_v21.py',ROOT/'scripts/build_feedback_development_engine.py',
        ROOT/'scripts/create_feedback_development_v21.py',ROOT/'scripts/build_feedback_v21_tools.py',
        ROOT/'scripts/launch_feedback_development_v21.py',ROOT/'scripts/wait_feedback_v21_three.py',
        ROOT/'scripts/save_feedback_v20_review.py',ROOT/'scripts/save_feedback_v21_one_review.py',
        ROOT/'scripts/compare_feedback_v21_one.py',ROOT/'scripts/prepare_feedback_v21_pending.py']
    for p in paths: shutil.copy2(p,archive/p.name)
    save(out/'reporting_code_manifest.json',{p.name:sha(archive/p.name) for p in paths})
    print(json.dumps(dict(phase=phase,model_calls=len(calls),exact_citations=citations,final_sentences=sentences,old_outputs_unchanged=True),ensure_ascii=False))


if __name__=='__main__': main()
