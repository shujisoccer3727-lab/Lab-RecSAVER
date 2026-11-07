"""同一生成内の2スコア比較。固定30件＋承認済み確認用2件。"""
import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
import numpy as np
import pandas as pd
from . import rater_tendency_joint_mvp_1000 as core

ROOT=core.ROOT
OLD=ROOT/'outputs/rater_tendency_reflection_mvp_30'
GROUNDED=ROOT/'outputs/rater_tendency_joint_mvp_1000_grounded_v2'
OUT=ROOT/'outputs/rater_feedback_score_comparison_mvp_30'
PROMPT=ROOT/'prompts/en/rater_feedback_score_comparison_v2.txt'
FIVE=['4816:2','3453:1','4163:2','8814:1','1637:1']
TEXT_FIELDS=['rater_tendency','essay_evidence','rater_conditioned_reasoning','rubric_reference_reasoning','comparison_feedback','uncertainty']
SCORE_FIELDS=['predicted_overall','rubric_reference_overall']


def parse(raw,history_ids):
    text=raw.strip()
    if text.startswith('```'):
        text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
    value=json.loads(text)
    assert isinstance(value,dict) and set(value)==set(TEXT_FIELDS+SCORE_FIELDS)
    assert all(type(value[k]) is int and 1<=value[k]<=5 for k in SCORE_FIELDS)
    assert all(isinstance(value[k],str) and value[k].strip() for k in TEXT_FIELDS)
    cited=re.findall(r'\b\d+:[12]\b',value['rater_tendency']+' '+value['rater_conditioned_reasoning'])
    assert all(h in history_ids for h in cited), 'Invalid historical ID'
    return value


def setup():
    core.OUT,core.PROMPT=OUT,PROMPT
    OUT.mkdir(exist_ok=True)
    if (OUT/'experiment_config.json').exists():
        return core.verify()
    core.OUT=OLD
    config=core.verify()
    core.OUT=OUT
    core.status('git_status_before')
    for name in ['target_manifest.csv','pilot_targets.csv','target_history_manifest.jsonl','baseline_A.jsonl']:
        (OUT/name).write_bytes((OLD/name).read_bytes())
    pilot=pd.read_csv(OUT/'pilot_targets.csv')
    targets=pd.read_csv(OUT/'target_manifest.csv').set_index('target_id')
    extra=[t for t in FIVE if t not in set(pilot.target_id)]
    assert extra==['4816:2','3453:1']
    order=FIVE+[t for t in pilot.target_id if t not in FIVE]
    assert len(order)==32 and len(set(order))==32
    execution=targets.loc[order].reset_index()
    execution['scope']=['main30' if t in set(pilot.target_id) else 'supplemental2' for t in order]
    execution.to_csv(OUT/'execution_order.csv',index=False)
    old={r['target_id']:r for r in core.read(OLD/'predictions.jsonl')}
    grounded={r['target_id']:r for r in core.read(GROUNDED/'predictions.jsonl')}
    core.previous.jsonl(OUT/'previous_reflection.jsonl',[old[t] for t in pilot.target_id])
    core.previous.jsonl(OUT/'previous_grounded.jsonl',[grounded[t] for t in order])
    frame=core.previous.data()
    audit=[]
    for tid in order:
        r=grounded[tid]
        ids=r['history_ids']
        prompt=core.render(frame,tid,ids)
        assert prompt.split('[Official Overall Scoring Rubric]\n',1)[1]==r['prompt'].split('[Official Overall Scoring Rubric]\n',1)[1]
        modified=frame.loc[[tid]+ids].copy()
        modified.loc[tid,['Overall',*core.previous.TRAITS]]=-999
        assert core.render(modified,tid,ids)==prompt
        h=frame.loc[ids]
        target=frame.loc[tid]
        assert len(ids)==3 and h.rater_id.eq(target.rater_id).all()
        assert not h.source_row_id.eq(target.source_row_id).any()
        assert not h.Filename.eq(target.Filename).any() and not h.Text.eq(target.Text).any()
        audit.append({'target_id':tid,'same_input_body':True,'gold_perturbation_invariant':True,'no_same_essay_history':True,
                      'reference_score_produced_without_gold_access':True})
    pd.DataFrame(audit).to_csv(OUT/'integrity_audit.csv',index=False)
    paths=[PROMPT,Path(__file__),OLD/'experiment_config.json',OLD/'predictions.jsonl',GROUNDED/'predictions.jsonl',
           *[OUT/name for name in ['target_manifest.csv','pilot_targets.csv','target_history_manifest.jsonl','execution_order.csv','previous_reflection.jsonl','previous_grounded.jsonl']]]
    config.update(revision='score_comparison_mvp',main_n=30,supplemental_n=2,
        pilot_selection='Unchanged prior 30; 2 supplemental cases authorized by user 2026-10-23; specified five first',
        changes='Prompt and minimal flat 8-field schema/parser only; same single-stage inference',
        input_sha256=dict(config['input_sha256'],**{str(p.relative_to(ROOT)):core.previous.sha(p) for p in paths}))
    core.save(OUT/'experiment_config.json',config)
    (OUT/'predictions.jsonl').touch()
    # Parser checks cover the changed schema, without generating synthetic results.
    good={**{k:'evidence' for k in TEXT_FIELDS},**{k:3 for k in SCORE_FIELDS}}
    assert parse(json.dumps(good),[])==good
    for bad in [dict(good,predicted_overall=True),dict(good,rubric_reference_overall=6),dict(good,comparison_feedback='')]:
        try:
            parse(json.dumps(bad),[])
        except AssertionError:
            pass
        else:
            raise AssertionError('Parser accepted invalid schema')
    return config


