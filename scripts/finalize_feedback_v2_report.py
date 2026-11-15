"""実結果を補う実測表と要確認点。モデル意味判定の正しさは認定しない。"""
import collections
import json
import re
import shutil
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now,sha


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    phase='full' if (out/'full_results.json').exists() else 'pilot'
    snap=load(out/f'{phase}_results.json');items=load(out/'inputs.json')
    metrics=load(out/'run_metrics.json');audit=load(out/'independent_audit.json')
    save(out/'feedback.json',dict(version=cfg['version'],phase=phase,results=snap['results'],
         quality_status='generated preliminary examples; known semantic problems; not validated for use with real raters',
         model=cfg['model'],generation=cfg['generation'],content_observations='pilot_content_observations.json'))
    eligible=set(snap['target_ids']);items=[i for i in items if i['target_id'] in eligible]
    issues=[]
    for c in snap['candidates']:
        reason=c.get('original_reason')
        if not reason: continue
        text=reason['rationale']
        chinese=re.findall(r'词汇|文本|评分|语法|广泛|较高|这些|表达|错误',text)
        if len(chinese)>=2:
            issues.append(dict(candidate=c['key'],kind='language_mismatch_flag',detail='Japanese requested, Chinese phrases present in rationale; not a language ground-truth label',accepted=c['accepted']))
        for cl in reason['claims']:
            if cl['kind']=='frequency' and not re.search(r'頻|多く|多い|繰り返|頻繁|frequen|often|repeated|经常|频繁',cl['feature'],re.I):
                issues.append(dict(candidate=c['key'],claim_id=cl['claim_id'],kind='frequency_label_requires_review',feature=cl['feature'],accepted=c['accepted']))
            if re.search(r'組織と文法|組織と.*誤り|文法と構文|組織.*文法',cl['feature']):
                issues.append(dict(candidate=c['key'],claim_id=cl['claim_id'],kind='atomic_judgment_requires_review',feature=cl['feature'],accepted=c['accepted']))
    save(out/'content_review_flags.json',dict(timestamp=now(),phase=phase,flags=issues,counts=dict(collections.Counter(x['kind'] for x in issues)),meaning='Inspection flags only; not an automatic finding that the claim is false'))
    table=['## 対象と実測の完了範囲','', '|採点者|対象数|観測Overallの分布|条件|生成候補|採用候補|採用答案|証拠あり答案|④照合済み答案|', '|---|---|---|---|---|---|---|---|---|']
    for rater in dict.fromkeys(i['rater_id'] for i in items):
        rows=[i for i in items if i['rater_id']==rater];tids={i['target_id'] for i in rows}
        dist=dict(sorted(collections.Counter(i['target']['overall'] for i in rows).items()))
        for condition in cfg['conditions']:
            cs=[c for c in snap['candidates'] if c['condition']==condition and c['target_id'] in tids]
            result=next(r for r in snap['results'] if r['condition']==condition and r['rater_id']==rater)
            evidence={g['target_id'] for g in result['essay_groups'] if g['eligible_claims']}
            table.append(f"|{rater}|{len(rows)}|{dist}|{condition}|{sum(bool(c.get('original_reason')) for c in cs)}/{len(cs)}|{sum(c['accepted'] for c in cs)}|{len({c['target_id'] for c in cs if c['accepted']})}|{len(evidence)}|{result['generation_status']['compared_targets']}|")
    table+=['','選択は従来の対象固定。候補複数件は独立した答案数に含めない。採用＝Overall再構成一致、証拠あり＝別の意味点検と機械検査を通過した主張あり。','']
    generated=out/f'{phase}_report.generated.md'
    if not generated.exists(): shutil.copy2(out/'report.md',generated)
    warning='> 以下は内容点検用の生成例です。原文・位置・IDの機械検査の成功は、文法分析や規範的評価の正しさを保証しません。pilot_content_observations.jsonに既知の誤分析を保存しています。実際の採点者へ提示するために検証済みのフィードバックではありません。\n\n'
    (out/'report.md').write_text(warning+generated.read_text(encoding='utf-8')+'\n'+'\n'.join(table),encoding='utf-8')
    assessment_generated=out/f'{phase}_assessment.generated.md'
    if not assessment_generated.exists(): shutil.copy2(out/'assessment.md',assessment_generated)
    extra=['','## 実測の検査・内容点検','',f"機械監査: {audit['all_machine_checks_passed']}（失敗{len(audit['errors'])}件）。意味的支持の正解性はこの監査に含まない。",'','### 暫定的な意味的支持の内訳','', '```json',json.dumps({k:{key:v for key,v in val.items() if key in ['claims','reviewed_claims','semantic_support_counts','eligible_claims','history_claims','mechanically_invalid']} for k,val in metrics['conditions'].items()},ensure_ascii=False,indent=2),'```','', '### 生成形式の失敗', '', '```json',json.dumps(metrics['failures'],ensure_ascii=False,indent=2),'```','', '原出力と再試行をcalls.jsonlに残した。得点不一致の候補を合格まで再生成していない。', '', '### 内容上の要確認フラグ', '', '```json',json.dumps(dict(collections.Counter(x['kind'] for x in issues)),ensure_ascii=False,indent=2),'```','', 'content_review_flags.jsonの言語・原子的主張・頻度分類のフラグは、主張が誤りという自動判定ではない。該当箇所を読むための記録。', '', '### 次の個別理由プロンプトで改善する点', '', '- 抽象的な「構造」「文法」「語彙が限定的」の説明だけでなく、どの構文・語の使い方・指示関係を判断したかを記す。引用は引き続きspan IDから取得する。', '- 誤りの存在・分布・理解を妨げる具体的な命題の不確定さを別々の主張とし、組織と文法も分ける。', '- 日本語の文章欄、分類enum、文字列／配列の型を明確にし、形式違反の再試行には失敗フィールド名と許容値を返す。', '- 高得点の説明を無理に整えず、観測Overallを再構成できない場合は候補不足として残す。', '- ④では全文の局所証拠と程度・頻度・伝達阻害の条件を対応させ、⑤では同じ論点の区別・位置・行動を明示する。意味的な正しさは別途内容確認が必要。', '', '実行は予備的な動作・出力確認。最終評価設計、代表性のある標本評価、本人の心理の復元、有効性やバイアス是正効果の結論は対象外。','']
    if (out/'pilot_content_observations.json').exists():
        extra += ['## 固定3答案で確認した具体的な問題', '', '```json',json.dumps(load(out/'pilot_content_observations.json'),ensure_ascii=False,indent=2),'```', '', 'これらは機械監査とは別の内容上の問題。原文に語があること、引用が支持すること、文法分析が正しいこと、ルーブリックの条件を満たすこと、採点者に有用な行動になることを順に区別する必要がある。', '']
    original=assessment_generated.read_text(encoding='utf-8').replace('Aのみ統合可能な対象','Aのみ自己検証で一致した対象').replace('Bのみ統合可能な対象','Bのみ自己検証で一致した対象')
    (out/'assessment.md').write_text(original+'\n'.join(extra),encoding='utf-8')
    for name in ['summarize_feedback_v2_run.py','finalize_feedback_v2_report.py']:
        shutil.copy2(ROOT/'scripts'/name,out/'code'/name)
    save(out/'report_code_manifest.json',{n:sha(out/'code'/n) for n in ['summarize_feedback_v2_run.py','finalize_feedback_v2_report.py']})
    print(json.dumps(dict(phase=phase,review_flags=len(issues),machine_checks_passed=audit['all_machine_checks_passed']),ensure_ascii=False),flush=True)


if __name__=='__main__': main()
