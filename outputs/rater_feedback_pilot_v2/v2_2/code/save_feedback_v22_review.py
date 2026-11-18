"""Codexが実入出力を読んだ開発レビュー。モデル原出力の採用判定とは別記録。"""
from src.recsaver.rater_feedback_development_v21 import ROOT,load,save,sha,now


def main():
    out=ROOT/'outputs/rater_feedback_pilot_v2/v2_2'
    r=load(out/'three_results.json');items={i['target_id']:i for i in load(out/'inputs.json')}
    claims=[c for candidate in r['candidates'] for c in (candidate['original_reason'] or {}).get('claims',[])]
    all_span=sum(set(c['span_ids'])=={s['span_id'] for s in items[c['target_id']]['target']['spans']} for c in claims)
    findings=[
        dict(id='R1',stage='generate',status='confirmed',claim_ids=[c['id'] for c in claims],
            finding=f'{all_span}/{len(claims)}主張が対象答案の全spanを列挙。原文は実在するが、具体的な判断箇所に絞られていない。英語の一般的な基準文言を反復する。',
            consequence='引用実在の検査に通っても、特徴・評価・程度を説明する局所的な根拠が特定できない。'),
        dict(id='R2',stage='generate',status='confirmed',claim_ids=['1868:1/K2/C3'],
            finding='trait_relationは“The Vocabulary score of 3 ...”だが、本人のVocabularyは4。K1/C3は4を記載。入力/元データ照合は一致しており、初出は生成段階。',
            consequence='Overall再構成一致とは別の誤り。得点マスク後は誤記自体も除去され、証拠点検は元Trait値との一致を検査しないためsupportedで残った。'),
        dict(id='R3',stage='generate → ground',status='confirmed_limitation',claim_ids=['1514:1/K1/C4','1514:1/K2/C3','1868:1/K2/C4','4902:1/K1/C4'],
            finding='1514 K1/C4は誤りの存在から“can impede communication”を足しgroundも反復して支持。同答案K2/C3の類似した影響判断はinsufficient。4902 K1/C4は“not frequent”を分布の説明なく支持。',
            consequence='誤り存在・広がり・意味理解への影響の分離は未達。supported20件はモデルの判定数であり、正しい理由20件を意味しない。'),
        dict(id='R4',stage='generate',status='insufficient_evidence',claim_ids=['4902:1/K1/C1'],
            finding='繰返しの例としてbutとdon’t you want toを挙げるが、U004/U005は各1箇所で、後者は疑問文。これらだけでは接続手段の反復や機械性の説明にならない。',
            consequence='他の箇所に反復がないとは断定しない。文書全体引用の付与と評価の意味的支持を分ける必要がある。'),
        dict(id='R5',stage='integrate/JP1',status='confirmed',claim_ids=['1514:1/K1/C2','1868:1/K1/C2','1868:1/K2/C2','4902:1/K1/C2','4902:1/K2/C2'],
            finding='複雑な文の形成問題が文法構造の3点に影響したと統合するが、個別理由は一般的な誤りと得点の一致を述べるにとどまる。支持例と反例が同じ主張IDで、反例理由も“問題があるが評価は3点”という同じ内容。',
            consequence='3ユニーク答案という形式条件は満たすが、重視度・得点規則・採点者固有性の証拠にはならない。共通評価傾向は未確定として開発レビューする。'),
    ]
    review=dict(timestamp=now(),execution_revision='2.2',scope='three',reviewer='Codex development review; not independent human evaluation',
        result_sha256=sha(out/'three_results.json'),target_ids=list(items),condition='B',usable_with_real_raters=False,
        counts=dict(total_claims=len(claims),claims_selecting_all_target_spans=all_span,meaning='Mechanical span selection count; not an unsupported-claim ground-truth rate'),
        findings=findings,comparison_rows=[],narrative='',prompt_improvements=[
            '個別理由では、観測得点の丸写しに代えて、評価対象の具体的な現象と、その現象を確認できるspan・文脈を対応づける。全spanを並べるだけの出力は具体性を示したと扱わない。任意の語数制約は追加しない。',
            '誤りの存在、出現分布、解釈可能性の判断を分け、影響を述べる場合は実際にどの読みが成立せず何が不明になるかを説明させる。支持・反証・判断保留の例を証拠点検の指示に加える。',
            '観測Overall/Traitsは入力からIDで参照し、理由の自由文に得点を再生成させない。意味点検対象と元の得点対応も別に検査し、自己検証一致を理由品質に流用しない。',
            '統合では、同じ特徴名や得点の一致ではなく、特徴に対して繰り返された評価判断を比較する。反例は何が支持判断と反するかを説明し、反する情報がなければ空配列と判断不能を許容する。',
            '④は公式条件の程度・頻度・適切さのどの部分をどの本文証拠で評価できるかを論点別に対応づけ、局所判断で未確認の条件とOverall全体を保留する。',
            '⑤は④と同じ論点について、採点者が次の答案で何を見分けるか、確認する証拠と基準の関係を示す。書き手への改善指示や根拠のない閾値を混ぜない。',
            '最終文では、要素①を公式記述の提示、②を推定された評価判断、③を実際の所在として区別する。内部IDだけでなく文章の各断定が引用元の何に支えられるかを開発点検する。',
            '長い入力は全文や不都合な証拠を捨てず、同じ証拠・主張・条件をID参照で共有する。元payloadへの完全復元と実トークン長を生成前に検査する。'])
    review['findings'] += [
        dict(id='R6',stage='compare',status='confirmed_limitation',issue_ids=list(r['comparisons']),
            finding='3比較とも全文spanを選ぶが、具体的な文形成上の問題と公式条件の程度・範囲を対応づけない。1514はSyntax.S4.C01/C02を選び、観測Syntax=3との差を説明しない。4902は局所誤りからhigher levelを満たさず他Traitに大きな影響がないと述べる。',
            consequence='観測得点だけに条件を固定しなかった点とlocal_onlyの射程は改善。ただし局所根拠の精査、条件ごとの適合、他観点への影響の保留は未達。1868のagreementにはOverall=3との単純一致が残る。'),
        dict(id='R7',stage='compare → text/5',status='confirmed',
            finding='next_actionのactorはraterで、focus on complex sentencesなど採点者の確認対象になったが、何と何を区別するかが誤り名の反復。最終⑤は「複雑な文の形成に問題がある箇所を重点的に評価する」となり、根拠のない重点化を追加。',
            consequence='明示的な書き直し指示は主文にないが、具体的な評価行動として不十分。compareのreview/unknownsや個別limitsには書き手の改善助言が残る。'),
        dict(id='R8',stage='text/1,2,3,4',status='confirmed',
            finding='①は公式条件ではなく文章特徴を述べ、②は推定と明示せず評価傾向の一部とする。③は「問題がある箇所が見られる」で対象ID・具体箇所・引用を表示しない。④は「局所的には評価が3点に影響」で証拠→条件→判断の関係を説明しない。①④の重複文もある。',
            consequence='5要素番号と内部IDが揃っても、各要素の意味内容は未達。短い本文は生成原文の診断用であり、完成した採点者用本文として採用しない。'),
        dict(id='R9',stage='text/4',status='confirmed_lineage_limitation',
            finding='全文7文は同じJP1の5主張・3答案を参照し、別の話題や対象IDの混入は検出しない。ただし④は3答案を一括参照しSyntax.S3.C02だけを示す。1514比較はS4条件を選んでいるのに、本文でその区別が失われた。',
            consequence='主張IDの異なる答案への誤接続は防ぐが、同一傾向内の答案別の条件・判断の意味的混同まで防げてはいない。内部参照の存在は各断定の意味的支持を保証しない。'),
        dict(id='R10',stage='known issue: 4902 quotation',status='not_retested_as_same_topic',
            finding='U001/U008の引用符実在は保持・照合され、今回「引用符がない」という断定は出ていない。ただし採用された統合はSyntaxの論点で、旧版の引用境界の比較を同じ論点として再試験してはいない。',
            consequence='既知の誤りが今回再出現しなかっただけで、引用境界判断の修正効果は証明できない。'),
    ]
    review['comparison_rows']=[
        ['個別判断の本文支持','v1.6は一般的特徴と観測得点の一致を反復。v2.0には正しい節を誤文とした例。',f'24主張中{all_span}件が全span選択。1514 K2の4主張は証拠不足で除外。一方1868 K2/C3は本人Vocabulary4を3と誤記。','部分支持を形式上排除する検査は機能したが、採用20主張の意味的妥当性は保証されない。'],
        ['特徴要約と評価傾向','旧P1/P2は組織・語彙・文法の特徴列挙だった。','JP1は3ユニーク答案の文形成の評価を参照。ただし3点への影響を繰り返し、支持と反例が同じ主張。','共通性のID条件は満たす。採点者の重視度・固有性・妥当な共通評価傾向は未確定。'],
        ['④の証拠と公式条件','v1.6は1868の局所的な語からOverall.S3条件全体を満たすと宣言。4902は引用符欠落を誤認。','新比較はSyntax条件のみでlocal_only。1514はS4、他2件はS3を選ぶ。全文を渡すが各条件への具体的な適合説明はない。','Overall全体の確定は避けたが、局所評価・他Traitへの影響・条件別の説明には未達。引用符の同一論点は未再試験。'],
        ['⑤の採点者行動','旧版にはapply→appliedなど添削寄り指示と「確認」の反復。','actor=raterで文形成を見る行動だが区別が具体化されず、最終⑤は重点的に評価と重視度を追加。','書き直し命令は主文にない。基準に照らした具体的な区別と根拠のない重点化の防止が必要。'],
        ['最終文章までの対応','旧版は全答案・全論点をまとめて渡し文ごとの出典不明。','JP1だけで文章化し7文すべてに5主張・3答案の内部ID。別話題のID混入はないが、1514のS4条件が本文のS3一括説明に埋没。','機械来歴は改善。③は具体箇所がなく、④も循環説明。意味的な対応保持は未達。'],
    ]
    review['narrative']='''指定rater_7のB条件3答案（1514:1、1868:1、4902:1）、各履歴3件、各2候補を使用した。3答案はいずれもOverall=3。候補6件の生成と自己検証は全件成功・一致したが、理由の正しさとは別の結果である。24個別主張のうちモデルの意味点検は20件をsupported、4件をinsufficientと判定し、統合には3ユニーク答案が入った。Codex点検では全24主張が全spanを列挙し、原文の実在は確認できても具体的な評価箇所は絞れていなかった。supported20件を正答数と解釈できない。

原因調査はモデルを呼ばず旧入出力から実施し、旧版の引用符誤認の初出は比較、誤り存在と影響の混同の初出は個別生成、文章特徴の傾向化は統合、Overallへの飛躍は比較と確認した。内部の認知的原因や旧最終文の完全な来歴は不明として残した。今回の個別生成でも、1868:1/K2/C3のVocabulary得点誤記、曖昧な頻度・影響判断、全文引用による根拠の希薄化が残った。

下流ではJP1を1候補として抽出し、3比較・1文章化まで実行した。ただし反例は支持例と同じ内容で、共通評価傾向の妥当性は未確定。1514のSyntax.S4と他2答案のSyntax.S3という条件選択を最終文が区別せず、④は「局所的には評価が3点に影響しているが、全体的な評価への影響は不明である」と循環的に述べるだけだった。⑤の原文「次回の評価では、複雑な文の形成に問題がある箇所を重点的に評価する」は採点者側の行動だが、何を区別するかを示さず、重点化の根拠もない。①は基準原文の提示でなく特徴要約、③は具体箇所を示さず、採点者への完成稿としては未達である。原文はfeedback.md/feedback.jsonに保持し、内容レビューに合わせた修正文への差替えはしていない。

版2.1で統合等が文脈上限を超えたため、版2.2は重複値の参照化だけを修正し、成功済み生成・検証・証拠点検18件をそのまま引き継いだ。全8下流入力は元入力への完全復元を検査し、全文や反する証拠を削らず、版2.2では文脈上限超過0件。引用・公式条件・内部参照の機械検査は通過したが、意味的支持・有用性を実証したわけではない。これは固定開発事例に対するCodexの開発レビューで、独立した人間評価、最終評価用標本、採点者バイアスや是正効果の検証ではない。'''
    assert review['comparison_rows'] and review['narrative'], 'Complete downstream content review first'
    save(out/'three_development_review.json',review)


if __name__=='__main__':main()
