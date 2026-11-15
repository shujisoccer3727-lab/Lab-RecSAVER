"""Inspect every exact chat input with the deployed tokenizer, without loading a GPU model."""
import json
import os
from pathlib import Path
import sys

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.human_score_disagreement_rater_tendency_inline import read_jsonl, atomic


def main():
    from transformers import AutoTokenizer
    out = ROOT / 'outputs/human_score_disagreement_rater_tendency_inline'
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    config = manifest['config']
    tokenizer = AutoTokenizer.from_pretrained(config['model']['model_id'], local_files_only=True, trust_remote_code=True)
    lengths = {}
    for item in read_jsonl(out / 'inputs.jsonl'):
        lengths[item['target_id']] = len(tokenizer.apply_chat_template(
            [dict(role='user', content=item['prompt'])], tokenize=True, add_generation_prompt=True))
    limit = config['model']['max_model_len']
    maximum_output = config['generation']['max_tokens']
    overflow = {tid: n for tid, n in lengths.items() if n + maximum_output > limit}
    result = dict(fingerprint=manifest['fingerprint'], target_count=len(lengths), min_prompt_tokens=min(lengths.values()),
                  max_prompt_tokens=max(lengths.values()), max_model_len=limit, reserved_output_tokens=maximum_output,
                  over_limit_targets=overflow, prompt_tokens_by_target=lengths)
    atomic(out / 'context_audit.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'prompt_tokens_by_target'}, indent=2))


if __name__ == '__main__':
    main()
