from pathlib import Path
import json, shutil

root = Path(__file__).resolve().parent
base = root / 'outputs/recsaver_stage3_v1_5_baseline_20261122'
out = root / 'outputs/recsaver_stage3_v1_6_baseline'
assert not out.exists(), 'Do not overwrite an existing experiment'
insertions = {
    'a': ('TASK', '''LOCAL EVIDENCE AND PASSAGE ROLE

Make one independently checkable claim per observation. In both feature
and scoring_relevance, keep the claim within the selected excerpts. If
two excerpts express a related idea, describe what connects those ideas
and how that local connection relates to the scoring dimension.

Verify any claim about where a passage occurs against its actual
position in target_text. Use labels such as opening, last sentence,
or closing only if the relevant essay or paragraph boundary is
verifiable. A position within a paragraph, a span's order in the
selection, or a repeated idea does not establish that a passage is a
conclusion. Use a rhetorical label such as thesis or conclusion only
when the selected text and its context support that function. If
position or function is uncertain, describe what the selected words
say or how the selected ideas connect, without assigning the label.

Keep scoring_relevance tied to the same local feature. Do not infer
essay-wide focus, coherence, or consistency from an isolated passage.
A limitation does not make an unsupported claim acceptable.

'''),
    'b': ('RUBRIC AND NEXT CHECK', '''CHECK THE REPRESENTATIVE CLAIM AGAINST THE SELECTED QUOTES

The upstream feature is a proposed interpretation. For every factual
part of textual_finding, check that a reader can verify it from the
selected quotes and any supplied source-position information. Quote
provenance confirms the source of the words. It does not by itself
confirm their document position or rhetorical function.

Use labels such as opening, last sentence, or closing only when the
supplied source information establishes the relevant boundary. Use a
rhetorical label such as thesis or conclusion only when the supplied
evidence supports that function. When such support is missing, state
the local feature that the selected words do show. If the remaining
feature is not useful for scoring review, choose another observation
with direct support. Use the existing no-representative option if none
is usable. Keep the next check tied to something observable.

''')}
proof = []
for key, (marker, addition) in insertions.items():
    name = ('recsaver_03a_case_evidence_review' if key == 'a' else 'recsaver_03b_integrated_feedback')
    src = root / 'prompts/en' / (name + '_v1_5.txt')
    dst = src.with_name(name + '_v1_6.txt')
    before = src.read_bytes()
    newline = b'\r\n' if b'\r\n' in before else b'\n'
    added = addition.encode().replace(b'\n', newline)
    boundary = newline + marker.encode() + newline
    assert before.count(boundary) == 1
    after = before.replace(boundary, newline + added + marker.encode() + newline)
    assert after.replace(added, b'', 1) == before
    assert after.count(b'{{INPUT_JSON}}') == 1
    assert b'"schema_version": "1.5"' in after
    assert not dst.exists()
    dst.write_bytes(after)
    proof.append(dict(prompt=str(dst.relative_to(root)), insertion_only=True, schema_version='1.5', placeholder_count=1))
(out / 'code').mkdir(parents=True)
runner = (base / 'code/run.py').read_text(encoding='utf-8')
runner = runner.replace('Fixed three-request v1.5 baseline', 'Fixed three-request v1.6 prompt baseline (v1.5 contract)')
runner = runner.replace("BASE=ROOT/'outputs/recsaver_stage3_v1_4_validation_20261121';COMMIT='1a0015a865b210a084ef08e9d0017f967eedc5de'", "BASE=ROOT/'outputs/recsaver_stage3_v1_5_baseline_20261122';COMMIT='bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac'")
runner = runner.replace('recsaver_03a_case_evidence_review_v1_5.txt', 'recsaver_03a_case_evidence_review_v1_6.txt').replace('recsaver_03b_integrated_feedback_v1_5.txt', 'recsaver_03b_integrated_feedback_v1_6.txt')
start = runner.index("differences=['3A receives")
end = runner.index(']))', start)
runner = runner[:start] + "differences=['Only the specified local-evidence/passage-role English additions in the two v1.6 canonical prompts; output contract remains 1.5.', 'Output path and comparison source updated to v1.5 commit bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac; runner, handoff and renderer reused.', 'No position metadata added to 3B; no candidate-audit prose supplied; no self-verification or SLM revision stage.'" + runner[end:]
(out / 'code/run.py').write_text(runner, encoding='utf-8')
verify = (base / 'code/verify.py').read_text(encoding='utf-8').replace('stage3b_pipeline/rater_7', 'stage3b/rater_7')
(out / 'code/verify.py').write_text(verify, encoding='utf-8')
(out / 'prompt_revision_checks.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
shutil.copyfile(root / 'setup_stage3_v16.py', out / 'code/setup_snapshot.py')
print('Created prompts and minimal runner copy; no model requests yet.')
