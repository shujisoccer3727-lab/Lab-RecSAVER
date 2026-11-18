"""版2.1の1答案を読んだ開発レビュー。妥当性認定と展開可否を分ける。"""
from src.recsaver.rater_feedback_development_v21 import ROOT,CONFIG,load,save,sha,now


def main():
    out=ROOT/load(CONFIG)['output_dir'];r=load(out/'one_results.json')
    assert r['target_ids']==['1514:1']
    assert load(out/'one_verification_audit.json')['direct_score_leaks']==0
    review=dict(timestamp=now(),reviewer='Codex development review; not independent human evaluation',
        result_sha256=sha(out/'one_results.json'),proceed_to_fixed_three=True,
        purpose='Only the user-fixed development cases, under unchanged version 2.1, to inspect processing and remaining errors; not quality acceptance or expansion to 27',
        confirmed=[
            'Both actual verification payloads contain no direct target scores; target fields are essay_id/text only.',
            'K2 all four claims marked insufficient with evaluation_supported=false; none entered integration.',
            'Single-essay integration correctly returned empty common_features/judgment_patterns.',
            'Comparison cites only Cohesion clauses and declares local scope, without concluding the Overall grade.',
            'Final sentences retain claim, issue and criterion IDs within the single topic.'],
        remaining=[
            dict(source='generate/K1,K2',issue='Japanese requested, but individual reasons are English. Every claim cites all 19 spans and remains generic; concrete feature evidence was not localized.'),
            dict(source='ground/K1',issue='After retry, atomic flags became true without changing the broad original claims. Mechanical acceptance does not establish atomicity or semantic support.'),
            dict(source='compare/I1',issue='The same organization description repeats; selected Cohesion clauses are not explained condition by condition. Observed Cohesion=4 versus selected level-3 wording is not examined.'),
            dict(source='text/element1,2,3',issue='Element1 describes the essay rather than stating the criterion; element2 recasts the future distinction as a tendency; element3 gives no concrete passage in the reader text.'),
            dict(source='text/element5,limits',issue='Next action is a rater check rather than an explicit rewrite, but remains broad. limits contains writing-improvement advice rather than research limitations.')],
        no_prompt_change_for_three=True,no_replacement=True,usable_with_real_raters=False)
    save(out/'one_review.json',review);save(out/'one_development_review.json',review)
    save(out/'development_review.json',dict(**review,status='One-case reviewed; fixed three-case execution pending'))
    print('One-case gate saved; remaining semantic errors explicitly retained')


if __name__=='__main__':main()
