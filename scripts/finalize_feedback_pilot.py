"""完了後の実行config・コード・検査・修正履歴を集約する。"""
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import now,save,read,sha


def main():
    out=ROOT/'outputs/rater_feedback_pilot'
    cfg=json.loads((ROOT/'configs/rater_feedback_pilot.json').read_text())
    resolved=json.loads((out/'resolved_config.json').read_text())
    archive=out/'revisions'/'initial_prepared_files'
    archive.mkdir(parents=True,exist_ok=True)
    current=[ROOT/'src/recsaver/rater_feedback_pilot.py',ROOT/'configs/rater_feedback_pilot.json',
             *sorted((ROOT/'prompts/en').glob('rater_feedback_pilot_*.txt'))]
    for path in current:
        prior=out/path.name
        if prior.exists() and not (archive/path.name).exists():
            shutil.copy2(prior,archive/path.name)
        shutil.copy2(path,prior)
    if not (archive/'resolved_config.json').exists():
        shutil.copy2(out/'resolved_config.json',archive/'resolved_config.json')
    resolved.update(pilot_config=cfg,finalized_at=now(),
                    runtime_model=dict(resolved['source_config']['model'],max_model_len=cfg['runtime_model_max_len']),
                    source_code_sha256={str(p.relative_to(ROOT)):sha(p) for p in current},
                    context_policy='Initial A calls: 8192. B context check failed without truncation. Reused A; later calls: 16384. Actual model and params saved per call.')
    resolved['pilot_input_sha256']={name:sha(out/name) for name in ['inputs.json','selection.json','rubric.json','semantic_review.json','tendency_review.json','content_review.json','pilot_review.json'] if (out/name).exists()}
    save(out/'resolved_config.json',resolved)
    calls=read(out/'calls.jsonl')
    history=json.loads((out/'execution_history.json').read_text())
    history['resumption_and_revisions']=dict(timestamp=now(),
        events=['2026-11-15: user requested resume; free GPU confirmed; Qwen used, no Gemma access',
                'A completed for first 10 targets; 7 obvious semantic insufficiencies conservatively downgraded; raw labels retained',
                'B exceeded 8192 context (9397 prompt tokens on logged retry); no input truncation; expanded runtime context to 16384',
                'First C lacked concrete anchors and element-level references; all first-pass outputs archived in revisions/first_pass',
                'C v2 one-shot failed twice; no final result accepted from it. Raw responses retained.',
                'Final C split into C_relation and C_text. Actual target/score, observed and adjacent official descriptions, element links and exact quotations are deterministically assembled; only explanatory prose is generated.',
                'Windows BOM in pilot review JSON caused a controller error; status archived, UTF-8-sig reading added; successful generations reused.',
                'Missing evidence reclassified from non-applicable to unassessed, with original model classification retained'],
        failed_calls=[{k:c.get(k) for k in ['timestamp','stage','key','attempt','error','prompt_tokens']} for c in calls if c['status']=='failed'])
    save(out/'execution_history.json',history)
    history['resumption_and_revisions']['events'].append('Rater 4 B invented an unsupported score cap; removed in a transparent synthesis review, original B and propagated C_text archived, only affected C_text regenerated from a clean synthesis input.')
    save(out/'execution_history.json',history)
    code_dir=out/'code'
    code_dir.mkdir(exist_ok=True)
    helpers=sorted((ROOT/'scripts').glob('*feedback_pilot*.py'))
    for helper in helpers:
        shutil.copy2(helper,code_dir/helper.name)
    save(code_dir/'manifest.json',dict(timestamp=now(),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in helpers}))
    guard='以下は観測Overallを条件として生成された参照推論から推定された傾向の候補であり、採点者本人の真の思考や評価の重みを示すものではない。2件以上の支持だけでは妥当性は証明されない。'
    quality=json.loads((out/'content_review.json').read_text()) if (out/'content_review.json').exists() else {}
    for path in (out/'results').glob('*.json'):
        result=json.loads(path.read_text())
        element=result['C']['elements'][1]
        if not element['text'].startswith(guard):
            element['model_text_before_scope_guard']=element['text']
            element['text']=guard+'\n\n'+element['text']
        result['C']['scope_guard']='Programmatically added source-conditioning and candidate-status caveat; raw model text retained in C_text and calls.jsonl'
        result['C']['quality_status']=quality.get('status','not_independently_validated')
        result['C']['content_review']=[q for q in quality.get('relations',[]) if q['rater_id']==result['rater_id']]
        save(path,result)
        cpath=out/'C'/path.name
        cache=json.loads(cpath.read_text())
        cache['result']=result['C']
        save(cpath,cache)
    tests=subprocess.run([sys.executable,'-m','unittest','tests.test_rater_feedback_pilot','-v'],cwd=ROOT,capture_output=True,text=True)
    (out/'tests.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    assert tests.returncode==0, 'tests failed; tests.txt saved'
    print('Final config, code, tests and revision history saved')


if __name__=='__main__':
    main()
