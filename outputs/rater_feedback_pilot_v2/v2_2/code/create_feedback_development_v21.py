"""版2.0の実出力で見つかった不具合を別版へ分離する。旧ソースを変更しない。"""
import shutil
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    out=ROOT/'outputs/rater_feedback_pilot_v2/v2_1'
    assert not out.exists(),'Never silently recreate a revision'
    out.mkdir(parents=True)
    old=ROOT/'outputs/rater_feedback_pilot_v2/v2_0'
    for name in ['cause_analysis.json','cause_analysis.md','old_cases.json','old_manifest.json','old_output_hashes.json']:
        shutil.copy2(old/name,out/name)
    prompts=ROOT/'prompts/rater_feedback_pilot_v2/v6';shutil.copytree(ROOT/'prompts/rater_feedback_pilot_v2/v5',prompts)
    for p in prompts.glob('*.txt'):
        if p.name!='verify.txt': p.write_text(p.read_text(encoding='utf-8').replace('/2.0','/2.1'),encoding='utf-8')
    additions={
        'generate':'''優先手順：先にclaimsを作り、その根拠に沿ってrationaleを最後に要約する。各主張ではspan_idsを先に選び、その箇所にある具体的な特徴をfeatureで述べ、evaluationで一つの判断だけを説明する。観点名の羅列で済ませない。原文の例文を自由生成しない。具体例はspan_idの参照に任せる。
overall_relationとtrait_relationは「どの特徴がどの観点の判断に関係し、何がなお説明できないか」を書く欄であり、「評価3に一致」「評価と一致」のような得点の言い換え・丸写しは禁止。得点を数値で繰り返さない。ある正確な部分だけを見て文法全般が正確としない。一つの存在判断に、頻度や伝達影響をlimits欄で追加しない。
''',
        'ground':'''反証を優先して点検する。存在判断のために挙げた箇所や例文が正しい場合、同じspanの他の部分に誤りがあっても、元の評価説明を丸ごとsupportedにしない。正しい表現を誤りとする判断はcontradicted。頻度や全体品質の主張に具体的な分布や比較の説明がないならinsufficient。rationaleの全体的な断定を根拠として主張を支持しない。
explanationではfeatureとevaluationのどの部分を確認したかを書く。特徴の存在が支持されても、その評価や程度・影響の説明を確認できない場合evaluation_supported=falseとしてinsufficientにする。追加証拠を明記せずに別の語句を根拠にしない。
''',
        'integrate':'''有効な答案が1件しかないときは共通性を判定できない。common_featuresとjudgment_patternsは必ず空配列とし、その理由をunknownsへ書く。異なる2候補は2答案ではない。十分な評価関係がなければ、特徴だけを残して評価判断は未確定にする。
'''}
    for stage,addition in additions.items():
        path=prompts/f'{stage}.txt';path.write_text(path.read_text(encoding='utf-8').replace('INPUT_JSON:',addition+'\nINPUT_JSON:'),encoding='utf-8')
    source=(ROOT/'src/recsaver/rater_feedback_development.py').read_text(encoding='utf-8')
    source=source.replace('configs/rater_feedback_development.json','configs/rater_feedback_development_v21.json')
    source=source.replace('feedback-pilot-v2/2.0','feedback-pilot-v2/2.1').replace('v2_0','v2_1').replace('/v5','/v6')
    source=source.replace('feedback_development_schema','feedback_development_schema_v21').replace('feedback_development_engine','feedback_development_engine_v21')
    source=source.replace('def masked_reason(reason):','def _legacy_masked_reason(reason):')
    extra='''DIRECT_SCORE_PATTERN = r'(?:Overall|Cohesion|Syntax|Vocabulary|Phraseology|Grammar|Conventions|evaluation|grade|band|level|総合(?:評価)?|評価|得点|スコア|文法|語彙|統語|結束性|表記規則)\\s*(?:の?(?:得点|評価|スコア))?\\s*(?:の|は|が|[:：=])?\\s*[1-5１-５一二三四五]'


def masked_reason(reason):
    safe,logs,residual=_legacy_masked_reason(reason)
    def scrub(text,path):
        def replacement(m):
            logs.append(dict(path=path,start=m.start(),end=m.end(),original=m.group(),
                replacement='[得点表現除去]',reason='direct_score_label_with_optional_separator'))
            return '[得点表現除去]'
        result=re.sub(DIRECT_SCORE_PATTERN,replacement,text,flags=re.I)
        residual.extend(dict(path=path,match=m.group()) for m in re.finditer(DIRECT_SCORE_PATTERN,result,re.I))
        return result
    for field in ['rationale','unexplained']: safe[field]=scrub(safe[field],field)
    for c in safe['claims']:
        for field in ['feature','evaluation','overall_relation','trait_relation','limits']:
            c[field]=scrub(c[field],c['claim_id']+'.'+field)
    return safe,logs,residual


'''
    source=source.replace('def validate_reason(obj,item):',extra+'def validate_reason(obj,item):')
    source=source.replace("assert len({s['target_id'] for s in p['support']})>=2", "assert len({s['target_id'] for s in p['support']})>=2, 'Need two distinct target essays, not repeated candidates'")
    source=source.replace("'new claim fields separate feature/evaluation/score relationships'", "'v2.1: scrub direct score labels without separators, e.g. evaluation3 / 評価3; v2.0 verification was contaminated', 'v2.1: evidence-first schema order and explicit counterchecks', 'v2.1: single-essay common arrays constrained empty', 'new claim fields separate feature/evaluation/score relationships'")
    (ROOT/'src/recsaver/rater_feedback_development_v21.py').write_text(source,encoding='utf-8')
    schema=(ROOT/'src/recsaver/feedback_development_schema.py').read_text(encoding='utf-8')
    schema=schema.replace("return obj(rationale=s,claims=arr(obj", "return obj(claims=arr(obj")
    schema=schema.replace("direction=enum(['positive','negative','mixed','unclear']),", "direction=enum(['positive','negative','mixed','unclear']),")
    schema=schema.replace("overall_relation=s,trait_relation=s,limits=s),1,4),unexplained=s)","overall_relation=s,trait_relation=s,limits=s),1,4),rationale=s,unexplained=s)")
    schema=schema.replace("judgment_type=enum(['presence','extent','impact','organization','range','appropriateness']),\n            feature=s,evaluation=s,span_ids=ids([x['span_id'] for e in essays for x in e['spans']],1),", "span_ids=ids([x['span_id'] for e in essays for x in e['spans']],1),\n            feature=s,evaluation=s,judgment_type=enum(['presence','extent','impact','organization','range','appropriateness']),")
    schema=schema.replace("support=obj(target_id=enum(tids),claim_ids=ids([c['id'] for c in claims],1))", "support=obj(target_id=enum(tids),claim_ids=ids([c['id'] for c in claims],1))\n        if len(set(tids))<2: return obj(common_features=arr(s,0,0),judgment_patterns=arr(s,0,0),unknowns=s)")
    (ROOT/'src/recsaver/feedback_development_schema_v21.py').write_text(schema,encoding='utf-8')
    engine=(ROOT/'src/recsaver/feedback_development_engine.py').read_text(encoding='utf-8').replace('from .feedback_development_schema import output_schema','from .feedback_development_schema_v21 import output_schema')
    (ROOT/'src/recsaver/feedback_development_engine_v21.py').write_text(engine,encoding='utf-8')
    save(out/'revision_origin.json',dict(timestamp=now(),source_version='2.0',
        defects=['Observed 評価3 survived v2.0 mask and contaminated reconstruction','Single-essay integration attempted duplicate supports',
            'Correct phrase misidentified as grammar error; generic circular score explanation remained'],
        reuse_old_generated_reasons=False,retry_budget_changed=False,score_mismatch_regeneration=False,
        fixed_targets_unchanged=True,downstream_reuse=False))
    print('Created isolated version 2.1; no old code or model output overwritten')


if __name__=='__main__':main()
