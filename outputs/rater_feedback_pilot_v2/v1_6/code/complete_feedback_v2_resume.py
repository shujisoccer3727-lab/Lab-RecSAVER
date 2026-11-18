"""保存済み全件結果の終端状態を照合し、今回の再開報告と参照先を保存する。

推論・履歴集約コマンドは実行せず、既存の生出力と失敗キャッシュを保持する。
"""
import json
import shutil
from pathlib import Path

from src.recsaver.rater_feedback_pilot_v2 import ROOT, load, save, now, sha


def main():
    cfg = load(ROOT / 'configs/rater_feedback_pilot_v2.json')
    out = ROOT / cfg['output_dir']
    snapshot = load(out / 'full_results.json')
    inputs = load(out / 'inputs.json')
    audit = load(out / 'independent_audit.json')
    anchors = load(out / 'anchor_audit.json')
    scan = load(out / 'verification_input_audit.json')
    assert audit['all_machine_checks_passed'] and anchors['all_machine_checks_passed']
    assert scan['whitelist_checks_passed'] and not scan['additional_free_text_suspects']
    assert len(snapshot['target_ids']) == 27 and len(snapshot['candidates']) == 108
    conditions = {}
    for condition in cfg['conditions']:
        cs = [c for c in snapshot['candidates'] if c['condition'] == condition]
        rs = [r for r in snapshot['results'] if r['condition'] == condition]
        assert len(cs) == 54 and len(rs) == 3
        eligible = {g['target_id'] for r in rs for g in r['essay_groups'] if g['eligible_claims']}
        compared = {tid for r in rs for tid, value in r['comparisons'].items() if value is not None}
        missing = sorted(eligible - compared)
        failures = []
        for tid in missing:
            cache = out / 'stages' / 'compare' / f'{condition}__full_{tid.replace(":", "_")}.json'
            assert cache.exists(), (condition, tid, cache)
            cached = load(cache)
            assert cached['result'] is None
            failures.append(dict(target_id=tid, cache=cache.relative_to(ROOT).as_posix(), error=cached.get('error')))
        assert all(r['generation_status']['integration_succeeded'] and
                   r['generation_status']['text_succeeded'] for r in rs)
        conditions[condition] = dict(
            selected_unique_targets=27, candidates=54,
            generated_success=sum(bool(c.get('original_reason')) for c in cs),
            generated_failed_keys=[c['key'] for c in cs if not c.get('original_reason')],
            verification_success=sum(c.get('verification') is not None for c in cs),
            verification_matches=sum(c['accepted'] for c in cs),
            integration_input_unique_targets=len(eligible),
            pattern_support_unique_targets=len({s['target_id'] for r in rs
                for p in r['synthesis']['patterns'] for s in p['support']}),
            comparison_success=len(compared), comparison_exhausted=len(missing),
            comparison_failures=failures, integrations=3, feedback_texts=3)
    result = dict(timestamp=now(), version=cfg['version'], saved_status=load(out/'status.json'),
        conditions=conditions, pending_batches=0, model_calls_during_resume=0,
        protocol_changed=False, experiment_code_changed_during_resume=False,
        old_outputs_and_failed_attempts_retained=True,
        progress_note='The old progress snapshot was stale; rebuilt from stage caches and calls.jsonl.',
        process_observation=dict(gpu_memory_used_mib=516, gpu_memory_free_mib=47892,
            gpu_utilization_percent=2, gpu_compute_processes=[],
            note='Read-only nvidia-smi observation during resume; other CPU Python processes were not stopped.'),
        documentation_command=dict(path='scripts/document_feedback_v2_revisions.py',
            previous_rejection='Automatic approval review could not complete because of usage limit; not a safety determination.',
            executed_during_resume=False, bypassed=False,
            note='Independent historical revision aggregation remains unexecuted. Current result audit and final README are separate reporting work.'),
        handoff='No pending inference. Exhausted generation/comparison failures are terminal under the saved retry budget. Do not regenerate for score mismatch or silently retry exhausted failures. Preserve config, prompts, selected targets and prior outputs.')
    save(out/'resume_completion.json', result)
    marker = '\n<!-- saved-state-resume-audit -->\n'
    lines = ['## 保存済み状態からの再開監査', '',
        '本処理は2026-11-15 20:54 JSTに終了済み。今回の再開ではモデルを起動せず、全件を再集計・監査して最終文書を確定した。', '',
        '|条件|生成成功／予定候補|生成失敗|検証実行成功|Overall一致候補|統合入力のユニーク答案|傾向の支持に列挙されたユニーク答案|④⑤成功／対象|④⑤失敗|',
        '|---|---|---|---|---|---|---|---|---|']
    for condition, v in conditions.items():
        lines.append(f"|{condition}|{v['generated_success']}/54|{len(v['generated_failed_keys'])}|{v['verification_success']}|{v['verification_matches']}|{v['integration_input_unique_targets']}|{v['pattern_support_unique_targets']}|{v['comparison_success']}/{v['integration_input_unique_targets']}|{v['comparison_exhausted']}|")
    lines += ['', '統合入力は、採用候補に本文に対応する暫定支持主張がある答案数。傾向の支持として実際に列挙された答案数とは別に集計した。候補の複数件を独立した答案として数えていない。', '',
        '各条件で生成失敗は1514:1のK2。生成後の自己検証は全106件が形式上成功し、Overall不一致37候補は不採用で保持した。生成失敗と得点不一致を混同しない。', '',
        '④⑤は39対象中24件が成功、15件は既定の形式再試行を使い切った終端失敗。未処理バッチはない。採点者別の統合・最終文章は各条件3件が成功したが、失敗した答案の④⑤を補完できたことは意味しない。失敗対象とキャッシュはresume_completion.json、各試行の原出力・エラーはcalls.jsonlに保持する。', '',
        '引用・単語の文字位置は24件すべて照合済み。ただし4件は補助的な観点別基準だけを選び、Overall条件を明示していない（anchor_audit.json）。機械検査の成功は基準対応の十分性を意味しない。', '',
        '観測Overall=5の2答案（条件ごと4候補）は、A/Bとも一致候補0件だった。このため統合は高得点答案の評価を説明できていない。採用範囲の偏りを含む予備出力であり、A/B差をTrait情報の因果的効果と扱わない。', '',
        '具体例（A・5627:1）では、本文の「My Mom, she」と「whats」を取り上げた一方、「whats」を指示代名詞とする分析、組織に関するOverall.S3.C02との対応、理解阻害の程度の根拠には問題がある。⑤「冗長性と誤用を確認し、その影響を評価する」は④の語には対応するが、次の採点で何を区別するかは十分に具体化されていない。これは改善課題を確認する生成例であり、妥当な助言と認定した例ではない。', '',
        '次回は個別理由の1主張を1つの検証可能な判断に分け、正しい用法との区別、複数箇所での頻度、理解への影響、判断保留を明示する。④はその証拠を公式条件の程度・頻度と結び、⑤はその未解決点を次回採点で見分ける手順にする。文法分析の正しさは文字列照合とは別に点検する。今回のプロンプトや研究条件は変更していない。', '',
        '前回のdocument_feedback_v2_revisions.pyは、利用上限で自動承認審査が完了せず実行されなかった。今回も同コマンドの実行や別経路による履歴集約は行っていない。旧版・既存の版別ログ・再利用証明は保持し、本処理と独立した文書化として残す。', '',
        '再開監査の詳細: [resume_completion.json](resume_completion.json)。引用検査: [independent_audit.json](independent_audit.json)、[anchor_audit.json](anchor_audit.json)、[verification_input_audit.json](verification_input_audit.json)。', '']
    for name in ['report.md', 'assessment.md']:
        path = out/name
        text = path.read_text(encoding='utf-8').split(marker)[0]
        path.write_text(text+marker+'\n'.join(lines), encoding='utf-8')
    current = cfg['output_dir']
    shared = f'''現在読むべき完成版は **v1_6**。保存済みの全27答案（3採点者：10・7・10答案）、履歴各3件、A/B各2候補の結果を監査した。

- レポートの正確なパス: `{current}/report.md`
- 所見の正確なパス: `{current}/assessment.md`

条件AはOverallのみ、Bは同じ採点者の6観点の得点も提示。モデルはQwen2.5-32B-Instruct-GPTQ-Int4、保存済み版1.6と生成設定を維持した。

各条件54候補中53生成成功・1失敗。Overall一致はA35候補／20答案、B34候補／19答案。統合・最終文章はA/B各3採点者で成功。答案別④⑤はA11/20、B13/19成功、計15件は既定再試行後の失敗として保持している。未処理バッチはなく、今回の再開で新しいモデル呼出しは行っていない。

機械監査は通過したが、文法分析の誤り、一般的すぎる傾向、Overall条件がない照合4件、採点上の確認より添削に寄る行動が残る。実際の採点者への利用に妥当性が確認されたフィードバックではない。有効性・バイアス是正効果は結論しない。

旧版・成功出力・全失敗試行は保持した。前回利用上限によって自動承認審査が完了しなかった履歴集約コマンドは実行せず、迂回もしていない。版別のログ・pilot_review.json・upstream_reuse.jsonと今回のresume_completion.jsonを参照する。Gitのcommit/pushは行っていない。
'''
    parent = out.parent
    for directory in [parent, out]:
        readme = directory/'README.md'
        backup = directory/'README.before_saved_state_resume.md'
        if readme.exists() and not backup.exists():
            shutil.copy2(readme, backup)
        prefix = 'v1_6/' if directory == parent else ''
        links = ['report.md','assessment.md','feedback.json','full_results.json','full_summary.json',
                 'run_metrics.json','resume_completion.json','progress.json','resolved_config.json']
        body = '\n'.join(f'- [{name}]({prefix}{name})' for name in links)
        readme.write_text('# 採点者フィードバック予備検証v2：現在の参照先\n\n'+shared+'\n'+body+'\n',encoding='utf-8')
    shutil.copy2(Path(__file__),out/'code'/Path(__file__).name)
    save(out/'resume_report_code_manifest.json', {Path(__file__).name:sha(out/'code'/Path(__file__).name)})
    print(json.dumps(conditions,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
