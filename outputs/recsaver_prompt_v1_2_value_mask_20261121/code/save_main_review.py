"""Record actual six-candidate mask preflight; content quality is a separate question."""
import run as r
from masking import mask_analysis
verdicts={}
notes={
'1514_1__K1':'Target/historical numerical values separated. Cohesion-higher/Syntax-lower is qualitative ordering, not an explicit equality to an identified history score. Original broad organization/syntax claims remain under-supported.',
'1514_1__K2':'Numerical target band values masked; all history IDs supplied. Short target passage still used to support broad organization and syntactic-variety claims.',
'1868_1__K1':'Remaining numeral in decision is explicitly this rater\'s history of scoring similar essays with a3, not a direct assertion of target equality. The target quote is retained, but no local keep-learning analysis was added.',
'1868_1__K2':'Explicit target Overall/Traits value masked. Claim that Overall and Traits all had that value is substantively false for Vocabulary/Phraseology, but no numerical value remains. Treat as content issue separately from mask input safety.',
'4902_1__K1':'Historical Overall3 retained after implementation correction; explicit target values masked. Minor-error characterization and rubric/observed-score alignment remain substantive concerns.',
'4902_1__K2':'Numeral in historical pattern/essays-receiving statement is attributed to actual history; target values masked. No explicit same-score relationship, calculation or unique band name found.'}
for c in r.cases():
    for rid in r.p.ids(c):
        folder=r.OUT/'masks'/rid;a=r.read(folder/'mask_audit.json');masked=r.read(folder/'masked_analysis.json')
        assert a['automatic_pass'] and not mask_analysis(masked,c['history'],c['target'])['audit']['changes']
        original=r.read(r.OUT/'stage1'/rid/'parsed.json');assert original['observed_score_alignment']['observed_target_scores']=={k:c['target'][k] for k in ['Overall','Traits']}
        verdicts[rid]=dict(pass_=True,reasons=[],confirmed_remaining_numerical_target_violation=False,confirmed_recoverable_score_relation=False,invalid_history_reference=False,review_scope='All score_free_analysis fields, source-ID roles, explicit equality/calculation/name ambiguities, unchanged quotes and copied observed values inspected.',content_note=notes[rid],mask_values=a['value_replacements'])
        verdicts[rid]['pass']=verdicts[rid].pop('pass_')
r.save(r.OUT/'main_mask_review.json',dict(reviewed_at=r.now(),reviewer='Codex provisional inspection; not human evaluation',candidates=verdicts,mask_version_sha256=r.sha(r.OUT/'code/masking.py'),content_quality_is_not_acceptance_filter=True))
print('Main input mask preflight: 6/6 pass. Content issues retained for separate review.')
