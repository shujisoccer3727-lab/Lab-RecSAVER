"""Summarize independent provisional claim review and paired retention."""
import sys,datetime
sys.dont_write_bytecode=True
import pipeline as p

review=p.read(p.OUT/'review_judgments.json')
mapping={x['review_id']:x for x in p.read(p.OUT/'review_key.json')}
blind={x['review_id']:x for x in p.read(p.OUT/'review_blind.json')}
retention=p.read(p.OUT/'retention_reviews.json')
manifest=p.read(p.OUT/'run_manifest.json')
machine=p.read(p.OUT/'mechanical_checks.json')
requests=p.read(p.OUT/'request_summary.json')
metrics=[];claim_rows=[];sections=[]
def fmt(x):return 'NA（処理失敗・評価不能）' if x is None else str(x)
all_by_group={}
for rv in review['reviews']:
    identity=mapping[rv['review_id']];gid=identity['group_id'];condition=identity['condition']
    all_by_group[(gid,condition)]=rv
    for c in rv['claims']:
        claim_rows.append(dict(record_type='claim',group_id=gid,condition=condition,review_id=rv['review_id'],claim_id=c['claim_id'],field=c['field'],claim_en=c['claim_en'],translation_ja=c['translation_ja'],verdict=c['verdict'],unsupported=c['verdict']!='supported',references=p.json.dumps(c['references'],ensure_ascii=False),reason_ja=c['reason_ja'],evaluator=review['evaluator'],truly_blinded=False))
for gid in p.GROUPS:
    if not p.read(p.OUT/'groups'/gid/'B/status.json')['processing_success']:
        claim_rows.append(dict(record_type='processing_status_not_a_claim',group_id=gid,condition='B',review_id=None,claim_id=None,field=None,claim_en=None,translation_ja=None,verdict='not_evaluable',unsupported=None,references='[]',reason_ja='厳密JSON不成立。Bの最終文なし。主張件数・未支持件数はNAで、この行を主張数に含めない。',evaluator=review['evaluator'],truly_blinded=False))
p.r.p.csvsave(p.OUT/'claim_comparison.csv',claim_rows,list(claim_rows[0]))

