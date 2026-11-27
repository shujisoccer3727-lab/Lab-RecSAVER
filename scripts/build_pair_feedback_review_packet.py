"""Collect current generated claims with their exact sources for a separate provisional review."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save

ap = argparse.ArgumentParser()
ap.add_argument('--config', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
manifest = read(out / 'manifest.json')
targets = {(t['rater_id'], t['target']['essay_id']): t for t in manifest['fixed_targets']}
packet = []
for pair in cfg['pairs']:
    for rater in pair['raters']:
        folder = out / 'stage5' / rater
        if not (folder / 'parsed.json').exists():
            packet.append(dict(rater_id=rater, status='no_parsed_feedback'))
            continue
        value = read(folder / 'parsed.json')
        inp = read(folder / 'input_3b.json')
        by_key = {o['observation_key']: o for o in inp['verified_observations']}
        keys = {value.get('representative_observation_key')}
        if isinstance(value.get('pattern'), dict):
            keys |= {s['observation_key'] for s in value['pattern']['support']}
        evidence = []
        for key in sorted(k for k in keys if isinstance(k, str) and k in by_key):
            o = by_key[key]
            t = targets[rater, o['target_essay_id']]
            local_input = read(out / 'stage4' / t['key'] / 'input.json')
            catalog = {s['span_id']: s for s in local_input['evidence_spans']}
            text = t['target']['text']
            selected = []
            for sid in o['evidence_span_ids']:
                s = catalog[sid]
                selected.append(dict(s, is_first_text_span=not text[:s['start']].strip(),
                                     is_last_text_span=not text[s['end']:].strip(),
                                     preceding_context=text[max(0, s['start'] - 160):s['start']],
                                     following_context=text[s['end']:s['end'] + 160]))
            evidence.append(dict(observation=o, source=t['source'], exact_source_spans=selected,
                                 note='Position/context added for post-generation provisional review only; not supplied retroactively to Stage 5.'))
        packet.append(dict(rater_id=rater, generated=value, selected_source_evidence=evidence,
                           render_checks=read(folder / 'render_checks.json') if (folder / 'render_checks.json').exists() else None))
save(out / 'feedback_review_packet.json', packet)
print(json.dumps(packet, ensure_ascii=False, indent=2))
