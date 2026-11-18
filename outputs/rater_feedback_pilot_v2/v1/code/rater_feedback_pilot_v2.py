"""Trait有無を対にした、新規理由→マスク→自己検証→統合→照合の予備実験。"""
from __future__ import annotations
import argparse
import collections
import copy
import json
import re
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from .rater_feedback_pilot import ROOT, now, sha, digest, save, append, csv_rows, read

TRAITS=['Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']
ASPECTS=['Overall',*TRAITS]
WORDS=r'(?:[1-5１-５]|one|two|three|four|five|一|二|三|四|五)'
LEAK_PATTERNS=[
 ('condition_id',r'\b(?:Overall|Cohesion|Syntax|Vocabulary|Phraseology|Grammar|Conventions)\.S[1-5](?:\.C\d+)?\b'),
 ('fraction',rf'\b{WORDS}\s*(?:/|out\s+of)\s*(?:5|five)\b'),
 ('japanese_fraction',r'[1-5一二三四五]\s*点中\s*[1-5一二三四五]\s*点'),
 ('score_declaration',rf'\b(?:overall|cohesion|syntax|vocabulary|phraseology|grammar|conventions|score|scored|rating|rated|level|band)\s*(?:(?:score|rating)\s*)?(?:(?:is|was|of|at|as|a)\s*){{0,3}}[:=\-]?\s*{WORDS}\b'),
 ('reverse_score',rf'\b{WORDS}\s*(?:points?|point\s+score)\b'),
 ('japanese_score',r'(?:[1-5１-５一二三四五]\s*点|(?:レベル|段階|得点|評価点)\s*[:：=]?\s*[1-5１-５一二三四五]|第[1-5１-５一二三四五]段階)'),
 ('ordinal_level',r'\b(?:first|second|third|fourth|fifth)\s+(?:level|band|rating|score)\b'),
 ('verbal_level',r'\b(?:the\s+)?(?:highest|lowest|middle|top|bottom)\s+(?:score|level|rating|band)\b|(?:最高|最低|中間)の?(?:得点|評価段階)'),
]


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def units(text, essay_id, limit=420):
    """文境界を優先するが、分割不能でも固定長で全字を保持する。"""
    ends=[m.end() for m in re.finditer(r'[.!?](?:[\t ]+|\r?\n+)|\r?\n\s*\r?\n',text)]
    ends.append(len(text))
    spans=[]; start=0
    for end in sorted(set(ends)):
        while end-start>limit:
            stop=start+limit
            spans.append(dict(span_id=f'{essay_id}@U{len(spans)+1:03}',start=start,end=stop,text=text[start:stop]))
            start=stop
        if end>start:
            spans.append(dict(span_id=f'{essay_id}@U{len(spans)+1:03}',start=start,end=end,text=text[start:end]))
            start=end
    assert ''.join(s['text'] for s in spans)==text
    assert all(text[s['start']:s['end']]==s['text'] for s in spans)
    return spans


def condition_catalog(structured):
    catalog={}
    for score, facets in structured['scores'].items():
        for aspect in ASPECTS:
            parent=facets[aspect]
            # セミコロン・文末単位。限定を含む節を途中で分断しない。
            pieces=list(re.finditer(r'[^;.]+(?:[;.]|$)',parent))
            for n, m in enumerate(pieces,1):
                start=m.start()+len(m.group())-len(m.group().lstrip())
                text=parent[start:m.end()]
                if not text.strip():
                    continue
                cid=f'{aspect}.S{score}.C{n:02}'
                catalog[cid]=dict(condition_id=cid,aspect=aspect,level=int(score),text=text,
                                  parent_id=f'{aspect}.S{score}',parent_text=parent,start=start,end=m.end(),
                                  source='rubrics/ellipse_rubric_structured.json',role='primary' if aspect=='Overall' else 'auxiliary analytic criterion')
                assert parent[start:m.end()]==text
    return catalog


def mask_string(text, path):
    logs=[]
    for reason, pattern in LEAK_PATTERNS:
        def replacement(m):
            logs.append(dict(path=path,start=m.start(),end=m.end(),original=m.group(),replacement='[得点表現除去]',reason=reason,offset_basis='current sequential text'))
            return '[得点表現除去]'
        text=re.sub(pattern,replacement,text,flags=re.I)
    residual=[dict(reason=r,match=m.group()) for r,p in LEAK_PATTERNS for m in re.finditer(p,text,flags=re.I)]
    return text, logs, residual


def masked_reason(reason):
    """得点・条件メタデータはwhitelistで落とし、引用はここでは再生成しない。"""
    output={}; logs=[]; residual=[]
    for key in ['rationale','unexplained']:
        output[key],log,rest=mask_string(reason.get(key,''),key)
        logs+=log; residual+=rest
    output['claims']=[]
    for c in reason.get('claims',[]):
        safe={k:c[k] for k in ['claim_id','scope','essay_id','span_ids','aspect','kind','direction'] if k in c}
        for k in ['feature','score_relation','support_explanation','limits']:
            safe[k],log,rest=mask_string(c.get(k,''),f"{c.get('claim_id')}.{k}")
            logs+=log;residual+=rest
        if 'condition_ids' in c:
            logs.append(dict(path=f"{c.get('claim_id')}.condition_ids",original=c['condition_ids'],replacement=None,reason='target-linked criterion metadata removed entirely'))
        output['claims'].append(safe)
    for k in set(reason)-{'rationale','claims','unexplained'}:
        logs.append(dict(path=k,original=reason[k],replacement=None,reason='not in verification whitelist'))
    return output, logs, residual


