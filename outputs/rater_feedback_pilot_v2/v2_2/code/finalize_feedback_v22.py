"""実生成の原文と開発レビューを別々に保存し、完了した範囲を明記する。"""
import collections
import json
import runpy
import shutil
from pathlib import Path
from src.recsaver.rater_feedback_development_v21 import ROOT,load,save,sha,now,IDS


def main():
    out=ROOT/'outputs/rater_feedback_pilot_v2/v2_2';prior=ROOT/'outputs/rater_feedback_pilot_v2/v2_1'
    result=load(out/'three_results.json');audit=load(out/'three_audit.json');review=load(out/'three_development_review.json')
    assert review['result_sha256']==sha(out/'three_results.json')
    save(out/'development_review.json',review)
    # コピーした旧1答案比較表も別名で残す。
    for suffix in ['json','md']:
        path=out/f'old_new_comparison.{suffix}'
        backup=out/f'one_old_new_comparison.{suffix}'
        if path.exists() and not backup.exists(): shutil.copy2(path,backup)
    comparison=dict(timestamp=now(),scope='three',reviewer=review['reviewer'],columns=['観点','旧出力','修正版の実出力','判断と限界'],rows=review['comparison_rows'])
    save(out/'old_new_comparison.json',comparison)
    def cell(v): return str(v).replace('|','\\|').replace('\n',' ')
    (out/'old_new_comparison.md').write_text('# 新旧の内容比較（固定3答案・開発レビュー）\n\n独立した人間評価ではない。改善だけでなく未達・失敗も含む。\n\n|観点|旧出力|修正版の実出力|判断と限界|\n|---|---|---|---|\n'+'\n'.join('|'+'|'.join(map(cell,row))+'|' for row in comparison['rows'])+'\n',encoding='utf-8')
    save(out/'execution_failures.json',dict(timestamp=now(),retained=[
        dict(stage='2.1 downstream',kind='context_overflow',record='../v2_1/three_audit.json',events=load(prior/'three_audit.json')['context_overflows'],action='No truncation or model call. Preserved and resumed changed downstream serialization in 2.2.'),
        dict(stage='2.2 CPU preflight first design',kind='insufficient_compaction',record='../v2_1/compaction_preflight.json',action='No model call. Evidence-only interning still exceeded context; replaced with lossless repeated-value interning.'),
        dict(stage='2.2 bootstrap',kind='ValueError_relative_path',record='../v2_2_attempt_01.log',action='No model call or downstream cache existed. Resolved __file__ before relative_to; retained traceback and upstream files.'),
        dict(stage='model format retries',record='calls.jsonl',action='All original outputs/errors retained, including reused upstream failed attempts; existing one-retry cap retained.')]))
    runpy.run_path(str(ROOT/'scripts/report_feedback_development_v22.py'),run_name='__main__')
    calls=[json.loads(line) for line in (out/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    counts={s:dict(success=sum(c['stage']==s and c['status']=='ok' for c in calls),failed_attempts=sum(c['stage']==s and c['status']!='ok' for c in calls)) for s in ['generate','verify','ground','merge','integrate','compare','text']}
    save(out/'completion.json',dict(timestamp=now(),execution_revision='2.2',semantic_pipeline_version=result['version'],condition='B',rater='rater_7',target_ids=IDS,
        summary=load(out/'three_summary.json'),audit=audit,stage_attempt_counts_including_reused=counts,
        all_requested_stages_executed=bool(result['synthesis'] is not None and all(v is not None for v in result['comparisons'].values()) and all(v is not None for v in result['texts'].values())),
        raw_output_semantic_acceptance=review['usable_with_real_raters'],quality_status='Development run complete; semantic limitations recorded, not a validated rater feedback product.',
        no_additional_candidates=True,no_replacement=True,no_27_expansion=True,no_commit_or_push=True))
    save(out/'feedback.json',dict(timestamp=now(),execution_revision='2.2',scope='three',rater='rater_7',target_ids=IDS,texts=result['texts'],
        quality_status='unmodified model output; see three_development_review.json; not accepted for real-rater use',lineage='sentence_lineage.json'))
    save(out/'resume_state.json',dict(timestamp=now(),status='completed_development_execution',requested_scope='three',completed_target_ids=IDS,pending_generation_candidates=0,
        all_stages_executed=load(out/'completion.json')['all_requested_stages_executed'],quality_review='three_development_review.json',next_command=None,
        upstream_reused_records=len(load(out/'three_resume_cache_before.json')['records'])))
    for p in [prior/'compaction_preflight.json',prior/'compaction_preflight_v22.json',prior/'three_summary.json']:
        shutil.copy2(p,out/('previous_'+p.name))
    log=ROOT/'outputs/rater_feedback_pilot_v2/v2_2_attempt_01.log'
    shutil.copy2(log,out/'execution.log')
    note='''\n\n## 今回の最終状態（実行修正版2.2）\n\n指定rater_7・B条件・1514:1 / 1868:1 / 4902:1の開発実行。上流は版2.1と同一の入力・プロンプト・生成設定・成功済み結果を使用し、2.2では重複入力の参照化だけを修正した。プロンプト版6および意味仕様2.1の表記は引継ぎ条件を示し、実行修正版は2.2である。参照化前の完全payloadはstage_inputs_expanded/、実payloadはstage_inputs/、毎回の完全復元検査はcompaction_checks.jsonl。\n\n現在読むべき正確なパス:\n- `outputs/rater_feedback_pilot_v2/v2_2/report.md`\n- `outputs/rater_feedback_pilot_v2/v2_2/assessment.md`\n\n[3答案の開発レビュー](three_development_review.json)・[厳密な参照監査](three_audit.json)・[完了範囲と段階別件数](completion.json)・[短い生成原文](feedback.md)・[機械可読の生成本文](feedback.json)・[修正と引継ぎ条件](revision_note.json)・[保持した失敗と修正履歴](execution_failures.json)。\n\n今後のプロンプト改善はassessment.md末尾。今回の内容点検はCodexによる開発レビューであり、独立した人間評価でも有効性・バイアス是正効果の検証でもない。原出力を内容レビューに合わせて書き換えてはいない。\n'''
    with (out/'README.md').open('a',encoding='utf-8') as f:f.write(note)
    extra='\n\n## 固定3答案の内容点検と次回の改善案\n\n'+review['narrative']+'\n\n'+ '\n'.join('- '+x for x in review['prompt_improvements'])+'\n\n詳細な例・主張ID・判定の限界はthree_development_review.json。生成成功と内容の正しさは別であり、採点者への実用可否は未達。\n'
    for name in ['report.md','assessment.md']:
        with (out/name).open('a',encoding='utf-8') as f:f.write(extra)
    summary=load(out/'three_summary.json')
    overview=['# 固定3答案の予備検証：実行修正版2.2','',
        '**実処理は完了。生成された採点者向け本文は内容上の未達があり、完成稿としては採用しない。**','',
        'rater_7・B条件のみ。対象本文・本人Overall/6Trait・各履歴3件は旧inputs、wide、rawの実物と一致（input_checks.json）。入力はinputs.json、元のパスとハッシュはresolved_config.json、対象・履歴IDはselection.json/input_checks.json。','',
        '|条件|対象答案|生成成功|候補終端失敗|自己検証成功・一致|統合に使用したユニーク答案|',
        '|---|---|---|---|---|---|',
        f"|Bのみ|3|{summary['generated']}/6|{6-summary['generated']}|6/6・6/6|3|",'',
        '生成の初回形式失敗1件、証拠点検の初回形式失敗4件は既存の各1回の再試行で成功。これらの失敗原出力を保持した。得点不一致による追加生成はない。版2.1の文脈上限超過3件と版2.2の準備エラーもexecution_failures.jsonに記録。','',
        '|対象答案|Overall|Cohesion|Syntax|Vocabulary|Phraseology|Grammar|Conventions|候補成功・自己検証一致|統合に入った主張|',
        '|---|---|---|---|---|---|---|---|---|---|']
    for item in load(out/'inputs.json'):
        tid=item['target_id'];t=item['target'];n=sum(c['eligible_for_integration'] for ca in result['candidates'] if ca['target_id']==tid for c in ca['original_reason']['claims'])
        overview.append('|'+ '|'.join(map(str,[tid,t['overall'],*[t['traits'][k] for k in ['Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']],'2/2・2/2',n]))+'|')
    overview+=['','モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、seed=20261115、temperature=0.2、top_p=0.8、各2候補、形式再試行1回。生成上限等もv1.6を維持。全段階の実seed・生成時刻・raw出力はcalls.jsonl。','',
        '1答案の先行実行は版2.1のone_results.json/one_review.jsonで完了。その後の3答案は同じ意味仕様で実行し、参照化が変わる下流だけを版2.2で新規生成した。候補や対象は差し替えていない。','','---','']
    report=out/'report.md';report.write_text('\n'.join(overview)+report.read_text(encoding='utf-8'),encoding='utf-8')
    readme=out/'README.md';readme.write_text(readme.read_text(encoding='utf-8').replace('（版2.1）','（実行修正版2.2、意味仕様2.1）',1),encoding='utf-8')
    script_paths=[Path(__file__).resolve(),ROOT/'scripts/audit_feedback_v22_three.py',ROOT/'scripts/build_feedback_v22_reporting.py',ROOT/'scripts/build_feedback_v22_engine.py',ROOT/'scripts/check_feedback_v22_context.py',ROOT/'scripts/launch_feedback_v22.py',ROOT/'scripts/save_feedback_v22_review.py']
    for p in script_paths: shutil.copy2(p,out/'code'/p.name)
    save(out/'finalization_code_manifest.json',{str(p.relative_to(ROOT)):sha(p) for p in script_paths})
    assert audit['integration_succeeded'] and not audit['context_overflows']
    print(json.dumps(dict(summary=load(out/'three_summary.json'),stage_attempts=counts,report=str(out/'report.md')),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
