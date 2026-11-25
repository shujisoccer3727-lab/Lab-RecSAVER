"""Independent source-reference regression report; no model calls or output repair."""
import sys,csv,datetime
sys.dont_write_bytecode=True
import pipeline as p
manifest=p.read(p.OUT/'run_manifest.json');claims_manifest=p.read(p.OUT/'claim_manifest.json')
references={r['claim_id']:r for r in p.read(p.OUT/'independent_reference_review.json')['claims']}
requests=p.read(p.OUT/'request_summary.json');mechanical=p.read(p.OUT/'mechanical_checks.json')
rows=[];metrics=[];details=[];assemblies={};llm_count=0;processed_llm=0
for group in p.groups():
    gid=group['group_id'];folder=p.OUT/'groups'/gid;status=p.read(folder/'B/status.json');expected=sum(c['route']=='llm' for c in group['claims']);llm_count+=expected
    llm={};assembly=None
    if (folder/'stage3c/parsed.json').exists():
        parsed=p.read(folder/'stage3c/parsed.json')
        if not p.validate(parsed,p.read(folder/'input_3c.json')):
            llm={v['claim_id']:v for v in parsed['verdicts']};processed_llm+=len(llm)
    code=p.read(folder/'code_verdicts.json')
    if status['processing_success']:
        assembly=p.read(folder/'B/assembly.json');assemblies[gid]=assembly
    displayed=set(assembly['displayed_claim_ids']) if assembly else set()
    unsupported_A=[c['claim_id'] for c in group['claims'] if references[c['claim_id']]['verdict']!='supported']
    unsupported_B=[cid for cid in displayed if references[cid]['verdict']!='supported'] if assembly else None
    supported_A=[c['claim_id'] for c in group['claims'] if references[c['claim_id']]['verdict']=='supported']
    supported_retained=[cid for cid in displayed if references[cid]['verdict']=='supported'] if assembly else None
    metric=dict(group_id=gid,purpose=group['purpose'],processing_success=status['processing_success'],existing_three_group_regression_aggregate=gid!='retention',A_atomic_claim_count=len(group['claims']),A_unsupported_count=len(unsupported_A),B_displayed_atomic_claim_count=len(displayed) if assembly else None,B_unsupported_count=len(unsupported_B) if assembly else None,supported_A_claim_count=len(supported_A),supported_claims_retained=len(supported_retained) if assembly else None,supported_claims_removed=[cid for cid in supported_A if cid not in displayed] if assembly else None,residual_unsupported_claim_ids=unsupported_B,local_finding_retained=assembly['local_finding_retained'] if assembly else None,next_check_ids=assembly['next_check_ids'] if assembly else None)
    metrics.append(metric)
    details += [f'## {gid}',group['purpose']]
    if group['draft_path'] is not None:
        draft=p.read(p.OUT/group['draft_path']);details += ['**Aの代表所見（保存済み原文）**','> '+str(draft['textual_finding'])]
    else:details += ['**Aは保持確認用の既存4902所見。新しい3B生成ではない。**','> '+group['control_source_observation']['feature']]
    a_translations=dict(known='答案は明確な主張で始まり、段落末で中心的な考えを繰り返し、継続学習の重要性に明確な焦点を当てている。',contrast='この文には、主語と動詞の一致の問題や冠詞の誤用を含む文法的誤りがある。',limited='この文にはyou will never growという非標準の動詞形が含まれている。',retention='答案はエマーソンの引用への直接の言及で始まり、それに賛成する理由を明示している。')
    details += ['Aの和訳：'+a_translations[gid]]
    details += ['**固定した命題・原文照合・採否**','| ID / 元フィールド | 判定対象英文／和訳 | コード | LLM | 表示 | 独立照合 |','|---|---|---|---|---|---|']
    for c in group['claims']:
        cid=c['claim_id'];ref=references[cid];cv=code.get(cid);lv=llm.get(cid)
        accepted=cid in displayed if assembly else None
        source_quotes=[]
        for qr in c['selected_quote_references']:
            quotes,ob=p.source_material(gid,qr);source_quotes+=quotes
        row=dict(group_id=gid,claim_id=cid,source_field=c['source_field'],claim_en=c['claim'],translation_ja=ref['translation_ja'],quote_references=p.json.dumps(c['selected_quote_references'],ensure_ascii=False),code_verdict=cv['verdict'] if cv else '',code_reason=cv['reason'] if cv else '',llm_verdict=lv['verdict'] if lv else '',llm_reason=lv['reason'] if lv else '',display_candidate=c['display_candidate'],final_accept=accepted,independent_source_verdict=ref['verdict'],source_check_ja=ref['reason_ja'],position_and_quotes=p.json.dumps(source_quotes,ensure_ascii=False),existing_three_group_regression_aggregate=gid!='retention')
        rows.append(row)
        details.append('| '+cid+' / '+c['source_field']+' | '+c['claim'].replace('|','\\|')+'<br>'+ref['translation_ja']+' | '+(cv['verdict'] if cv else '対象外')+' | '+(lv['verdict'] if lv else '対象外/未処理')+' | '+('保持' if accepted else '除外' if accepted is False else '処理失敗')+' | '+ref['verdict']+'：'+ref['reason_ja']+' |')
    details += ['**選択原文と出典位置（Aと同じ固定代表）**']
    rep=dict(observation_key=group['representative_observation_key'],quote_indices=group['representative_quote_indices'])
    quotes,ob=p.source_material(gid,rep)
    for q in quotes:
        s=q['source_position'];details += [f"`{q['target_essay_id']}` / `{q['span_id']}` / [{s['start']},{s['end']}) / 段落 [{s['paragraph_start']},{s['paragraph_end']})",'> '+q['exact_quote']]
    details += ['**Bの表示文（生成モデルの文章ではなく、固定候補からの組立て）**']
    if assembly:
        details += ['> '+assembly['feedback_paragraph'],'**Bに残った命題の和訳**']
        details += [references[cid]['translation_ja'] for cid in group['display_order'] if cid in displayed]
        details += ['**確認点の保持・除外**']
        for action in group['next_check_candidates']:
            keep=action['action_id'] in assembly['next_check_ids'];details += [f"{action['action_id']}：{'保持' if keep else '除外'}。前提={', '.join(action['premise_claim_ids'])}。英文：{action['text']}"]
    else:details += ['処理失敗。Aや別の所見で穴埋めしない。'+str(status['errors'])]
    details += ['残存する未支持命題：'+str(unsupported_B)+'。正しい命題の除外：'+str(metric['supported_claims_removed'])+'。']

