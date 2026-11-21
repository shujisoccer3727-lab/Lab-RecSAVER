"""Finalize evidence-backed review and manifests without any model generation."""
import run as r
import json,collections,csv
notes={
'1514_1__K1':'The selected opening sentence cannot by itself establish whole-essay organization/cohesive range. Higher Cohesion/lower Syntax is an interpretation, not recovered rater weighting. Mask preserves the hypothesis but reconstruction=4 differs from observed3.',
'1514_1__K2':'History217 is described as counterevidence even though lower quality/lower score is compatible with the proposed pattern. One target quote supports neither overall structural variety nor an identified balancing rule. Reconstruction4 does not make the reason independently correct or incorrect.',
'1868_1__K1':'Exact keep-learning sentence is retained. The reason still asserts whole-essay organization and vocabulary range rather than analyzing the local construction. The history-attributed3 in decision is intentionally retained; not an explicit same-score equality.',
'1868_1__K2':'Structured observed scores copy all values, but free prose says Overall and Traits were3 although Vocabulary/Phraseology=4. Value-only masking hides3 without correcting this false collective statement. Stage2 also repeats a collective history-score claim; its cited histories have Vocabulary4.',
'4902_1__K1':'Minor errors across all six dimensions is broader than the quoted evidence and underplays the profile differences in historical Syntax/Phraseology. The preserved historical Overall3 must not be confused with unmasked target data.',
'4902_1__K2':'Exact quote preservation improved in this generation, including source paragraph breaks, but frequency/severity and full-essay syntactic variety are not established by the selected opening. Rubric/observed Syntax alignment remains weak.'}
content=[]
for c in r.cases():
    for rid in r.p.ids(c):
        orig=r.read(r.OUT/'stage1'/rid/'parsed.json');masked=r.read(r.OUT/'masks'/rid/'masked_analysis.json')
        content.append(dict(candidate_id=rid,reviewer='Codex provisional; not human evaluation',input_source=f'stage1/{rid}/input.json',original_source=f'stage1/{rid}/parsed.json',masked_source=f'masks/{rid}/masked_analysis.json',original_evidence=orig['score_free_analysis'],masked_evidence=masked,input_target=dict(essay_id=c['target']['essay_id'],Overall=c['target']['Overall'],Traits=c['target']['Traits'],quoted_source_text=c['target']['text']),mask_fidelity='met: only audited values changed; evidence text retained',meaning_support='partially_met at most; see specific finding',specific_finding=notes[rid],content_improvement_from_mask='not established: nonnumeric claims and their evidential limits preserved'))
stage3=r.read(r.OUT/'stage3/rater_7/parsed.json');rubric=r.read(r.OUT/'rubric.json')
review3=[
dict(criterion='evaluative_relationship_across_distinct_essays',label='partially_met',output_source='stage3/rater_7/parsed.json#/patterns/0/supporting_cases',reason='Two distinct source IDs and scores present, but the shared minor-error description does not establish how the rater evaluated each feature; alternative profiles and original weak analyses not reconciled.'),
dict(criterion='representative_quote_judgment_score_connection',label='not_met',output_source='stage3/rater_7/parsed.json#/patterns/0/representative_decision',reason='Real opening quotation4902 supports a stance, not minor errors across all six dimensions or their relation to Overall3. Final paragraph has no exact source quotation.'),
dict(criterion='rubric_dimension_band_accuracy',label='not_met',output_source='stage3/rater_7/parsed.json#/patterns/0/rubric_comparison',output_evidence=stage3['patterns'][0]['rubric_comparison'],input_source='rubric.json#/scores',input_evidence={'Overall3':rubric['scores']['3']['Overall'],'Overall4':rubric['scores']['4']['Overall']},reason='Quoted criterion is exactly Overall4, while comparison calls it support for Overall3. rarely vs some-cases interference distinction lost.'),
dict(criterion='concrete_next_scoring_check',label='partially_met',output_source='stage3/rater_7/parsed.json#/patterns/0/next_scoring_check',reason='Rater-directed severity/meaning distinction is useful direction, but no exact passage, competing interpretations or band-correct retain/reconsider condition supplied.'),
dict(criterion='source_role_integrity',label='not_met',output_source='stage3/rater_7/parsed.json#/patterns/0/counterexamples_and_scope/0',reason='8722:1 is a history essay, not an accepted target; source existence does not justify target_essay_id role.'),
dict(criterion='scope_counts',label='met',output_source='stage3/rater_7/parsed.json#/evidence_scope',reason='Four accepted records and two distinct targets correctly separated; limitations mention both targets Overall3.')]
r.save(r.OUT/'content_review.json',dict(reviewed_at=r.now(),reviewer='Codex provisional semantic review; not independent human evaluation',candidates=content,stage3=review3,final_feedback_usable=False,feedback_original=stage3['feedback_paragraph']))
assert r.read(r.OUT/'invariant_checks.json')['passed'] and r.read(r.OUT/'masking_tests.json')['passed']
counts={};trunc=0
for name,glob in [('stage1','stage1/*/raw.txt'),('stage2','stage2/*/raw.txt'),('diagnostic','stage2_diagnostics/*/*/raw.txt'),('stage3','stage3/*/raw.txt')]:
    files=list(r.OUT.glob(glob));counts[name]=len(files)
    trunc+=sum(r.read(f.parent/'result.json')['truncated'] for f in files)
assert counts==dict(stage1=6,stage2=6,diagnostic=3,stage3=1)
summary=r.read(r.OUT/'summary.json');assert summary['accepted_records']==4 and summary['distinct_accepted_targets']==2
assert r.read(r.OUT/'stage3/rater_7/result.json')['schema_valid']
for name in ['validation_report.md','README.md','saved_mask_results.csv','stage2_diagnostics.csv','candidate_results.csv','essay_results.csv','content_review.json']:assert (r.OUT/name).stat().st_size>0
r.finalize();m=r.read(r.OUT/'run_manifest.json');m.update(completed_at=r.now(),status='completed_initial_integration_evaluated_content_not_ready',code_files_sha256={str(f.relative_to(r.OUT)).replace('\\','/'):r.sha(f) for f in (r.OUT/'code').glob('*.py')},generation_counts=counts,output_truncations=trunc,mask_checks=21,stage3_execution_success=True,stage3_feedback_usable=False,content_reviewer='Codex provisional; not human evaluation')
r.save(r.OUT/'run_manifest.json',m)
r.save(r.OUT/'final_checks.json',dict(passed=True,checked_at=r.now(),generation_counts=counts,output_truncations=trunc,tests_passed=True,invariant_checks_passed=True,baseline_unchanged=m['baseline_unchanged'],canonical_prompts_unchanged=True,stage2_requests_exclude_original_scores_and_audits=True,stage3_uses_original_unmasked_records=True,first_integration_evaluated=True,final_feedback_usable=False))
r.status('completed',summary=summary,report='validation_report.md',stage3_feedback_usable=False)
print(json.dumps(dict(counts=counts,truncated=trunc,summary=summary),indent=2))
