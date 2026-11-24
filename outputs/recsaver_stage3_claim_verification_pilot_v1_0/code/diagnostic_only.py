"""Quarantined reading of fenced 3C responses, never accepted as condition B."""
import sys
sys.dont_write_bytecode=True
import pipeline as p
for gid in p.GROUPS:
    folder=p.OUT/'groups'/gid/'stage3c'
    raw=(folder/'raw.txt').read_text(encoding='utf-8');text=raw.strip()
    assert not (folder/'parsed.json').exists()
    assert text.startswith('```json') and text.endswith('```')
    inner=text.split('\n',1)[1].rsplit('```',1)[0].strip()
    try:
        value=p.json.loads(inner,object_pairs_hook=p.engine_module.legacy.no_dupes)
        error=None
    except Exception as ex:value=None;error=str(ex)
    p.save(folder/'diagnostic_only.json',dict(strict_json_pass=False,transformation='Remove one outer Markdown code fence for quarantined diagnosis only.',excluded_from_condition_B=True,counts_as_processing_success=False,parse_error=error,diagnostic_value=value,raw_sha256=p.sha(folder/'raw.txt')))
    if value is not None:
        p.save(folder/'diagnostic_revised_decision_not_accepted.json',dict(excluded_from_condition_B=True,revised_decision=value.get('revised_decision')))
    print(gid,': strict JSON failed; quarantined diagnostic available =',value is not None,'; B remains failed')
p.finish()
