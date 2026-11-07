"""参照プロンプトを保存した共通本文から独立再構築し、不一致対象を特定する。"""
from pathlib import Path
import json
import sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from src.recsaver.config import load_config
from src.recsaver.utils import read_jsonl
config=load_config('configs/human_score_disagreement.yaml');out=root/config['output_dir']
template=(root/config['reference_prompt']).read_text(encoding='utf-8')
rubric=(out/'rubric_used.md').read_text(encoding='utf-8')
mismatches=[]
for item in read_jsonl(out/'prepared_targets.jsonl'):
    expected=template.format(overall_rubric=rubric,rating_history=item['history_text'],target_essay=item['essay'],gold_overall=item['gold_overall'])
    if item['reference_prompt']!=expected:
        first=next((i for i,(a,b) in enumerate(zip(item['reference_prompt'],expected)) if a!=b),min(len(item['reference_prompt']),len(expected)))
        mismatches.append(dict(target_id=item['target_id'],first_difference=first,stored_excerpt=repr(item['reference_prompt'][first:first+90]),expected_excerpt=repr(expected[first:first+90])))
(out/'prompt_audit_mismatches.json').write_text(json.dumps(mismatches,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(mismatches,ensure_ascii=False,indent=2))
