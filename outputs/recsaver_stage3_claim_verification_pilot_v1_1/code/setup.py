"""Freeze manual atomic decomposition, citations, display candidates and premises."""
from pathlib import Path
import json,hashlib,shutil,subprocess,datetime
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/recsaver_stage3_claim_verification_pilot_v1_0'
COMMIT='38697e9bc153f8824c5e62c394e44b5be73fe759'
PROMPT=ROOT/'prompts/en/recsaver_03c_verify_atomic_claims_v1_1.txt'
def read(f):return json.loads(Path(f).read_text(encoding='utf-8-sig'))
def sha(f):return hashlib.sha256(Path(f).read_bytes()).hexdigest()
def save(f,v):
    f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==COMMIT
assert not (OUT/'claim_manifest.json').exists(),'Already frozen; do not overwrite'
groups=[]
for gid in ['known','contrast','limited']:
    src=BASE/'groups'/gid;dst=OUT/'groups'/gid
    for name in ['sources.json','input_3b.json','A/parsed.json','A/feedback_paragraph.txt','source_positions.json']:
        (dst/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/name,dst/name)
    for f in (src/'evidence_spans').glob('*.json'):
        target=dst/'evidence_spans'/f.name;target.parent.mkdir(exist_ok=True);shutil.copyfile(f,target)

def ref(key,indices):return dict(observation_key=key,quote_indices=indices)
def claim(cid,field,text,refs,kind='local',route='llm',display=None,rewrite='独立した命題となるよう主語・照応を補い、複合文から切り出した。',position=None,depends=None):
    return dict(claim_id=cid,source_field=field,claim=text,selected_quote_references=refs,kind=kind,route=route,display_candidate=display or text,rewrite_record=rewrite,position_check=position,depends_on=depends or [])
k='1868:1::O1';r0=[ref(k,[0])];r1=[ref(k,[1])];rb=[ref(k,[0,1])]
known=[
 claim('K01','textual_finding','The first selected passage occurs at the start of the essay.',r0,route='code_position',position=dict(boundary='essay_start',quote_index=0),display='The first selected passage occurs at the start of the essay.'),
 claim('K02','textual_finding','The first selected passage presents continued learning as a way to improve skills.',r0,display='The opening passage presents continued learning as a way to improve skills.'),
 claim('K03','textual_finding','The first selected passage functions as a thesis statement.',r0),
 claim('K04','textual_finding','The second selected passage reiterates the first passage\'s idea of continued learning.',rb,display='The selected passages repeat the idea of continued learning.'),
 claim('K05','textual_finding','The second selected passage occurs at the end of its paragraph.',r1,route='code_position',position=dict(boundary='paragraph_end',quote_index=1)),
 claim('K06','textual_finding','The essay maintains a clear focus on the importance of continuous learning.',rb),
 claim('K07','evidence_limit','The selected passages do not establish the overall coherence of the essay.',rb,kind='limitation'),
 claim('K08','evidence_limit','The selected passages establish cohesion within the first paragraph.',rb),
 claim('K09','pattern_status; pattern_limit','The supplied local evidence does not establish a repeated scoring behavior across essays.',[],kind='pattern_abstention'),
 claim('K10','rubric_review.band_assessment','The selected excerpts do not establish whether the recorded Cohesion band is appropriate.',rb,kind='band_abstention',display='This evidence alone does not establish whether that band is appropriate.')]
known[1]['display_dependencies']=['K01']
c='8699:1::O1';cr=[ref(c,[0])]
contrast=[
 claim('C01','textual_finding','The selected sentence contains grammatical errors.',cr),
 claim('C02','textual_finding; next_check.inspect','The selected sentence contains subject-verb agreement errors.',cr),
 claim('C03','textual_finding; next_check.inspect','The selected sentence contains incorrect use of articles.',cr),
 claim('C04','evidence_limit','The selected sentence does not establish the overall grammatical accuracy of the essay.',cr,kind='limitation'),
 claim('C05','pattern_status; pattern_limit','The supplied local evidence does not establish a repeated scoring behavior across essays.',[],kind='pattern_abstention'),
 claim('C06','rubric_review.band_assessment','The selected excerpt does not establish whether the recorded Grammar band is appropriate.',cr,kind='band_abstention',display='This evidence alone does not establish whether that band is appropriate.')]