def score_record(row, raw, expected_rater=None):
    source=int(row['source_row_id']); position=row['rater_position']; original=raw[source]
    rater=original[f'Rater_{position}'].strip()
    assert rater==row['rater_id'] and (expected_rater is None or rater==expected_rater)
    assert original['Text']==row['Text'] and original['Filename']==row['Filename']
    values={}
    invalid=[]
    for name in ASPECTS:
        assert original[f'{name}_{position}']==row[name], f'{name} raw/wide mismatch'
        try:
            value=float(row[name]); valid=value.is_integer() and 1<=value<=5
            values[name]=int(value) if valid else None
        except (ValueError,TypeError):
            valid=False;values[name]=None
        if not valid:
            invalid.append(dict(aspect=name,raw_value=row[name]))
    return dict(essay_id=f'{source}:{position}',rater_id=rater,source_row_id=source,rater_position=int(position),
                text=row['Text'],overall=values['Overall'],traits={k:values[k] for k in TRAITS},invalid_scores=invalid)


def prepare(cfg,out):
    if (out/'resolved_config.json').exists():
        assert load(out/'resolved_config.json')['config']==cfg, 'Run config changed: use a new version/output directory'
        return
    old=load(ROOT/cfg['source_inputs']); selection=load(ROOT/cfg['source_selection'])
    wide=csv_rows(ROOT/cfg['wide_path']); raw=csv_rows(ROOT/cfg['raw_path'])
    byid={f"{w['source_row_id']}:{w['rater_position']}":w for w in wide}
    items=[]; checks=[]
    for original in old:
        tid=original['target_id']; target=score_record(byid[tid],raw,original['target_rater'])
        assert target['text']==original['target_text'] and target['overall']==original['gold_overall']
        history=[score_record(byid[h],raw,target['rater_id']) for h in original['history_ids']]
        assert len(history)==3 and all(h['source_row_id']!=target['source_row_id'] for h in history)
        assert [h['text'] for h in history]==[h['text'] for h in original['history']]
        for e in [target,*history]:
            e['spans']=units(e['text'],e['essay_id'],cfg['span_max_chars'])
        items.append(dict(target_id=tid,rater_id=target['rater_id'],target=target,history=history))
        checks.append(dict(target_id=tid,raw_wide_and_previous_text_match=True,actual_rater_id=target['rater_id'],
                           history_ids=[h['essay_id'] for h in history],invalid_scores={e['essay_id']:e['invalid_scores'] for e in [target,*history] if e['invalid_scores']}))
    assert [i['target_id'] for i in items]==selection['selected_target_ids'] and len(items)==27
    pilot=sorted([i for i in items if i['rater_id']=='rater_7'],key=lambda i:(i['target']['source_row_id'],i['target']['rater_position']))[:3]
    rubric=load(ROOT/cfg['rubric_path']); conditions=condition_catalog(rubric)
    save(out/'inputs.json',items);save(out/'conditions.json',conditions);save(out/'rubric.json',rubric)
    save(out/'input_checks.json',checks)
    save(out/'selection.json',dict(previous_selection=selection,pilot_rule=cfg['pilot_rule'],pilot_ids=[i['target_id'] for i in pilot],full_ids=[i['target_id'] for i in items]))
    paths=[ROOT/cfg[k] for k in ['source_inputs','source_selection','raw_path','wide_path','rubric_path']]
    paths += [ROOT/'outputs/rater_feedback_pilot'/p for p in ['README.md','report.md','assessment.md','resolved_config.json','feedback.json']]
    paths += [Path(__file__),ROOT/'src/recsaver/model.py',*sorted((ROOT/cfg['prompt_dir']).glob('*.txt'))]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    save(out/'resolved_config.json',dict(config=cfg,timestamp=now(),source_sha256=hashes,
         prior_reference_text_reused=False,trait_source='Actual raw Rater_1/Rater_2 value matched to rater_id; own profile only',
         rubric_limitation='Source DOCX absent; stored official transcription used; clause offsets return to complete source wording'))
    archive=out/'code';archive.mkdir(exist_ok=True)
    for p in [Path(__file__),ROOT/'src/recsaver/model.py',*sorted((ROOT/cfg['prompt_dir']).glob('*.txt'))]:
        shutil.copy2(p,archive/p.name)


def generation_payload(item,condition,rubric,conditions):
    def record(e):
        r={k:e[k] for k in ['essay_id','overall','spans']}
        if condition=='B':
            r['traits']=e['traits']
        return r
    return dict(input_explanation='本人のOverallのみ。Trait得点は与えない。' if condition=='A' else '本人のOverallと6観点Trait得点を与える。',
                target=record(item['target']),history=[record(h) for h in item['history']],
                official_rubric=rubric['scores'],condition_catalog=compact_conditions(conditions))


def compact_conditions(conditions):
    return {cid:{k:c[k] for k in ['aspect','level','text','parent_id']} for cid,c in conditions.items()}


def parse_json(text):
    clean=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip())
    return json.loads(clean)


