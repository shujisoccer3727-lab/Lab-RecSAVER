"""grounded v2の単一生成をそのまま使う、固定30件のPrompt拡張実験。"""
import argparse
import json
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from . import rater_tendency_grounded_pilot_v2 as grounded

core = grounded.core
ROOT = core.ROOT
SOURCE = grounded.OUT
OUT = ROOT / 'outputs/rater_tendency_reflection_mvp_30'
PROMPT = ROOT / 'prompts/en/rater_tendency_joint_prediction_reflection_mvp.txt'


def timestamp():
    return datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()


def setup():
    core.OUT, core.PROMPT = OUT, PROMPT
    OUT.mkdir(exist_ok=True)
    if (OUT / 'experiment_config.json').exists():
        return core.verify()
    core.OUT = SOURCE
    config = core.verify()
    core.OUT = OUT
    core.status('git_status_before')
    for name in ['target_manifest.csv','pilot_targets.csv','target_history_manifest.jsonl','baseline_A.jsonl']:
        (OUT / name).write_bytes((SOURCE / name).read_bytes())
    ids = pd.read_csv(OUT / 'pilot_targets.csv').target_id.tolist()
    source = {r['target_id']:r for r in core.read(SOURCE / 'predictions.jsonl')}
    core.previous.jsonl(OUT / 'grounded_v2_baseline.jsonl', [source[t] for t in ids])
    frame = core.previous.data()
    audit = []
    for tid in ids:
        r = source[tid]
        prompt = core.render(frame,tid,r['history_ids'])
        suffix = '[Official Overall Scoring Rubric]\n'
        assert prompt.split(suffix,1)[1] == r['prompt'].split(suffix,1)[1]
        modified = frame.loc[[tid]+r['history_ids']].copy()
        modified.loc[tid,['Overall',*core.previous.TRAITS]] = -999
        assert core.render(modified,tid,r['history_ids']) == prompt
        audit.append({'target_id':tid,'same_rubric_history_target':True,'gold_perturbation_invariant':True,
                      'same_history_ids':True,'single_generation_pipeline':True})
    pd.DataFrame(audit).to_csv(OUT / 'integrity_audit.csv',index=False)
    paths = [PROMPT,Path(__file__),SOURCE/'experiment_config.json',SOURCE/'predictions.jsonl',
             *[OUT/name for name in ['target_manifest.csv','pilot_targets.csv','target_history_manifest.jsonl','baseline_A.jsonl','grounded_v2_baseline.jsonl']]]
    config.update(revision='reflection_mvp_30',changes='Prompt content only; same JSON schema, inference and parsing functions, no extra stages',
                  pilot_selection='Reuse byte-identical grounded v2 pilot_targets.csv; 30 targets, no resampling',
                  input_sha256=dict(config['input_sha256'],**{str(p.relative_to(ROOT)):core.previous.sha(p) for p in paths}))
    core.save(OUT/'experiment_config.json',config)
    (OUT/'predictions.jsonl').touch()
    return config


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['prepare','pilot','analyze','launch'])
    phase=parser.parse_args().phase
    setup()
    if phase=='launch':
        status=OUT/'execution_status.json'
        if status.exists():
            prior=json.loads(status.read_text())
            if prior.get('status')=='running':
                try:
                    os.kill(prior['pid'],0)
                except ProcessLookupError:
                    pass
                else:
                    raise RuntimeError('Already running')
        with (OUT/'execution.log').open('a',encoding='utf-8') as log:
            p=subprocess.Popen([sys.executable,'-u','-m','src.recsaver.rater_tendency_reflection_mvp','pilot'],
                cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        print(f'Launched PID={p.pid}',flush=True)
    elif phase=='pilot':
        state={'status':'running','pid':os.getpid(),'started_at':timestamp()}
        core.save(OUT/'execution_status.json',state)
        try:
            core.run()  # Same run/render/parse/VLLMGenerator; only Prompt and destination differ.
            from .rater_tendency_reflection_review import review
            review()
            state['status']='completed'
        except BaseException:
            state.update(status='failed',error=traceback.format_exc())
            raise
        finally:
            state['ended_at']=timestamp()
            core.save(OUT/'execution_status.json',state)
    elif phase=='analyze':
        from .rater_tendency_reflection_review import review
        review()


if __name__=='__main__':
    main()