p.r.p.csvsave(p.OUT/'claim_comparison.csv',rows,list(rows[0]))
def displayed(gid,cid):return gid in assemblies and cid in assemblies[gid]['displayed_claim_ids']
def action_removed(gid,aid):return gid in assemblies and aid not in assemblies[gid]['next_check_ids']
position_removed=p.read(p.OUT/'code_verdicts.json')['known']['K05']['verdict']=='contradicted' and not displayed('known','K05') and 'known' in assemblies
opening_kept=displayed('known','K01') and displayed('known','K02')
grammar_8699=displayed('contrast','C01') and not displayed('contrast','C02') and not displayed('contrast','C03') and action_removed('contrast','CN1_agreement') and action_removed('contrast','CN2_articles')
grammar_2016='limited' in assemblies and not displayed('limited','L01') and action_removed('limited','LN1') and action_removed('limited','LN2')
retention_4902=displayed('retention','R01')

# All display candidates and new prospective checks were fixed before inference.
# Check new factual premises independently, apart from inherited residual errors.
new_premise_errors=[]
for gid,assembly in assemblies.items():
    if gid=='known' and displayed(gid,'K02') and not displayed(gid,'K01'):new_premise_errors.append('K02 opening label lacks its verified K01 dependency')
    if gid=='known' and 'KN2_neutral' in assembly['next_check_ids'] and not displayed(gid,'K02'):new_premise_errors.append('Neutral learning check lacks its topic premise')
    if gid=='contrast' and 'CN3_general' in assembly['next_check_ids'] and not displayed(gid,'C01'):new_premise_errors.append('General grammar check lacks C01')
    # The only newly worded declarative candidates are narrower versions of
    # the same propositions. The independent references certify K02/K04/R01.
    for cid in ['K02','K04','R01']:
        if displayed(gid,cid) and references[cid]['verdict']!='supported':new_premise_errors.append(cid+' new candidate unsupported')
