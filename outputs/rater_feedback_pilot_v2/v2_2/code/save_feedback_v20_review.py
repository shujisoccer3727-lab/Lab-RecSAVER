"""実際に読んだ版2.0の失敗を保存する。生成原本・採否を書き換えない。"""
from src.recsaver.rater_feedback_pilot_v2 import ROOT,save,load,sha,now


def main():
    out=ROOT/'outputs/rater_feedback_pilot_v2/v2_0'
    findings=[
        dict(stage='mask/verify',severity='blocking',source='stage_inputs/verify/B__1514_1__K1.json',
            observed='rationale、unexplained、overall_relation、trait_relationに評価3が残存。',
            judgment='K1の再構成一致は得点漏洩で汚染されており有効な一致件数に含められない。K2は不一致なので追加生成しない。'),
        dict(stage='generate/ground',severity='content_error',source='1514:1/K1/C1',
            observed='you will never know if what you could have done was worth your time相当の節を文法的に不正確と断定しgroundが支持。',
            judgment="その節自体の明確な文法誤りを示していない。U019の後半にtry to something等の別の問題があっても、元の例への誤り断定を支持しない。You'llはU018であり自由生成引用は選択U019だけから取得できない。"),
        dict(stage='generate',severity='insufficient',source='1514:1/K1/C2-C4',
            observed='広い語彙・組織・文法について全spanを指定し、評価3に一致を反復。',
            judgment='特徴と評価の欄を分けただけでは具体性・判断関係は改善していない。'),
        dict(stage='integrate',severity='format_failure',source='stages/integrate/B__one_rater_7.json',
            observed='単一答案で2試行とも異なる2答案の支持制約に違反。',
            judgment='単一答案のschemaで共通配列を空にする必要がある。'),
        dict(stage='compare/text',severity='content_error',source='B|one_local_1514:1',
            observed='誤り例の断定をそのまま継承し、Overall.S3.C04への適合と評価3への該当を述べた。',
            judgment='局所判断から段階への飛躍が残る。影響不明としながら理解阻害条件に該当とする記述も不整合。'),
        dict(stage='text',severity='unsupported_addition',source='B|one_local_1514:1/element5',
            observed='次回の評価で評価傾向を確定しますと追加。',
            judgment='対応する④⑤にはない断定。ID整合性は文章の含意の正しさを保証しない。')]
    save(out/'one_review.json',dict(timestamp=now(),reviewer='Codex development review; not independent human evaluation',
        result_sha256=sha(out/'one_results.json'),proceed_to_fixed_three=False,findings=findings,
        successor='outputs/rater_feedback_pilot_v2/v2_1',generation_originals_retained=True))
    previous=out/'development_review.json'
    if previous.exists() and not (out/'development_review.before_generation.json').exists():
        import shutil
        shutil.copy2(previous,out/'development_review.before_generation.json')
    save(previous,load(out/'one_review.json'))
    (out/'assessment.blocking_addendum.md').write_text('# 版2.0：3答案への展開を中止\n\n評価3が実際の検証payloadに残っていた。形式上の一致1件を有効な自己検証一致と扱わない。版2.1へ分離してマスクと指示を修正し、全生成をやり直す。得点不一致を理由に追加生成したものではない。\n\n'+str(findings)+'\n',encoding='utf-8')
    print('v2.0 review saved: blocked expansion; contaminated verification retained')


if __name__=='__main__':main()
