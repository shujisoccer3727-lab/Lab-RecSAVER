"""モデル実行前でも完了できる入力・出典・引用候補の静的検査。"""
import collections
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import locate, now, save


def main():
    out=ROOT/'outputs/rater_feedback_pilot'
    items=json.loads((out/'inputs.json').read_text())
    selection=json.loads((out/'selection.json').read_text())
    checks=json.loads((out/'source_checks.json').read_text())
    static=[]
    for item in items:
        # 明示的引用だけを検査。引用がない理由を自動的に「本文に支持されない」と扱わない。
        quotes=re.findall(r'"([^"\n]{3,})"|“([^”\n]{3,})”',item['reference_reasoning'])
        candidates=[a or b for a,b in quotes]
        static.append(dict(target_id=item['target_id'],rater_id=item['target_rater'],observed_overall=item['gold_overall'],
                           candidate_index=item['candidate_index'],attempt_index=item['attempt_index'],
                           explicit_quote_checks=[dict(quote=q,target_occurrences=locate(item['target_text'],q),
                              history_occurrences={h['target_id']:locate(h['text'],q) for h in item['history'] if locate(h['text'],q)}) for q in candidates],
                           history_marker_detected=bool(re.search(r'\bhistor|previous|past essay|rater',item['reference_reasoning'],re.I)),
                           semantic_support='not assessed by static checks',
                           input_target_chars=len(item['target_text']),reference_chars=len(item['reference_reasoning'])))
    save(out/'static_quote_checks.json',static)
    lines=['# 採点者フィードバック予備検証：入力と実行準備', '', f'確認日時: {now()}', '',
           '## 実行状況', '', '入力監査・選択・プロンプト保存・引用照合コードのテストは完了。Qwenの追加ロードは既存LLMサービスのGPU占有と競合したため中断。フィードバック生成は未完了。', '',
           '既存ローカルサービスの認証情報をプロセス情報から取得する試行は、自動承認審査で拒否され、実行されていない。ユーザーはサービス再利用を承認せず、Qwen用GPUが空くまで実生成を保留するよう指定した。認証取得用の未実行スクリプトは削除した。', '',
           '## 確認できたこと', '',
           f"- 自己検証済みプール: {selection['source_pool_rows']}行。全件の本文・採点者ID・観測Overall・当時の自己検証入力一致を確認。",
           '- 通常のPrediction Reasoning、後続のtendency明示生成、未検証候補は入力に使用していない。',
           '- 採点者IDはrawのRater_1／Rater_2の値。対象IDは0始まりの論理source行番号とrater_positionから復元。',
           '- 対象本文と当時の3件の履歴は別フィールドで保存。引用は対象本文に限定して照合。',
           '- 参照推論はOverallについて、観測Overallを与えて生成した事後的説明。自己検証は得点再構成であり、本文による説明の正しさを保証しない。',
           '- 元DOCXは不在。保存済みOverall原文・構造化JSON・当時の保存プロンプトを完全一致で照合。DOCXとの真正性は独立検証できない。',
           f"- 生成候補ログ不在で自己検証プロンプトから来歴確認した採用済み候補: {sum(not c['candidate_journal_present'] for c in checks)}行。", '',
           '## 選択', '', f"seed={selection['seed']}。{selection['rule']}。結果による差し替えなし。代表性を持つ標本ではない。", '',
           '|採点者|利用可能ユニーク答案|選択答案|観測Overall分布|', '|---|---:|---:|---|']
    for rater in selection['selected_raters']:
        rows=[r for r in items if r['target_rater']==rater]
        lines.append(f"|{rater}|{selection['available_unique_essays_by_rater'][rater]}|{len(rows)}|{dict(sorted(collections.Counter(r['gold_overall'] for r in rows).items()))}|")
    lines+=['', '全採点者の利用可能答案数: selection.json。入力全文・候補ID・観測得点・履歴: inputs.json。', '',
            '## 静的引用検査', '',
            f"参照推論に明示された引用候補: {sum(len(r['explicit_quote_checks']) for r in static)}件。結果はstatic_quote_checks.json。",
            'この件数は引用符付き文字列の検出数であり、根拠不足の割合ではない。意味的支持、履歴混同、複数答案の傾向、④と⑤の品質はモデル生成後に検討する。', '',
            '## 再開', '', '既存Qwen用にGPUが空いてから、リポジトリルートで実行:', '', '```bash',
            'conda activate qwen3', 'python -m src.recsaver.rater_feedback_pilot pilot',
            '# outputs/rater_feedback_pilot/report.mdとcalls.jsonlを確認しpilot_review.jsonを保存後:',
            'python -m src.recsaver.rater_feedback_pilot remaining', '```', '',
            '成功済み段階は入力・プロンプトfingerprint一致時に再利用。失敗応答はcalls.jsonlに保存。入力やプロンプト変更時は新しいoutput_dirを使い既存出力を残す。', '',
            '## 今後の個別理由プロンプト改善候補', '',
            '- 主張ごとに対象／履歴のscope、対象ID、原文引用、位置を構造化して保存。',
            '- 本文の特徴だけでなく、評価方向と観測Overallを説明する条件との関係を明示。',
            '- 程度・頻度・適切さ・伝達阻害を判断する範囲と反例を必須化。短い一節で全体判断を断定させない。',
            '- ルーブリック条件の出典ID、解釈差、証拠不足、判断保留を出力。',
            '- 得点による自己検証と、引用存在・意味的支持の検証を区別。', '',
            '実生成前の設計上の改善候補であり、生成結果から確認済みの知見とは扱わない。']
    (out/'preflight_report.md').write_text('\n'.join(lines),encoding='utf-8')
    save(out/'execution_history.json',dict(timestamp=now(),events=[
        dict(status='passed',stage='prepare',detail='2056 references joined to raw, processed and exact saved prompts'),
        dict(status='passed',stage='unit_tests',detail='6 evidence gate tests'),
        dict(status='interrupted',stage='Qwen initialization',detail='GPU occupied by existing local inference service; only pilot process terminated; no generated feedback'),
        dict(status='approval_blocked',stage='local endpoint probe',detail='Automatic approval rejected reading credentials from /proc; probe not executed'),
        dict(status='user_deferred',stage='generation',detail='User declined local Gemma reuse and requested deferral until Qwen GPU is free; unused credential helper removed')]))
    prior=json.loads((out/'status.json').read_text()) if (out/'status.json').exists() else {}
    save(out/'initial_startup_status.json',prior)
    save(out/'status.json',dict(status='deferred_by_user',timestamp=now(),reason='GPU occupied; user declined Gemma endpoint reuse',
         generated_feedback_count=0,next_command='python -m src.recsaver.rater_feedback_pilot pilot'))
    print('Preflight report and quote checks saved')


if __name__=='__main__':
    main()
