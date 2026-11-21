"""Additional template-contract checks and lexical flags, no semantic auto-approval."""
import sys,re
sys.dont_write_bytecode=True
import run as r
rows={}
for phase,ip in [('stage3b_fixed',r.OUT/'fixed_3b_input.json'),('stage3b_pipeline',r.OUT/'handoff/input_3b.json')]:
    f=r.OUT/phase/'rater_7';v=r.read(f/'parsed.json');payload=r.read(ip);template=v['feedback_paragraph_template'];obs={o['observation_key']:o for o in payload['verified_observations']};rep=obs.get(v['representative_observation_key']);assembly=r.read(f/'assembly_result.json')
    contract=[]
    if rep:
        q=rep['quotes'][v['representative_quote_index']]
        contract=[dict(kind='target_id_not_copied_in_template',pass_=rep['target_essay_id'] not in template),dict(kind='selected_excerpt_not_copied_in_template',pass_=q not in template)]
    text=' '.join([v['rubric_comparison']['explanation'],*v['next_scoring_check'].values(),template])
    rows[phase]=dict(template_contract_checks=contract,template_contract_all_pass=all(c['pass_'] for c in contract),none_direction_alternative_band_terms=re.findall(r'.{0,45}(?:higher band|lower band|comparison band).{0,45}',text,re.I) if v['rubric_comparison']['comparison_direction']=='none' else [],indeterminate_endorsement_lexical_flags=re.findall(r'.{0,45}(?:consistent with|supports? (?:the )?observed score|evidence supports this score).{0,65}',text,re.I) if v['rubric_comparison']['relationship']=='indeterminate' else [],lexical_flags_require_Codex_context_review=True,assembly_pass=assembly['pass_'])
r.save(r.OUT/'template_and_content_flags.json',rows)
print('Template contract checks and review flags saved')
