"""Record the one initialization-only interruption; never discard an inference."""
import sys
sys.dont_write_bytecode=True
import pipeline as p
assert not list((p.OUT/'groups').glob('**/raw.txt'))
log=(p.OUT/'execution.log').read_text(encoding='utf-8')
assert 'Loading model weights took' not in log and 'Processed prompts:' not in log
assert not (p.OUT/'initialization_interruption.json').exists()
process=p.read(p.OUT/'process.json');ledger=p.read(p.OUT/'request_ledger.json')
assert len(ledger)==1 and ledger[0]['stage']=='c'
(p.OUT/'process.json').rename(p.OUT/'initialization_interrupted_process.json')
(p.OUT/'request_ledger.json').rename(p.OUT/'initialization_interrupted_prepared_request.json')
p.save(p.OUT/'initialization_interruption.json',dict(recorded_at=p.r.p.now(),process=process,prepared_requests=ledger,model_generate_calls=0,outputs_discarded=0,reason='Existing handoff had a hardcoded both Overall=3 limit; replaced before inference with a neutral same-rater two-essay limit for new groups.',proof='Worker stopped before model weights finished loading. No Processed prompts entry or raw response existed.',log_sha256_at_interruption=p.sha(p.OUT/'execution.log')))
m=p.read(p.OUT/'run_manifest.json');m['initialization_interruptions_before_inference']=1;m['initialization_interruption_path']='initialization_interruption.json';m['new_group_limit_metadata']='Old both Overall=3 sentence replaced with accurate neutral same-rater two-essay statement; known saved input unchanged.';p.save(p.OUT/'run_manifest.json',m)
print('Preserved interrupted initialization; zero inference outputs discarded.')
