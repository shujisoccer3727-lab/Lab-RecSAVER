"""CPU source and implementation checks. No model calls."""
import sys, csv, subprocess, hashlib, ast
sys.dont_write_bytecode = True
import run as r

checks = []
def ck(kind, ok, **details):
    checks.append(dict(kind=kind, pass_=bool(ok), **details))

setup_tree = ast.parse((r.OUT/'code/setup_snapshot.py').read_text(encoding='utf-8'))
insertions = ast.literal_eval(next(n.value for n in setup_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'insertions' for t in n.targets)))
for key, (marker, addition) in insertions.items():
    new_prompt = r.PROMPTS[key].read_bytes()
    old_path = r.PROMPTS[key].with_name(r.PROMPTS[key].name.replace('_v1_6', '_v1_5'))
    old_prompt = old_path.read_bytes()
    newline = b'\r\n' if b'\r\n' in old_prompt else b'\n'
    added = addition.encode().replace(b'\n', newline)
    boundary = newline + marker.encode() + newline
    ck('canonical_specified_insertion_only', new_prompt == old_prompt.replace(boundary, newline+added+marker.encode()+newline), prompt=key)
    ck('canonical_placeholder_and_schema', new_prompt.count(b'{{INPUT_JSON}}') == 1 and b'"schema_version": "1.5"' in new_prompt, prompt=key)

# Compare the saved experiment files with the named commit, not only HEAD.
tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', r.COMMIT, '--', r.BASE.relative_to(r.ROOT).as_posix()], cwd=r.ROOT, text=True).splitlines()
for rel in tracked:
    f = r.ROOT/rel
    committed = subprocess.check_output(['git', 'show', r.COMMIT + ':' + rel], cwd=r.ROOT)
    current = f.read_bytes()
    exact = committed == current
    ck('comparison_commit_content', exact or committed.replace(b'\r\n', b'\n') == current.replace(b'\r\n', b'\n'), file=rel, byte_identical=exact, committed_sha256=hashlib.sha256(committed).hexdigest(), working_sha256=r.sha(f), eol_only_difference=not exact and committed.replace(b'\r\n', b'\n') == current.replace(b'\r\n', b'\n'))

old = r.read(r.BASE/'run_manifest.json')
new = r.read(r.OUT/'run_manifest.json')
for key in ['model', 'generation', 'max_tokens', 'sampling', 'seed', 'system_message', 'chat']:
    ck('manifest_setting_identical', old[key] == new[key], field=key)
old_tree = ast.parse((r.BASE/'code/run.py').read_text())
new_tree = ast.parse((r.OUT/'code/run.py').read_text())
for node in old_tree.body:
    if isinstance(node, ast.FunctionDef) and node.name not in ['prepare']:
        other = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == node.name)
        ck('runner_function_identical', ast.dump(node) == ast.dump(other), function=node.name)
for eid in r.TARGETS:
    name = eid.replace(':', '_')
    ck('3A_saved_input_identical', r.sha(r.OUT/'prepared_3a'/name/'input.json') == r.sha(r.BASE/'stage3a'/name/'input.json'), target=eid)

fixed = r.read(r.OUT/'fixed_input.json')
sources = {s['essay_id']: s for s in fixed['source_essays']}
raw = r.ROOT/'data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv'
if not raw.exists():
    candidates = list((r.ROOT/'data').glob('*.csv'))
    assert len(candidates) == 1, candidates
    raw = candidates[0]
scores = []
with raw.open(encoding='utf-8-sig', newline='') as f:
    for row_number, row in enumerate(csv.DictReader(f), start=2):
        for eid in r.TARGETS:
            source_id, position = eid.split(':')
            # IDs are source row indices (zero based), as in the frozen case manifest.
            if row_number - 2 != int(source_id):
                continue
            src = sources[eid]
            ck('raw_rater_identity', row['Rater_'+position] == fixed['rater_id'], target=eid)
            ck('raw_target_text', row['Text'] == src['text'], target=eid)
            for dimension, value in dict(Overall=src['Overall'], **src['Traits']).items():
                actual = float(row[dimension+'_'+position])
                ck('raw_own_rater_score', actual == value, target=eid, dimension=dimension, saved=value, raw=actual)
            scores.append(dict(target=eid, raw_csv=str(raw.relative_to(r.ROOT)), csv_row=row_number, rater_column='Rater_'+position, rater_id=row['Rater_'+position], own_scores={d:float(row[d+'_'+position]) for d in ['Overall']+list(src['Traits'])}))
ck('raw_both_targets_found', len(scores) == 2)
r.save(r.OUT/'source_checks.json', dict(total=len(checks), passed=sum(c['pass_'] for c in checks), checks=checks, failed=[c for c in checks if not c['pass_']], own_rater_score_provenance=scores))
print('Source checks:', sum(c['pass_'] for c in checks), '/', len(checks))
assert all(c['pass_'] for c in checks), [c for c in checks if not c['pass_']]
