"""Saved-artifact and post-display checks. No inference or assembly changes."""
import sys,csv
sys.dont_write_bytecode=True
import pipeline as p
checks=[]
def ck(name,ok):checks.append(dict(name=name,pass_=bool(ok)))
decision=p.read(p.OUT/'baseline_decision.json');ref={c['claim_id']:c for c in p.read(p.OUT/'independent_reference_review.json')['claims']}
review=[]
for g in p.groups():
    gid=g['group_id'];folder=p.OUT/'groups'/gid;a=p.read(folder/'B/assembly.json');raw=(folder/'stage3c/raw.txt').read_text(encoding='utf-8');parsed=p.read(folder/'stage3c/parsed.json')
    ck(gid+' strict original parse unchanged',p.strict_parse(raw)==parsed and p.sha(folder/'stage3c/raw.txt')==p.read(folder/'stage3c/generation.json')['raw_sha256'])
    ck(gid+' all planned IDs',not p.validate(parsed,p.read(folder/'input_3c.json')))
    ck(gid+' fixed displayed candidates',all(d['candidate']==next(c['display_candidate'] for c in g['claims'] if c['claim_id']==d['claim_id']) for d in a['decisions']))
    ck(gid+' no A fallback',not a['fallback_to_A'])
    actions=[]
    for action in g['next_check_candidates']:
        actions.append(dict(action_id=action['action_id'],kept=action['action_id'] in a['next_check_ids'],premise_claim_ids=action['premise_claim_ids'],independent_premises_supported=all(ref[c]['verdict']=='supported' for c in action['premise_claim_ids'])))
    review.append(dict(group_id=gid,displayed_claims=[dict(claim_id=cid,independent_verdict=ref[cid]['verdict'],source_check=ref[cid]['reason_ja']) for cid in a['displayed_claim_ids']],next_checks=actions,assessment='固定表示候補と原文を照合。LLMの誤支持K06/C02とその元来の確認前提は残存誤りであり、新設と数えない。'))
known=p.read(p.OUT/'groups/known/B/assembly.json');contrast=p.read(p.OUT/'groups/contrast/B/assembly.json');limited=p.read(p.OUT/'groups/limited/B/assembly.json');retention=p.read(p.OUT/'groups/retention/B/assembly.json')
ck('position error removed; local opening kept','K05' not in known['displayed_claim_ids'] and all(c in known['displayed_claim_ids'] for c in ['K01','K02']))
ck('8699 general error retained and article removed','C01' in contrast['displayed_claim_ids'] and 'C03' not in contrast['displayed_claim_ids'] and 'CN2_articles' not in contrast['next_check_ids'])
ck('2016 error and dependent checks removed','L01' not in limited['displayed_claim_ids'] and not limited['next_check_ids'] and not limited['local_finding_retained'])
ck('2016 withheld; no replacement source',limited['reviewed_quotes'][0]['exact_quote']==p.read(p.OUT/'groups/limited/input_3b.json')['verified_observations'][0]['quotes'][0] and 'No verified local finding remains.' in limited['feedback_paragraph'])
ck('4902 valid relation preserved','R01' in retention['displayed_claim_ids'])
ck('residual errors explicitly recorded',decision['residual_unsupported_claims']['known']==['K06'] and decision['residual_unsupported_claims']['contrast']==['C02'])
ck('all existing three groups aggregate; control excluded',decision['existing_three_group_aggregate']['group_ids']==['known','contrast','limited'] and decision['existing_three_group_aggregate']['retention_control_excluded'])
ck('four requests only',len(p.read(p.OUT/'request_ledger.json'))==4)
ck('complete planned verdicts',decision['llm_verdicts_processed']==decision['llm_verdicts_planned']==20)
with (p.OUT/'claim_comparison.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
ck('22 distinct claim records',len(rows)==22 and len({r['claim_id'] for r in rows})==22)
for name in ['claim_manifest.json','run_manifest.json','claim_comparison.csv','validation_report.md']:
    ck('required artifact '+name,(p.OUT/name).is_file())
p.save(p.OUT/'post_display_source_review.json',dict(evaluator='Codex、原文参照判定との暫定照合',groups=review,new_unsupported_claims=[],residual_errors=['K06','C02'],not_a_generalization_evaluation=True))
p.save(p.OUT/'final_integrity_checks.json',dict(total=len(checks),passed=sum(c['pass_'] for c in checks),checks=checks,failed=[c for c in checks if not c['pass_']]))
p.finish();print('Final integrity:',sum(c['pass_'] for c in checks),'/',len(checks))
assert all(c['pass_'] for c in checks),[c for c in checks if not c['pass_']]
