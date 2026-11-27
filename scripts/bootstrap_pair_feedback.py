"""Extract reusable mechanical contracts; never import experiment review verdicts."""
import ast
from pathlib import Path

root = Path(__file__).resolve().parents[1]
dest = root / 'src/recsaver/pair_feedback_contracts.py'
source = root / 'outputs/recsaver_stage3_v1_6_baseline/code/run.py'
names = {'array', 'need', 'obs_schema', 'a_schema', 'b_schema', 'gate_a',
         'sentence', 'quoted_sentence', 'review_and_render'}
text = source.read_text(encoding='utf-8')
tree = ast.parse(text)
parts = [ast.get_source_segment(text, n) for n in tree.body
         if isinstance(n, ast.FunctionDef) and n.name in names]
dest.write_text('"""Mechanical v1.6 contracts, generalized from baseline; no semantic verdicts."""\nimport re\n\n' + '\n\n'.join(parts) + '\n', encoding='utf-8')
source = root / 'outputs/recsaver_prompt_v1_2_value_mask_20261121/code/masking.py'
text = source.read_text(encoding='utf-8').replace('□', '[MASK]')
(root / 'src/recsaver/pair_feedback_masking.py').write_text(text, encoding='utf-8')
print('Extracted mechanical functions and value-only masker.')