for gid in p.GROUPS:
    folder=p.OUT/'groups'/gid;ret=next(x for x in retention['groups'] if x['group_id']==gid)
    row=dict(group_id=gid,in_new_group_effect_aggregate=gid!='known',B_processing_success=p.read(folder/'B/status.json')['processing_success'])
    sections += [f'## {gid}：A/B比較',ret['summary_ja']]
    for condition in ['A','B']:
        rv=all_by_group.get((gid,condition))
        if rv is None:
            row[condition+'_total_claims']=None;row[condition+'_unsupported_claims']=None
            sections += [f'### {condition}：処理失敗','厳密JSON契約が不成立のため正式なB最終文はない。Aへの差し替えは行わず、Bの未支持件数・全主張数・保持・新設はNAとする。']
            diagnostic=p.read(folder/'stage3c/diagnostic_only.json')['diagnostic_value']
            if diagnostic is not None:
                original=p.read(folder/'A/parsed.json')
                unchanged=diagnostic['revised_decision']==original
                sections += ['**採用しない診断用の3C修正案（Bの表示文ではない）**','> '+str(diagnostic['revised_decision']['textual_finding'])]
                if unchanged:sections += ['和訳：'+all_by_group[(gid,'A')]['finding_translation_ja'],'外側コードフェンスを診断用にだけ除いた隔離解析ではrevised_decisionはAと完全一致。正式parsed.jsonやB表示に昇格させていない。この文をBの比較件数・保持数に使わない。']
            continue
        row[condition+'_total_claims']=len(rv['claims']);row[condition+'_unsupported_claims']=sum(c['verdict']!='supported' for c in rv['claims'])
        record=blind[rv['review_id']];decision=record['decision']
        sections += [f'### {condition}：代表所見の英文原文と和訳','> '+str(decision['textual_finding']),'和訳：'+rv['finding_translation_ja'],'> '+decision['next_check']['inspect'],'和訳：'+rv['next_inspect_translation_ja'],'> '+decision['next_check']['distinguish'],'和訳：'+rv['next_distinguish_translation_ja'],'**選択引用の原文と位置**']
        pos={(q['observation_key'],q['quote_index']):q for q in record['source_positions']}
        for selected in record['selected_evidence']:
            q=pos[(selected['observation_key'],selected['quote_index'])];s=q['source_position']
            sections += [f"`{selected['target_essay_id']}` / `{q['span_id']}` / Unicode [{s['start']},{s['end']}) / 段落 `{s['paragraph_id']}` [{s['paragraph_start']},{s['paragraph_end']}) / at_paragraph_end={s['at_paragraph_end']}",'> '+q['exact_quote']]
        sections += ['**独立に分解した実質的主張**','| ID | 英文命題／和訳 | 暫定判定 | 原文・基準との照合 |','|---|---|---|---|']
        for c in rv['claims']:
            sections.append('| '+c['claim_id']+' | '+c['claim_en'].replace('|','\\|')+'<br>'+c['translation_ja']+' | '+c['verdict']+' | '+c['reason_ja']+' |')
        sections += ['傾向の保留：'+rv['pattern_assessment_ja'],'局所所見と確認点：'+rv['local_and_next_check_ja']]
    row.update(complete_supported_findings_A=ret['complete_supported_findings_A'],same_findings_retained=ret['same_findings_retained'],supported_findings_replaced=ret['supported_findings_replaced'],supported_patterns_A=ret['supported_patterns_A'],same_patterns_retained=ret['same_patterns_retained'],supported_propositions_A=ret['supported_propositions_A'],supported_propositions_retained=ret['supported_propositions_retained'],added_unsupported_claims_B=None if not row['B_processing_success'] else len(ret['added_unsupported_claims_B']),B_grounded_local_finding=ret['B_grounded_local_finding'],B_concrete_next_check=ret['B_concrete_next_check'],improvement=ret['improvement'],retention_reason_ja=ret['retention_reason_ja'])
    metrics.append(row)
    sections += ['**保持・置換・新規未支持主張**',ret['retention_reason_ja'],f"Aの完全支持所見={ret['complete_supported_findings_A']}、支持された正の傾向={ret['supported_patterns_A']}、支持命題={ret['supported_propositions_A']}。Bへの同内容保持・置換・新規未支持・局所所見/確認点の保持は、Bが処理失敗のためすべてNA。"]

new=[x for x in metrics if x['in_new_group_effect_aggregate']]
new_unsupported_A=sum(x['A_unsupported_claims'] or 0 for x in new)
new_unsupported_B=sum(x['B_unsupported_claims'] for x in new) if all(x['B_processing_success'] for x in new) else None
known=retention['known_regression']
ready=known['operation_check_passed'] and any(x['improvement'] for x in new) and all(x['B_processing_success'] and x['added_unsupported_claims_B']==0 and x['same_findings_retained']==x['complete_supported_findings_A'] and x['same_patterns_retained']==x['supported_patterns_A'] and x['B_concrete_next_check'] for x in new)
summary=dict(evaluator=review['evaluator'],truly_blinded=False,groups=metrics,known_regression=known,new_group_count=len(new),new_group_A_unsupported=new_unsupported_A,new_group_A_total_claims=sum(x['A_total_claims'] or 0 for x in new),new_group_B_unsupported=new_unsupported_B,new_group_B_total_claims=sum(x['B_total_claims'] for x in new) if all(x['B_processing_success'] for x in new) else None,new_group_improvements_confirmed=sum(x['improvement'] for x in new),new_groups_with_evaluable_paired_effect=sum(x['B_processing_success'] for x in new),normal_display_groups_A=sum((p.OUT/'groups'/g/'A/feedback_paragraph.txt').exists() for g in p.GROUPS),normal_display_groups_B=sum((p.OUT/'groups'/g/'B/feedback_paragraph.txt').exists() for g in p.GROUPS),next_comparison_guide_met=ready,stop_after_this_pilot=True,automatic_prompt_retuning=False,scope='少数の保存済み採用群。一般性能や採点者間のズレの改善は結論づけない。')
p.save(p.OUT/'pilot_summary.json',summary)

