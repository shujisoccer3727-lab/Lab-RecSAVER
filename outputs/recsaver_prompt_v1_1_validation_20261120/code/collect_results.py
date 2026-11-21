"""Build paired comparison tables without treating diagnostic extraction as success."""
from pathlib import Path
import importlib.util,json
out=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',out/'code/run.py');r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
audit=r.read(out/'common_mechanical_audit.json')['versions'];review=r.read(out/'preflight_review.json');rows=[]
old_saved={}
with (r.OLD/'candidate_results.csv').open(encoding='utf-8-sig',newline='') as f:
    import csv
    old_saved={v['candidate_id']:v for v in csv.DictReader(f)}
for c in r.cases():
    for rid in r.ids(c):
        row=dict(candidate_id=rid,essay_id=c['target']['essay_id'],old_saved_confirmed_leak=old_saved[rid]['confirmed_leak'])
        for ver in ['v1_0','v1_1']:
            m=audit[ver][rid];sem=review['baseline_common_review'][rid] if ver=='v1_0' else review['candidates'][rid]
            row.update({f'{ver}_strict_json':m['strict_json'],f'{ver}_structure':m['structure'],f'{ver}_direct_or_recoverable_disclosure':sem['direct_or_recoverable_disclosure'],f'{ver}_numbered_target_band_or_range':sem['numbered_target_band_or_range'],f'{ver}_quote_total':len(m['quotes']),f'{ver}_quote_exact':m.get('quote_counts',{}).get('exact',0),f'{ver}_quote_whitespace_only':m.get('quote_counts',{}).get('whitespace_only',0),f'{ver}_quote_other_changes':sum(v for k,v in m.get('quote_counts',{}).items() if k not in ['exact','whitespace_only']),f'{ver}_observed_scores_complete_equal':m['all_observed_scores_equal'],f'{ver}_missing_traits':';'.join(m['score_missing']),f'{ver}_wrong_score_values':json.dumps(m['score_wrong'],ensure_ascii=False),f'{ver}_patterns':m['pattern_count'],f'{ver}_evidence_items':m['target_evidence_count']})
        row.update(v1_0_history_role_errors=len(audit['v1_0'][rid]['history_role_errors']),v1_1_history_role_errors=len(audit['v1_1'][rid]['history_role_errors']),content_judgement=review['candidates'][rid]['comparison_judgement'],content_reason=review['candidates'][rid]['comparison_reason'],v1_1_preflight_pass=review['candidates'][rid]['pass'])
        rows.append(row)
r.csvsave(out/'stage1_comparison.csv',rows,list(rows[0]))
diag=[]
for test in ['A','B','C']:
    for ver in ['v1_0','v1_1']:
        f=out/'stage2_diagnostics'/test/ver
        if not (f/'result.json').exists():
            diag.append(dict(test=test,version=ver,strict_json=False,structure=False,markdown_fence=False,format_errors='not executed',status=None,overall=None,issues=None,diagnostic_only_status=None,diagnostic_only_overall=None,expected_status='contaminated_input' if test in ['A','B'] else 'not_contaminated',expected_behavior_strict=False,diagnostic_behavior=False,source_issue_identified=False));continue
        res=r.read(f/'result.json');raw=(f/'raw.txt').read_text(encoding='utf-8');strict=r.read(f/'parsed.json') if (f/'parsed.json').exists() else {};d=r.read(f/'diagnostic_reading.json')['value'] or {}
        def expected(v):return v.get('status')=='contaminated_input' and v.get('reconstructed_overall') is None and bool(v.get('reference_analysis_issues')) if test in ['A','B'] else v.get('status') in ['estimated','insufficient_information']
        diag.append(dict(test=test,version=ver,strict_json=res['json_valid'],structure=res['schema_valid'],markdown_fence=raw.strip().startswith('```'),format_errors=';'.join(res['errors']),status=strict.get('status'),overall=strict.get('reconstructed_overall'),issues=json.dumps(strict.get('reference_analysis_issues'),ensure_ascii=False),diagnostic_only_status=d.get('status') if not res['json_valid'] else None,diagnostic_only_overall=d.get('reconstructed_overall') if not res['json_valid'] else None,expected_status='contaminated_input' if test in ['A','B'] else 'not_contaminated',expected_behavior_strict=res['schema_valid'] and expected(strict),diagnostic_behavior=expected(d),source_issue_identified=bool(d.get('reference_analysis_issues')) if test in ['A','B'] else None))
r.csvsave(out/'stage2_diagnostics.csv',diag,list(diag[0]))
r.save(out/'table_metadata.json',dict(created_at=r.now(),semantic_reviewer='Codex provisional; not human evaluation',diagnostic_extraction_excluded_from_acceptance=True,baseline_rule_note='The old saved leak flag combined numbered bands with disclosure and excluded 4902 K2 range. Common review separates disclosure from target band/range application; all six old candidates have band application.'))
print(json.dumps(diag,ensure_ascii=False,indent=2))
