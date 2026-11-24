"""Freeze pre-output selection and retain the original engine with retries disabled."""
from pathlib import Path
import json,csv,hashlib,subprocess,shutil,re,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
COMMIT='2d49a6f4b635cedece5fdf25eda9d2ac9c48cb3d'
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def save(f,v):
    f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
assert not (OUT/'selection_manifest.json').exists(),'Selection already frozen'
base=ROOT/'outputs/recsaver_stage3_v1_6_baseline'
names=['recsaver_03a_case_evidence_review_v1_6.txt','recsaver_03b_integrated_feedback_v1_6.txt','recsaver_03c_verify_integrated_claims_v1_0.txt']
attachment=Path('/mnt/c/Users/GUESTUSER/.codex/attachments/8290436a-16f0-41db-ad34-e15108418c22/貼り付けたテキスト.txt').read_text(encoding='utf-8')
expected=attachment.split('--- BEGIN PROMPT ---',1)[1].split('--- END PROMPT ---',1)[0].strip()+'\n'
assert (ROOT/'prompts/en'/names[2]).read_text(encoding='utf-8')==expected
for n in names[:2]:
    committed=subprocess.check_output(['git','show',COMMIT+':prompts/en/'+n],cwd=ROOT)
    assert committed.replace(b'\r\n',b'\n')==(ROOT/'prompts/en'/n).read_bytes().replace(b'\r\n',b'\n')
engine_source=ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py'
engine=engine_source.read_text(encoding='utf-8');assert engine.count('for attempt in range(2):')==1
(OUT/'code/engine.py').write_text(engine.replace('for attempt in range(2):','for attempt in range(1):'),encoding='utf-8')
old_cases=json.loads((ROOT/'outputs/recsaver_prompt_v1_0_initial_20261118/case_manifest.json').read_text())
development={c['target']['essay_id'] for c in old_cases['development']}
history={s['essay_id'] for c in old_cases['development'] for s in c['history']}
group_defs=[dict(group_id='contrast',target_ids=['8699:1','873:1'],pool='recsaver_mvp/verified_reference_pool.jsonl',reason='同一rater_7、Cohesion=2対3。8699にはHowever/Rather than等の接続と断片化、873にはFirstly/Secondly/Thirdlyと理由・例示があり、局所の接続特徴と本人得点を対照できる。得点差の原因や採点規則の同定はできない。',role='比較可能な局所特徴・異なる得点の対照。傾向成立を事前保証しない。'),dict(group_id='limited',target_ids=['2016:1','3650:1'],pool='reasoning_eval_v1/verified_reference_pool.jsonl',reason='同一rater_7、両答案Cohesion=3、Grammar=2。著者の言葉への反対と列挙・理由を含み、局所所見は点検可能だが、共通特徴・得点だけから採点傾向を支持する対照がない。',role='根拠不足時の傾向保留と局所所見保持の確認。')]
all_ids={eid for g in group_defs for eid in g['target_ids']}
wide={}
with (ROOT/'data/processed/rater_essay_wide.csv').open(newline='',encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        eid=row['source_row_id']+':'+row['rater_position']
        if eid in all_ids:wide[eid]=row
raw_path=ROOT/'data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv'
raw={}
with raw_path.open(newline='',encoding='utf-8-sig') as f:
    for i,row in enumerate(csv.DictReader(f)):
        if any(e.split(':')[0]==str(i) for e in all_ids):raw[i]=row
traits=['Cohesion','Syntax','Vocabulary','Phraseology','Grammar','Conventions']
selection=[]
for g in group_defs:
    records=[];candidates=[];poolpath=ROOT/'outputs'/g['pool']
    with poolpath.open(encoding='utf-8-sig') as f:
        for line_no,line in enumerate(f,1):
            rec=json.loads(line)
            if rec.get('target_id') in g['target_ids']:
                assert rec['verified'] and rec['reconstructed_overall']==rec['gold_overall']
                assert not rec.get('score_leak',False)
                candidates.append(dict(jsonl_line=line_no,record=rec))
    for eid in g['target_ids']:
        w=wide[eid];idx,pos=eid.split(':');r=raw[int(idx)]
        assert w['rater_id']==r['Rater_'+pos]=='rater_7'
        assert w['Text']==r['Text']
        scores={d:int(float(w[d])) for d in ['Overall']+traits}
        assert all(scores[d]==float(r[d+'_'+pos]) for d in scores)
        matching=[c for c in candidates if c['record']['target_id']==eid]
        assert matching and all(c['record']['gold_overall']==scores['Overall'] for c in matching)
        records.append(dict(essay_id=eid,rater_id=w['rater_id'],text=w['Text'],Overall=scores['Overall'],Traits={d:scores[d] for d in traits},score_provenance=dict(raw_csv=str(raw_path.relative_to(ROOT)),source_row_id=int(idx),csv_row=int(idx)+2,rater_column='Rater_'+pos,score_suffix='_'+pos),prior_development_target_overlap=eid in development,prior_development_history_overlap=eid in history,prior_saved_pool_exposure=True))
    folder=OUT/'groups'/g['group_id'];save(folder/'sources.json',records);save(folder/'saved_accepted_records.json',candidates)
    selection.append(dict(**g,rater_id='rater_7',targets=[{k:v for k,v in rec.items() if k!='text'} for rec in records],pool_sha256=sha(poolpath),accepted_candidate_count=len(candidates),acceptance_policy='保存済みverified=trueかつ再構成Overall一致。旧実験の検証基準を新v1.2相当とみなさず、本文・本人Traitをrawで再照合。候補解釈は3A/3B/3Cへ渡さない。'))
known=OUT/'groups/known';known.mkdir(parents=True,exist_ok=True)
for src,dst in [('stage3b/rater_7/input.json','input_3b.json'),('stage3b/rater_7/parsed.json','A/parsed.json'),('stage3b/rater_7/feedback_paragraph.txt','A/feedback_paragraph.txt')]:
    target=known/dst;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/src,target)
