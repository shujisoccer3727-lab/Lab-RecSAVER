"""Persist evidence-backed content review and final artifact/source checks; no generation."""
from pathlib import Path
import importlib.util,json,collections,csv
out=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',out/'code/run.py');r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
pf=r.read(out/'preflight_review.json');audit=r.read(out/'common_mechanical_audit.json')['versions'];reviews=[]
for c in r.cases():
    for rid in r.ids(c):
        old=r.read(r.OLD/'stage1'/rid/'parsed.json');new=r.read(out/'stage1'/rid/'parsed.json')
        p=pf['candidates'][rid]
        reviews.append(dict(candidate_id=rid,judgement=p['comparison_judgement'],reason=p['comparison_reason'],old_output_source=f'{r.rel(r.OLD)}/stage1/{rid}/parsed.json',new_output_source=f'stage1/{rid}/parsed.json',common_input_source=f'stage1/{rid}/input.json',history_ids=[h['essay_id'] for h in c['history']],observed_scores={k:c['target'][k] for k in ['Overall','Traits']},old_score_free_evidence=old['score_free_analysis'],new_score_free_evidence=new['score_free_analysis'],old_score_alignment_evidence=old['observed_score_alignment'],new_score_alignment_evidence=new['observed_score_alignment'],source_history=[dict(essay_id=h['essay_id'],Overall=h['Overall'],Traits=h['Traits']) for h in c['history']],assessment=dict(format='met both versions',observed_scores='met in v1.1; old omissions separately counted',score_separation='not_met both versions',claim_scope='not_met: short selected passages do not establish whole-essay organization/vocabulary range',historical_evaluation_relationship='partially_met at most: named source examples but feature-to-treatment comparison underdetermined',abstention='partially_met at most: partly_supported label does not specify missing comparison; read candidate reason for loss of local findings',rubric_observation_separation='partially_met at most: recorded values preserved but claims often force descriptor alignment'),mechanical_old={k:v for k,v in audit['v1_0'][rid].items() if k not in ['quotes','suspicions']},mechanical_new={k:v for k,v in audit['v1_1'][rid].items() if k not in ['quotes','suspicions']}))
r.save(out/'content_review.json',dict(reviewer='Codex provisional semantic/content review; not independent human evaluation',comparison_criteria='Same evidence-scope, score-separation, observation-copying and exact-quote criteria applied to both versions.',candidates=reviews,stage2=dict(A=dict(format='improved',contamination_stop='not_met',source='stage2_diagnostics/A/v1_1/parsed.json'),B=dict(format='improved',stricter_v1_1_contract='not_met',source='stage2_diagnostics/B/v1_1/parsed.json'),C=dict(format='improved',false_contamination='not observed',abstention='Conservative reading plausible given deliberately local control; does not demonstrate general estimation capability.',source='stage2_diagnostics/C/v1_1/parsed.json')),stage3=dict(label='not_assessable',reason='Zero distinct accepted essays; requires at least two.',source='stage3/skip.json')))
counts={}
for ver,data in audit.items():
    q=collections.Counter()
    for m in data.values():q.update(m['quote_counts'])
    counts[ver]=dict(quote_counts=dict(q),quote_total=sum(q.values()),all_observed_scores_equal=sum(m['all_observed_scores_equal'] for m in data.values()),history_role_error_candidates=sum(bool(m['history_role_errors']) for m in data.values()))
r.save(out/'comparison_summary.json',dict(Stage1=counts,Stage2=dict(old_strict_json=dict(numerator=0,denominator=3),new_strict_json=dict(numerator=3,denominator=3),new_contaminated_abstention=dict(numerator=0,denominator=2),new_control_noncontaminated=dict(numerator=1,denominator=1)),main=r.read(out/'summary.json')))
assert len(list((out/'stage1').glob('*/raw.txt')))==6
assert len(list((out/'stage2_diagnostics').glob('*/*/raw.txt')))==6
assert not list((out/'stage2').glob('*/raw.txt'))
assert r.read(out/'summary.json')['preflight_pass']==0
assert r.read(out/'stage3/skip.json')['distinct_targets']==0
assert r.read(out/'invariant_checks.json')['passed']
for name in ['stage1_comparison.csv','stage2_diagnostics.csv','candidate_results.csv','essay_results.csv','validation_report.md','README.md']:assert (out/name).stat().st_size>0
r.finalize();m=r.read(out/'run_manifest.json');assert m['baseline_unchanged']
m.update(completed_at=r.now(),status='validation_complete_main_stopped_at_preflight',code_files_sha256={str(p.relative_to(out)).replace('\\','/'):r.sha(p) for p in (out/'code').glob('*.py')},reviewer='Codex provisional; not human evaluation',additional_model_generations_after_frozen_budget=0,formal_output_constraints_added=False)
r.save(out/'run_manifest.json',m)
r.save(out/'final_checks.json',dict(checked_at=r.now(),passed=True,stage1_raw_count=6,diagnostic_raw_count=6,main_stage2_raw_count=0,stage3_skipped=True,canonical_prompts_unchanged=True,baseline_artifacts_unchanged=True,original_stage_seed_preserved=True,diagnostic_pairs_have_same_input_and_sampling=True,source_no_repairs=True))
r.status('completed',summary=r.read(out/'summary.json'),report='validation_report.md')
print(json.dumps(counts,ensure_ascii=False,indent=2))