def validate_reason(obj,item,conditions):
    assert isinstance(obj.get('rationale'),str) and isinstance(obj.get('claims'),list) and 1<=len(obj['claims'])<=4
    essays={e['essay_id']:e for e in [item['target'],*item['history']]}
    ids=set()
    for c in obj['claims']:
        assert re.fullmatch(r'C\d{1,2}',c['claim_id']) and c['claim_id'] not in ids;ids.add(c['claim_id'])
        assert c['scope'] in ['target','history'] and c['aspect'] in ASPECTS
        assert c['kind'] in ['presence','frequency','communication','organization','range','appropriateness']
        assert c['direction'] in ['positive','negative','mixed','unclear']
        assert c['semantic_support'] in ['supported','uncertain','unsupported']
        assert isinstance(c['span_ids'],list) and isinstance(c['condition_ids'],list)
        for k in ['feature','score_relation','support_explanation','limits']:
            assert isinstance(c[k],str)
        essay=essays.get(c['essay_id']); spans={} if essay is None else {s['span_id']:s for s in essay['spans']}
        scope_ok=essay is not None and ((c['scope']=='target')==(c['essay_id']==item['target_id']))
        valid=scope_ok and bool(c['span_ids']) and all(s in spans for s in c['span_ids'])
        condition_ok=bool(c['condition_ids']) and all(cid in conditions for cid in c['condition_ids'])
        c['machine_check']=dict(scope_valid=scope_ok,span_ids_valid=valid,condition_ids_valid=condition_ok)
        c['evidence']=[dict(essay_id=c['essay_id'],**spans[s]) for s in c['span_ids'] if s in spans]
    return obj


def verification_payload(item,masked,rubric):
    payload=dict(history=[{k:h[k] for k in ['essay_id','text','overall']} for h in item['history']],
                 target={k:item['target'][k] for k in ['essay_id','text']},masked_reason=masked,
                 official_overall_rubric={score:facets['Overall'] for score,facets in rubric['scores'].items()})
    assert set(payload['target'])=={'essay_id','text'}
    assert all(set(h)=={'essay_id','text','overall'} for h in payload['history'])
    assert all('condition_ids' not in c for c in masked['claims'])
    return payload


class Engine:
    """既存VLLMGeneratorを使い、各入力ごとのseedを保ったバッチを追加。"""
    def __init__(self,cfg,out):
        self.cfg,self.out=cfg,out;self.generator=None
        from transformers import AutoTokenizer
        self.tokenizer=AutoTokenizer.from_pretrained(cfg['model']['model_id'],local_files_only=True,trust_remote_code=True)

    def path(self,stage,key):
        return self.out/'stages'/stage/(key.replace(':','_').replace('|','__')+'.json')

    def batch(self,stage,jobs):
        if not jobs:
            return {}
        template=(ROOT/self.cfg['prompt_dir']/f'{stage}.txt').read_text(encoding='utf-8')
        completed={};pending=[]
        for key,payload,validator in jobs:
            prompt=template+json.dumps(payload,ensure_ascii=False,separators=(',',':'))
            fp=digest(prompt+json.dumps(dict(model=self.cfg['model'],generation=self.cfg['generation'],max_tokens=self.cfg['max_tokens'][stage],version=self.cfg['version']),sort_keys=True))
            path=self.path(stage,key)
            if path.exists():
                prior=load(path);assert prior['fingerprint']==fp, f'Fingerprint changed: {stage}/{key}; use new run version'
                completed[key]=prior['result'];continue
            pending.append(dict(key=key,payload=payload,validator=validator,prompt=prompt,fingerprint=fp))
        for offset in range(0,len(pending),self.cfg['batch_size']):
            current=pending[offset:offset+self.cfg['batch_size']]
            for attempt in range(self.cfg['format_retries']+1):
                if not current:
                    break
                prompts=[];params=[];records=[];valid=[]
                for j in current:
                    prompt=j['prompt']+ ('\n前の出力の検査エラー: '+j['error']+'\nJSON全体を修正してください。候補の得点不一致を修正する再生成ではありません。' if 'error' in j else '')
                    ids=self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=True,add_generation_prompt=True)
                    # 条件ラベルだけseedから外す。同じtarget/candidateはA/Bで対にする。
                    paired=j['key'].split('|',1)[-1]
                    seed=int(digest(f"{self.cfg['seed']}:{stage}:{paired}:{attempt}")[:8],16)
                    p=dict(self.cfg['generation'],max_tokens=self.cfg['max_tokens'][stage],seed=seed)
                    record=dict(timestamp=now(),stage=stage,key=j['key'],attempt=attempt,model=self.cfg['model'],sampling_parameters=p,prompt=prompt,prompt_tokens=len(ids),fingerprint=j['fingerprint'])
                    fit=len(ids)+p['max_tokens']<=self.cfg['model']['max_model_len']
                    append(self.out/'context_checks.jsonl',dict(stage=stage,key=j['key'],prompt_tokens=len(ids),max_tokens=p['max_tokens'],fits=fit,truncated=False))
                    if not fit:
                        record.update(status='failed',error='Context overflow; nothing truncated; no call made')
                        append(self.out/'calls.jsonl',record)
                        save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=None,error=record['error']))
                        completed[j['key']]=None;continue
                    prompts.append(self.tokenizer.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True))
                    params.append(p);records.append(record);valid.append(j)
                if not valid:
                    break
                if self.generator is None:
                    free=subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True)
                    assert int(free.stdout.strip().splitlines()[0])>=24000,'GPU busy: do not stop other jobs'
                    from .model import VLLMGenerator
                    self.generator=VLLMGenerator(self.cfg)
                from vllm import SamplingParams
                start=time.monotonic()
                outputs=self.generator.llm.generate(prompts,[SamplingParams(n=1,**p) for p in params],use_tqdm=False)
                retry=[]
                for j,record,output in zip(valid,records,outputs):
                    record.update(raw_output=output.outputs[0].text,elapsed_batch_seconds=time.monotonic()-start,
                                  output_tokens=len(output.outputs[0].token_ids),finish_reason=output.outputs[0].finish_reason)
                    try:
                        result=j['validator'](parse_json(record['raw_output']))
                        record['status']='ok';completed[j['key']]=result
                        save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=result,timestamp=now()))
                    except Exception as exc:
                        record.update(status='failed',error=f'{type(exc).__name__}: {exc}')
                        j['error']=record['error'];retry.append(j)
                        if attempt==self.cfg['format_retries']:
                            completed[j['key']]=None
                            save(self.path(stage,j['key']),dict(fingerprint=j['fingerprint'],result=None,error=record['error']))
                    append(self.out/'calls.jsonl',record)
                print(stage, f'{offset+len(valid)}/{len(pending)}', 'retry',len(retry),flush=True)
                current=retry
        return completed


