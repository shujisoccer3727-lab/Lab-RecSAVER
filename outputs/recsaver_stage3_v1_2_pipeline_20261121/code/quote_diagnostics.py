"""Diagnosis only: never alter requests, outputs or handoff."""
import sys
sys.dont_write_bytecode=True
import run as r
from difflib import SequenceMatcher
fixed=r.read(r.OUT/'fixed_input.json');source=next(e for e in fixed['source_essays'] if e['essay_id']=='4902:1');v=r.read(r.OUT/'stage3a/4902_1/parsed.json')
q=v['observations'][0]['quotes'][0];changed=q.replace('"To be yourself','" To be yourself',1)
r.save(r.OUT/'rejected_quote_diagnostics.json',dict(target_essay_id='4902:1',strict_original_exact=q in source['text'],diagnostic_insertion_of_space_after_opening_quote_exact=changed in source['text'],original_excerpt=q,diagnostic_only=True,excluded_from_model_input_and_acceptance=True,duplicate_observation_ids=[o['observation_id'] for o in v['observations']],unique_quoted_strings=len(set(q for o in v['observations'] for q in o['quotes']))))
record=next(x for x in fixed['accepted_records'] if x['record_id']=='4902_1__K2');issue=v['source_analysis_issues'][1];candidates=r.strings(record);closest=max(candidates,key=lambda s:SequenceMatcher(None,issue['candidate_excerpt'],s).ratio())
r.save(r.OUT/'rejected_issue_diagnostics.json',dict(record_id=record['record_id'],generated_excerpt=issue['candidate_excerpt'],closest_source_string=closest,exact_substring=any(issue['candidate_excerpt'] in s for s in candidates),diagnostic_only=True))
print('Space insertion explains target quote failure:',changed in source['text']);print('Closest K2 candidate string:',closest)
