"""Render the recorded Codex provisional review; never call or edit a model."""
import sys
sys.dont_write_bytecode=True
import run as r

review=r.read(r.OUT/'content_review.json')
machine=r.read(r.OUT/'invariant_checks.json')
source_checks=r.read(r.OUT/'source_checks.json')
requests=r.read(r.OUT/'request_summary.json')
manifest=r.read(r.OUT/'run_manifest.json')
b=r.read(r.OUT/'stage3b/rater_7/parsed.json')
display=r.read(r.OUT/'stage3b/rater_7/render_result.json')
inp=r.read(r.OUT/'handoff/input_3b.json')
restored=[]
sections=[]
rows=[]
for eid in r.TARGETS:
    folder=r.OUT/'stage3a'/eid.replace(':','_')
    a=r.read(folder/'parsed.json')
    gate=r.read(folder/'mechanical_checks.json')
    er=next(x for x in review['essay_reviews'] if x['target_essay_id']==eid)
    sections += [f'## A：{eid}', er['reason_ja']]
    for o,check in zip(a['observations'],gate['checks']):
        ov=next(x for x in er['observations'] if x['observation_id']==o['observation_id'])
        sections += [f"### {o['observation_id']} / {o['dimension']} / 完全な局所所見：{'合格' if ov['complete_local_supported'] else '未達'}"]
        for field in ['feature','scoring_relevance','limitation','next_check']:
            sections += [f"**{field}（生成英文）**",'> '+o[field], '和訳：'+ov['translations_ja'][field]]
        sections += ['**選択原文との照合**',ov['reason_ja'],'| 区間ID | 段落 | Unicode位置 [start,end) | 原文 |','|---|---|---|---|']
        for s,q in zip(check['source_spans'],check['reconstructed_quotes']):
            record=dict(target_essay_id=eid,observation_id=o['observation_id'],span_id=s['span_id'],paragraph_id=s['paragraph_id'],start=s['start'],end=s['end'],exact_quote=q)
            restored.append(record)
            sections.append(f"| {s['span_id']} | {s['paragraph_id']} | [{s['start']}, {s['end']}) | {q.replace(chr(13),'').replace(chr(10),'<br>')} |")
    rows.append(dict(target_essay_id=eid,generated=len(a['observations']),mechanical_pass=sum(x['pass_'] for x in gate['checks']),complete_local_supported=sum(x['complete_local_supported'] for x in er['observations'])))

criteria=review['criteria']
accepted=all(c['pass_'] for c in criteria) and machine['passed']==machine['total'] and source_checks['passed']==source_checks['total']
next_comparison='「直接統合」と「同じ入力・初稿に対する主張単位の自己検証あり」の比較'
decision=dict(accepted_as_baseline=accepted,status='minimum_gate_met' if accepted else 'minimum_gate_not_met',criteria=criteria,B_string_reference_match=review['B_string_reference_match'],B_semantic_support=review['B_semantic_support'],blocked_by=[x['criterion'] for x in criteria if not x['pass_']],actual_primary_model_requests=len(requests),actual_requests_by_condition=manifest['actual_requests_by_condition'],stop_after_this_run=True,prompt_adjustment_stopped=True,automatic_prompt_tuning=False,new_integration_method_implemented=False,self_verification_calls=0,slm_revision_calls=0,scope='固定2答案での回帰確認。一般性能・複数seed安定性は未評価。',remaining_obstacles=review['remaining_obstacles'],next_stage=next_comparison if accepted else '今回の実行で停止。残った障害と根拠を報告。')
r.save(r.OUT/'baseline_decision.json',decision)
r.save(r.OUT/'restored_quotes.json',restored)
catalog=r.read(r.OUT/'evidence_spans/1868_1.json')
position_context=[s for s in catalog if s['span_id'] in ['E1868_1_P001','E1868_1_P001_S001','E1868_1_P001_S004','E1868_1_P001_S005']]
r.save(r.OUT/'position_regression_1868.json',dict(target_essay_id='1868:1',positions=position_context,selected_span_ids=r.read(r.OUT/'stage3a/1868_1/parsed.json')['observations'][0]['evidence_span_ids'],claimed_quote_actual_span_id='E1868_1_P001_S005',unselected_span_not_counted_as_support=True,semantic_review=review['position_regression_1868_ja']))
r.p.csvsave(r.OUT/'observation_results.csv',rows,list(rows[0]))
summary=dict(primary_requests=len(requests),additional_judge_calls=0,regeneration_calls=0,strict_json_pass=sum(x['json_valid'] for x in requests),schema_pass=sum(x['schema_valid'] for x in requests),targets_with_complete_local_observation=sum(x['complete_local_supported']>0 for x in rows),B_string_reference_match=review['B_string_reference_match'],B_semantic_support=review['B_semantic_support'],machine_passed=machine['passed'],machine_total=machine['total'],source_checks_passed=source_checks['passed'],source_checks_total=source_checks['total'],baseline_accepted=accepted)
r.save(r.OUT/'summary.json',summary)
if accepted:
    r.save(r.OUT/'baseline_method.json',dict(method='direct_integration',prompt_revision='1.6',schema_version='1.5',comparison_commit=r.COMMIT,prompts=manifest['prompts'],fixed_targets=r.TARGETS,input_contract='v1.5',three_requests_only=True,scope=decision['scope'],next_stage=next_comparison,freeze_prompt_adjustment=True))
