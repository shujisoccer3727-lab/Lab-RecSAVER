"""同一30件・同一生成設定での根拠引用／匿名化指示改訂Pilot。"""
import argparse
import json
from pathlib import Path
from . import rater_tendency_joint_mvp_1000 as core

ROOT = core.ROOT
SOURCE = ROOT / 'outputs/rater_tendency_joint_mvp_1000'
OUT = ROOT / 'outputs/rater_tendency_joint_mvp_1000_grounded_v2'
PROMPT = ROOT / 'prompts/en/rater_tendency_joint_prediction_grounded_v2.txt'


def setup():
    core.OUT, core.PROMPT = OUT, PROMPT
    OUT.mkdir(exist_ok=True)
    if (OUT / 'experiment_config.json').exists():
        return core.verify()
    # Validate v1 fingerprints before reusing its exact manifests and baseline.
    core.OUT = SOURCE
    config = core.verify()
    core.OUT = OUT
    core.status('git_status_before')
    for name in ['target_manifest.csv', 'pilot_targets.csv', 'target_history_manifest.jsonl', 'baseline_A.jsonl', 'integrity_audit.csv']:
        (OUT / name).write_bytes((SOURCE / name).read_bytes())
    inputs = dict(config['input_sha256'])
    for path in [PROMPT, Path(__file__), SOURCE / 'experiment_config.json', SOURCE / 'predictions.jsonl',
                 *[OUT / name for name in ['target_manifest.csv','pilot_targets.csv','target_history_manifest.jsonl','baseline_A.jsonl']]]:
        inputs[str(path.relative_to(ROOT))] = core.previous.sha(path)
    config.update(input_sha256=inputs, revision='grounded_v2',
                  changes='Prompt only: exact target/history quotes, recorded history score grounding, neutral anonymization markers',
                  pilot_selection='Byte-identical pilot_targets.csv reused from v1; no resampling')
    core.save(OUT / 'experiment_config.json', config)
    (OUT / 'predictions.jsonl').touch()
    core.analyze()
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare','pilot','analyze'])
    args = parser.parse_args()
    setup()
    if args.phase == 'pilot':
        core.run()
    elif args.phase == 'analyze':
        core.analyze()


if __name__ == '__main__':
    main()
