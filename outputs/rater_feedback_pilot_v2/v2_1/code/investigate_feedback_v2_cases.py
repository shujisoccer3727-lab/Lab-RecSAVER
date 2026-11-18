"""指定された開発3答案の旧版の来歴を、モデルを呼ばずに記録する。"""
import json
import re
import shutil
from src.recsaver.rater_feedback_pilot_v2 import ROOT, load, save, sha, now

IDS = ['1514:1', '1868:1', '4902:1']
OUT = ROOT/'outputs/rater_feedback_pilot_v2/v2_0'


def main():
    old = ROOT/'outputs/rater_feedback_pilot_v2/v1_6'
    snapshot = load(old/'full_results.json')
    r = next(r for r in snapshot['results'] if r['condition']=='B' and r['rater_id']=='rater_7')
    candidates = [c for c in snapshot['candidates'] if c['condition']=='B' and c['target_id'] in IDS]
    items = [i for i in load(old/'inputs.json') if i['target_id'] in IDS]
    calls = [json.loads(s) for s in (old/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    links=[]
    for c in candidates:
        for claim in (c.get('original_reason') or {}).get('claims',[]):
            cid=claim.get('id',f"{c['target_id']}/K{c['candidate_index']}/{claim['claim_id']}")
            patterns=[p for p in r['synthesis']['patterns'] if any(cid in s['claim_ids'] for s in p['support'])]
            comparisons=[x for x in (r['comparisons'].get(c['target_id']) or {}).get('relationships',[]) if cid in x['claim_ids']]
            links.append(dict(candidate_key=c['key'],target_id=c['target_id'],claim_id=cid,
                original_claim=claim,verified=c['verification'],accepted=c['accepted'],
                pattern_nodes=patterns,official_condition_ids=claim['condition_ids'],
                comparison_nodes=comparisons,
                final_elements=[dict(element=e['number'],text=e['text'],claimed_pattern_ids=e['pattern_ids'],
                    claimed_target_ids=e['target_ids'],provenance='aggregate metadata only; no sentence-level link recorded') for e in r['elements']],
                final_sentence_link_confirmed=False))
    sentences=[dict(element=e['number'],sentence=n+1,text=t,
        available_pattern_ids=e['pattern_ids'],available_target_ids=e['target_ids'],
        exact_source_claims_unknown=True,reason='v1.6 text output has no sentence-level evidence IDs; global IDs were attached afterwards')
        for e in r['elements'] for n,t in enumerate(re.split(r'(?<=。)',e['text'])) if t.strip()]
    findings=[
        dict(problem='引用符があるのにないとする',first_observed='compare/B|full_4902:1/I1/analysis_anchors[1]',
             confirmed='4902:1@U008には二つのASCII引用符が存在する。比較出力は引用符が欠けると記述。個別主張にはこの欠落の指摘はない。',
             hypothesis='語だけのanchorが句読点を表さず、全文を見てもモデルが生成した引用境界分析を文字列検査が検証しなかった。注意不足の内部原因までは特定できない。'),
        dict(problem='誤りの存在と意味理解への影響',first_observed='generate/B|1868:1|K1/rationaleおよびC3.limits; groundの支持判定で維持',
             confirmed='C3.featureは誤りの存在のみだが、limitsでは全体のコミュニケーションは阻害されないと追加判断。rationaleは一部で阻害されると記述し整合しない。groundは一部の範囲で支持と説明しながら全体をsupportedにした。',
             hypothesis='複合主張の部分判定と、広がり・解釈可能性の独立欄がないため過剰な支持が下流へ伝わった。'),
        dict(problem='文章特徴の要約を評価傾向にする',first_observed='generateのscore_relation=観測評価と一致など; integrate/P1,P2で共通傾向化',
             confirmed='個別の評価と得点との関係が循環的で、統合は組織・文法・語彙の列挙を評価していると表現。2答案のID要件だけでは判断の共通性は検査されない。',
             hypothesis='特徴の共通性と評価判断の共通性を同じpatternに入れたことが一因。'),
        dict(problem='局所証拠からOverall全体を確定',first_observed='compare/B|full_1868:1/I1/rubric_based_proposal',
             confirmed='analysis_anchorsはThe/main、mistake/that。一方でOverall.S3.C01〜C04を満たすと宣言。選択condition_idsは観点別のみで、宣言内のOverallは構造化照合を受けていない。',
             hypothesis='自由文の基準宣言と構造化IDが独立しており、局所判断とOverall判断の射程を型で分けていなかった。'),
        dict(problem='⑤が添削指示になる',first_observed='pilot compare/B|pilot_1514:1; fullは同答案compare終端失敗',
             confirmed='pilot_content_observations.jsonにapply→appliedの指摘と添削寄りの行動が記録される。fullの1868:1は誤りを確認の反復で、評価判断の区別が具体的でない。',
             hypothesis='確認という動詞の形式判定を満たしても、採点者の評価行動であるかの意味は検査していなかった。'),
        dict(problem='別答案の指摘が最終文章へ混入',first_observed='text/B|full_rater_7：文単位の出典を復元不能',
             confirmed='全採用答案・2patternの比較が同じtext入力。最終③④⑤に付くtarget_idsは例示2答案だが、入力にはそれ以外も存在。個々の文がどの答案由来か記録がない。',
             hypothesis='混入可能な構造は確認できるが、全ての文の混入を断定できない。P2は1514:1と8538:1由来で、例示2答案と一致しない。'),
    ]
    save(OUT/'cause_analysis.json',dict(timestamp=now(),reviewer='Codex development review; not independent human evaluation',
        targets=IDS,condition='B',findings=findings,claim_lineage=links,final_sentence_inventory=sentences))
    rows=['# 旧版の原因調査（モデル呼出しなし）','','Codexによる開発レビュー。確認できた入出力と原因仮説を区別する。','',
        '|問題|最初に確認した段階|確認事項|原因仮説／限界|','|---|---|---|---|']
    rows += ['|'+'|'.join(x[k].replace('|','\\|').replace('\n',' ') for k in ['problem','first_observed','confirmed','hypothesis'])+'|' for x in findings]
    rows += ['','## 主張ごとの対応','','長い原文・span・統合・基準・④⑤はcause_analysis.jsonのclaim_lineageに保存。最終文章は文単位の根拠IDがなかったため、正確な対応は不明として記録した。','']
    (OUT/'cause_analysis.md').write_text('\n'.join(rows),encoding='utf-8')
    files=[p for p in old.rglob('*') if p.is_file()]
    save(OUT/'old_output_hashes.json',{p.relative_to(ROOT).as_posix():sha(p) for p in files})
    save(OUT/'old_cases.json',dict(items=items,candidates=candidates,synthesis=r['synthesis'],
         comparisons={tid:r['comparisons'].get(tid) for tid in IDS},elements=r['elements'],
         calls=[c for c in calls if any(tid in c['key'] for tid in IDS) or c['key']=='B|full_rater_7']))
    save(OUT/'old_manifest.json',dict(timestamp=now(),saved_config=load(old/'resolved_config.json'),
         prompts={p.name:p.read_text(encoding='utf-8') for p in (old/'code').glob('*.txt')},
         old_files=len(files),model_called=False))
    print(f'Cause investigation saved: {len(links)} original claims; {len(sentences)} final sentences; {len(findings)} findings')


if __name__=='__main__': main()