l='2016:1::O1';lr=[ref(l,[0])]
limited=[
 claim('L01','textual_finding; next_check.inspect','The phrase "you will never grow" is a nonstandard verb form.',lr),
 claim('L02','evidence_limit','The selected excerpt does not establish the frequency of grammatical errors throughout the essay.',lr,kind='limitation'),
 claim('L03','pattern_status; pattern_limit','The supplied local evidence does not establish a repeated scoring behavior across essays.',[],kind='pattern_abstention'),
 claim('L04','rubric_review.band_assessment','The selected excerpt does not establish whether the recorded Grammar band is appropriate.',lr,kind='band_abstention',display='This evidence alone does not establish whether that band is appropriate.')]
definitions=[('known',known,k,[0,1]),('contrast',contrast,c,[0]),('limited',limited,l,[0])]
for gid,claims,key,indices in definitions:
    folder=OUT/'groups'/gid;payload=read(folder/'input_3b.json');draft=read(folder/'A/parsed.json')
    allrefs=[ref(o['observation_key'],list(range(len(o['quotes'])))) for o in payload['verified_observations']]
    for item in claims:
        item['original_field_values']={field:draft.get(field) for field in item['source_field'].split('; ') if field in draft}
        if item['kind']=='pattern_abstention':item['selected_quote_references']=allrefs
    if gid=='known':
        actions=[dict(action_id='KN1_original',source_field='next_check.inspect',text=draft['next_check']['inspect'],depends_on=['K06'],premise_claim_ids=['K06'],rewrite_record='原文のsame focusの前提を対応付ける。'),dict(action_id='KN2_neutral',source_field='next_check.distinguish',text='Inspect the transitions between paragraphs and check whether the discussion of continued learning connects across them.',depends_on=['K02'],premise_claim_ids=['K02'],rewrite_record='原文の確認指示を予期的な問いへ限定。既に全体が同じfocusを持つという前提を加えず、局所にある話題を追う表示候補を推論前に固定。')]
    elif gid=='contrast':
        actions=[dict(action_id='CN1_agreement',source_field='next_check.inspect',text='Inspect other sentences for subject-verb agreement errors similar to those in the selected sentence.',depends_on=['C02'],premise_claim_ids=['C02'],rewrite_record='原文の複数の診断種類を別々の確認候補へ分ける。'),dict(action_id='CN2_articles',source_field='next_check.inspect',text='Inspect other sentences for article errors similar to those in the selected sentence.',depends_on=['C03'],premise_claim_ids=['C03'],rewrite_record='同上。'),dict(action_id='CN3_general',source_field='next_check.inspect; next_check.distinguish',text='Inspect other sentences for grammatical errors and check their frequency and effect on clarity.',depends_on=['C01'],premise_claim_ids=['C01'],rewrite_record='元の誤り一般の確認と頻度・影響を統合。特定の診断種類の前提は含めない表示候補を推論前に固定。')]
    else:
        actions=[dict(action_id='LN1',source_field='next_check.inspect',text=draft['next_check']['inspect'],depends_on=['L01'],premise_claim_ids=['L01'],rewrite_record='similar grammatical issuesの前提をL01へ対応付ける。'),dict(action_id='LN2',source_field='next_check.distinguish',text=draft['next_check']['distinguish'],depends_on=['L01'],premise_claim_ids=['L01'],rewrite_record='先の誤診の頻度・種類を問う確認指示としてL01へ対応付ける。')]
    groups.append(dict(group_id=gid,purpose='既知例の回帰診断。採点傾向は保留の事例。',representative_observation_key=key,representative_quote_indices=indices,claims=claims,next_check_candidates=actions,display_order=[x['claim_id'] for x in claims],sources_path=f'groups/{gid}/sources.json',draft_path=f'groups/{gid}/A/parsed.json',effect_aggregate=gid!='known'))

