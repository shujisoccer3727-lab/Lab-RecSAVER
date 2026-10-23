"""保存済み生成文を編集せず、5件の和訳を対にして資料化。"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
rows = {r['target_id']:r for r in map(json.loads,(OUT/'predictions.jsonl').read_text(encoding='utf-8').splitlines())}
translations = {
'4816:2': [
'履歴1（ID=5456:2）と履歴3（ID=8849:2）に見られるように、この採点者は、言語の不正確さや構成上の問題が大きいエッセイには2点を付ける傾向がある。一方、履歴2（ID=8842:2）では、一貫性がより高く誤りが少ないエッセイに4点を付けている。このことは、明確な構成と言語の不正確さの少なさを重視していることを示唆する。',
'対象エッセイには「graduate in three years」「save money and go to college」といった表現があり、ある程度の言語運用能力が見られるが、重大な誤りもあり、構文の多様性に乏しい。例えば「Some schools districts offer programs that allow high school students to graduate in three years instead of the traditional four years」は基本的な理解を示しているが、構文の複雑さに欠ける。また、「one year early graduate you need accomplice yours accomplishment and with your savings can pay your colllege」は、意思伝達を妨げる文法・構文上の誤りを示している。',
'対象エッセイの言語の不正確さと構成上の問題は、履歴1・3で2点を付けた採点者の傾向と一致する。ただし、一貫した考えがいくらかあり、履歴1・3より誤りが少ないことから3点が示唆される。履歴2でも、一貫性が高く誤りが少ないものに高い点を付けていたためである。',
'言語の不正確さや構成上の問題はあるものの、一貫した考えがいくらかあり、最低得点の事例より誤りが少ないため、3点と予測する。これは、一般的な構文と汎用的な語彙に言語運用が限られ、ときに意思伝達を妨げる誤りがあるというルーブリックの記述に対応する。'],
'3453:1': [
'この採点者は、ある程度の言語運用能力はあるが、ときおり誤りが見られ、しっかりした構成に欠けるエッセイに3点を付ける傾向がある。例えば、履歴1（ID=365:1）は重大な文法・構文上の誤りがあり2点であるのに対し、履歴3（ID=1382:1）は構成がより整い、誤りも少なく3点である。',
'このエッセイにはある程度の言語運用能力が見られるが、ときおり誤りがあり、しっかりした構成に欠ける。例えば「It\'s better that there are other ways to influence people because they learn different things and become postivite about themselves.」は文構造の基本的な理解を示しているが、「postivite」という綴りの誤りを含む。また、「People won\'t have to rely on other people giving them bad influence so they can be unsussecful.」には論理的な流れがあるものの、「unsussecful」という綴りの誤りと、「giving them bad influence」という軽微な文法上の問題がある。',
'ときおり誤りがあり、しっかりした構成に欠けるという特徴は、履歴3（ID=1382:1）に見られる、この採点者が3点を付ける傾向と一致する。',
'このエッセイにはある程度の言語運用能力が見られるが、ときおり誤りがあり、しっかりした構成に欠ける。この点は、ルーブリックの3点に対応する。言語の不正確さは意思伝達を大きく妨げるほどではないものの、目立つ形で存在する。'],
'4163:2': [
'この採点者は、ある程度の言語運用能力があり、ときおり文法・構文上の誤りが見られるものの、構成は概ね整っているエッセイに3点を付ける傾向がある。例えば、エッセイ7461:2には文法・構文上の誤りがあるにもかかわらずOverallで3点を付けており、エッセイ全体の一貫性と意思伝達を重視していることが示される。',
'このエッセイにはある程度の言語運用能力が見られるが、ときおり文法・構文上の誤りがある。例えば「Your attitude is the best way to achieve your goals or just a plus to get everything easily」は明確な考えを示しているものの、構文上の問題がいくらかある。また、「Some people say, is not always neccesary have a good actitud」には文法上の誤りがあるが、伝えたい内容はなお伝わる。',
'ある程度の言語運用能力があり、ときおり誤りを含むエッセイに3点を付ける採点者の傾向は、対象エッセイに見られる言語能力と構成に対応している。',
'このエッセイは構成が概ね整っており、ある程度の言語運用能力もあるが、ときおり文法・構文上の誤りがあり、場合によって意思伝達を妨げている。これは、言語の不正確さによって一部で意思伝達が妨げられるという、ルーブリックの3点に対応する。'],
'8814:1': [
'この採点者は、言語運用と構成にある程度の力が見られるものの、文法・構文上の目立った誤りがあるエッセイに3点を付ける傾向がある。例えば、履歴1（ID=3529:2）は、構成がある程度整い語彙の幅もあるにもかかわらず、文法・構文上の誤りが多いためOverallは2点だった。対照的に、履歴3（ID=3502:2）はOverallが3点であり、誤りはあるが、より高い水準の語彙や言い回しも示すという、より釣り合いの取れた評価になっている。',
'このエッセイには言語運用と構成にある程度の力が見られるが、目立った誤りもある。例えば「video」の代わりに「videi」、「many」の代わりに「nany」となっており、綴りと語彙の誤りが見られる。一方、「Being able to take classes at home through video or just online helps make sure all students have a chance to succeed,」といった表現もあり、相応の水準の語彙と構成が示されている。また、「The option of online school is nothing but beneficial」は、明確な立場と主張を示している。',
'誤りがある一方、言語運用と構成には相応の力が見られる点は、履歴3（ID=3502:2）で見られた、採点者が3点を付ける傾向と一致する。文法・構文上の誤りは履歴1（ID=3529:2）と似ているが、全体的な一貫性と語彙の水準からは、3点に近い評価が示唆される。',
'文法・構文上の目立った誤りはあるものの、言語運用と構成にある程度の力が見られるため、Overallは3点と予測する。これは、運用能力は限られているが、誤りをいくらか含みつつも意思伝達は概ね明確という、ルーブリックの3点の基準に対応する。'],
'1637:1': [
'この採点者は、ある程度の言語運用能力があり、ときおり文法・構文上の誤りが見られるものの、構成は概ね整っているエッセイに3点を付ける傾向がある。例えば、履歴2（ID=4087:1）は、ある程度の構文の多様性と語彙の幅がある一方、ときおり言語の不正確さが見られ、Overallは3点となっている。',
'このエッセイにはある程度の言語運用能力が見られるが、ときおり文法・構文上の誤りがある。例えば「In my opinion summer vacation should remain longer」は語彙の幅と構文の多様性を示しているが、「they might have an accident due to the weather」には軽微な文法上の誤りがある（「they might have an accident due to the weather」は「they might have an accident due to the weather conditions」とすべきである）。また、構成は概ね整っており、夏休みを長いままにすべき理由が明確に示されている。',
'対象エッセイの概ね整った構成と、ときおり見られる言語の不正確さは、履歴2（ID=4087:1）で見られた、この採点者が3点を付ける傾向と一致する。',
'このエッセイには語彙の幅と構文の多様性があり、ときおり言語の不正確さがあるものの、意思伝達を大きく妨げるほどではない。構成は概ね整っており、理由も明確に示されている。ルーブリックと採点者の傾向に基づけば、3点が適切である。']}
notes = {
'4816:2':'発表候補。履歴の2点・4点と対象の3点を接続する例。ただし採点者固有性や、構文の複雑さを低く評価する根拠は未確証。',
'3453:1':'発表候補。本文の綴りに言及する例。ただし構成の弱さの根拠は具体性に欠ける。',
'4163:2':'具体的な引用と伝達可能性への言及例。冒頭の英文の何が構文上の問題かは説明不足。',
'8814:1':'長所と短所を併記する例。匿名化表記Generic_Cityへの旧版の否定的言及はない。ただし綴り・語彙・文法の区別は曖昧。',
'1637:1':'問題例。due to the weatherは文法的に成立しており、weather conditionsへの変更は必須の文法修正ではない。以下の和訳は誤指摘もそのまま訳す。'}
blocks = ['# 生成採点理由5件：英語原文と和訳',
'出典: grounded v2のpredictions.jsonl。全5件ともGold Overall=3、予測Overall=3。目的抽出であり全体の代表性は保証しない。英語は保存された生成文の全文（各フィールド）を無編集で掲載し、英文内の誤り・誤指摘も保持する。和訳は説明の正しさを保証せず、モデルの主張を訳したもの。人手評価は未実施。']
for number,(tid,jp) in enumerate(translations.items(),1):
    r = rows[tid]
    blocks.extend([f'## {number}. target_id={tid}｜Gold=3・予測=3',notes[tid],
                   '根拠履歴ID: '+', '.join(r['rater_tendency']['supporting_history_ids'])])
    english = [r['rater_tendency']['description'],*[r['reasoning'][k] for k in ['essay_evidence','tendency_connection','scoring_explanation']]]
    for label,en,ja in zip(['評価傾向','Essay本文の根拠','評価傾向との接続','得点の説明'],english,jp):
        blocks.extend([f'### {label}', '**原文**\n\n'+en,'**和訳**\n\n'+ja])
    en = r['rater_tendency']['uncertainty']
    ja = '共通ルーブリックを超えた採点者固有の傾向を確定するには、根拠が不足している。'
    blocks.extend(['### 不確実性','**原文**\n\n'+en,'**和訳**\n\n'+ja])
(OUT/'presentation_examples_bilingual.md').write_text('\n\n'.join(blocks)+'\n',encoding='utf-8')
print('Saved bilingual examples: 5 targets, 25 paired fields')