def valid_score(obj):
    assert type(obj.get('predicted_overall')) is int and obj['predicted_overall'] in range(1,6),'expected integer predicted_overall 1..5'
    return obj


def rule_flags(text):
    return re.findall(r'.{0,25}(?:[1-5]点(?:程度に留|にとど|を上限)|減点幅|点減点|cap(?:ped)?\s+at|deduct\s+\d|得点上限).{0,40}',text,re.I)


def claim_key(tid,k,cid):
    return f'{tid}/K{k}/{cid}'


def validate_ground(obj,claims):
    assert isinstance(obj.get('reviews'),list)
    assert sorted(r['claim_id'] for r in obj['reviews'])==sorted(c['claim_id'] for c in claims),'grounding must cover every claim once'
    for r in obj['reviews']:
        assert r['support'] in ['supported','uncertain','unsupported']
        assert isinstance(r['explanation'],str) and isinstance(r['counter_span_ids'],list)
    return obj


def flatten_claims(groups):
    return {c['id']:c for g in groups for c in g['eligible_claims']}


def validate_integration(obj,claimmap,all_ids):
    assert isinstance(obj.get('patterns'),list) and len(obj['patterns'])<=2
    for p in obj['patterns']:
        assert p['pattern_id'] and isinstance(p['support'],list)
        tids=set()
        for support in p['support']:
            assert support['target_id'] in all_ids and support['claim_ids']
            assert all(i in claimmap and claimmap[i]['target_id']==support['target_id'] for i in support['claim_ids']),'invalid support claim/target'
            tids.add(support['target_id'])
        assert len(tids)>=2,'common tendency needs two distinct essays, not two candidates'
        for example in p['counterexamples']:
            assert example['claim_ids'] and all(i in claimmap and claimmap[i]['target_id']==example['target_id'] for i in example['claim_ids'])
        assert all(i in all_ids for i in p['insufficient_target_ids'])
        for n in p['non_applicable']:
            assert any(c['target_id']==n['target_id'] for c in claimmap.values()),'missing evidence is not non-applicable'
        assert not rule_flags(json.dumps(p,ensure_ascii=False)),'unsupported score/deduction rule'
    assert isinstance(obj.get('unknowns'),str)
    return obj


def validate_comparison(obj,item,claimmap,conditions):
    assert isinstance(obj.get('relationships'),list) and len(obj['relationships'])<=2
    spans={s['span_id']:s for s in item['target']['spans']}
    for r in obj['relationships']:
        assert r['claim_ids'] and all(c in claimmap and claimmap[c]['target_id']==item['target_id'] for c in r['claim_ids'])
        assert r['span_ids'] and all(s in spans for s in r['span_ids'])
        assert r['condition_ids'] and all(c in conditions for c in r['condition_ids'])
        for k in ['feature_confirmed','inferred_judgment','rubric_based_proposal','agreement_review_unknown','scope_limit']:
            assert isinstance(r[k],str) and r[k]
        assert r['system_checked'] and all(x['span_ids'] and all(s in spans for s in x['span_ids']) for x in r['system_checked'])
        action=r['next_action']
        assert action['where_span_ids'] and all(s in spans for s in action['where_span_ids'])
        assert all(isinstance(action[k],str) and action[k] for k in ['distinguish','action','reason'])
        assert not rule_flags(json.dumps(r,ensure_ascii=False)),'new score threshold/deduction rule'
        r['citations']=[dict(essay_id=item['target_id'],**spans[s]) for s in r['span_ids']]
        r['official_conditions']=[conditions[c] for c in r['condition_ids']]
        r['full_target_seen']=True
        r['semantic_status']='model-provisional; machine validity is not semantic truth'
    return obj


