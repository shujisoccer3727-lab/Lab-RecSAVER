"""比較文章のAI予備確認を記録。未検証事項を正解判定しない。"""
import json
import re
from pathlib import Path
from src.recsaver import rater_feedback_score_comparison_mvp as ex
from src.recsaver.rater_tendency_grounded_review_v2 import quotes

ex.setup()
out=Path(__file__).resolve().parent
rows=ex.records()
main=set(ex.pd.read_csv(out/'pilot_targets.csv').target_id)
frame=ex.core.previous.data()
assert len(rows)==32 and all(r['parse_success'] for r in rows.values())
assert all(r['predicted_overall']==r['rubric_reference_overall'] for r in rows.values())
reviews=[]
notes={
'4163:2':'入力に採点者の文章コメントはない。the rater noted/notingとしてRubric記述を採点者の評言に帰属させている。',
'7497:1':'rater_tendencyのas seen in the comments and scoresは、入力にない採点者コメントの存在を示唆する。初回rawにも同種の問題。',
'1637:1':'In my opinion summer vacation should remain longer等を誤り／一貫性不足として引用するが、何が誤りかの説明が不十分。',
'4735:1':'content and coherence over minor errorsという相対的重み付けはK=3からの推定にすぎず、固有の重みの実証ではない。'}
for tid,r in rows.items():
    # All feedback paragraphs were read alongside their numeric fields.
    # Extra digits in five paragraphs concern historical scores, not JSON mismatch.
    q=quotes(r['essay_evidence'])
    missing=[s for s in q if s not in str(frame.loc[tid,'Text'])]
    known_failure=tid in ['4163:2','7497:1']
    reviews.append({'target_id':tid,'scope':'main30' if tid in main else 'supplemental2','reviewer':'AI preliminary; not human',
        'A_four_components_expressed':True,'B_two_scores_with_rationales_expressed':True,
        'C_difference_explanation':'not_applicable_equal_scores',
        'D_agreement_explained_at_comparison_logic_level':True,
        'D_fabricated_between_score_gap':False,
        'E_reference_presented_as_objective_truth':'no_explicit_claim_found; independence_not_established',
        'F_addressee_is_rater':True,
        'G_grounding':'known_unsupported_attribution' if known_failure else 'not_fully_verified',
        'feedback_score_labels_match_json':True,
        'target_quotations_not_exact':json.dumps(missing,ensure_ascii=False),
        'notes':notes.get(tid,'得点と文章の対応を確認。傾向の固有性、言語誤り・影響の正確性は追加の人手確認が必要。')})
ex.pd.DataFrame(reviews).to_csv(out/'content_review.csv',index=False)
assessment='''# 内容評価のAI予備確認

独立した人手評価ではない。全32件のcomparison_feedbackをスコア値と照合して読んだ。元資料はreview_all_32.md。

固定30件の集計:
- A: 傾向・対象特徴・条件付き予測の根拠・Rubric参考値との比較の4要素を文章上表出: 30件。ただし正しさの認定ではない。
- B: 双方の得点と理由の明示: 30件。
- C: 得点が異なる例: 0件。具体的な評価差を適切に説明した例も0件（分母0であり成否率は定義しない）。
- D: 一致と共通の評価観点を説明し、架空のスコア差を作っていない: 30件。ただしRubricの一般的な言い換えにとどまる例があり、理由全体の妥当性を保証しない。
- E: comparison_feedbackに参考値を絶対的正解と断定する明示的表現は確認されず、uncertaintyに解釈上の不確実性がある。ただし全件一致で、条件付き予測へのアンカリングがないとは検証できない。
- F: あなたの採点履歴／予測という採点者宛の比較: 30件。答案執筆者への一般的助言を主内容とする例は確認されなかった。
- G: 4163:2と7497:1の少なくとも2件で、入力にない採点者コメントの帰属・示唆がある。その他もgroundingの完全な正しさは未検証。欠落フィールドがないことを内容の適切さとは判定しない。

2つのscoreとcomparison_feedbackの対応は32件で一致。数字検出で余分な数字があった377:2、1162:2、6690:1、4735:1、6843:2も確認した。これらは歴史的スコアの言及で、今回の2スコアとの矛盾ではない。
対象の引用文字列の非一致はcontent_review.csvに記録したが、句読点、抜粋、修正文等も含み得るため、その数を捏造件数と呼ばない。

生成タイプ:
1. 評価差のある例: 主30件・追加2件とも0件。差異例を作るための再生成はしない。
2. 一致例: 主30件、追加2件。3点同士／4点同士。
3. 根拠や比較に問題のある例: 少なくとも4163:2と7497:1。発表資料には4163:2を問題例として原文のまま掲載。

既存reflectionと比べて双方の得点が明示され、比較文章の形式は得られた。しかし、全件一致と定型的な理由から、研究目的である評価差の説明の有効性は確認できない。
Rubric-referenceは同じPrompt内で履歴を閲覧したLLMの推定であり、条件付き予測とは独立でない。参考値のGoldへの一致率は算出していない。
32件中7497:1だけJSONDecodeErrorにより既存と同じ上限内で1回retryした。初回rawは引用符のエスケープ不足で、全attemptを保存した。1段階の方式は維持したが、全対象が厳密に1回の呼出しで終わったわけではない（生成attempt計33回）。
途中切断は0件。Prompt・設定は途中で変えず、出力の修正・Goldへの補正もしていない。

主比較のAccuracyは53.3%、MAE=.500、RMSE=.753、QWK=.136。旧reflectionは56.7%、.467、.730、.213。小規模な探索であり性能改善の証明ではない。
次の作業は独立した人手確認と、全件一致の原因・参考スコアへのアンカリングの分析。995件への拡大は承認待ちで、今回は実行しない。
'''
(out/'content_assessment.md').write_text(assessment,encoding='utf-8')
report=out/'report.md'
text=report.read_text(encoding='utf-8').replace('presentation_examples_bilingual.mdに保存予定','presentation_examples_bilingual.mdに保存済み')
text+='\n\n'+assessment
report.write_text(text,encoding='utf-8')
ex.core.save(out/'execution_status.json',{'status':'completed','main_attempted':30,'supplemental_attempted':2,'schema_valid':32,
    'generation_attempts':sum(len(r['attempts']) for r in rows.values()),'stopped_after_pilot':True,'full_run_started':False})
ex.core.verify()
ex.core.status('git_status_after')
print('Saved AI content review: 30 main + 2 supplemental; no score differences; 2 known unsupported attributions')