costs=[]
for gid in p.GROUPS:
    request_rows=[r for r in requests if '/'+gid+'/' in r['request']]
    stage_costs=[]
    for stage in ['a','b','c']:
        group_requests=[r for r in request_rows if r['stage']==stage]
        if group_requests:
            start=min(datetime.datetime.fromisoformat(r['started']) for r in group_requests);end=max(datetime.datetime.fromisoformat(r['finished']) for r in group_requests)
            stage_costs.append(dict(stage=stage,requests=len(group_requests),prompt_tokens=sum(r['prompt_tokens'] for r in group_requests),output_tokens=sum(r['output_tokens'] for r in group_requests),observed_batch_elapsed_seconds=(end-start).total_seconds(),timing_caveat='同時バッチ内の群別専用GPU時間ではない。'))
    costs.append(dict(group_id=gid,common_3A_requests=0 if gid=='known' else 2,A_new_3B_requests=0 if gid=='known' else 1,B_incremental_3C_requests=1,stage_costs=stage_costs))
interruption=p.read(p.OUT/'initialization_interruption.json')
init_seconds=(datetime.datetime.fromisoformat(interruption['recorded_at'])-datetime.datetime.fromisoformat(interruption['process']['started'])).total_seconds()
p.save(p.OUT/'cost_summary.json',dict(groups=costs,batches=p.read(p.OUT/'batch_costs.json'),actual_new_requests=manifest['actual_new_requests'],initialization_only_interruption_seconds_upper_bound=init_seconds,initialization_interruption_inference_calls=0,initialization_interruption_outputs_discarded=0,notes='既知Aは保存物再利用で新規要求0。Bの追加コストは各群3C×1。3AはA/B共通。バッチ壁時計は共有を含み、群間で単純加算しない。再起動後最初のbatch_costsはモデル読込を含む。中断初期化時間は別計上。'))

