"""実検証payloadの追加検査。引用・履歴得点・IDは検査対象の自由記述から外す。"""
import collections
import json
import re
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    patterns=[r'''["']?(?:overall|score|rating|level|得点|評価点|评分|分数)["']?\s*(?:[:：=]|为|是)\s*["']?(?:[1-5１-５]|one|two|three|four|five|一|二|三|四|五)\b''',r'(?:评分|分数|總分|总分).{0,8}[一二三四五1-5].{0,3}分']
    checks=[];suspects=[];mask_reasons=collections.Counter()
    for path in sorted((out/'conditions').glob('*/verification_inputs/*.json')):
        p=load(path);reason=p['masked_reason']
        fields={k:v for k,v in reason.items() if k in ['rationale','unexplained']}
        for c in reason['claims']:
            fields.update({c['claim_id']+'.'+k:v for k,v in c.items() if k in ['feature','score_relation','support_explanation','limits']})
        for field,value in fields.items():
            for pattern in patterns:
                for m in re.finditer(pattern,value,re.I):
                    suspects.append(dict(file=str(path.relative_to(out)),field=field,match=m.group(),interpretation='Potential direct-score leak requiring inspection; not an automatic judgment'))
        assert set(p['target'])=={'essay_id','text'}
        assert all(set(h)=={'essay_id','text','overall'} for h in p['history'])
        assert all('condition_ids' not in c for c in reason['claims'])
        mask_path=path.parent.parent/'mask'/path.name
        log=load(mask_path)['mask_log'];mask_reasons.update(x['reason'] for x in log)
        checks.append(str(path.relative_to(out)))
    result=dict(timestamp=now(),verification_inputs_checked=len(checks),whitelist_checks_passed=True,additional_free_text_suspects=suspects,mask_reasons=dict(mask_reasons),scope='Only direct disclosure scan; qualitative rubric-based inference is allowed; absence of matches is not a semantic guarantee')
    save(out/'verification_input_audit.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
    assert not suspects,'Inspect potential direct score disclosure before accepting verification results'


if __name__=='__main__': main()
