"""Persist Codex's provisional reading of the six fixed outputs; no model call."""
from pathlib import Path
import importlib.util, json, re, collections
OUT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('experiment',OUT/'code/run.py');run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)
cases=run.read(OUT/'case_manifest.json')['development']
reviews={};content=[];lines=['# 個別理由と統合の暫定内容点検','',
    '点検者はCodex。人手評価・独立評価・確定正解ではない。機械的事実は`mechanical_audit.json`・各候補の`mechanical_checks.json`、意味判断は本ファイルと`content_review.json`に分ける。引用の実在は主張の正しさや採点者の実際の思考を保証しない。',
    '', '全生成6候補を対象に点検。採用0候補のため、採用後の内容品質・選別改善は評価できない。以下の出典は当実験ディレクトリからの相対パスとJSON pointer。', '']
criteria=[
 ('B1.1','特徴と評価の仕方','partially_met','history_patterns/0/pattern','評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。'),
 ('B1.2','履歴本文と得点の支持','partially_met','history_patterns/0/support','履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。'),
 ('B1.3','対象だけから恒常傾向を作らない','met','history_patterns/0/support','異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。'),
 ('B1.4','反例と不足の扱い','partially_met','history_patterns/0/counterevidence','第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。'),
 ('B2.1','引用の原文一致',None,'target_evidence/0/quotes','完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。'),
 ('B2.2','引用の意味的支持','partially_met','target_evidence/0','対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。'),
 ('B2.3','文法・意味分析の妥当性','partially_met','target_evidence/0/observable_feature','awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。'),
 ('B2.4','誤りと理解への影響の区別','not_assessable','target_evidence/0','具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。'),
 ('B3.1','履歴・本文・評価判断の接続','partially_met','decision_explanation','履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。'),
 ('B3.2','長短所列挙を超える説明','partially_met','decision_explanation','balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。'),
 ('B3.3','欠点・重み・計算の捏造回避','partially_met','decision_explanation','数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。'),
 ('B3.4','説明できない点の明示','partially_met','insufficient_evidence','不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。')]
for c in cases:
    for rid in run.ids(c):
        folder=OUT/'stage1'/rid;value=run.read(folder/'parsed.json');a=value['score_free_analysis'];audit=run.read(folder/'mechanical_checks.json')
        if rid=='4902_1__K2':
            confirmed=False
            reason='“The rubric for scores 2 and 3 ...”は対象の観測値を一意に復元する開示とは確認できない。複数bandの数値を含むことは別途指示遵守上の懸念として残す。'
        else:
            confirmed=True
            reason='target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。'
        scan=run.read(folder/'leak_scan.json')
        reviews[rid]=dict(confirmed_leak=confirmed,reviewer='Codex provisional semantic inspection',source=f'stage1/{rid}/parsed.json#/score_free_analysis/target_evidence/0/rubric_connection',quote=a['target_evidence'][0]['rubric_connection'],reason=reason,machine_suspicions=len(scan['suspicions']),note='No text rewritten. The plural-band case was found in semantic review despite zero machine hits.')
        lines += [f'## rater_7 / {c["target"]["essay_id"]} / {rid}', '',
            f'出力: `stage1/{rid}/parsed.json`。入力: `stage1/{rid}/input.json`。対象Overall={c["target"]["Overall"]}。履歴ID: '+', '.join(e['essay_id'] for e in c['history'])+'。',
            '', '**根拠となる生成原文**', '',
            '- pattern: '+json.dumps(a['history_patterns'][0]['pattern'],ensure_ascii=False),
            '- target feature: '+json.dumps(a['target_evidence'][0]['observable_feature'],ensure_ascii=False),
            '- decision: '+json.dumps(a['decision_explanation'],ensure_ascii=False),
            '- score-free rubric connection: '+json.dumps(a['target_evidence'][0]['rubric_connection'],ensure_ascii=False),'',
            '|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|','|---|---|---|']
        target_quote=a['target_evidence'][0]['quotes'][0]
        source_info=dict(target_essay_id=c['target']['essay_id'],history_ids=[h['essay_id'] for h in c['history']],observed_target_scores={k:c['target'][k] for k in ['Overall','Traits']})
        for code,title,label,path,explanation in criteria:
            if code=='B2.1':label='met' if audit['summary']['quote_mismatches']==0 else 'partially_met'
            if code=='B2.4' and rid=='4902_1__K1':label='not_met';explanation='rubric_connectionに“communication impeded in some cases”とあるが、どこで何が読めなくなるかの分析がなく、引用への結び付けが不足。'
            pointer='/score_free_analysis/'+path
            ev=a
            for k in path.split('/'):
                ev=ev[int(k)] if isinstance(ev,list) else ev[k]
            rec=dict(candidate_id=rid,criterion=code,label=label,output_source=f'stage1/{rid}/parsed.json#{pointer}',output_evidence=ev,input_source=f'stage1/{rid}/input.json',input_evidence=source_info,provisional_reason=explanation)
            if code.startswith('B2'):
                rec['input_evidence']=dict(**source_info,source_target_text=c['target']['text'],mechanical_checks_source=f'stage1/{rid}/mechanical_checks.json')
            content.append(rec)
            lines.append(f'|{code} {title}|{label}|`{path}`。{explanation} 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|')
        lines += ['',f'機械的引用検査: {audit["summary"]["quotes_checked"]-audit["summary"]["quote_mismatches"]}/{audit["summary"]["quotes_checked"]}件が完全一致。',
            '得点分離点検: '+reason, '']
        if rid.startswith('1868'):
            lines += ['個別の重要点: 観測Traits辞書が全入力と一致しないのは省略による。K1はSyntax、K2はSyntax/Grammar/Conventionsが欠ける。**記載された得点値が誤っているという意味ではない。** K1のrubric_connectionはVocabulary/Phraseologyにも3の帯を当てる一方、本人の対象Vocabulary/Phraseologyは4。この不整合を未解決として扱えていない。', '']
        if rid.startswith('4902'):
            lines += ['個別の重要点: 履歴8630:1はOverall=3、Syntax=2、Phraseology=1、1462:1はOverall=3、Syntax=3、Phraseology=3、8722:1はOverall=5。これらの併存だけで本人がCohesion/Syntaxを他観点より優先したとは確定しない。数値重みはないが、優先度の推定を過度に一般化している。','']
