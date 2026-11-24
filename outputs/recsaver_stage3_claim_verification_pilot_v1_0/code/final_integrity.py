"""Final artifact consistency; never create an accepted B from diagnostics."""
import sys,csv
sys.dont_write_bytecode=True
import pipeline as p
checks=[]
def ck(name,ok):
    checks.append(dict(name=name,pass_=bool(ok)))
summary=p.read(p.OUT/'pilot_summary.json');ledger=p.read(p.OUT/'request_ledger.json')
ck('nine_requests_only',len(ledger)==9)
for entry in ledger:
    f=p.OUT/entry['request'];generation=p.read(f/'generation.json')
    ck('unchanged_raw_'+entry['request'],p.sha(f/'raw.txt')==generation['raw_sha256'])
    ck('no_retry_'+entry['request'],generation['attempt']==0)
for gid in p.GROUPS:
    folder=p.OUT/'groups'/gid;f=folder/'stage3c';status=p.read(folder/'B/status.json')
    ck('failed_closed_'+gid,not status['processing_success'] and not status['fallback_to_A'] and not (folder/'B/feedback_paragraph.txt').exists() and not (folder/'B/parsed.json').exists())
    ck('no_formal_parse_'+gid,not p.read(f/'result.json')['json_valid'] and not (f/'parsed.json').exists())
    diagnostic=p.read(f/'diagnostic_only.json')
    ck('quarantine_only_'+gid,diagnostic['excluded_from_condition_B'] and not diagnostic['counts_as_processing_success'])
    ck('diagnostic_revision_unchanged_'+gid,diagnostic['diagnostic_value']['revised_decision']==p.read(folder/'A/parsed.json'))
    metric=next(m for m in summary['groups'] if m['group_id']==gid)
    ck('failed_quality_metrics_are_NA_'+gid,all(metric[k] is None for k in ['B_total_claims','B_unsupported_claims','same_findings_retained','supported_findings_replaced','added_unsupported_claims_B','B_grounded_local_finding','B_concrete_next_check']))
    (folder/'B/processing_failure.txt').write_text('No accepted feedback paragraph was produced. Stage 3C returned a Markdown-fenced response, which failed the strict JSON contract. No repair, regeneration, or fallback to condition A was performed. Diagnostic-only readings are quarantined under stage3c and are not condition B.\n',encoding='utf-8')
review=p.read(p.OUT/'review_judgments.json');mapping={m['review_id']:m for m in p.read(p.OUT/'review_key.json')}
for rv in review['reviews']:
    gid=mapping[rv['review_id']]['group_id'];payload=p.read(p.OUT/'groups'/gid/'input_3b.json')
    obs={o['observation_key']:o for o in payload['verified_observations']};refs={r['rubric_ref_id']:r for r in payload['rubric_entries']}
    for claim in rv['claims']:
        valid=True
        for ref in claim['references']:
            o=obs.get(ref['observation_key']);valid &= o is not None and all(type(i) is int and 0<=i<len(o['quotes']) for i in ref['quote_indices'])
            if ref.get('rubric_ref_id'):
                rub=refs.get(ref['rubric_ref_id']);valid &= rub is not None and rub['dimension']==o['dimension']
        ck('independent_review_refs_'+rv['review_id']+'_'+claim['claim_id'],valid)
ck('new_group_A_claim_counts',summary['new_group_A_unsupported']==3 and summary['new_group_A_total_claims']==10)
ck('new_group_B_not_zero',summary['new_group_B_unsupported'] is None and summary['new_group_B_total_claims'] is None)
ck('display_counts_and_stop',summary['normal_display_groups_A']==3 and summary['normal_display_groups_B']==0 and not summary['next_comparison_guide_met'] and summary['stop_after_this_pilot'])
with (p.OUT/'claim_comparison.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
ck('claim_csv_counts',sum(r['record_type']=='claim' for r in rows)==17 and sum(r['record_type']=='processing_status_not_a_claim' for r in rows)==3)
ck('review_table_omits_audit_verdicts','claim_checks' not in (p.OUT/'review_blind.json').read_text(encoding='utf-8'))
for name in ['selection_manifest.json','run_manifest.json','claim_comparison.csv','validation_report.md','cost_summary.json','review_protocol.json']:
    ck('required_file_'+name,(p.OUT/name).is_file())
p.save(p.OUT/'final_integrity_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),checks=checks,failed=[c for c in checks if not c['pass_']]))
p.finish()
print('Final integrity:',sum(c['pass_'] for c in checks),'/',len(checks))
assert all(c['pass_'] for c in checks),[c for c in checks if not c['pass_']]
