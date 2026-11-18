"""CPUで入力・引用・マスクと全生成入力のコンテキスト長を事前確認する。"""
import json
from pathlib import Path
from src.recsaver.rater_feedback_pilot_v2 import (
    ROOT, load, save, units, mask_string, masked_reason, verification_payload,
    generation_payload, validate_integration,
)


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json')
    out=ROOT/cfg['output_dir']
    items=load(out/'inputs.json'); rubric=load(out/'rubric.json'); conditions=load(out/'conditions.json')
    for item in items:
        for e in [item['target'],*item['history']]:
            assert ''.join(s['text'] for s in e['spans'])==e['text']
            assert all(e['text'][s['start']:s['end']]==s['text'] for s in e['spans'])
            assert e['rater_id']==item['rater_id']
    long='No punctuation '+('あ'*1100)
    assert ''.join(s['text'] for s in units(long,'test',100))==long
    for c in conditions.values():
        assert c['parent_text'][c['start']:c['end']]==c['text']
    for score in ['Overall is three','score: 3','3 out of 5','5点中3点','Overall.S3.C01','third level','最高得点','５点']:
        masked,logs,residual=mask_string(score,'test')
        assert logs and not residual,(score,masked)
    text='There are 3 reasons and 5 students. essay 1514:1 span U003.'
    assert mask_string(text,'test')[0]==text
    reason={'rationale':'Overall is three. Has examples.', 'claims':[dict(claim_id='C1',scope='target',essay_id=items[0]['target_id'],span_ids=[items[0]['target']['spans'][0]['span_id']],aspect='Grammar',kind='presence',direction='negative',condition_ids=['Overall.S3.C01'],feature='score: 3',score_relation='errors',support_explanation='examples',limits='unknown')], 'gold_overall':3,'traits':{'Grammar':2}}
    masked,logs,residual=masked_reason(reason)
    assert not residual and 'gold_overall' not in masked and 'traits' not in masked
    payload=verification_payload(items[0],masked,rubric)
    assert all('traits' not in h for h in payload['history']) and 'overall' not in payload['target']
    assert 'condition_ids' not in json.dumps(payload)
    # 同じ答案の候補を2件にしても共通傾向として通さない。
    try:
        validate_integration({'patterns':[{'pattern_id':'P1','support':[{'target_id':'x','claim_ids':['a']},{'target_id':'x','claim_ids':['b']}]}]}, {'a':{'target_id':'x'},'b':{'target_id':'x'}}, ['x'])
    except AssertionError:
        pass
    else:
        raise AssertionError('duplicate essay counted as two supports')
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True)
    template=(ROOT/cfg['prompt_dir']/'generate.txt').read_text(encoding='utf-8')
    contexts=[]
    for i in items:
        a=generation_payload(i,'A',rubric,conditions); b=generation_payload(i,'B',rubric,conditions)
        assert 'traits' not in a['target'] and all('traits' not in h for h in a['history'])
        for ar,br in zip([a['target'],*a['history']],[b['target'],*b['history']]):
            assert ar=={k:v for k,v in br.items() if k!='traits'}
        for condition,p in [('A',a),('B',b)]:
            prompt=template+json.dumps(p,ensure_ascii=False,separators=(',',':'))
            n=len(tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True))
            contexts.append(dict(condition=condition,target_id=i['target_id'],prompt_tokens=n,max_new_tokens=cfg['max_tokens']['generate'],fits=n+cfg['max_tokens']['generate']<=cfg['model']['max_model_len']))
    result=dict(targets=len(items),conditions=len(conditions),all_checks_passed=True,contexts=contexts,max_prompt_tokens=max(c['prompt_tokens'] for c in contexts))
    save(out/'preflight_checks.json',result)
    assert all(c['fits'] for c in contexts),'Context overflow: do not generate/truncate'
    print(json.dumps({k:v for k,v in result.items() if k!='contexts'},ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