run.save(OUT/'leak_review.json',reviews)
run.save(OUT/'content_review.json',dict(reviewer='Codex provisional; not independent human evaluation',candidate_criterion_reviews=content,integrated_feedback={f'C{i}':dict(label='not_assessable',reason='No accepted records; Stage3 skipped. No output exists.') for i in range(1,9)}))
lines += ['## 統合フィードバック（C1〜C8）','','採用0件によりStage 3を仕様どおり省略した。複数答案の傾向、代表例、ルーブリック比較、具体的な採点チェック、採点者向けか、一致/ずれ/不明の区別、一般化、元理由との整合の8項目はすべて`not_assessable`。`stage3/skip.json`が根拠。統合プロンプトの内容品質は未検証であり、改善・劣化を判定しない。']
(OUT/'content_review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
rows=run.decisions()
assert not any(r['accepted'] for r in rows)
run.stage3(None)
# Attach review completion to the result tables without changing the frozen selection logic.
for r in rows:r['content_review']='completed_provisional; see content_review.json'
run.csvsave(OUT/'candidate_results.csv',rows,list(rows[0]))
summary=run.read(OUT/'summary.json')
summary.update(rows=rows,stage3_executed=0,stage3_skipped=1,stage3_skip_reason='No accepted records',confirmed_leak_candidates=sum(v['confirmed_leak'] for v in reviews.values()),machine_suspected_candidates=sum(v['machine_suspicions']>0 for v in reviews.values()))
run.save(OUT/'summary.json',summary)
run.finalize()
m=run.read(OUT/'run_manifest.json')
m.update(status='initial_validation_closed_with_stage3_skipped',completed_at=run.now(),content_review='Codex provisional; no additional LLM evaluator',holdout='All 1211 valid same-rater essays appear in prior targets. Reserved items not generated; no certified unused final set available.',review_code_sha256={str(p.relative_to(OUT)).replace('\\','/'):run.sha(p) for p in (OUT/'code').glob('*.py')})
m['source_files_unchanged_after']={p:run.sha(run.ROOT/p)==h for p,h in m['source_sha256'].items()}
assert all(m['source_files_unchanged_after'].values())
run.save(OUT/'run_manifest.json',m)
print(json.dumps({k:v for k,v in summary.items() if k!='rows'},indent=2))