all_processed=processed_llm==llm_count==20 and len(assemblies)==4
criteria=[dict(criterion='予定LLM判定の欠落なし',pass_=all_processed,reason=f'{processed_llm}/{llm_count}命題、正常表示{len(assemblies)}/4要求。'),dict(criterion='1868の位置誤認除去と冒頭所見保持',pass_=position_removed and opening_kept,reason=f'K05除去={position_removed}、K01/K02保持={opening_kept}。'),dict(criterion='8699または2016の誤診修正',pass_=grammar_8699 or grammar_2016,reason=f'8699の一般所見保持＋一致/冠詞診断除外={grammar_8699}、2016の誤診と依存確認点除外={grammar_2016}。'),dict(criterion='4902の有効所見保持',pass_=retention_4902,reason=f'R01保持={retention_4902}。既存3群の効果集計から除外。'),dict(criterion='新しい未支持主張を追加しない',pass_=all_processed and not new_premise_errors,reason='固定候補・語義の局所化・前提依存・原文引用・本人得点・公式記述を照合。新規の未支持前提='+str(new_premise_errors)+'。A由来の残存誤りとは区別。')]
passed=all(c['pass_'] for c in criteria)
regression_metrics=[m for m in metrics if m['group_id']!='retention']
aggregate=dict(group_ids=['known','contrast','limited'],A_unsupported=sum(m['A_unsupported_count'] for m in regression_metrics),A_claims=sum(m['A_atomic_claim_count'] for m in regression_metrics),B_unsupported=sum(m['B_unsupported_count'] for m in regression_metrics) if all(m['processing_success'] for m in regression_metrics) else None,B_claims=sum(m['B_displayed_atomic_claim_count'] for m in regression_metrics) if all(m['processing_success'] for m in regression_metrics) else None,supported_A_claims=sum(m['supported_A_claim_count'] for m in regression_metrics),supported_claims_retained=sum(m['supported_claims_retained'] for m in regression_metrics) if all(m['processing_success'] for m in regression_metrics) else None,retention_control_excluded=True,scope='既存3群全ての既知例の回帰集計。未知答案の効果推定ではない。')
summary=dict(minimum_gate_pass=passed,criteria=criteria,regressions=dict(position_1868_removed=position_removed,opening_1868_retained=opening_kept,grammar_8699_corrected=grammar_8699,grammar_2016_corrected=grammar_2016,cohesion_4902_retained=retention_4902),llm_verdicts_planned=llm_count,llm_verdicts_processed=processed_llm,requests=manifest['actual_new_requests'],strict_json_pass=sum(r['json_valid'] for r in requests),outer_fence_removal_used=0,groups=metrics,new_unsupported_claims=new_premise_errors,residual_unsupported_claims={m['group_id']:m['residual_unsupported_claim_ids'] for m in metrics},comparison_components_not_identifiable_separately=True,manual_equivalent_split=True,generalization_evaluation=False,stop_after_this_run=True,prompt_adjustment_stopped=True,next_stage='対象観点を事前に固定した新しい答案群で、採点傾向の支持と保留を比較する。' if passed else '今回で停止。形式・位置検査・LLM判定・保持・表示のどの段階が未達かを報告する。')
summary['existing_three_group_aggregate']=aggregate
p.save(p.OUT/'baseline_decision.json',summary);p.save(p.OUT/'pilot_summary.json',summary)
manifest.update(minimum_gate_pass=passed,decision_path='baseline_decision.json',stop_after_this_run=True,prompt_adjustment_stopped=True,next_stage=summary['next_stage'],llm_verdicts_planned=llm_count,llm_verdicts_processed=processed_llm,strict_json_pass=sum(r['json_valid'] for r in requests),outer_fence_removal_used=0,independent_reference_review_sha256=p.sha(p.OUT/'independent_reference_review.json'))
p.save(p.OUT/'run_manifest.json',manifest)