def records():
    from .full_prediction_experiment import recover_jsonl
    rows=recover_jsonl(OUT/'predictions.jsonl')
    assert len({r['target_id'] for r in rows})==len(rows)
    digest=core.previous.sha(OUT/'experiment_config.json')
    assert all(r['config_sha256']==digest for r in rows)
    return {r['target_id']:r for r in rows}


def run(phase):
    config=setup()
    if phase=='remaining':
        assert (OUT/'first_five_review.md').exists(), 'Review first five before continuing'
        assert all(t in records() for t in FIVE)
    targets=pd.read_csv(OUT/'execution_order.csv')
    if phase=='first5':
        targets=targets.head(5)
    completed=records()
    pending=[t for t in targets.target_id if t not in completed]
    if not pending:
        print('All requested targets checkpointed; no generation',flush=True)
        return
    gpu=subprocess.run(['/usr/lib/wsl/lib/nvidia-smi','--query-gpu=memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
    assert max(map(int,gpu.stdout.split()))<4000,'GPU occupied; no other process stopped'
    from .model import VLLMGenerator
    from .full_prediction_experiment import append_jsonl
    from vllm import SamplingParams
    generator=VLLMGenerator(config)
    frame=core.previous.data()
    baseline={r['target_id']:r for r in core.read(OUT/'previous_grounded.jsonl')}
    started=time.monotonic()
    for tid in pending:
        ids=baseline[tid]['history_ids']
        prompt=core.render(frame,tid,ids)
        chat=[{'role':'user','content':prompt}]
        tokens=generator.tokenizer.apply_chat_template(chat,tokenize=True,add_generation_prompt=True)
        formatted=generator.tokenizer.apply_chat_template(chat,tokenize=False,add_generation_prompt=True)
        record={'target_id':tid,'history_ids':ids,'prompt':prompt,'prompt_tokens':len(tokens),
                'config_sha256':core.previous.sha(OUT/'experiment_config.json'),'parse_success':False,'attempts':[]}
        if len(tokens)+config['generation']['max_tokens']>config['model']['max_model_len']:
            record['failure_reason']='context_overflow; no truncation'
        else:
            for attempt in range(config['max_parse_retries']+1):
                seed=int(hashlib.sha256(f'{core.SEED}:{tid}:{attempt}'.encode()).hexdigest()[:8],16)
                output=generator.llm.generate([formatted],SamplingParams(**config['generation'],seed=seed),use_tqdm=False)[0].outputs[0]
                record['attempts'].append({'raw':output.text,'output_tokens':len(output.token_ids),'finish_reason':output.finish_reason,'seed':seed})
                try:
                    record.update(parse(output.text,ids),parse_success=True)
                    break
                except (ValueError,AssertionError,TypeError,KeyError) as error:
                    record['failure_reason']=f'invalid_json_schema_or_history_id: {type(error).__name__}'
            record['retry_count']=len(record['attempts'])-1
            if record['parse_success']:
                record.pop('failure_reason',None)
        append_jsonl(OUT/'predictions.jsonl',record)
        completed[tid]=record
        core.save(OUT/'progress.json',{'phase':phase,'completed':len(completed),'total':32,'elapsed_seconds':time.monotonic()-started})
        print(tid,record['parse_success'],len(completed),flush=True)
    core.verify()
    core.status('git_status_after')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['prepare','first5','remaining'])
    phase=parser.parse_args().phase
    setup() if phase=='prepare' else run(phase)
