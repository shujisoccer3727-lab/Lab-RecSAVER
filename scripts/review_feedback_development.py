"""Codexが読んだ実例の開発レビューを保存するための補助（自動正解判定ではない）。"""
import json
import re
from src.recsaver.rater_feedback_development import ROOT,CONFIG,load,save,now


def main():
    cfg=load(CONFIG);out=ROOT/cfg['output_dir']
    facts=[]
    for item in load(out/'inputs.json'):
        quote_positions=[m.start() for m in re.finditer('"',item['target']['text'])]
        facts.append(dict(target_id=item['target_id'],ascii_double_quote_positions=quote_positions,
            caveat='Presence/positions alone do not establish quotation function, clarity or rubric compliance'))
    save(out/'literal_punctuation_checks.json',facts)
    if not (out/'one_results.json').exists():
        review=dict(timestamp=now(),reviewer='Codex development review; not independent human evaluation',
            status='New generated outputs not available; semantic improvement not assessed',
            source_join='All 3 targets and their 3 own histories match raw/wide/v1.6 text and all scores',
            tests='16 CPU tests passed; all 6 guided schemas passed complete JSON and EOS',
            old_findings=load(out/'cause_analysis.json')['findings'],
            implementation_review=[
                'One major judgment per claim requested; actual atomicity still needs model-output review.',
                'Grounded support requires atomic + feature supported + evaluation supported; exact source positions checked separately.',
                'An inferred pattern must cite claims from two different targets; same-essay candidates cannot meet this.',
                'Comparison scope is local_only/cannot_judge; semantic overreach in prose still needs review.',
                'Final text receives only one topic and holds sentence-level claim/issue/criterion IDs; IDs alone cannot prove entailment.'],
            remaining='No actual new reasons, reconstruction scores, integration, C4/C5 or final text yet. Do not describe implementation changes as demonstrated content improvements.')
        save(out/'development_review.json',review)
        rows=['# 新旧比較（生成結果待ち）','','生成前の実装比較であり、改善効果の確認ではない。Codexによる開発レビュー。','',
            '|観点|旧版で確認した具体例|修正版の処理|修正版の実出力|','|---|---|---|---|',
            '|本文から個別判断を確認|1868:1の存在判断に、limitsで伝達阻害なしを追加。rationaleは一部阻害と記述|feature/evaluation/関係/限界を分け、部分支持は採用しない|未生成・未確認|',
            '|統合が特徴要約だけか|P1は組織・文法・語彙の列挙を評価傾向にした|common_featuresとjudgment_patternsを分離、別答案の支持IDを要求|未生成・未確認|',
            '|④の証拠と射程|4902:1@U008に引用符があるのに欠落と記述。1868:1で局所からOverallの全条件を宣言|全文・原文句読点を渡し、局所的な結論に限定|未生成・未確認|',
            '|⑤が採点者の行動か|pilotの1514:1はapplyの添削寄り、full1868:1は誤り確認を反復|actor=rater、評価対象・区別・手順・基準関係を分離。意味を内容レビュー|未生成・未確認|',
            '|最終文章の証拠対応|例示IDは1868/4902だがP2は1514/8538。文ごとの出典なし|論点ごとに限定入力、各文に内部主張・比較・条件ID|未生成・未確認|','']
        (out/'old_new_comparison.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps(dict(literal_source_checks=len(facts),new_outputs_available=(out/'one_results.json').exists()),ensure_ascii=False))


if __name__=='__main__':main()
