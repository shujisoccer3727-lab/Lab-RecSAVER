"""Inspect installed guided-decoding support without loading a model."""
from pathlib import Path
import ast,importlib.util,json
base=Path('/home/guestuser/miniforge3/envs/qwen3/lib/python3.10/site-packages')
path=base/'vllm/sampling_params.py'
tree=ast.parse(path.read_text())
for node in tree.body:
    if isinstance(node,ast.ClassDef) and node.name in ['GuidedDecodingParams','SamplingParams']:
        print(node.name)
        for n in node.body:
            if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id in ['json','guided_decoding','backend','regex','choice','whitespace_pattern']:
                print(ast.get_source_segment(path.read_text(),n))
print('backends',json.dumps({name:importlib.util.find_spec(name) is not None for name in ['outlines','xgrammar','jsonschema']}))
for p in (base/'vllm/model_executor/guided_decoding').glob('*.py'):
    print(p.name)
for name in ['__init__.py','outlines_decoding.py']:
    source=(base/'vllm/model_executor/guided_decoding'/name).read_text()
    tree=ast.parse(source)
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and ('local' in n.name or 'outlines' in n.name):
            print(ast.get_source_segment(source,n)[:4500])
