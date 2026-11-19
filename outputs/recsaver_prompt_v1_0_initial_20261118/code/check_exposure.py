"""Check whether any valid same-rater essay is absent from a known prior experiment."""
from pathlib import Path
import csv, importlib.util
out=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('exp',out/'code/run.py');run=importlib.util.module_from_spec(sp);sp.loader.exec_module(run)
prior=run.ROOT/'outputs/full_prediction_main_results/common_targets.csv'
with prior.open(encoding='utf-8-sig',newline='') as f: used={r['target_id'] for r in csv.DictReader(f)}
with (run.ROOT/'data/processed/rater_essay_wide.csv').open(encoding='utf-8-sig',newline='') as f:
    eligible=[r for r in csv.DictReader(f) if r['rater_id']=='rater_7' and all(r[t] in ['1','2','3','4','5','1.0','2.0','3.0','4.0','5.0'] for t in ['Overall']+run.TRAITS)]
ids={f"{r['source_row_id']}:{r['rater_position']}" for r in eligible}
result=dict(source=run.source(prior),source_sha256=run.sha(prior),valid_same_rater_count=len(ids),already_in_prior_targets=len(ids&used),absent_from_prior_target_set=sorted(ids-used),meaning='Prior target exposure excludes these essays from certified unused final evaluation. Absence alone would not certify unused elsewhere.')
run.save(out/'prior_exposure_audit.json',result)
m=run.read(out/'case_manifest.json')
for r in m['reserved']:
    if r['essay_id'] in used:r['prior_exposure']='confirmed prior target in '+run.source(prior)+'; cannot serve as unused final evaluation'
run.save(out/'case_manifest.json',m)
print(result)