manifest.update(baseline_registered=accepted,minimum_gate_pass=accepted,blocked_by_criteria=decision['blocked_by'],decision_path='baseline_decision.json',next_stage=decision['next_stage'],source_checks_path='source_checks.json',prompt_revision='1.6',output_schema_version='1.5',generation_request_count=len(requests),additional_model_judgments=0,self_verification_calls=0,slm_revision_calls=0)
r.save(r.OUT/'run_manifest.json',manifest)
r.finalize()

criterion_table='\n'.join('| '+x['criterion']+' | '+('合格' if x['pass_'] else '未達')+' | '+x['reason_ja']+' |' for x in criteria)
request_table='\n'.join(f"| {x['request']} | {x['prompt_tokens']} | {x['output_tokens']} | {x['finish_reason']} | {x['json_valid']} | {x['schema_valid']} | {x['attempt']} |" for x in requests)
prompt_table='\n'.join(f"| {v['windows_path']} | `{v['sha256']}` |" for v in manifest['prompts'].values())
eol_files=[x['file'] for x in source_checks['checks'] if x['kind']=='comparison_commit_content' and x['eol_only_difference']]
report=f'''# Stage 3 v1.6：固定2答案・最低ライン1回検証

**判定：{'合格。直接統合の比較ベースラインとして確定。' if accepted else '未達。比較ベースラインとして確定しない。'}**

| 基準 | 判定 | 根拠 |
|---|---|---|
{criterion_table}

Bの文字列・参照一致：{review['B_string_reference_match']}。意味の裏づけ：{review['B_semantic_support']}。両方を必要条件として判定した。Aは生成所見全体を単位とし、一部だけ正しい所見は数えない。

内容判定はCodexによる暫定評価で、人手による確定評価でも追加モデル判定でもない。機械検査とは独立して `content_review.json` に記録。固定2答案の回帰確認であり、一般性能・複数seed安定性・文章の洗練・前回と同じ引用の再現・積極的な傾向提示は追加条件にしない。

## 比較元と変更範囲

比較元はコミット `{r.COMMIT}` の `outputs/recsaver_stage3_v1_5_baseline_20261122/`。
README、manifest、decision、report、保存済み実入力・原文区間表を確認した。
指定英文だけを正本2本の指定箇所に挿入。schema_versionは「1.5」、プレースホルダーは各1個を維持。
新しい英文に過去の誤答・判定基準・答案固有の正解例を追加していない。

| 実際に使用した正本 | SHA-256 |
|---|---|
{prompt_table}

3Aの実入力2件は前回とバイト同一。fixed_inputと区間表もバイト同一。採用候補・Stage 1/2結果は保存データを再利用し、再実行しなかった。3Aは本文・区間表・観点名だけを受け取る。3Bは今回の3A所見を既存の機械ゲートで原文照合後に受け取り、本人の観測点・公式基準を付加する。候補監査自由文と新しい位置メタデータは3Bに渡していない。

raw CSVのRater_1が両答案でrater_7であること、本文、Overallおよび全6 Traitを照合。1868:1はOverall=3、Cohesion=3、Syntax=3、Vocabulary=4、Phraseology=4、Grammar=3、Conventions=3。4902:1はOverall=3、Cohesion=2、他Trait=3。出典行と列は `source_checks.json` に記録。

既存ランナーのprepare以外の全関数・表示処理はASTで同一。prepareは参照元コミット、正本名、出力先と差分記録のみを更新。検証コードは比較元3Bの保存パスとチェックアウト改行の扱いを更新した。モデルに渡す内容には影響しない。

比較コミットに管理された保存物は内容一致。ローカルの4ファイル（{', '.join(eol_files)}）はWindowsチェックアウトのCRLF/LF差だけがあり、両ハッシュと改行差を記録した。再利用する実入力・区間表にその差はない。比較元の全ローカル保存物は実行前後ハッシュ不変。

## 実行条件と機械検査

Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。モデル設定・system指示・チャットテンプレート・生成設定を前回manifestと照合。実runtimeと各要求のsampling・テンプレートも保存物で照合した。

| 要求 | 入力tokens | 出力tokens | 終了 | 厳密JSON | 構造 | transport attempt |
|---|---|---|---|---|---|---|
{request_table}

3A各答案1回、通し3B1回の計{len(requests)}要求。追加生成・再生成による選別・追加モデル判定・生出力/解析JSONの手修正なし。統合の自己検証とSLM改稿は未実装・未実行。GPUの実行順序によるトークン単位の再現性は評価しない。

| 機械検査 | 結果 |
|---|---|
| 生成前の既存表示・参照検査 | 11/11 |
| コミット・正本・入力・本人得点・コード同一性 | {source_checks['passed']}/{source_checks['total']} |
| 実入力・引用・公式基準・表示・設定・生出力ハッシュ | {machine['passed']}/{machine['total']} |

機械検査は引用文字列・ID・参照の正確さを示す。意味の裏づけと採点判断の適切さは以下の暫定内容判定で別に確認した。

'''+ '\n\n'.join(sections)+f'''

## B：最終フィードバックの照合

代表：`{b['representative_observation_key']}`、quote_indices={b['quote_indices']}。
観測基準参照：`{b['rubric_review']['observed_band_ref_id']}`。
比較帯：`{b['rubric_review']['comparison_band_ref_id']}`。

文字列・参照一致：{review['B_string_reason_ja']}

意味の裏づけ：{review['B_semantic_reason_ja']}

**textual_finding（生成英文）**

> {b['textual_finding']}

和訳：{review['b_translations_ja']['textual_finding']}

**evidence_limit（生成英文）**

> {b['evidence_limit']}

和訳：{review['b_translations_ja']['evidence_limit']}

### 既存コードが組み立てた最終フィードバック全文

> {display['feedback_paragraph']}

和訳（生成文を修正しない）：

{review['final_feedback_translation_ja']}

## C：判断範囲と次の確認

**pattern_limit（生成英文）**

> {b['pattern_limit']}

和訳：{review['b_translations_ja']['pattern_limit']}

**next_check.inspect（生成英文）**

> {b['next_check']['inspect']}

和訳：{review['b_translations_ja']['inspect']}

**next_check.distinguish（生成英文）**

> {b['next_check']['distinguish']}

和訳：{review['b_translations_ja']['distinguish']}

判定根拠：{review['C_reason_ja']}

隣接帯の方向・区別条件：{review['adjacent_band_review_ja']}。

## 前回の問題と終了

1868の位置誤認：{review['position_regression_1868_ja']}

3Aのfeatureが実際に引用した選択外S005の原文（文脈照合用。合格所見の根拠に追加しない）：

> {next(s['text'] for s in catalog if s['span_id']=='E1868_1_P001_S005')}

和訳：人々が日々専門家となり、達人と認められる実際の鍵は、新しいことを学び続ける過程にある。

S005=[611,765)、第1段落=[0,765)。この文が実際に段落末であることと、選択されたS004が段落末であることは別である。全段落・前後の正確な原文位置はposition_regression_1868.jsonに保存した。

4902の有効所見：{review['valid_observation_4902_ja']}

残った障害：{review['remaining_obstacles']}

{'合格したため、この時点でプロンプト調整を打ち切る。次段階は'+next_comparison+'。同じ入力・同じ初稿を固定し、今回その比較手法の実装や生成は行わない。' if accepted else '未達でも今回の実行で停止する。追加生成・調整を行わない。'}

生出力・実入力・解析JSONはstage3aとstage3b、復元引用・Unicode出典位置はrestored_quotes.json、本人得点出典はsource_checks.json、判定はbaseline_decision.json、使用正本名・SHA-256・比較コミット・生成要求数はrun_manifest.jsonに保存した。
'''
(r.OUT/'validation_report.md').write_text(report,encoding='utf-8')
print('A/B/C decision saved:', accepted, '; no additional model calls')
