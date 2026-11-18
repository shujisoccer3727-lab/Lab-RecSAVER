"""版2.1の証拠重複による文脈上限超過だけを修正し、成功済み上流を引き継ぐ。"""
import collections
import json
import shutil
import traceback
from pathlib import Path
from src.recsaver import rater_feedback_development_v21 as pilot
from src.recsaver.feedback_payload_compaction import compact_payload

ROOT = pilot.ROOT
CONFIG = ROOT/'configs/rater_feedback_development_v22.json'


def prepare():
    old = ROOT/'outputs/rater_feedback_pilot_v2/v2_1'
    out = ROOT/'outputs/rater_feedback_pilot_v2/v2_2'
    assert pilot.load(old/'status.json')['status'].startswith('completed'), 'Previous process must finish first'
    if (out/'resolved_config.json').exists():
        cfg=pilot.load(CONFIG)
        assert all(pilot.sha(ROOT/p)==h for p,h in pilot.load(out/'resolved_config.json')['source_sha256'].items())
        return cfg,out
    out.mkdir(exist_ok=True)
    cfg=pilot.load(pilot.CONFIG)
    cfg.update(output_dir=str(out.relative_to(ROOT)).replace('\\','/'),execution_revision='2.2-lossless-evidence-interning',
        fingerprint_version_note='Keep original 2.1 semantic version solely for identical upstream fingerprints; execution revision 2.2 changes downstream serialization only.')
    pilot.save(CONFIG,cfg)
    for name in ['inputs.json','input_checks.json','rubric.json','conditions.json','selection.json','cause_analysis.json','cause_analysis.md',
                 'old_cases.json','old_manifest.json','old_output_hashes.json','one_review.json','one_development_review.json','one_results.json',
                 'one_summary.json','old_new_comparison.json','old_new_comparison.md','development_review.json']:
        shutil.copy2(old/name,out/name)
    for folder in ['masks']:
        shutil.copytree(old/folder,out/folder,dirs_exist_ok=True)
    copied={}
    for stage in ['generate','verify','ground']:
        for p in (old/'stages'/stage).glob('*.json'):
            assert pilot.load(p)['result'] is not None
            dest=out/'stages'/stage/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            copied[str(dest.relative_to(out)).replace('\\','/')]=dict(sha256=pilot.sha(dest),source=str(p.relative_to(ROOT)))
        shutil.copytree(old/'stage_inputs'/stage,out/'stage_inputs'/stage,dirs_exist_ok=True)
    upstream_calls=[]
    for line in (old/'calls.jsonl').read_text(encoding='utf-8').splitlines():
        call=json.loads(line)
        if call['stage'] in ['generate','verify','ground']:
            upstream_calls.append(line)
    (out/'calls.jsonl').write_text('\n'.join(upstream_calls)+'\n',encoding='utf-8')
    pilot.save(out/'three_resume_cache_before.json',dict(records=copied))
    files=[Path(__file__).resolve(),ROOT/'src/recsaver/feedback_payload_compaction.py',ROOT/'src/recsaver/feedback_development_engine_v22.py',ROOT/'tests/test_feedback_payload_compaction.py',CONFIG]
    sources=dict(pilot.load(old/'resolved_config.json')['source_sha256'])
    sources.update({str(p.relative_to(ROOT)).replace('\\','/'):pilot.sha(p) for p in files})
    pilot.save(out/'resolved_config.json',dict(config=cfg,source_sha256=sources,upstream_source=str(old.relative_to(ROOT)),timestamp=pilot.now()))
    archive=out/'code';shutil.copytree(old/'code',archive)
    for p in files: shutil.copy2(p,archive/p.name)
    pilot.save(out/'revision_note.json',dict(timestamp=pilot.now(),execution_revision='2.2',
        first_failure='2.1 repeated full evidence for each claim: merge1868=32927, integrate=54531, compare1868=48254 prompt tokens; no truncation/model call.',
        fix='Only downstream repeated objects, arrays and long strings serialized once by reference ID; target full text, all original claims, review, exact evidence and official criteria preserved. Every compact payload is losslessly expanded and compared before a call; output JSON schemas still use original expanded data.',
        affected_stages=['merge','integrate','compare','text'],reused_stages=['generate','verify','ground'],
        reused_records=copied,model_sampling_seed_candidate_retry_budget_changed=False,prompt_templates_changed=False,
        no_score_mismatch_regeneration=True,old_outputs_retained=True,not_a_new_research_condition=True))
    return cfg,out


def main():
    cfg,out=prepare()
    from src.recsaver.feedback_development_engine_v22 import Engine
    pilot.save(out/'status.json',dict(timestamp=pilot.now(),status='running',scope='three',execution_revision='2.2'))
    try:
        pilot.run(cfg,out,Engine(cfg,out),'three')
    except BaseException:
        pilot.save(out/'status.json',dict(timestamp=pilot.now(),status='failed',traceback=traceback.format_exc()))
        raise


if __name__=='__main__': main()
