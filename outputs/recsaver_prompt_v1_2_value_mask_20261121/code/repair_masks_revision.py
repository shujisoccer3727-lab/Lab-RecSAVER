"""Explicit implementation-bug correction before main reconstruction; no LLM resampling."""
import run as r
old=r.read(r.OUT/'run_manifest.json')
oldhash=old['masking_sha256'];old['masking_sha256']=r.sha(r.OUT/'code/masking.py')
old['mask_revision_after_generation']=dict(time=r.now(),old_sha256=oldhash,new_sha256=old['masking_sha256'],reason='Correct false masking of clearly attributed historical Overall3 in new4902 K1/K2. Original code and copies retained in implementation_revision_2. Stage1 raw and sampling unchanged. No main Stage2 called yet.',affected_new_candidates=['4902_1__K1','4902_1__K2'])
r.save(r.OUT/'run_manifest.json',old)
diag_before={t:r.read(r.OUT/'diagnostic_masks'/t/'input.json') for t in ['A','B','C']}
for c in r.cases():
    for rid in r.p.ids(c):
        for root,folder in [(r.BASE,r.OUT/'saved_v1_1_masks'/rid),(r.OUT,r.OUT/'masks'/rid)]:
            r.apply_record(folder,r.read(root/'stage1'/rid/'parsed.json'),r.read(root/'stage1'/rid/'input.json'))
for t in ['A','B','C']:
    inp=r.read(r.BASE/'stage2_diagnostics'/t/'v1_1/input.json');c=next(c for c in r.cases() if c['target']['essay_id']==inp['target']['essay_id'])
    v=r.apply_record(r.OUT/'diagnostic_masks'/t,dict(score_free_analysis=inp['reference_analysis']),dict(history=inp['history'],target=c['target']))
    inp['reference_analysis']=v['masked_analysis'];assert inp==diag_before[t],'Diagnostic request must remain identical across this fix'
print('Corrected mask copies; all diagnostic request payloads unchanged; no raw generations changed.')
