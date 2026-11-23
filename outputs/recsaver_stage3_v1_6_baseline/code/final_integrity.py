"""Check saved final artifacts only. No generation or transformation."""
import sys,json
from pathlib import Path
sys.dont_write_bytecode=True
out=Path(__file__).resolve().parents[1]
files=list(out.glob('stage3*/*/raw.txt'))
assert len(files)==3
assert all(json.loads(f.read_text(encoding='utf-8'))==json.loads(f.with_name('parsed.json').read_text(encoding='utf-8')) for f in files)
manifest=json.loads((out/'run_manifest.json').read_text(encoding='utf-8'))
assert manifest['actual_requests']==manifest['generation_request_count']==3
assert manifest['baseline_unchanged'] and manifest['prompts_unchanged']
for name in ['run_manifest.json','baseline_decision.json','validation_report.md','restored_quotes.json','position_regression_1868.json','stage3b/rater_7/feedback_paragraph.txt']:
    assert (out/name).is_file(),name
print('Final artifacts: 3 raw/parsed pairs intact; prompts and comparison source unchanged; decision saved.')
