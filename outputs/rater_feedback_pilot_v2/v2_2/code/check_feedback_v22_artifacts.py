"""最終成果物・参照先・保存状態の検査。モデルは呼び出さない。"""
import json
import re
import shutil
from pathlib import Path
from src.recsaver.rater_feedback_development_v21 import ROOT,load,save,sha,now


def main():
    out=ROOT/'outputs/rater_feedback_pilot_v2/v2_2';broken=[]
    for name in ['README.md','report.md','assessment.md','feedback.md','old_new_comparison.md']:
        text=(out/name).read_text(encoding='utf-8')
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if '://' not in link and not (out/link.split('#')[0]).exists(): broken.append([name,link])
    assert not broken,broken
    for path in out.glob('*.json'):load(path)
    cfg=load(out/'resolved_config.json')
    assert all(sha(ROOT/p)==h for p,h in cfg['source_sha256'].items())
    assert all(sha(ROOT/p)==h for p,h in load(out/'old_output_hashes.json').items())
    assert all(sha(out/p)==v['sha256'] for p,v in load(out/'three_resume_cache_before.json')['records'].items())
    assert load(out/'three_development_review.json')['result_sha256']==sha(out/'three_results.json')
    assert load(out/'completion.json')['all_requested_stages_executed']
    readme=(out/'README.md').read_text(encoding='utf-8')
    assert all('outputs/rater_feedback_pilot_v2/v2_2/'+p in readme for p in ['report.md','assessment.md'])
    save(out/'artifact_checks.json',dict(timestamp=now(),all_checks_passed=True,broken_links=broken,
        frozen_sources_unchanged=True,original_v16_outputs_unchanged=True,reused_upstream_cache_records_unchanged=18,
        report='outputs/rater_feedback_pilot_v2/v2_2/report.md',assessment='outputs/rater_feedback_pilot_v2/v2_2/assessment.md'))
    shutil.copy2(Path(__file__).resolve(),out/'code'/Path(__file__).name)
    print(json.dumps(load(out/'artifact_checks.json'),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