# The positive control is the existing valid 4902 Cohesion observation, not a new 3B generation.
src=OUT/'groups/known';dst=OUT/'groups/retention';dst.mkdir(parents=True,exist_ok=True)
payload=read(src/'input_3b.json');o=next(x for x in payload['verified_observations'] if x['observation_key']=='4902:1::O1')
sources=[s for s in read(src/'sources.json') if s['essay_id']=='4902:1']
save(dst/'sources.json',sources);save(dst/'input_3b.json',dict(rater_id='rater_7',accepted_target_ids=['4902:1'],verified_observations=[o],rubric_entries=[r for r in payload['rubric_entries'] if r['dimension']=='Cohesion'],evidence_limitations=['One existing local observation used only as a retention control.']))
shutil.copyfile(src/'evidence_spans/4902_1.json',dst/'4902_1_source_catalog.json');(dst/'evidence_spans').mkdir(exist_ok=True);shutil.copyfile(src/'evidence_spans/4902_1.json',dst/'evidence_spans/4902_1.json')
save(dst/'source_positions.json',[s for s in read(src/'source_positions.json') if s['observation_key']=='4902:1::O1'])
rr=[ref('4902:1::O1',[0,1])]
retention=[claim('R01','existing_observation.feature; existing_observation.scoring_relevance','The selected excerpts explicitly connect the writer\'s agreement with the quotation to a stated reason.',rr,display='The writer explicitly states a reason for agreeing with the quotation.',rewrite='既存の有効なCohesion所見から、引用への賛同と理由の明示という同じ局所関係だけを独立した英文へまとめた。'),claim('R02','existing_observation.limitation','The selected excerpts do not establish the overall coherence of the essay.',rr,kind='limitation')]
groups.append(dict(group_id='retention',purpose='4902:1の既存有効所見の保持確認。既存3群の改善集計・未知答案の効果推定から除外。',representative_observation_key='4902:1::O1',representative_quote_indices=[0,1],claims=retention,next_check_candidates=[dict(action_id='RN1',source_field='existing_observation.next_check',text=o['next_check'],depends_on=['R01'],premise_claim_ids=['R01'],rewrite_record='既存確認指示をそのまま保持候補とする。')],display_order=['R01','R02'],sources_path='groups/retention/sources.json',draft_path=None,effect_aggregate=False,control_source_observation=o))
frozen=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
save(OUT/'claim_manifest.json',dict(frozen_at=frozen,before_inference=True,comparison_commit=COMMIT,splitter='Codexによる人手相当の分割。自動分割ではない。',groups=groups,position_policy='主張IDに固定した引用の実start/endと段落/答案境界を比較。境界を確定できなければinsufficient。修辞機能は位置で判定しない。',assembly_policy='支持された命題だけを固定候補と順序で表示。依存する主張が非支持なら確認点を除外。局所所見なしは保留。別の所見・元初稿で補填しない。',display_only_statuses=dict(no_local_finding='No verified local finding remains.',no_next_check='No next check survived the claim prerequisites.'),comparison_limitations='位置のコード検査、人手相当の分割、LLM判定の組合せ。個別寄与、自動分割・未知答案性能は識別しない。'))
old=read(BASE/'run_manifest.json')
engine=(BASE/'code/engine.py').read_text(encoding='utf-8')
engine=engine.replace('from vllm import LLM,SamplingParams','from vllm import LLM,SamplingParams\n        from vllm.sampling_params import GuidedDecodingParams')
needle='[SamplingParams(**v[2]) for v in pending]'
assert engine.count(needle)==1
engine=engine.replace(needle,"[SamplingParams(**v[2],guided_decoding=GuidedDecodingParams(json=SCHEMA_FACTORY(v[0]['payload']),backend='outlines')) for v in pending]")
(OUT/'code/engine.py').write_text(engine,encoding='utf-8')
save(OUT/'run_manifest.json',dict(created_at=frozen,comparison_commit=COMMIT,baseline_path=str(BASE),prompt=dict(path=str(PROMPT.relative_to(ROOT)),sha256=sha(PROMPT)),model=old['model'],generation=old['generation'],max_tokens=old['max_tokens'],sampling=old['sampling'],seed=old['seed'],system_message=old['system_message'],chat=old['chat'],format_policy=dict(guided_json=True,backend='outlines',strict_json_required=True,outer_fence_removal=False,json_body_repair=False,duplicate_or_missing_ids='processing_failure'),planned_requests=4,hard_request_limit=4,stage1_to_3b_new_requests=0,regeneration_requests=0,claim_manifest_sha256=sha(OUT/'claim_manifest.json'),baseline_files_sha256={str(f.relative_to(BASE)):sha(f) for f in BASE.rglob('*') if f.is_file() and '__pycache__' not in f.parts},engine_source=dict(path=str((BASE/'code/engine.py').relative_to(ROOT)),sha256=sha(BASE/'code/engine.py'),changes='SamplingParamsに各要求のJSON schemaとoutlines backendを追加。輸送再試行なしを維持。'),scope='既知例の回帰診断。人手相当の主張分割。自動分割・未知答案性能を評価しない。'))
print('Frozen:',sum(len(g['claims']) for g in groups),'claims;',sum(c['route']=='llm' for g in groups for c in g['claims']),'LLM verdicts; 4 requests.')
