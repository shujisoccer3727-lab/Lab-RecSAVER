"""完了MVPの原文・和訳と予備内容確認を保存。生成文は変更しない。"""
import json
from pathlib import Path
from src.recsaver import rater_tendency_reflection_mvp as ex

ex.setup()
out=Path(__file__).resolve().parent
rows=ex.core.records()
old={r['target_id']:r for r in ex.core.read(out/'grounded_v2_baseline.jsonl')}
translations={
'7497:1':'予測Overallの3点は、ルーブリックと採点者の傾向に整合している。このエッセイにはある程度の言語運用能力が見られるが、ときおり意思伝達を妨げる誤りがある。指摘した誤りがエッセイ全体の意思伝達を大きく妨げているか、採点者が再確認するとよい。また、自宅と学校の両方で授業を受ける利点を論じている点には長所があり、それも認めるべきである。',
'7236:2':'予測Overallの3点は、言語運用と構成にある程度の力がある一方、ときおり理解を妨げる誤りがあることを反映している。採点者は、指摘された誤りが実際に意思伝達を妨げるかを再確認し、言語運用と構成の長所も考慮するとよい。この振り返りは、エッセイ全体の質を釣り合いよく評価する助けになる。',
'8814:1':'根拠に基づき、Overallを3点と予測する。このエッセイにはある程度の言語運用能力が見られる一方、ときおり意思伝達を妨げる誤りがあり、ルーブリックと整合している。指摘された誤りが実際に意思伝達を妨げているかを振り返り、論証と語彙の長所も考慮するとよい。この振り返りは、エッセイ全体の伝達上の有効性を釣り合いよく評価する助けになる。',
'1637:1':'Overallを3点と予測する。このエッセイにはある程度の言語運用能力が見られるが、ときおり文法・構文上の誤りがあり、一部では意思伝達を妨げている。意思伝達は概ね明確だが、改善できる誤りもある。明確さと一貫性を確保するため、句読法と文法を再確認するとよい。構成と語彙の使用には長所も見られ、それらは維持すべき良い点である。',
'7085:1':'Overallを3点と予測する。このエッセイにはある程度の構文の多様性と語彙・表現の幅を伴う言語運用能力が見られるが、文法・構文上の誤りがあり、一部では意思伝達を妨げている。構成は概ね整っているが、考えのつながりが欠けたり、うまくいっていなかったりする箇所もある。指摘された誤りが実際に意思伝達を妨げているかを振り返り、多様な文構造と明確な考えという長所も考慮するとよい。'}
blocks=['# 振り返り情報の生成例5件：原文と和訳','原文はscoring_explanation全文。和訳はモデルの主張を訳したもので、正しさや有用性の実証ではない。全項目の英語原文と元資料はreview_all_30.mdを参照。']
for tid,jp in translations.items():
    blocks.extend([f'## {tid}（予測Overall={rows[tid]["predicted_overall"]}）',
                  '**原文**\n\n'+rows[tid]['reasoning']['scoring_explanation'], '**和訳**\n\n'+jp])
(out/'reflection_examples_bilingual.md').write_text('\n\n'.join(blocks),encoding='utf-8')
changes=[{'target_id':t,'grounded_v2':old[t]['predicted_overall'],'reflection':r['predicted_overall']} for t,r in rows.items() if r['parse_success'] and old[t]['predicted_overall']!=r['predicted_overall']]
assessment='''

## 内容の予備確認と限界

AIによる予備確認であり、人手評価ではない。全30件に再確認や長所の考慮を促す文が出力された。
8814:1では誤りが実際に意思伝達を妨げるかと、論証・語彙の長所を確認するよう促す。
ただし、30件で繰り返される「誤りが意思伝達を妨げるか確認する」という助言は一般的になりやすく、個々のEssayに特有の振り返りとして十分かは未検証。
reasoningでrubricという語を含むのは11件。語の不在は比較内容の不在を直ちには意味しないが、具体的な基準との対応の説明は弱い例がある。
「no clear discrepancy」等を明示する出力は0件。Promptに制約を書いたことと、出力がその制約を満たしたことは区別する。
過去履歴に見られた事実と、そこから推定した採点者固有の傾向の区別も依然として弱い例がある。
全30件のrater_tendency.uncertaintyには根拠不足の留保があるが、その一方でdescriptionやconnectionでは傾向を断定する出力もあり、説明内部の整合性に確認が必要。
biased/unfair等の単語はreasoning内では0件。機械検出だけで全ての不適切な断定がないとは結論しない。
今回、別Rubric-only scoreや比較LLMは導入しておらず、正規スキーマの予測スコアは1つのみ。
全30件で再試行0回のため、各対象はLLM生成1回で終了した。
旧版よりAccuracyが1件分上がったが、30件の探索的な結果であり改善の証明ではない。
次の段階に進む前に、全30件の人手確認でRubric比較の具体性、差異なし／不明の明示、建設性、誤指摘の有無を確認することを推奨。
1,000件への拡大やPrompt再修正は今回実施していない。
原文・和訳の例はreflection_examples_bilingual.md。入力・モデル・生成設定は変更していないが、Promptが異なるため予測値まで不変とは限らない。
'''
assessment+='\n\n予測変更対象:\n\n```json\n'+json.dumps(changes,ensure_ascii=False,indent=2)+'\n```\n'
report=out/'report.md'
text=report.read_text(encoding='utf-8')
if '## 内容の予備確認と限界' not in text:
    report.write_text(text+assessment,encoding='utf-8')
ex.core.verify()
ex.core.status('git_status_after')
print(json.dumps(changes,ensure_ascii=False))
