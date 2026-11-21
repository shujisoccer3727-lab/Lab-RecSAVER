"""Codex's completed semantic preflight, persisted before any main Stage2 request."""
from pathlib import Path
import importlib.util
out=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',out/'code/run.py');r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
audit=r.read(out/'common_mechanical_audit.json')['versions'];new={};old={}
notes={
'1514_1__K1':('悪化','対象の観測Overallを直接記載し、対象1514:1をhistory supportに混入。短い引用から全体の構成・語彙幅も断定。引用は3/3一致だが履歴根拠の役割が不正。'),
'1514_1__K2':('同程度','数値帯の残存と、短い引用から全体品質への拡張が継続。高品質・高得点の履歴を反例と呼ぶ誤りも残る。観測値の全項目保持は両版とも通過。'),
'1868_1__K1':('悪化','観測Traitの欠落は解消したが、対象1文から構成・語彙幅を断定し、意思決定説明で観測Overallも直接開示。不足・uncertaintyが空となり保留が弱まった。Vocabulary/Phraseology=3という誤った帯対応は消えたが、論点自体の縮小で全面改善とはしない。'),
'1868_1__K2':('悪化','観測Traitsの欠落は解消。一方、1文を根拠に構成・語彙幅を断定し、limitations・uncertainty・insufficient_evidenceが全て空。狭い履歴から断定できないという保留が失われた。'),
'4902_1__K1':('悪化','引用の非空白差は消えたが、観測Overallの直接開示と、全観点の誤りをminorと括る過小分析が残る。Cohesion=3側の記述を本人Cohesion=2と整合させる新たな基準対応の不整合がある。'),
'4902_1__K2':('同程度','2/3帯と意味妨害をまとめる元の文は消えたが、代わりにOverall=3の明示と一般的な全体特徴を反復。意味妨害の慎重な分析に置換できたとは言えない。履歴引用の空白差は2件のまま。Syntax=4側に近い記述を3と整合させる問題も残る。')}
for c in r.cases():
    for rid in r.ids(c):
        v=r.read(out/'stage1'/rid/'parsed.json');a=v['score_free_analysis'];m=audit['v1_1'][rid]
        direct=rid in ['1514_1__K1','1868_1__K1','4902_1__K1']
        # Store all exact suspect strings; final role-sensitive conclusions are below, not regex verdicts.
        issues=[dict(path='/score_free_analysis/target_evidence/0/evaluative_interpretation',text=a['target_evidence'][0]['evaluative_interpretation'],finding='Numerical Overall value explicitly applied to target')]
        if direct:issues.append(dict(path='/score_free_analysis/decision_explanation',text=a['decision_explanation'],finding='Observed target Overall explicitly named'))
        reasons=['numbered_target_band_or_range']
        if direct:reasons.append('direct_observed_target_score_disclosure')
        if rid=='1514_1__K1':
            reasons.append('target_essay_used_as_history_support')
            issues.append(dict(path='/score_free_analysis/history_patterns/0/support/1/history_essay_id',text='1514:1',finding='Target is not in supplied history; target score also disclosed as a supposed history observation'))
        new[rid]=dict(pass_=False,direct_or_recoverable_disclosure=direct,numbered_target_band_or_range=True,rejection_reasons=reasons,observed_score_copying_correct=m['all_observed_scores_equal'],issues=issues,review_scope='All strings in score_free_analysis inspected, including patterns, support, uncertainty, insufficient_evidence and decision.',comparison_judgement=notes[rid][0],comparison_reason=notes[rid][1],role_sensitive_notes='Numeric history scores and essay quote numbers alone are allowed. Numeric target performance matching is band application, not automatically direct recorded-score disclosure. Direct count is conservative and limited to explicit observed target value statements.')
        new[rid]['pass']=new[rid].pop('pass_')
        ov=r.read(r.OLD/'stage1'/rid/'parsed.json')['score_free_analysis']
        old[rid]=dict(direct_or_recoverable_disclosure=False,numbered_target_band_or_range=True,reason='Numbered target descriptor/application in rubric_connection; 4902 K2 plural scores2/3 included by the common v1.1 input contract. No explicit recorded-target observation distinguished from descriptor here.',evidence=ov['target_evidence'][0]['rubric_connection'])
# No v1.1 candidate qualifies: construct a diagnostic-only, source-verifiable control.
c=r.cases()[0];payload=r.read(r.OLD/'stage2/1514_1__K1/input.json')
quote='This shows that with hard work you can accomplish any goal and letting yourself grow.'
assert quote in c['target']['text']
payload['reference_analysis']=dict(history_patterns=[],target_evidence=[dict(evidence_id='T1',dimensions=['Syntax'],quotes=[quote],observable_feature='The passage coordinates "you can accomplish any goal" with "letting yourself grow", using nonparallel constructions.',evaluative_interpretation='The nonparallel coordination limits sentence control, while the intended positive claim about effort and growth remains recoverable.',linked_history_pattern_ids=[],rubric_connection='Syntax concerns how clauses and phrases are coordinated. Inspect the nonparallel coordination in this passage without equating its presence with a particular performance band.',uncertainty='One passage does not establish the frequency or severity of such constructions across the whole essay.')],decision_explanation='T1 identifies a local construction limitation with recoverable meaning. No defensible feature-to-score relationship has been established from the supplied history, so this observation does not demonstrate the rater\'s weighting or a stable preference.',insufficient_evidence=['The local evidence does not establish how the rater balanced all dimensions.'])
assert set(payload['target'])=={'essay_id','text'}
r.save(out/'diagnostic_control/input.json',payload)
record=dict(reviewed_at=r.now(),reviewer='Codex provisional semantic/content review; not independent human evaluation',review_frozen_before_main_stage2=True,candidates=new,baseline_common_review=old,diagnostic_control=dict(source='constructed_diagnostic_only',candidate_id='1514_1__K1',input_path='diagnostic_control/input.json',reason='All six v1.1 candidates contain target numerical band application. Fixed source passage from first target; preserve complete identical history, target and rubric. Hand-authored reference analysis is not a model output or a repaired candidate and is excluded from acceptance.',construction_source='stage1/1514_1__K1/input.json target, exact local quote',supports_ordinary_qualitative_findings=True))
r.save(out/'preflight_review.json',record)
print('Saved preflight: 0/6 pass; diagnostic C is explicitly constructed control.')
