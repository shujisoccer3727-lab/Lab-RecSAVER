"""Read only the condition-hidden review export, never 3C audit verdicts."""
import json
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]
for record in json.loads((OUT/'review_blind.json').read_text(encoding='utf-8')):
    print('\nREVIEW',record['review_id'],record['case_group'])
    print(json.dumps(record['decision'],ensure_ascii=False,indent=2))
    for selected in record['selected_evidence']:
        position=next(q for q in record['source_positions'] if q['observation_key']==selected['observation_key'] and q['quote_index']==selected['quote_index'])
        print('SELECTED',json.dumps(position,ensure_ascii=False))
    print('OFFICIAL',json.dumps(record['rubric_entries'],ensure_ascii=False))