def run_pipeline(cfg,out,engine,phase):
    items=load(out/'inputs.json'); selection=load(out/'selection.json')
    if phase=='pilot':
        items=[i for i in items if i['target_id'] in selection['pilot_ids']]
    byid={i['target_id']:i for i in items}
    rubric=load(out/'rubric.json'); conditions=load(out/'conditions.json')
    candidates={};jobs=[]
    for condition in cfg['conditions']:
        for item in items:
            # 無効なOverallは両条件、TraitはBだけで記録・除外。補完しない。
            bad=any(e['overall'] is None for e in [item['target'],*item['history']])
            bad|=condition=='B' and any(e['invalid_scores'] for e in [item['target'],*item['history']])
            for k in range(1,cfg['candidates_per_target']+1):
                key=f"{condition}|{item['target_id']}|K{k}"
                candidates[key]=dict(key=key,condition=condition,target_id=item['target_id'],candidate_index=k,invalid_input=bool(bad))
                if not bad:
                    jobs.append((key,generation_payload(item,condition,rubric,conditions),lambda x,it=item:validate_reason(x,it,conditions)))
    generated=engine.batch('generate',jobs)
    verify_jobs=[]
    for key,c in candidates.items():
        reason=generated.get(key)
        c['original_reason']=reason
        if not reason:
            c.update(accepted=False,rejection='invalid input' if c['invalid_input'] else 'generation failure');continue
        masked,logs,residual=masked_reason(reason)
        item=byid[c['target_id']]
        payload=verification_payload(item,masked,rubric)
        artifact=out/'conditions'/c['condition']/'mask'/f"{c['target_id'].replace(':','_')}_K{c['candidate_index']}.json"
        safe=not residual and (len(masked['rationale'].replace('[得点表現除去]','').strip())>=30 or sum(len(x['feature']) for x in masked['claims'])>=60)
        save(artifact,dict(candidate_key=key,masked_reason=masked,mask_log=logs,residual_check=residual,safe_for_verification=bool(safe),
                           target_score_fields_absent=True,target_linked_condition_ids_absent=True,essay_quantities_untouched=True))
        payload_path=artifact.parent.parent/'verification_inputs'/artifact.name
        save(payload_path,payload)
        c['mask_artifact']=str(artifact.relative_to(out));c['verification_input']=str(payload_path.relative_to(out))
        if safe:
            verify_jobs.append((key,payload,valid_score))
        else:
            c.update(accepted=False,rejection='mask unsafe or rationale broken')
    verified=engine.batch('verify',verify_jobs)
    ground_jobs=[]
    for key,c in candidates.items():
        result=verified.get(key)
        item=byid[c['target_id']]
        c['verification']=result
        c['accepted']=bool(result and result['predicted_overall']==item['target']['overall'])
        if not c['accepted']:
            c.setdefault('rejection','verification failure' if result is None else 'Overall reconstruction mismatch')
            continue
        reason=c['original_reason']; claims=reason['claims']
        payload=dict(target_id=item['target_id'],essays=[{k:e[k] for k in ['essay_id','text','spans']} for e in [item['target'],*item['history']]],
                     claims=masked_reason(reason)[0]['claims'],task='machine span validity is separate; evaluate semantic support provisionally')
        ground_jobs.append((key,payload,lambda x,cs=claims:validate_ground(x,cs)))
    grounded=engine.batch('ground',ground_jobs)
    groups=[]
    for condition in cfg['conditions']:
        for item in items:
            entries=[c for c in candidates.values() if c['condition']==condition and c['target_id']==item['target_id']]
            eligible=[]
            for c in entries:
                review=grounded.get(c['key']);c['grounding_review']=review
                reviews={} if review is None else {r['claim_id']:r for r in review['reviews']}
                if not c['accepted']:
                    continue
                for claim in c['original_reason']['claims']:
                    r=reviews.get(claim['claim_id'])
                    machine=claim['machine_check']
                    allowed=bool(claim['scope']=='target' and all(machine.values()) and r and r['support']=='supported')
                    claim['grounding_review']=r;claim['eligible_for_integration']=allowed
                    claim['id']=claim_key(item['target_id'],c['candidate_index'],claim['claim_id'])
                    claim['target_id']=item['target_id'];claim['candidate_index']=c['candidate_index']
                    if allowed:
                        eligible.append(claim)
            group=dict(condition=condition,target_id=item['target_id'],rater_id=item['rater_id'],observed_overall=item['target']['overall'],
                       accepted_candidate_keys=[c['key'] for c in entries if c['accepted']],eligible_claims=eligible,
                       candidate_comparison=None,independent_essay_count=1 if eligible else 0)
            groups.append(group)
    merge_jobs=[]
    for g in groups:
        candidate_count=len({c['candidate_index'] for c in g['eligible_claims']})
        if candidate_count<2:
            g['candidate_comparison']=dict(groups=[dict(summary=c['feature'],claim_ids=[c['id']],candidate_count=1) for c in g['eligible_claims']],
                                           differences=[],unknowns='No two eligible candidates; cross-candidate agreement cannot be judged')
        else:
            cmap={c['id']:c for c in g['eligible_claims']}
            def validate_merge(obj,cm=cmap):
                for key in ['groups','differences']:
                    assert isinstance(obj[key],list)
                    for part in obj[key]:
                        assert part['claim_ids'] and all(c in cm for c in part['claim_ids'])
                        part['candidate_count']=len({cm[c]['candidate_index'] for c in part['claim_ids']})
                assert isinstance(obj['unknowns'],str)
                return obj
            key=f"{g['condition']}|{g['target_id']}"
            merge_jobs.append((key,dict(target_id=g['target_id'],claims=g['eligible_claims']),validate_merge))
    merged=engine.batch('merge',merge_jobs)
    for g in groups:
        if g['candidate_comparison'] is None:
            g['candidate_comparison']=merged.get(f"{g['condition']}|{g['target_id']}") or dict(groups=[],differences=[],unknowns='merge format failure; original eligible claims retained')
    raters=list(dict.fromkeys(i['rater_id'] for i in items))
    integrate_jobs=[];lookup={}
    for condition in cfg['conditions']:
        for rater in raters:
            gs=[g for g in groups if g['condition']==condition and g['rater_id']==rater]
            cm=flatten_claims(gs);tids=[g['target_id'] for g in gs]
            key=f'{condition}|{phase}_{rater}';lookup[key]=(gs,cm,tids)
            integrate_jobs.append((key,dict(rater_id=rater,essays=gs),lambda x,cmap=cm,ids=tids:validate_integration(x,cmap,ids)))
    integrated=engine.batch('integrate',integrate_jobs)
    compare_jobs=[]
    for g in groups:
        if not g['eligible_claims']:
            continue
        condition=g['condition'];item=byid[g['target_id']];rater=g['rater_id']
        synthesis=integrated.get(f'{condition}|{phase}_{rater}') or dict(patterns=[],unknowns='integration failed')
        reasons=[c['original_reason'] for c in candidates.values() if c['condition']==condition and c['target_id']==g['target_id'] and c['accepted']]
        payload=dict(target_id=g['target_id'],target_text=item['target']['text'],target_spans=item['target']['spans'],
                     observed_overall=item['target']['overall'],accepted_reasons=reasons,eligible_claims=g['eligible_claims'],
                     candidate_comparison=g['candidate_comparison'],inferred_patterns=synthesis['patterns'],
                     official_rubric=rubric['scores'],condition_catalog=compact_conditions(conditions))
        if condition=='B':
            payload['own_observed_traits']=item['target']['traits']
        key=f"{condition}|{phase}_{g['target_id']}"
        cm={c['id']:c for c in g['eligible_claims']}
        compare_jobs.append((key,payload,lambda x,it=item,cmap=cm:validate_comparison(x,it,cmap,conditions)))
    compared=engine.batch('compare',compare_jobs)
    text_jobs=[]
    for condition in cfg['conditions']:
        for rater in raters:
            key=f'{condition}|{phase}_{rater}'
            gs,cm,tids=lookup[key]
            synthesis=integrated.get(key) or dict(patterns=[],unknowns='integration format failure')
            relations=[dict(target_id=tid,result=compared.get(f'{condition}|{phase}_{tid}')) for tid in tids]
            # 全文検討はcompareに分割保存済み。最終文章化はその結果を統合する。
            payload=dict(rater_id=rater,synthesis=synthesis,per_essay_comparisons=relations,
                         accepted_target_ids=[g['target_id'] for g in gs if g['accepted_candidate_keys']],
                         no_eligible_evidence_target_ids=[g['target_id'] for g in gs if not g['eligible_claims']])
            def validate_text(obj):
                for field in ['criterion_intro','tendency','examples_intro','relationship','next_checks','limits']:
                    assert isinstance(obj.get(field),str) and obj[field]
                assert not rule_flags(json.dumps(obj,ensure_ascii=False)),'unsupported scoring/deduction rule'
                return obj
            text_jobs.append((key,payload,validate_text))
    texts=engine.batch('text',text_jobs)
    results=[]
    for condition in cfg['conditions']:
        for rater in raters:
            key=f'{condition}|{phase}_{rater}';gs,cm,tids=lookup[key]
            synthesis=integrated.get(key) or dict(patterns=[],unknowns='integration failed; no inferred tendency asserted')
            comparisons={tid:compared.get(f'{condition}|{phase}_{tid}') for tid in tids}
            body=texts.get(key)
            relationships=[dict(target_id=tid,**r) for tid,obj in comparisons.items() if obj for r in obj['relationships']]
            condition_ids=list(dict.fromkeys(cid for r in relationships for cid in r['condition_ids']))
            examples=sorted([tid for tid,obj in comparisons.items() if obj and obj['relationships']],key=lambda t:tuple(map(int,t.split(':'))))[:2]
            selected=[r for r in relationships if r['target_id'] in examples]
            if body:
                parts=[body[k] for k in ['criterion_intro','tendency','examples_intro','relationship','next_checks']]
            else:
                parts=['公式基準は保存済み一覧を参照。','文章化に失敗。共通傾向は確定できない。','確認済みの証拠を別欄に示す。','個別照合結果を参照。','具体的な確認行動は個別照合結果を参照。']
            elements=[dict(number=n+1,text=t,condition_ids=condition_ids if n in [0,3,4] else [],
                           pattern_ids=[p['pattern_id'] for p in synthesis['patterns']] if n==1 else [],
                           target_ids=examples if n in [2,3,4] else []) for n,t in enumerate(parts)]
            final=dict(condition=condition,rater_id=rater,target_ids=tids,essay_groups=gs,synthesis=synthesis,
                       comparisons=comparisons,elements=elements,example_target_rule='first two numerically ordered eligible comparison targets',
                       example_relationships=selected,official_conditions={cid:conditions[cid] for cid in condition_ids},
                       limits=body['limits'] if body else 'text generation failed',quality_status='pilot; semantic judgments provisional, not independently validated')
            results.append(final)
            save(out/'conditions'/condition/'results'/f'{phase}_{rater}.json',final)
    snapshot=dict(phase=phase,timestamp=now(),target_ids=list(byid),candidates=list(candidates.values()),essay_groups=groups,results=results)
    save(out/f'{phase}_results.json',snapshot)
    write_reports(out,cfg,snapshot)
    return snapshot