fixed=json.loads((base/'fixed_input.json').read_text());save(known/'sources.json',[s for s in fixed['source_essays'] if s['essay_id'] in ['1868:1','4902:1']])
for eid in ['1868:1','4902:1']:
    target=known/'evidence_spans'/f'{eid.replace(":","_")}.json';target.parent.mkdir(exist_ok=True);shutil.copyfile(base/'evidence_spans'/target.name,target)
frozen_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
save(OUT/'selection_manifest.json',dict(frozen_at=frozen_at,before_new_3A_3B_3C_outputs=True,comparison_commit=COMMIT,known=dict(group_id='known',rater_id='rater_7',target_ids=['1868:1','4902:1'],purpose='動作確認専用。Aの保存済み入力・解析JSON・最終文をバイト同一再利用し、効果集計から除外。',new_requests=1),new_groups=selection,requested_new_group_max=2,new_group_count=2,selection_limitations='旧採用プールの受入基準は現行v1.2と同一ではない。既存採用を保持し、再採用・Stage1/2再実行なし。保存プールでの既知露出があるため独立最終評価ではない。',missing_groups=[]))
old=json.loads((base/'run_manifest.json').read_text())
save(OUT/'run_manifest.json',dict(created_at=frozen_at,comparison_commit=COMMIT,baseline_path=str(base),prompts={k:dict(path='prompts/en/'+n,sha256=sha(ROOT/'prompts/en'/n)) for k,n in zip(['a','b','c'],names)},model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],sampling=old['sampling'],seed=old['seed'],system_message=old['system_message'],chat=old['chat'],planned_new_requests=dict(stage3a=4,stage3b=2,stage3c=3,total=9),hard_request_limit=11,stage1_calls=0,stage2_calls=0,regeneration_calls=0,automatic_judge_calls=0,slm_revision_calls=0,engine_reuse=dict(source=str(engine_source.relative_to(ROOT)),source_sha256=sha(engine_source),snapshot='code/engine.py',only_change='Transport retry loop range(2) -> range(1); no retry under any exception.'),baseline_files_sha256={str(p.relative_to(base)):sha(p) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts},comparison_interpretation='追加モデル呼び出しと追加原文位置情報を含む検証・修正工程全体の比較。それぞれの寄与は識別できない。',selection_sha256=sha(OUT/'selection_manifest.json')))
print('Selection frozen: contrast 8699:1 / 873:1; limited 2016:1 / 3650:1; known pair reused. Planned requests: 9.')
