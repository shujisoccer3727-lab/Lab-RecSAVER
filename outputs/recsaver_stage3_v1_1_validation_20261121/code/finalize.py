"""Final immutable-source and request checks; no generation."""
import sys
sys.dont_write_bytecode=True
import run as r
r.audit()
old=r.read(r.BF/'messages.json');new=r.read(r.F/'messages.json')
payload=r.read(r.F/'input.json');text=r.PROMPT.read_bytes().decode('utf-8')
old_chat=(r.BF/'rendered_chat.txt').read_bytes().decode('utf-8')
new_chat=(r.F/'rendered_chat.txt').read_bytes().decode('utf-8')
import json
checks=dict(input_byte_identical=r.sha(r.BF/'input.json')==r.sha(r.F/'input.json'),sampling_identical=r.read(r.BF/'sampling.json')==r.read(r.F/'sampling.json'),only_placeholder_substitution=new==[dict(role='user',content=text.replace('{{INPUT_JSON}}',json.dumps(payload,ensure_ascii=False,allow_nan=False)))],chat_template_identical=old_chat.replace(old[0]['content'],new[0]['content'])==new_chat,raw_hash_matches=r.sha(r.F/'raw.txt')==r.read(r.F/'generation.json')['raw_sha256'],no_truncation=not r.read(r.F/'result.json')['truncated'],model_snapshot_identical=r.read(r.OUT/'environment.json')['model_snapshot']==r.read(r.BASE/'environment.json')['model_snapshot'])
assert all(checks.values()),checks
m=r.read(r.OUT/'run_manifest.json');m['implementation_files_sha256']={str(f.relative_to(r.OUT)):r.sha(f) for f in (r.OUT/'code').glob('*.py')};m['request_invariants']=checks;m['actual_model_calls']=1;m['stage1_calls']=0;m['stage2_calls']=0
r.save(r.OUT/'run_manifest.json',m)
for label,folder in [('v1_0',r.BF),('v1_1',r.F)]:
    v=r.read(folder/'parsed.json');sources={s['essay_id']:s['text'] for s in payload['source_essays']};paragraph=v['feedback_paragraph']
    matches=[]
    def walk(x):
        if isinstance(x,dict):
            for q in x.get('quotes',[]):
                eid=x.get('target_essay_id')
                if q in paragraph and eid in paragraph and q in sources.get(eid,''):matches.append(dict(target_essay_id=eid,quote=q))
            for y in x.values():walk(y)
        elif isinstance(x,list):
            for y in x:walk(y)
    walk(v)
    checks[label+'_paragraph_verified_structured_excerpt_present']=bool(matches)
    checks[label+'_paragraph_excerpt_matches']=matches
r.save(r.OUT/'invariant_checks.json',checks)
print(json.dumps(checks,ensure_ascii=False,indent=2))