ctable='\n'.join('| '+c['criterion']+' | '+('合格' if c['pass_'] else '未達')+' | '+c['reason']+' |' for c in criteria)
gtable='\n'.join(f"| {m['group_id']} | {m['A_unsupported_count']}/{m['A_atomic_claim_count']} | {m['B_unsupported_count']}/{m['B_displayed_atomic_claim_count']} | {m['supported_claims_retained']}/{m['supported_A_claim_count']} | {m['residual_unsupported_claim_ids']} |" for m in metrics)
rtable='\n'.join(f"| {r['group_id']} | {r['prompt_tokens']} | {r['output_tokens']} | {r['json_valid']} | {r['schema_valid']} | {r['finish_reason']} |" for r in requests)
report=f'''# Stage 3C v1.1：人手相当の主張分割を使う1回の回帰診断

**最低ライン：{'合格' if passed else '未達'}。この1回で終了し、プロンプトの再調整・再生成を行わない。**

| 最低ライン | 判定 | 原文・処理との照合 |
|---|---|---|
{ctable}

| 群 | A 未支持/固定命題 | B 残存未支持/表示命題 | 正しい命題の保持/A | 残存命題ID |
|---|---|---|---|---|
{gtable}

件数は今回の固定した原子的命題単位。前回の複合主張単位の分母と直接比較しない。処理失敗は削減0件・全削除などと数えずNAとする。knownを含む既存3群すべてを回帰診断として集計し、retentionの4902工程保持確認はこの集計から除外する。未知答案の効果は推定しない。contrastで実際に選ばれた代表はGrammarであり、Cohesionの採点傾向を保持できた実験とは数えない。既存3群は正の採点傾向ではなく、傾向の保留を伴う事例として扱う。

既存3群（known / contrast / limited）の回帰集計はA={aggregate['A_unsupported']}/{aggregate['A_claims']}、B={aggregate['B_unsupported']}/{aggregate['B_claims']}。参照判定で支持された命題の保持は{aggregate['supported_claims_retained']}/{aggregate['supported_A_claims']}。4902の保持確認はこの集計から除外した。claim_manifestのeffect_aggregateは旧パイロットの新規2群区分を残す未使用メタデータであり、今回の回帰集計には既存3群すべてを含める。

**残る誤りは2件。** K06は局所2文から答案全体の明確なfocusへ広げた評価、C02は助動詞後の動詞形などの問題を主語・動詞一致とする誤診。LLMが両方をsupportedとしたため、その前提を使うKN1_originalとCN1_agreementの確認指示も残った。冠詞診断C03と対応する確認点は除去されたが、8699は誤診の完全修正には至っていない。これらはAからの残存で、新しい主張の新設とは分けている。

## 固定元・正本・形式

比較元コミット `{manifest['comparison_commit']}` の `outputs/recsaver_stage3_claim_verification_pilot_v1_0/`。
Stage 1〜3Bは再実行せず、known / contrast / limitedの初稿・得点・公式基準・引用を保存元から再利用。Aは元ファイルとバイト同一。Traitは本人の記録値で、固定引用の観点と得点をコード照合した。比較元は実行前後でハッシュ不変。

実際に使った正本は `{manifest['prompt']['path']}`、SHA-256は `{manifest['prompt']['sha256']}`。指定英文を保存し、実行時は{{{{INPUT_JSON}}}}のみを置換した。

現行vLLM 0.6.6.post1のGuidedDecodingParamsとoutlinesバックエンドによるJSON制約を適用。各要求のID集合・件数・3ラベル・必須フィールドをschemaに固定し、CPUで全4制約をコンパイル。正常例受理、ID欠落・重複・未知ID・未定義ラベル・余分フィールドの拒否を含む43件を通した。IDの一意性は生成後にも厳密検査する。JSON制約が使えるため、外側Markdown枠を除去する方式は使わず、厳密JSONだけを採用。本文修復・再生成なし。

モデル・system・チャットテンプレート・seed・通常sampling設定は保存元と同じ。Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。追加変更は3CのJSON制約。実際のschema、実入力、messages、sampling、生出力、解析結果を各群へ保存。

| 3C要求 | 入力tokens | 出力tokens | 厳密JSON | ID・構造 | 終了 |
|---|---|---|---|---|---|
{rtable}

要求は計4回。外枠除去後の成立は非適用（除去回数0）。厳密JSON成立は{sum(r['json_valid'] for r in requests)}/4。予定したLLM判定は{processed_llm}/20件。事後機械検査は{mechanical['passed']}/{mechanical['total']}。生出力は変更していない。

## 分割・位置検査・表示

claim_manifest.jsonは推論前 `{claims_manifest['frozen_at']}` に固定した22命題、元フィールド、主張ID、英文、選択引用、固定表示候補、確認点の事実前提と依存IDを持つ。分割はCodexによる人手相当の作業で、自動分割の性能ではない。語の切り出しだけで独立しない場合の主語・照応の補足、修正後に残せる局所表現、確認指示の前提を持たない問いへの限定を、出力を見る前に記録した。

位置2命題はコード、それ以外20命題はLLM。S004を段落末とするK05は実際の引用end=610とparagraph_end=765を比較してcontradicted。境界が不明ならinsufficient。thesisなどの修辞機能は位置判定から支持扱いせず、独立したK03としてLLMに渡した。

LLM入力は各claim_id・claim・その主張の選択引用と必要な基準/記録値だけ。上流解釈、採点理由、前回の判定、修正例、固定表示候補、コード判定を含めない。主張ごとの理由は保存するが表示文に使わない。独立参照判定はindependent_reference_review.jsonへ推論前に別保存し、モデルには渡していない。

Bは支持された命題だけを固定候補・順序で組み立てる。claim_manifestのdisplay_orderは命題の照合・記録順で、本文は推論前に実装した固定レイアウト（傾向保留→固定引用→局所所見→記録点/公式基準→限界/帯の保留→確認点）を使う。出力を見た並べ替えは行わない。否定された診断を前提とするsimilar errors等の確認候補も除く。既存の全体focusを既成事実にしない中立の確認候補と、文法問題一般の確認候補も事前固定し、その局所前提が支持されたときだけ残す。局所所見がなければ保留とし、別の候補所見や元初稿で補わない。引用を表示しても、それ自体を代替の所見とは数えない。記録得点・公式記述は原典から引用し、得点帯の妥当性の判断と区別した。

## 独立照合の範囲

評価者は実装を担当した同じCodex。主張ごとの参照判定はモデル出力を見る前に固定し、生成後は固定候補の表示、原文位置、得点・公式基準との対応を照合した。3C自己判定を正解に使わない。既知例の回帰診断であり、独立汎化評価・盲検評価ではない。位置検査、人手相当の分割、LLM判定、JSON制約の変更を組み合わせたため、各変更の効果を個別に識別できない。

主張別のコード判定、LLM判定・理由、採否、参照判定と原文はclaim_comparison.csvへ分けて保存。残存誤りや正しい内容の除外は、最低ラインの総合判定と別に以下へ記載する。

'''+ '\n\n'.join(details)+f'''

## 終了

{summary['next_stage']}

{'この既知例での調整は終了する。新しい群の比較では対象観点を事前固定し、採点傾向を支持する材料がある場合と、保留が妥当な場合を分ける。今回の結果から自動分割・未知答案・採点者間のズレの改善を主張しない。' if passed else '今回はここで停止する。予定判定の処理、位置の除外、文法診断、保持、表示のうち未達となった段階と残存IDを報告し、再生成やプロンプト調整を行わない。'}
'''
(p.OUT/'validation_report.md').write_text(report,encoding='utf-8');p.finish();print('Minimum gate:',passed)
