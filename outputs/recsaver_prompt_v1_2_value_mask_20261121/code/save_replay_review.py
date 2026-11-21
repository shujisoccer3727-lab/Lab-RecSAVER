"""Persist Codex's inspected replay verdicts; not an automatic semantic evaluator."""
import run as r
from masking import mask_analysis
candidates={}
for c in r.cases():
    for rid in r.p.ids(c):
        f=r.OUT/'saved_v1_1_masks'/rid;a=r.read(f/'mask_audit.json');masked=r.read(f/'masked_analysis.json')
        assert not mask_analysis(masked,c['history'],c['target'])['audit']['changes']
        bad=rid=='1514_1__K1';assert a['automatic_pass'] is (not bad)
        candidates[rid]=dict(pass_=not bad,remaining_input_violation=bad,invalid_history_reference=bad,review='Codex provisional; all fields inspected. Masked target values replaced only; historical score statements remain attributable to supplied history. Feature-based comparisons are not treated as explicit score equality.',reason='Target1514:1 appears as a history source; source score object cannot be certified history evidence.' if bad else 'No confirmed recoverable target score, numerical target band value or ambiguous attribution remains. Text quality is unchanged by value masking.',mask_values=a['value_replacements'])
        candidates[rid]['pass']=candidates[rid].pop('pass_')
diagnostics={}
for test in ['A','B','C']:
    a=r.read(r.OUT/'diagnostic_masks'/test/'mask_audit.json');assert a['automatic_pass']
    diagnostics[test]=dict(pass_=True,reason='Values in single-band target statements masked.' if test=='A' else 'Both target alternative-band values masked.' if test=='B' else 'No target score value present; all history scores/source numbers retained unchanged.',mask_values=a['value_replacements']);diagnostics[test]['pass']=diagnostics[test].pop('pass_')
c=r.cases()[0];eq=dict(decision_explanation='The target received the same Overall score as history essay 217:1.')
v=mask_analysis(eq,c['history'],c['target']);assert not v['audit']['automatic_pass'] and v['masked_analysis']==eq
r.save(r.OUT/'diagnostic_masks/D_equivalence/original_analysis.json',eq);r.save(r.OUT/'diagnostic_masks/D_equivalence/mask_audit.json',v['audit'])
r.save(r.OUT/'replay_review.json',dict(reviewed_at=r.now(),reviewer='Codex provisional semantic inspection; not human evaluation',candidates=candidates,diagnostics=diagnostics,equivalence_control=dict(pass_=False,reason='Same score as identified history essay is recoverable with no target number. Quarantined unchanged; no Stage2 request.')))
print('Replay reviewed: 5/6 input-eligible; A/B/C eligible; equivalence quarantined.')