def write_reports(out,cfg,snapshot):
    phase=snapshot['phase'];cs=snapshot['candidates'];rs=snapshot['results']
    counts={condition:dict(targets=len({c['target_id'] for c in cs if c['condition']==condition}),
                          candidates=sum(c['condition']==condition for c in cs),
                          generated=sum(c['condition']==condition and bool(c.get('original_reason')) for c in cs),
                          verified_calls=sum(c['condition']==condition and bool(c.get('verification')) for c in cs),
                          accepted=sum(c['condition']==condition and c['accepted'] for c in cs),
                          accepted_unique_targets=len({c['target_id'] for c in cs if c['condition']==condition and c['accepted']}),
                          eligible_claims=sum(len(g['eligible_claims']) for g in snapshot['essay_groups'] if g['condition']==condition)) for condition in cfg['conditions']}
    save(out/f'{phase}_summary.json',counts)
    for condition in cfg['conditions']:
        save(out/'conditions'/condition/f'{phase}_candidates.json',[c for c in cs if c['condition']==condition])
    lines=['# 採点者フィードバック予備検証v2', '',f'版: {cfg["version"]} / 対象範囲: {phase}', '',
           '新規理由候補→得点マスク→Overall自己検証→答案単位候補整理→採点者別統合→公式条件選択・全文照合→5要素の文章化。旧参照推論の文章は使用していない。', '',
           'Aは本人Overallのみ、Bは同じ採点者本人のOverall＋6Trait。共通の公式Overall＋6観点ルーブリック、同じモデル・生成設定・対象・履歴・候補数を使用。', '',
           '## 完了件数', '', '```json',json.dumps(counts,ensure_ascii=False,indent=2),'```','']
    for rater in dict.fromkeys(r['rater_id'] for r in rs):
        lines += [f'## {rater}', '', '### 個別理由の条件比較例', '', '|対象|条件|採用候補|新規理由文|', '|---|---|---|---|']
        tids=next(r['target_ids'] for r in rs if r['rater_id']==rater)
        for tid in sorted(tids,key=lambda t:tuple(map(int,t.split(':'))))[:2]:
            for cond in cfg['conditions']:
                entries=[c for c in cs if c['condition']==cond and c['target_id']==tid]
                entry=next((c for c in entries if c['accepted']),entries[0])
                text=(entry.get('original_reason') or {}).get('rationale','生成失敗').replace('|','\\|').replace('\n','<br>')
                lines.append(f"|{tid}|{cond}|{entry['candidate_index'] if entry['accepted'] else '採用なし'}|{text}|")
        for result in [r for r in rs if r['rater_id']==rater]:
            lines += ['',f"### 条件{result['condition']}：共通傾向と5要素", '']
            for e in result['elements']:
                lines += [e['text'],'']
                if e['number']==1:
                    for cid,c in result['official_conditions'].items():
                        lines += [f"- {cid}（{c['aspect']}、段階{c['level']}、{c['role']}）: {c['text']}"]
                if e['number']==3:
                    for rel in result['example_relationships']:
                        for quote in rel['citations']:
                            lines += [f"- {rel['target_id']} / {quote['span_id']} [{quote['start']}:{quote['end']}]: {json.dumps(quote['text'],ensure_ascii=False)}"]
                if e['number']==4:
                    for rel in result['example_relationships']:
                        lines += [f"- {rel['target_id']} / {rel['issue_id']}: 本文={rel['feature_confirmed']} / 理由の判断={rel['inferred_judgment']}",
                                  f"  - 基準から妥当と考えられる評価: {rel['rubric_based_proposal']}",f"  - 一致・見直し・判断不能: {rel['agreement_review_unknown']}",
                                  f"  - システム確認済み: {json.dumps(rel['system_checked'],ensure_ascii=False)} / 条件: {rel['condition_ids']}"]
                if e['number']==5:
                    for rel in result['example_relationships']:
                        a=rel['next_action']
                        lines += [f"- {rel['target_id']} / {rel['issue_id']}から: 区別={a['distinguish']}。見る場所={a['where_span_ids']}。行動={a['action']}。理由={a['reason']}"]
            lines += ['', '#### 5要素の対応表', '', '|要素|対象|条件|傾向|', '|---|---|---|---|']
            for e in result['elements']:
                lines.append(f"|{e['number']}|{e['target_ids']}|{e['condition_ids']}|{e['pattern_ids']}|")
            lines += ['', '#### 支持・反例・非該当・証拠不足', '', '```json',json.dumps(result['synthesis'],ensure_ascii=False,indent=2),'```', '',
                      '研究上の制約: '+result['limits'], '意味的支持・条件の解釈はモデルによる暫定判断。原文とIDの機械的一致は内容の正解を保証しない。', '']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    accepted={cond:{c['target_id'] for c in cs if c['condition']==cond and c['accepted']} for cond in cfg['conditions']}
    assessment=['# 予備実験v2の所見', '', '実行・出力内容の確認に限定する。最終評価方法の設計・新たな評価モデルの学習・有効性評価は行わない。', '',
                '## 条件別の候補採否', '', '```json',json.dumps(counts,ensure_ascii=False,indent=2),'```','',
                f"Aのみ統合可能な対象: {sorted(accepted['A']-accepted['B'])}",f"Bのみ統合可能な対象: {sorted(accepted['B']-accepted['A'])}",
                '条件で自己検証の通過対象が異なるため、傾向の差をTrait情報の因果的効果と断定しない。', '',
                '## 確認事項と残る制約', '',
                '- 個別理由は新規生成。旧inputsから復元したのは本文・履歴ID・観測値だけで、旧参照推論は入力していない。',
                '- 引用はspan IDから原文・文字位置を取得。全文を保持し、分割不能な文章も固定長の位置で追跡。',
                '- マスクは直接得点・段階表現と条件IDに限定。答案の数量、履歴Overall、span IDは削除しない。実検証payloadを別ファイルに保存。',
                '- 採否はOverall再構成一致。証拠・scopeの機械検査と、意味的支持の暫定モデル判定を分離。得点一致は説明の正しさを保証しない。',
                '- 同一答案の候補は答案単位に整理し、支持は異なる対象を最低2件必要とする。',
                '- 公式条件の選択を観測段階・固定方向の隣接段階から解放。各条件は公式原文の文字位置・親段階全文へ戻れる。限定を省略して新規基準を作らない。',
                '- ④は対象全文と採用理由を答案ごとに読み、本文の特徴・推定判断・基準から妥当な評価・不一致／不明点を分離。⑤は区別・場所・行動を構造化。',
                '- 機械的なIDの有効性だけでは、具体性、誤り判定、理解阻害の強さ、行動の有用性の妥当性は分からない。一般論や指示の復唱は内容レビューで確認する。',
                '- 元DOCXは不在。保存済み公式転記を使用し、真正性を原本から独立確認していない。',
                '- 本人の真の理由、採点者固有性、Traitの重み、フィードバックの有効性、バイアス是正効果を実証していない。', '']
    (out/'assessment.md').write_text('\n'.join(assessment),encoding='utf-8')
    (out/'README.md').write_text(f'''# 採点者フィードバック予備実験v2

実行範囲: {phase}。条件A=Traitなし、B=本人Traitあり。新規理由2候補／対象・条件。

- report.md: 採点者別にA/Bの理由比較・5要素本文・引用と公式条件・対応表
- assessment.md: 件数・条件別の採否差・所見と制約
- {phase}_results.json / {phase}_summary.json: 機械可読の全結果と集計
- inputs.json / selection.json / input_checks.json: 元データ照合・選択・欠損
- conditions.json: 公式条件ID・原文・親段階・文字位置
- conditions/A, conditions/B: 別々の候補・マスク履歴・実検証入力・最終結果
- stages/: 生成・検証・意味的点検・候補整理・統合・全文比較・文章化の中間出力
- calls.jsonl / context_checks.jsonl: 全呼出し・失敗・seed・日時・コンテキスト検査
- resolved_config.json / code/: 実行設定とコード・プロンプトの版

旧実験を上書きせず、最終実験・評価モデルの学習は行っていない。
再開: python -m src.recsaver.rater_feedback_pilot_v2 full
同一入力・設定・プロンプトの成功段階のみ再利用。変更する場合は新しい版・実行先を使う。
''',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=['prepare','pilot','full','pilot-and-full','report'])
    parser.add_argument('--config',default='configs/rater_feedback_pilot_v2.json')
    args=parser.parse_args();cfg=load(ROOT/args.config);out=ROOT/cfg['output_dir'];out.mkdir(parents=True,exist_ok=True)
    prepare(cfg,out)
    if args.phase=='prepare':
        print('prepared',out,flush=True);return
    state=dict(status='running',phase=args.phase,started_at=now())
    save(out/'status.json',state)
    try:
        if args.phase=='report':
            snapshot=load(out/('full_results.json' if (out/'full_results.json').exists() else 'pilot_results.json'))
            write_reports(out,cfg,snapshot)
        else:
            engine=Engine(cfg,out)
            if args.phase=='full':
                assert (out/'pilot_review.json').exists() and load(out/'pilot_review.json')['proceed'],'Review 3-target pilot before full expansion'
            phase='pilot' if args.phase in ['pilot','pilot-and-full'] else 'full'
            snapshot=run_pipeline(cfg,out,engine,phase)
            if args.phase=='pilot-and-full':
                print('PILOT_READY: inspect pilot_results.json and write pilot_review.json with matching pilot_sha256',flush=True)
                deadline=time.monotonic()+1200
                while True:
                    gate=out/'pilot_review.json'
                    if gate.exists():
                        review=load(gate)
                        if review.get('proceed') and review.get('pilot_sha256')==sha(out/'pilot_results.json'):
                            break
                    assert time.monotonic()<deadline,'pilot review timed out; results retained'
                    time.sleep(3)
                snapshot=run_pipeline(cfg,out,engine,'full')
        state.update(status='completed',scope=snapshot['phase'],target_count=len(snapshot['target_ids']))
    except BaseException:
        state.update(status='failed',error=traceback.format_exc());raise
    finally:
        state['ended_at']=now();save(out/'status.json',state)


if __name__=='__main__':
    main()
