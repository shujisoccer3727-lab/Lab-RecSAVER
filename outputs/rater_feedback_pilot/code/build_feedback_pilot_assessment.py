"""予備検証の実測集計と内容上の留保をまとめる。"""
import collections
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import now,save


def main():
    out=ROOT/'outputs/rater_feedback_pilot'
    get=lambda name:json.loads((out/name).read_text(encoding='utf-8-sig'))
    results=get('feedback.json')
    inputs=get('inputs.json')
    selection=get('selection.json')
    checks=get('checks.json')
    audit=get('final_audit.json')
    refs=get('reference_quote_audit.json')
    history=get('history_scope_audit.json')
    quality=get('content_review.json') if (out/'content_review.json').exists() else {}
    claims=[c for r in results for a in r['A'] for c in a['claims']]
    model_labels=collections.Counter(c.get('model_semantic_support',c['semantic_support']) for c in claims)
    lines=['# 採点者フィードバック予備検証：所見と次回の改善', '',f'集計日時: {now()}', '',
      '## 結果の位置づけ', '',
      '既存の自己検証済み・観測Overall条件付きの個別参照推論を使い、入力の結合、証拠整理、傾向の候補化、公式基準との照合、5要素の文章化を実呼出しで確認した。代表性のある最終実験や、フィードバックの有効性・採点者バイアスの是正効果の検証ではない。', '',
      '5要素の原文引用・位置・ID・観測得点・公式基準の転記はプログラムで固定している。最終Cではモデルに個別の関係説明と本文の文章化を分けて依頼した。したがって、モデルの一括生成だけで5要素を正しく対応付けられたとは結論しない。', '',
      '## 実際の入力と対象', '',
      '- 出典: outputs/reasoning_eval_large/verified_reference_pool.jsonl。観測得点なしの通常予測理由、後続tendency系、未検証候補は使用していない。参照推論の新規生成・得点による自己検証の再実行は0件。',
      '- 採用済みプール2,056行を元CSVの論理行番号・採点列位置に結合し、Rater_1／Rater_2の値、本文、観測Overall、保存済み自己検証入力を照合。今回の27選択候補はすべて候補生成journalの実入力も一致。',
      '- 元ルーブリックDOCXは不在。Overall原文MD、構造化JSON、当時の保存プロンプトの一致を確認。原DOCXとの真正性は独立確認できない。観点別ルーブリックや実際のTrait得点・重みは推定していない。',
      f"- seed={selection['seed']}。候補はcandidate_index、attempt_index順。採点者・答案はseedを含むSHA256順。重複候補を履歴数に数えず、ユニークtext_id_kaggleを優先して最大10答案を選択。結果による対象差し替えはない。", '',
      '|採点者|利用可能ユニーク答案|実行答案|観測Overall分布|統合利用可能な暫定主張|傾向候補|', '|---|---:|---:|---|---:|---:|']
    for r in results:
        cs=[c for a in r['A'] for c in a['claims']]
        lines.append(f"|{r['rater_id']}|{selection['available_unique_essays_by_rater'][r['rater_id']]}|{r['target_count']}|{dict(sorted(collections.Counter(r['observed_scores'].values()).items()))}|{sum(c['usable_for_synthesis'] for c in cs)}|{len(r['B']['patterns'])}|")
    lines+=['', f"合計{checks['target_count']}答案。対象本文・観測得点・参照推論・候補ID・当時の3件の履歴はinputs.json。全採点者の利用可能数と選択記録はselection.json。", '',
      '## 既存参照推論に必要な具体性があるか', '',
      f"単一引用符も含めた引用符抽出では、元参照推論の{refs['target_count_with_explicit_quotes']}/27件に計{refs['explicit_quote_count']}の明示的引用を検出した。このうち厳密な本文一致は{sum(bool(q['target_occurrences']) for q in refs['quotes'])}件。句読点の違い等を含み、不一致をすべて捏造と解釈しない。引用符に依らない具体的記述もあるため、これは具体性の完全な測定ではない。初期の静的検査は単一引用符を見落としていたが、最終監査で修正した。", '',
      '多くの理由はOverallの定型表現を含み、評価方向と観測得点の定性的説明は得られる。一方、範囲・頻度・伝達阻害をどこで判断したか、反する例、保留理由は不足しやすい。Aで本文から根拠を探し直す処理自体が追加のモデル判断であり、元の採点者理由を回復したことにはならない。', '',
      '## 本文から確認できない記述・引用の問題', '',
      f"Aで抽出した主張は{checks['extracted_claims']}件（1答案最大3件）。原モデルの意味的支持ラベルは{dict(model_labels)}。レビュー反映後は{checks['semantic_support_counts']}で、厳密引用一致・対象scope等を通った統合利用可能な暫定主張は{checks['usable_claims']}件。", '',
      f"Aの引用は{checks['quote_count']}件、そのうち厳密不一致は{checks['invalid_quote_count']}件。不一致のうち{audit['failed_quotes_whitespace_only']}件は空白・改行正規化だけなら一致するが、根拠として復帰させず除外した。参照推論の主張の原文不一致は{checks['rationale_span_failures']}件。", '',
      'これらは抽出された最大3主張・追加生成引用の検査結果であり、参照推論中の全主張に対する「誤説明率」や、人間が評価した意味的正確性の割合ではない。引用の存在と意味的支持は別判定である。', '',
      '最初の採点者では、we were kidsを誤りとする説明、Kobe Bryantの例への接続を欠如と決めつける説明、短い正しい文から誤りがまれとする説明など7主張を理由付きで保留した。semantic_review.jsonとA_reviewed/に保存し、原モデル判定をA/に保持した。このレビューはCodexによる対象を絞った内容確認で、独立した人間評価ではない。', '',
      '## 対象答案と入力履歴の区別', '',
      f"明示的に過去の採点評価へ言及する参照推論は{len(history)}件: {', '.join(h['target_id'] for h in history)}。該当文と元の履歴IDはhistory_scope_audit.jsonに分離した。これらは対象答案の本文証拠にしていない。", '',
      f"そのうち、Aのhistory_separationが履歴言及なしとする点検フラグは{sum(h.get('A_history_denial_needs_review',False) for h in history)}件。たとえば61:1ではunassessed_claimsに過去評価への言及を残しながらhistory_separationで明示言及なしと答えており、モデルだけの区別は一貫していない。", '',
      'Aの最大3主張では後半の履歴言及が抽出されず、unassessed_claimsやhistory_separationに回る可能性がある。明示的な履歴言及の分離は可能だが、言及がない理由に履歴の影響がないことまでは確認できない。対象本文と3履歴は別々に保存・照合している。', '',
      '## 共通傾向の候補と反例・判断不能', '']
    for r in results:
        lines += [f"### {r['rater_id']}", '']
        if not r['B']['patterns']:
            lines += ['共通傾向は判断できない。']
        for p in r['B']['patterns']:
            ev={c['evidence_id']:c for a in r['A'] for c in a['claims']}
            tids=sorted({ev[e]['target_id'] for e in p['support_evidence_ids']})
            lines += [p['inferred_tendency'], '',
                      f"支持する異なる対象: {tids}。観測Overall: { {t:r['observed_scores'][t] for t in tids} }。",
                      f"反例ID: {p['counterexample_evidence_ids']}。非該当: {p['non_applicable_target_ids']}。証拠不足で未判定: {p.get('unassessed_target_ids',[])}。", '',
                      p['unknowns'], '']
    lines += ['2件以上という条件は候補化の最低条件にすぎない。同じ特徴の頻出から重視度を、低得点との共存から採点者固有のバイアスを推定していない。比較採点者や特徴頻度を統制した分析は行っていない。反例なしと、反例を判断する証拠なしを区別する。', '',
      'rater_4のB原出力には「完全に伝達を妨げなければ3点程度」という、証拠と公式基準から導けない得点上限の一般化が混入し、C_textにも伝播した。tendency_review.jsonでこの規則を除外し、原Bと影響した原C_textを残して、C_textだけを再生成した。B_reviewed/のbefore_review欄は採用しなかった原表現であり、最終Cの入力には渡していない。', '',
      '## ④と⑤の生成品質', '',
      '初回の一括Cは各要素の証拠IDが空で、④が文法一般論にとどまった。強化した一括Cも観測得点と基準段階の取り違え等で停止した。最終Cは転記情報を固定したため対応の機械的誤りを防げたが、文章が具体的な言語特徴を説明するかは別問題として残る。', '']
    if quality:
        lines += ['レビュー担当: '+quality.get('reviewer','Codex'), '', '|採点者・関係|④の具体性と不足|⑤の導出と不足|', '|---|---|---|']
        for q in quality.get('relations',[]):
            lines.append(f"|{q['rater_id']} / {q['relation_id']}|{q['relation_review']}|{q['next_check_review']}|")
    lines += ['', '一般的な「全体を確認する」だけの確認点は、どの文で意味を補う必要があるか、どの段落間の接続が不成功なのか、理解できる誤りとの対比などへ具体化する必要がある。機械的なID・引用一致検査の通過は、この意味的品質の通過ではない。', '',
      '## 次回の個別理由生成プロンプトの改善案', '',
      '1. 主張を一文一機能に分ける。語彙の範囲・文法誤り・伝達阻害を一つのsupportedラベルにまとめない。',
      '2. 各主張にscope（target/history/uncertain）、対象ID、公式条件ID、原文のspan ID・位置を付ける。引用を自由生成させず、検証可能なspanから選択させる。',
      '3. 評価方向と観測Overallへの定性的な説明を分離し、基準の程度・頻度・適切さ・伝達阻害の条件を保持する。',
      '4. 全体判断には複数文・段落のどの範囲を見たか、反例、判断不能な点を要求する。局所例から全体頻度を断定させない。',
      '5. 引用存在検査と意味的支持を別にし、得点再構成だけで正しい参照説明と認めない。特に正しい文を誤りとする説明や、話題の具体例を接続欠如と誤認する説明を検査する。',
      '6. Bでは候補・未確立・非該当・反例・証拠不足を別フィールドにする。候補を出しながら無限定に「判断できない」と書く曖昧さも防ぐ。',
      '7. Cでは固定情報と判断文を分ける。説明は本文の具体的構造→公式条件→参照推論の判断→解釈差・不足→次回確認という一つの論点ごとに生成する。',
      '8. 文法誤り数に基づく新しい減点規則を作らず、次回確認は④で特定した不足の検証手順として書かせる。日本語説明の遵守も段階別に検査する。', '',
      '9. 出力例の値に仕様説明文を置くと、その文が復唱される例もあった。型定義と生成指示を分け、説明対象の実際の言語特徴を少なくとも一つ分析させる。基準の引用や指示の復唱だけの出力は、意味的照合の成功に数えない。', '',
      '## 保存先と再開', '',
      '- report.md: 採点者別の5要素本文、対応表、支持・反例・不明点、原文引用と位置。',
      '- feedback.json / results/: 機械可読の最終データ。A/、A_reviewed/、B/、B_reviewed/、C_relation/、C_text/、C/に中間結果。',
      '- inputs.json / selection.json / provenance.json: 入力全文、来歴、選択、確認不能事項。',
      '- resolved_config.json / prompts / snapshots/: 実際のモデル・生成条件・コードとプロンプト版。calls.jsonlに各呼出しのseed・日時・入力・応答・失敗。',
      '- final_audit.json / checks.json / tests.txt: 引用・位置・欠損・失敗・元ファイル不変の検査。execution_history.jsonとrevisions/に初回出力と修正履歴。',
      '- 再実行: python -m src.recsaver.rater_feedback_pilot remaining（同じ成功済み段階は再利用）。入力・プロンプト変更時は該当段階を別名保存し、新しい実行先を使う。', '',
      '今回確認できるのは処理の動作と生成内容の課題である。フィードバックの有効性、採点者バイアスの存在・是正効果、採点者本人の真の思考を実証していない。']
    (out/'assessment.md').write_text('\n'.join(lines),encoding='utf-8')
    print('assessment.md saved')


if __name__=='__main__':
    main()