table='\n'.join(f"| {x['group_id']} | {x['A_unsupported_claims']}/{x['A_total_claims']} | NA | NA（A分母={x['complete_supported_findings_A']}） | NA | NA | NA | NA |" for x in metrics)
costtable='\n'.join(f"| {c['group_id']} | {c['common_3A_requests']} | {c['A_new_3B_requests']} | {c['B_incremental_3C_requests']} | "+'; '.join(f"{s['stage']}: {s['observed_batch_elapsed_seconds']:.2f}s, in={s['prompt_tokens']}, out={s['output_tokens']}" for s in c['stage_costs'])+' |' for c in costs)
batchtable='\n'.join('| '+', '.join(b['requests'])+f" | {b['wall_seconds']:.2f} | {b['includes_model_initialization']} |" for b in p.read(p.OUT/'batch_costs.json'))
batch_costs=p.read(p.OUT/'batch_costs.json')
known_response_seconds=next(c for c in costs if c['group_id']=='known')['stage_costs'][0]['observed_batch_elapsed_seconds']
prompts='\n'.join(f"| {v['path']} | `{v['sha256']}` |" for v in manifest['prompts'].values())
selection=p.read(p.OUT/'selection_manifest.json')
selection_table='\n'.join('| '+g['group_id']+' | '+g['rater_id']+' | '+', '.join(g['target_ids'])+' | '+g['reason']+' |' for g in selection['new_groups'])
request_table='\n'.join(f"| {r['request']} | {r['prompt_tokens']} | {r['output_tokens']} | {r['json_valid']} | {r['schema_valid']} | {r['finish_reason']} |" for r in requests)
known_audit=p.read(p.OUT/'groups/known/stage3c/diagnostic_only.json')['diagnostic_value']['claim_checks']
known_wrong_reason=next(x['reason'] for x in known_audit if x['field']=='textual_finding')
report=f'''# 統合フィードバックの主張単位自己検証：1回の小規模パイロット

**次の比較へ進む目安：{'満たした' if ready else '満たしたとは判定しない'}。プロンプトは再調整せず、このパイロットで終了。**

{retention['overall_conclusion_ja']}

問いは「同じ統合初稿を主張ごとに根拠と照合すると、支持された所見を保持しつつ、根拠のない主張を減らせるか」。Aは直接統合、BはAの構造化判断に原文位置情報付き3Cを1回追加したもの。追加モデル呼び出しと追加位置情報の寄与は、この比較では個別に識別できない。

| 群 | A 未支持/全主張 | B 未支持/全主張 | 支持所見の同内容保持/A | 支持所見の置換 | Bの新規未支持 | B根拠付き局所所見 | B具体的確認点 |
|---|---|---|---|---|---|---|---|
{table}

既知ペアは動作確認専用で新規群の効果集計から除外。新規2群だけではA={summary['new_group_A_unsupported']}/{summary['new_group_A_total_claims']}、Bは未支持件数・全主張数ともNA。正常なA/B対比較は0/2群で、改善の有無を評価できなかった。Aには修正対象があったが、改善を確認できた群は0群であり、処理失敗を未支持主張の削減や新設0件と数えない。Aの完全支持所見・正の傾向は各群0件で、部分的に支持される命題は別記した。分母0は保持成功の実証と解釈しない。少数群の記述的な件数であり、一般性能・採点者間のズレの改善は結論づけない。

## 選定と比較の固定

比較元コミット `{manifest['comparison_commit']}`、成果物 `outputs/recsaver_stage3_v1_6_baseline/`。
選定固定時刻は `{selection['frozen_at']}`。全ての新しい3A・3B・3C出力より前にselection_manifest.jsonを保存。

| 群 | 採点者 | 答案 | 選定理由 |
|---|---|---|---|
{selection_table}

全4答案は本人のraw得点・採点者列・本文と照合した。開発用対象・履歴との重複は各false。保存採用プールでの過去露出はあり、未使用の最終評価群とは呼ばない。旧採用プールの検証基準は現行v1.2と同一ではない。既存verifiedかつOverall再構成一致を採用根拠として再利用し、候補解釈・候補監査自由文はモデルへ渡していない。Stage 1/2再実行なし。

既知群はrater_7の1868:1・4902:1。保存済み3B実入力・解析JSON・最終文をバイト同一で再利用し、3Cだけ新規1回。過去の失敗ラベル・正解例・修正例は3C入力へ追加しなかった。

## 実装と機械検査

3A/3B正本はv1.6、3Cはユーザー指定英文をそのまま保存。{{{{INPUT_JSON}}}}のみを置換し、旧3B schema_version=1.5を維持。実際に使用した3本のファイル名・SHA-256は次のとおり。

| 正本 | SHA-256 |
|---|---|
{prompts}

モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、既存snapshot・vLLM・量子化・GPU設定を再利用。全要求temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335、既定system・チャットテンプレートを維持。実行環境・sampling・テンプレート・実入力は機械検査で照合。

既存v1.6の3Aゲート・スコア/公式基準の付加・3Bスキーマ/参照/表示処理を再利用。新群についてだけ、旧ランナーの「両方Overall=3」という固定説明を正確な中立の2答案説明に置き換えた。既知群の入力は変更しない。3Cではsource_excerptsとsource_positionをコードで復元し、upstream_interpretationという提案の解釈と分離した。Unicodeの[start,end)、段落ID、段落/答案境界、および境界と接するかの真偽を、未正規化の原文と照合した。位置一致からthesis/conclusionという機能を自動認定しない。

3Cのrevised_decisionは既存3Bのスキーマ・同群の引用index・観点・本人得点・公式参照を検査してから、同じコードで表示する。候補にない引用/別群の観測キー/不正index/追加の位置フィールドは拒否。3Cの自由文の意味は機械検査で保証せず独立内容評価へ回す。不正ならBは処理失敗で、Aへの差し替えなし。

生成前の19検査は通過。事後の機械検査は{machine['passed']}/{machine['total']}。これは位置・参照・不正出力の拒否を含む制御の成功であり、3CのJSONや内容の成功を意味しない。正常表示はA={summary['normal_display_groups_A']}/3群、B={summary['normal_display_groups_B']}/3群。厳密JSON成立は6/9要求で、3Cはすべて失敗。生出力は変更せず保存し、成立した6要求だけに正式parsed.jsonがある。3Cのdiagnostic_only.jsonは外側コードフェンスを除く診断用の隔離解析であり、正式parsed.jsonやB表示には昇格させていない。実際の新規要求は{manifest['actual_new_requests']}（3A×4、3B×2、3C×3）、上限11以内。再生成・追加自動採点モデル・SLM改稿なし。

| 要求 | 入力tokens | 出力tokens | 厳密JSON | スキーマ | 終了 |
|---|---|---|---|---|---|
{request_table}

3Cの3応答はいずれも先頭がMarkdownのコードフェンスで、JSON解析はline 1 column 1で失敗した。全要求stop終了で、長さによる切り詰めではない。3C応答を修復してBに採用することは今回行っていない。

モデルロード中に旧群専用説明へ気づき、推論開始前に初期化を1回中断した。出力破棄0・推論0で、履歴と証拠はinitialization_interruption.jsonに保存。モデル呼び出し後の修正や選別ではない。

## 評価方法と限界

review_blind.csv / .jsonに、比較条件名と3C自身のclaim_checksを伏せた出力表を作成。原文・本人得点・公式基準を参照し、Codex（実装を担当した同じassistant）が別工程で暫定レビューした。ただし実装者は条件と既知例を知っているため、真の条件盲検は実現できなかった。3Cの判定を正解や件数に使っていない。独立レビューはreview_judgments.json、対応表はreview_key.json、保持・置換の比較はretention_reviews.json。

主張の単位は独立に照合できる実質的命題。同義の反復は1件とし、複合所見を分割。傾向保留・帯の判断も各1件。コードが忠実に表示する引用・ID・得点・公式記述の単なる転載は機械検査へ分離し、純粋な将来の指示は主張数へ入れず確認点の有用性として判定する。contradictedとinsufficientを未支持に含める。分母や単位の詳細はreview_protocol.json、全命題の英文・和訳・出典・理由はclaim_comparison.csv。

'''+ '\n\n'.join(sections)+f'''

## 既知ペアの回帰確認

3Cが段落末の誤りを検出したか：{known['detected_unsupported_paragraph_end']}。

{known['reason_ja']}

**採用しない診断用の3C自己判定の英文（正解として使わない）**

> {known_wrong_reason}

和訳：観測キー1868:1::O1の引用index [0,1]は、答案が明確な主張で始まり、段落末で中心的な考えを繰り返しているという主張を支持する。

独立照合：これはS004のend=610に対するparagraph_end=765、at_paragraph_end=falseと食い違う。3C自身のsupported判定をそのまま正解としなかった。3群とも診断用revised_decisionはAと同一であったが、これを正式なBの保持成功・改善なしの対比較件数へ算入しない。

最終文での変化：{known['revision_type']}。動作確認：{known['operation_check_passed']}。この結果は新しい群の効果集計に含めない。

## 追加コスト

| 群 | A/B共通の新規3A | Aの新規3B | Bの追加3C | 段階別の観測経過時間・tokens |
|---|---|---|---|---|
{costtable}

群の段階別時間は各要求の開始からバッチ結果保存までの観測経過時間。同時バッチ内の専用GPU時間ではなく、群間・段階内で単純加算しない。実際のバッチ壁時計とモデル読込込みの初回コストはbatch_costs.jsonへ分離。中断初期化は{init_seconds:.2f}秒以下（停止後の記録までを含む上限）で別計上し、推論要求数へ足さない。cost_summary.jsonに方式ごとの追加要求・入力tokens・出力tokens・処理時間を保存。

| 実際のバッチ | 壁時計（秒） | モデル初期化込み |
|---|---|---|
{batchtable}

既知群3Cの応答生成区間は{known_response_seconds:.2f}秒で、初期化込みのバッチ壁時計は{batch_costs[0]['wall_seconds']:.2f}秒。新規2群の追加3Cバッチは{batch_costs[3]['wall_seconds']:.2f}秒。Aの新規3Bは2群同時に{batch_costs[2]['wall_seconds']:.2f}秒で、3Aの{batch_costs[1]['wall_seconds']:.2f}秒はA/B共通の前処理要求。専用GPU時間や単独実行時の速度は推定しない。

## 終了

{retention['next_step_ja']}

この1回のパイロットで終了した。結果を見てプロンプトを再調整せず、追加のモデル判定・再生成・SLM改稿は実施していない。
'''
(p.OUT/'validation_report.md').write_text(report,encoding='utf-8')
manifest.update(pilot_summary_path='pilot_summary.json',claim_comparison_path='claim_comparison.csv',evaluation_evaluator=review['evaluator'],evaluation_truly_blinded=False,known_pair_excluded_from_effect_aggregate=True,next_comparison_guide_met=ready,stop_after_this_pilot=True,automatic_prompt_retuning=False,stage3c_strict_json_pass=0,stage3c_strict_json_fail=3,normal_display_groups_A=3,normal_display_groups_B=0,diagnostics_excluded_from_condition_B=True)
p.save(p.OUT/'run_manifest.json',manifest);p.finish()
print('Report saved; next-comparison guide met:',ready)
