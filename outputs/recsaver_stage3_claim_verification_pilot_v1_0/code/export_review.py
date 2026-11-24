"""Export feedback evidence with condition names and all 3C verdicts hidden."""
import sys,csv,hashlib
sys.dont_write_bytecode=True
import pipeline as p
records=[];key=[]
for group_index,gid in enumerate(p.GROUPS,1):
    folder=p.OUT/'groups'/gid;inp=p.read(folder/'input_3b.json');sources=p.read(folder/'sources.json');positions=p.read(folder/'source_positions.json')
    for condition in ['A','B']:
        target=folder/condition
        if not (target/'feedback_paragraph.txt').exists():continue
        opaque='R'+hashlib.sha256(('pilot-v1:'+gid+':'+condition).encode()).hexdigest()[:8]
        value=p.read(target/'parsed.json');render=p.read(target/'render_result.json')
        records.append(dict(review_id=opaque,case_group='G'+str(group_index),decision=value,display_text=(target/'feedback_paragraph.txt').read_text(encoding='utf-8'),selected_evidence=render['selected_evidence'],available_observations=inp['verified_observations'],rubric_entries=inp['rubric_entries'],source_positions=positions,source_essays=sources))
        key.append(dict(review_id=opaque,group_id=gid,condition=condition))
records.sort(key=lambda r:r['review_id'])
p.save(p.OUT/'review_blind.json',records);p.save(p.OUT/'review_key.json',key)
rows=[dict(review_id=r['review_id'],case_group=r['case_group'],display_text=r['display_text'],structured_decision=p.json.dumps(r['decision'],ensure_ascii=False),selected_evidence=p.json.dumps(r['selected_evidence'],ensure_ascii=False),official_rubric=p.json.dumps(r['rubric_entries'],ensure_ascii=False),source_positions=p.json.dumps(r['source_positions'],ensure_ascii=False)) for r in records]
p.r.p.csvsave(p.OUT/'review_blind.csv',rows,list(rows[0]))
p.save(p.OUT/'review_protocol.json',dict(exported_at=p.r.p.now(),condition_labels_hidden_in_review_table=True,stage3c_verdicts_omitted=True,evaluator='Codex (the implementing assistant), provisional source/score/rubric review',truly_blinded_evaluation=False,limitation='実装者が同じ会話で初稿と条件を知っているため、表から条件名と3C判定を除いても真の条件盲検は実現できない。3Cの判定を正解にせず、原文・本人得点・公式基準と別に照合する。',claim_unit='モデル判断の独立に検証可能な実質的命題。繰り返した同義の命題は1件。コードが忠実に挿入する原文・ID・記録得点・公式基準の単なる転載は機械検査へ分離。純粋な将来の確認指示は実質的事実主張に数えず、確認点の有用性として別評価。傾向保留と得点帯の判断は各1命題。複合所見・限界の実質的な追加断定は分割。',unsupported_definition='contradictedまたはinsufficient。3C claim_checksは独立評価の件数にも正解にも使用しない。',retention_unit='Aの完全に支持された局所所見と傾向。言い換えは保持、別の正しい所見への代表変更は置換。部分的に支持された初稿については命題単位の保持も別記。'))
print('Review export:',len(records),'records; condition names and 3C audit verdicts omitted.')
