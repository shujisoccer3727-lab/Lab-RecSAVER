"""変更のない上流3段階だけを、入力同一性の証明付きで次版へ引き継ぐ。"""
import json
import shutil
import argparse
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,append,sha,digest,now


def fingerprint(prompt,cfg,stage):
    return digest(prompt+json.dumps(dict(model=cfg['model'],generation=cfg['generation'],max_tokens=cfg['max_tokens'][stage],version=cfg['version']),sort_keys=True))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='outputs/rater_feedback_pilot_v2/v1_3')
    parser.add_argument('--stages',nargs='+',default=['generate','verify','ground'])
    args=parser.parse_args()
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    src=ROOT/args.source;old=load(src/'resolved_config.json')['config']
    assert not (out/'upstream_reuse.json').exists(),'reuse already recorded; do not duplicate histories'
    for key in ['model','generation','seed','conditions','candidates_per_target','span_max_chars','source_inputs','source_selection']:
        assert cfg[key]==old[key],f'changed upstream setting: {key}'
    assert sha(src/'inputs.json')==sha(out/'inputs.json')
    stages=args.stages;calls=[json.loads(x) for x in (src/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    bases={}
    for c in calls:
        if c['stage'] in stages: bases.setdefault((c['stage'],c['key']),c)
    reuse=[]
    for stage in stages:
        assert cfg['max_tokens'][stage]==old['max_tokens'][stage]
        if stage in cfg.get('guided_stages',[]):
            assert cfg['guided_backend']==old['guided_backend']
            from src.recsaver.feedback_output_schema import output_schema
            for (s,key),c in bases.items():
                if s==stage:
                    payload=json.loads(c['prompt'].split('INPUT_JSON:')[1])
                    assert output_schema(stage,payload)==c['output_json_schema'],'schema changed: cannot reuse this stage'
        assert sha(ROOT/cfg['prompt_dir']/f'{stage}.txt')==sha(ROOT/old['prompt_dir']/f'{stage}.txt')
        for p in (src/'stages'/stage).glob('*.json'):
            prior=load(p)
            matching=[c for (s,key),c in bases.items() if s==stage and (key.replace(':','_').replace('|','__')+'.json')==p.name]
            assert len(matching)==1
            base=matching[0];assert fingerprint(base['prompt'],old,stage)==prior['fingerprint']
            newfp=fingerprint(base['prompt'],cfg,stage)
            result=dict(prior,fingerprint=newfp,reused_from=str(p.relative_to(ROOT)),source_fingerprint=prior['fingerprint'],reuse_recorded_at=now())
            save(out/'stages'/stage/p.name,result)
            reuse.append(dict(stage=stage,key=base['key'],source_path=str(p.relative_to(ROOT)),source_sha256=sha(p),source_fingerprint=prior['fingerprint'],fingerprint=newfp,input_prompt_identical=True,sampling_model_parameters_identical=True,failed_candidate_remains_failed=prior['result'] is None))
    for c in calls:
        if c['stage'] not in stages: continue
        record=dict(c,reused_not_new_call=True,source_call_history=str((src/'calls.jsonl').relative_to(ROOT)),source_version=old['version'],source_fingerprint=c['fingerprint'],fingerprint=fingerprint(bases[(c['stage'],c['key'])]['prompt'],cfg,c['stage']),reuse_recorded_at=now())
        append(out/'calls.jsonl',record)
    for line in (src/'context_checks.jsonl').read_text(encoding='utf-8').splitlines():
        c=json.loads(line)
        if c['stage'] in stages: append(out/'context_checks.jsonl',dict(c,reused_from=old['version']))
    save(out/'upstream_reuse.json',dict(timestamp=now(),source_version=old['version'],source_call_history_sha256=sha(src/'calls.jsonl'),reason='Unchanged stages only: prompts, schemas, model, sampling, IDs, text and fixed output budgets verified',entries=reuse,new_model_calls_for_reused_entries=0,all_affected_downstream_results_regenerated=True))
    shutil.copy2(ROOT/'scripts/reuse_feedback_v2_upstream.py',out/'code/reuse_feedback_v2_upstream.py')
    print(f'Reused {len(reuse)} unchanged upstream records; old failed candidates retained; downstream not copied',flush=True)


if __name__=='__main__': main()
