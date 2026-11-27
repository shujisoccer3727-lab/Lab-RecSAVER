# 採点者3組の履歴件数を揃えたフィードバック生成

未使用エッセイを用いた事後的な事例分析。3点差の事例を選んだ分析である。採点時刻はデータ列に存在せず、行順・ID順は採点時系列として扱っていない。

比較用5エッセイを全6名の全生成段階から除外し、本人の別エッセイ20件をseed 20261126で事前固定した。各ターゲットエッセイには残る19件から固定した本人履歴3件を使い、理由候補2件を生成した。個別理由とフィードバックは英語の生成原文を保持している。

本人の真の採点理由、採点上の因果的な重み、再採点での点差縮小、一般的な性能は検証していない。引用の出典一致と意味的な支持を区別する。Stage 6のモデル検証は実施していない。以下の内容点検は、この実行に対するCodexの暫定レビューであり、独立した人手評価ではない。

正式なStage 5代表所見・確認点と比較用5エッセイを点検した。全保存所見の意味的妥当性を網羅的に認定していない。パターン支持所見は正式5出力とも空であった。

## 段階別集計

|採点者|対象|出力候補|JSON通過|スキーマ通過|マスク通過|完全一致|採用エッセイ|有効所見付き|統合M|状態|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
|rater_12|20|40|40|40|40|27|15|14|14|rendered|
|rater_13|20|40|40|40|38|31|16|16|14|strict_json_failed|
|rater_10|20|40|40|40|37|25|14|14|14|rendered|
|rater_11|20|40|40|40|39|25|15|15|14|rendered|
|rater_2|20|40|40|40|40|26|14|14|14|rendered|
|rater_7|20|40|40|40|38|27|15|15|14|rendered|

JSON通過はStage 1の厳密JSON解析、完全一致はマスク入力検査とStage 3の値検査を通り、観測Overallと完全一致した候補数。採用エッセイは少なくとも1候補が通ったエッセイ数である。

renderedは英語表示文の成立、strict_json_failedは厳密JSON不成立を表す。表示成立は意味的な正しさの認定ではない。

有効所見付きは少なくとも1件の出典照合が通ったエッセイを指し、意味的な支持の認定ではない。統合対象は再構成の完全一致で選ばれた部分集合であり、本人の全採点履歴を代表する標本とは扱わない。

## 件数合わせ

- pair_1: 所見付きエッセイ 14 / 16 件から双方 M=14 件。容量による上限: なし。
- pair_2: 所見付きエッセイ 14 / 15 件から双方 M=14 件。容量による上限: なし。
- pair_3: 所見付きエッセイ 14 / 15 件から双方 M=14 件。容量による上限: なし。

抽出は生成前の固定順位による。未使用の所見も全て保存している。M=1では評価傾向を保留し、M=0では証拠不足を記録する。

## 固定した英語フィードバックと暫定点検

### rater_12

A scoring pattern cannot be established from these cases. Insufficient evidence from distinct essays to establish a consistent feature-to-evaluation pattern. In essay essay_877968498339559487d0d5a4, the relevant excerpt is “I think that have a good attitude is great.” The sentence contains a grammatical error in the verb form 'have' which should be 'having'. The recorded Grammar score is 2. The official descriptor for Grammar:2 is “Many errors in grammar and usage.” This evidence alone does not establish whether that band is appropriate. This observation does not establish the frequency of grammatical errors throughout the essay. Next inspect: Other sentences in the essay for similar verb form errors or other grammatical issues. Check: The frequency and impact of grammatical errors on the essay's clarity.

代表所見の出典: `AAAXMP138200001572302814_OR` / source_row_id=5856 / Grammar。行番号は出典識別に用い、採点時系列とは扱わない。

暫定点検: 代表の局所文法所見は支持、評価傾向と帯の適否は保留。原文の『I think that have a good attitude is great.』には非標準的な節構造があり、haveをhavingとする読みは局所的に妥当である。1文から文法誤りの頻度やGrammar:2のMany errorsを認定しておらず、その保留は適切。14エッセイという入力数自体が不足しているという判断ではなく、同一の特徴と評価の関係を支持する横断的な比較根拠が提示されなかった。

### rater_13

英語表示文は未成立。構造化出力または失敗記録を参照。

暫定点検: 厳密JSON不成立、正式フィードバックの対応評価は保留。生出力はMarkdownのjsonコードフェンスで囲まれており、最初の非空白文字が{ではない。正式parsed.jsonと表示文は作成されていない。フェンスの除去、再生成、診断的読みを成功へ算入する処理は行わなかった。生出力を読めることと、比較条件の正式出力が成立することを区別する。

### rater_10

A scoring pattern cannot be established from these cases. The provided observations do not establish a consistent pattern of feature-to-evaluation relationship across multiple essays. In essay essay_96b587aeaf1f53910d5e55c9, the relevant excerpt is “To be more specific about how importance of attitude, your day is great or bad is depended on how your attitude toward the happen.” In essay essay_96b587aeaf1f53910d5e55c9, the relevant excerpt is “ For example, you dressed a beautiful shirt in the pretty day, suddenly, somebody walked pass you and spilled coffee on your shirt.” In essay essay_96b587aeaf1f53910d5e55c9, the relevant excerpt is “ Which attitude should you make to let your day continuing to be a great day?” In essay essay_96b587aeaf1f53910d5e55c9, the relevant excerpt is “ You get angry and ruin everything, or you give a bright smile and make a nice conversation.” The essay uses a clear example to illustrate the importance of a positive attitude, showing the writer's ability to use examples to support their argument and maintain a coherent flow of ideas. The recorded Cohesion score is 4. The official descriptor for Cohesion:4 is “Organization generally well controlled; a range of cohesive devices used appropriately such as reference and transitional words and phrases to connect ideas; generally appropriate overlap of ideas”. This evidence alone does not establish whether that band is appropriate. This evidence does not establish the overall coherence of the essay, only the coherence within this specific example. Next inspect: Review the transitions between paragraphs to ensure they maintain the flow of the argument. Check: The consistency of the main idea and the logical connections between paragraphs.

代表所見の出典: `AAAXMP138190000186842108_OR` / source_row_id=4299 / Cohesion。行番号は出典識別に用い、採点時系列とは扱わない。

暫定点検: 例示部分の局所的なつながりは支持、全体的な結束性と評価傾向は保留。態度についての説明、シャツにコーヒーをこぼされる例、反応を問う疑問、怒る反応と笑顔の反応の対比が選択4区間に揃っている。例示内部の話題の連続は確認できる。引用だけでエッセイ全体の結束性やCohesion:4の妥当性を確定しておらず、他段落間のつながりを点検する確認点は利用できる。

### rater_11

A scoring pattern cannot be established from these cases. The available observations do not show a consistent pattern of feature-to-evaluation relationship across multiple essays. In essay essay_eeb87df489f116eb7f0767b9, the relevant excerpt is “Firstly honesty is the best policy, because it builds a good relationship.” In essay essay_eeb87df489f116eb7f0767b9, the relevant excerpt is “ saying the truth builds a healthy relationship.” The essay uses transitional phrases such as 'Firstly' and 'saying the truth' to connect ideas within the paragraph. The recorded Cohesion score is 3. The official descriptor for Cohesion:3 is “Organization generally controlled; cohesive devices used but limited in type; Some repetitive, mechanical, or faulty use of cohesion use within and/or between sentences and paragraphs.” This evidence alone does not establish whether that band is appropriate. This observation is limited to the local context and does not establish the overall coherence of the essay. Next inspect: Other paragraphs for similar transitional phrases or logical connections to ensure consistency in the essay's structure. Check: The presence of transitional phrases and their effectiveness in maintaining a logical flow of ideas.

代表所見の出典: `AAAXMP138200001277382845_OR` / source_row_id=5561 / Cohesion。行番号は出典識別に用い、採点時系列とは扱わない。

暫定点検: 一部支持、接続表現の分類に意味的な問題。Firstlyは列挙の接続標識として確認できる。一方、saying the truthは命題の内容を表す表現であり、それ自体をtransitional phraseとする分類は支持しにくい。同じ段落内でhonestyとtruthを言い換える語彙的な結び付きは考えられるが、生成文はその違いを説明していない。接続標識と論理的関係を区別して点検する必要がある。原文引用と記録得点の出典一致は、この分類の正しさを保証しない。生成文は修正せず保持した。

### rater_2

A scoring pattern cannot be established from these cases. The provided observations do not establish a consistent pattern of feature-to-evaluation relationship across multiple essays. In essay essay_3b9f17fe0fbc82924e5e05cf, the relevant excerpt is “ I am strongly agree with this option, in my opinion, the elective courses are the clases that make you be in high school for four years.” In essay essay_3b9f17fe0fbc82924e5e05cf, the relevant excerpt is “ To graduate in three years is not imposible when you have the time and the bocation to do it, for example: if you take off all the elective cources in your clases, you are going to see that those clases are the ones that make u be at school one extra year more, then if you try to finish all the elective cources during the summer, you are going to have many extra time to complete the classes that you must need to graduate.” The essay contains grammatical errors such as nonstandard verb forms and structures, which can affect the clarity and correctness of the argument. The recorded Grammar score is 3. The official descriptor for Grammar:3 is “Some errors in grammar and usage.” This evidence alone does not establish whether that band is appropriate. This observation does not establish the frequency of such errors throughout the essay, only their presence in these specific sentences. Next inspect: Review other sentences in the essay for similar grammatical errors to assess the overall frequency and impact on the argument. Check: The frequency and impact of grammatical errors on the overall clarity and correctness of the argument.

代表所見の出典: `AAAXMP138190000175792128_OR` / source_row_id=7694 / Grammar。行番号は出典識別に用い、採点時系列とは扱わない。

暫定点検: 局所文法所見は一部支持、上流の誤り分類と影響範囲に注意。I am strongly agreeは非標準的な動詞構造として確認できる。上流所見が同列に挙げたTo graduate in three years is not imposibleは、不定詞主語の構造自体を文法誤りとは認定できず、imposibleの綴りはConventionsと区別すべきである。ただし選択された長い第2引用にはmany extra timeなど別の文法上の問題があり、文法問題の存在という狭い所見は支持される。実際の理解阻害や論証の正否、エッセイ全体での頻度を引用だけで確定しない。生成文と上流所見は変更していない。

### rater_7

A scoring pattern cannot be established from these cases. The provided observations do not show a consistent pattern of feature-to-evaluation relationship across multiple essays. In essay essay_10bde717c719b4cc15923b78, the relevant excerpt is “Some people feel inspired to the quote " unless you do something beyond of you have mastered, you will never grow" written by Author Ralph Waldo Emerson.” In essay essay_10bde717c719b4cc15923b78, the relevant excerpt is “ I say its because to achieve an new goal, to be a bigger person, and discover the unknown.” The essay begins with a quote from Ralph Waldo Emerson and then provides a personal interpretation of the quote's meaning. The recorded Cohesion score is 2. The official descriptor for Cohesion:2 is “Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition.” This evidence alone does not establish whether that band is appropriate. This observation does not establish the overall coherence of the essay, only the initial connection between the quote and the writer's interpretation. Next inspect: Review the transitions between paragraphs to see if the writer maintains the connection to the initial quote throughout the essay. Check: Check if the writer's interpretation of the quote is maintained and developed throughout the essay.

代表所見の出典: `AAAUUP138190000573842110_OR` / source_row_id=8679 / Cohesion。行番号は出典識別に用い、採点時系列とは扱わない。

暫定点検: 引用提示と自分の目標への局所的な接続は支持、確認点の適用文脈は限定的。原文はEmersonの言葉として引用を提示し、新しい目標や成長に結び付けた自分の説明を続けている。引用の意味を正確に解釈したかやエッセイ全体の結束性までは選択2区間で確定しない。冒頭位置は事後の原文区間表で確認できたが、Stage 5へ位置情報を追加したわけではない。確認点はinitial quoteを前提としており、引用から始まらない比較用エッセイへ直接対応させる根拠は得られなかった。

## 比較用5エッセイとの照合

以下の比較は生成後の別監査である。比較用エッセイの得点と原文を、生成済みのフィードバックへ追加したり、生成文を手直ししたりしていない。局所的な確認点としての対応を記録し、Overallの3点差の原因とは扱わない。

### AAAXMP138200001580432804_OR（Overall 2 / 5）

**rater_12 — Grammar（記録得点 3）**

固定フィードバックの確認点（英語原文）: Other sentences in the essay for similar verb form errors or other grammatical issues. The frequency and impact of grammatical errors on the essay's clarity.

原文根拠 S11 [786:993]: “ it's just like how a 2nd grader doesn't know certain things a 10th grader know's but if the tenth grader started teaching the 2nd grader stuff then the 2nd grader would would know more then they did before.”

対応する公式基準 Grammar:3: “Some errors in grammar and usage.”

対応判定: 一部対応。would wouldという助動詞の重複が、他の文法上の問題を点検する対象になる。代表所見と同じhave/having型の誤りがあるという根拠は確認していない。確認点のother grammatical issuesという範囲では照合できるが、1区間から誤りの頻度や理解阻害の程度、記録Grammar:3やOverall:2の妥当性は決まらない。

**rater_13 — Overall（記録得点 5）**

比較に使用できる固定フィードバックの確認点は未成立。

対応する公式基準 Overall:5: “Native-like facility in the use of language with syntactic variety, Appropriate word choice and phrases; well-controlled text organization; precise use of grammar and conventions; rare language inaccuracies that do not impede communication.”

対応判定: 対応評価保留（正式出力不成立）。比較用エッセイの原文と全記録得点は照合済みだが、rater_13の正式な固定フィードバックは厳密JSONエラーにより成立していない。生出力の確認点を正式出力として採用したり、原文から代わりの確認点を補作したりしない。この事例で両者の正式フィードバックを並べた比較は成立していない。下記Overall:5の基準は出典確認のために示し、適切な点数との認定ではない。

### AAAXMP138200001666792812_OR（Overall 2 / 5）

**rater_12 — Grammar（記録得点 3）**

固定フィードバックの確認点（英語原文）: Other sentences in the essay for similar verb form errors or other grammatical issues. The frequency and impact of grammatical errors on the essay's clarity.

原文根拠 S4 [304:658]: “ For example, this help students by teaching them how to write a clear sentence so the reader can understand the massage of the writer, and this helps them at school too because sometimes teacher makes them write an essay or a paragraph and for that they need to know how to write a constructed sentence to make sure their ideas are clear for the reader.”

原文根拠 S8 [1275:1580]: “ For example, this helps them by making sure their ideas are clear, it helps them to learn were to put a period or commas in their sentence, it teaches them how to start a paragraph or sentence to make sure their topic is clear, and it helps the reader to know when you have end a sentence or a paragraph.”

対応する公式基準 Grammar:3: “Some errors in grammar and usage.”

対応判定: 対応可（局所文法の確認）。this help studentsやwhen you have endに、動詞の一致・語形を点検できる箇所がある。複数箇所で文法形式と意味の回復可能性を確認するという固定確認点に対応する。haveを含むだけで代表所見と同一の構文問題だとは扱わない。記録Grammar:3に対応するSome errorsという記述と照合できるが、観測Overallの2と5の差をこの所見で説明したり、再採点後の点数を推定したりしない。

**rater_13 — Overall（記録得点 5）**

比較に使用できる固定フィードバックの確認点は未成立。

対応する公式基準 Overall:5: “Native-like facility in the use of language with syntactic variety, Appropriate word choice and phrases; well-controlled text organization; precise use of grammar and conventions; rare language inaccuracies that do not impede communication.”

対応判定: 対応評価保留（正式出力不成立）。rater_13の正式な固定フィードバックが成立していないため、両者の確認点の比較を保留する。原文や記録得点の検証は完了しているが、これは利用できる確認点が得られたことを意味しない。コードフェンスを除いて成功扱いにする処理や報告用の手修正は行っていない。

### AAAXMP138190000293162108_OR（Overall 5 / 2）

**rater_10 — Cohesion（記録得点 5）**

固定フィードバックの確認点（英語原文）: Review the transitions between paragraphs to ensure they maintain the flow of the argument. The consistency of the main idea and the logical connections between paragraphs.

原文根拠 S3 [477:754]: “Firstly, there is two type of people in the world, "Possitive and negative people", possitive people get less stress, and are more healthy for many reasons for example: when these people gets really sick, they never stop fighting against sickness in order to win and persevere.”

原文根拠 S6 [1135:1297]: “A person with a possitive attitude is always welcome in any job, and any place because this person will make pople arround him feel happy to be working with them.”

原文根拠 S11 [2292:2379]: “To Conclude, possitive attitude is the key to success in School, work and relationship.”

対応する公式基準 Cohesion:5: “Text organization consistently well controlled using a variety of effective linguistic features such as reference and transitional words and phrases to connect ideas across sentences and paragraphs; appropriate overlap of ideas.”

対応判定: 対応可（段落間の論理接続の確認）。健康、仕事、結論へと扱う場面が移りながらpositive attitudeという主題を共有している。段落間で主張が保たれ、各具体例が主張をどう発展させるかを確認するという固定確認点に対応する。標識の存在だけでCohesion:5のconsistently well controlledを認定せず、例示間の論理的なつながりを全文で点検する対象として示す。

**rater_11 — Cohesion（記録得点 2）**

固定フィードバックの確認点（英語原文）: Other paragraphs for similar transitional phrases or logical connections to ensure consistency in the essay's structure. The presence of transitional phrases and their effectiveness in maintaining a logical flow of ideas.

原文根拠 S3 [477:754]: “Firstly, there is two type of people in the world, "Possitive and negative people", possitive people get less stress, and are more healthy for many reasons for example: when these people gets really sick, they never stop fighting against sickness in order to win and persevere.”

原文根拠 S5 [1122:1131]: “Secondly,”

原文根拠 S6 [1135:1297]: “A person with a possitive attitude is always welcome in any job, and any place because this person will make pople arround him feel happy to be working with them.”

対応する公式基準 Cohesion:2: “Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition.”

対応判定: 一部対応（分類上の問題を別記）。FirstlyとSecondlyの列挙標識、および後続の健康・仕事の理由づけは照合できる。接続標識があることと、その標識が実際に論理関係を明確にすることを分けて点検する。固定フィードバックのsaying the truthの分類には問題があるため、その語句の扱いは移用しない。これだけで記録Cohesion:2の適否や代替点数は確定しない。

### AAAXMP138190000301142128_OR（Overall 5 / 2）

**rater_10 — Cohesion（記録得点 5）**

固定フィードバックの確認点（英語原文）: Review the transitions between paragraphs to ensure they maintain the flow of the argument. The consistency of the main idea and the logical connections between paragraphs.

原文根拠 S6 [412:585]: “ Students should not finish high school in three yeas because it gives them opportunities to learn new things, have a part-time job and still be enjoying their teenage life.”

原文根拠 S7 [589:651]: “First, students will have the opportunity to learn new things.”

原文根拠 S12 [1166:1224]: “Second, students will have a chance to do a part-time job.”

原文根拠 S19 [1661:1748]: “Finally, student will have a break like always, but also will enjoy their teenage life.”

原文根拠 S26 [2479:2660]: “ Students should finish school with the traditional four years, because it gives students opportunities to learn new things, have a part-time job and still enjoy their teenage life.”

対応する公式基準 Cohesion:5: “Text organization consistently well controlled using a variety of effective linguistic features such as reference and transitional words and phrases to connect ideas across sentences and paragraphs; appropriate overlap of ideas.”

対応判定: 対応可（主張と理由のつながりの確認）。冒頭の3理由の予告、First・Second・Finallyによる展開、終盤での主張の再提示を原文で確認できる。各理由が主張を発展させるか、段落間で同じ主張が保たれるかという固定確認点に対応する。Cohesion:5の一貫した制御を標識の個数だけで認定せず、具体例の役割や反復の効果を点検する。

**rater_11 — Cohesion（記録得点 2）**

固定フィードバックの確認点（英語原文）: Other paragraphs for similar transitional phrases or logical connections to ensure consistency in the essay's structure. The presence of transitional phrases and their effectiveness in maintaining a logical flow of ideas.

原文根拠 S7 [589:651]: “First, students will have the opportunity to learn new things.”

原文根拠 S12 [1166:1224]: “Second, students will have a chance to do a part-time job.”

原文根拠 S19 [1661:1748]: “Finally, student will have a break like always, but also will enjoy their teenage life.”

原文根拠 S26 [2479:2660]: “ Students should finish school with the traditional four years, because it gives students opportunities to learn new things, have a part-time job and still enjoy their teenage life.”

対応する公式基準 Cohesion:2: “Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition.”

対応判定: 一部対応（分類上の問題を別記）。First・Second・Finallyの機能と、終盤の再提示へのつながりは点検できる。saying the truthを接続標識とした分類は支持せず、実際の列挙標識と命題の内容を区別して照合する。語形・綴りの問題と段落の接続が成立するかを分けて点検し、記録Cohesion:2やOverall:2の正否をこの抜粋だけで決めない。

### AAAXMP138200001998652127_OR（Overall 2 / 5）

**rater_2 — Grammar（記録得点 2）**

固定フィードバックの確認点（英語原文）: Review other sentences in the essay for similar grammatical errors to assess the overall frequency and impact on the argument. The frequency and impact of grammatical errors on the overall clarity and correctness of the argument.

原文根拠 S1 [0:122]: “I think that a student should be able to have an idea of what they wanna do when they older and not when they at children.”

原文根拠 S5 [459:589]: “When you young you believe that you can do it all and that life will just hand you whatever you want when thats not how life goes.”

対応する公式基準 Grammar:2: “Many errors in grammar and usage.”

対応判定: 対応可（局所文法の確認）。when they olderとWhen you youngに、連結動詞の欠落を点検できる具体例がある。別の文でも同種の構造を確認し、形式上の誤りと意味の回復可能性を分けるという確認点に対応する。2区間から全体の頻度や理解阻害、Grammar:2のMany errorsの充足は認定しない。元の代表所見にあった綴りと文法の分類上の問題も、別途保持した。

**rater_7 — Cohesion（記録得点 5）**

固定フィードバックの確認点（英語原文）: Review the transitions between paragraphs to see if the writer maintains the connection to the initial quote throughout the essay. Check if the writer's interpretation of the quote is maintained and developed throughout the essay.

原文根拠 S1 [0:122]: “I think that a student should be able to have an idea of what they wanna do when they older and not when they at children.”

原文根拠 S8 [1176:1257]: “For example, when I was younger I always dreamed about being a pro soccer player.”

原文根拠 S17 [1851:1978]: “ Overall the point is that you jus need to work hard for what you want to be in life and to not start too early in life either.”

対応する公式基準 Cohesion:5: “Text organization consistently well controlled using a variety of effective linguistic features such as reference and transitional words and phrases to connect ideas across sentences and paragraphs; appropriate overlap of ideas.”

対応判定: 直接対応する根拠なし（冒頭引用の前提がない）。全文を点検すると、比較用エッセイは職業について考え始める年齢の意見から始まり、サッカーの個人的経験へ展開している。固定確認点が前提とするinitial quoteに対応する冒頭引用は得られなかった。段落間の接続一般には関連し得るが、固定確認点を別の問いへ書き換えて適合した扱いにはしない。引用がないこと自体はCohesionの減点根拠ではなく、記録Cohesion:5の妥当性もこの不対応からは判断できない。

## 実行上の記録と制約

元データはraw 8,890行、wide 17,780行、有効17,731件・27名。固定5件の行番号・Filename・本文・両者のOverallと6 Trait・空欄Kaggle IDを照合した。

Filename、空欄以外のKaggle ID、空白・改行のみ正規化した本文ハッシュの連結成分で除外する。同一性衝突は別途監査し、モデルには原文を渡す。rater_2では同一エッセイの2レコードでTraitプロフィールが矛盾していたため、そのエッセイを候補プールから隔離した。集計定義の違いにより候補プールは指定時点の1,601件に対し1,599件となった。他の5名は指定件数を再現した。全員の20件は確保できた。

検査版1.1で、数値を含まない固有帯ラベルnative-likeを隔離する修正を行った。旧監査と原出力を保存し、以前の小規模確認で再構成済みだった影響候補1件は比較用採用集計から除外した。生成文は変更していない。

Stage 3では不正な履歴IDを出力した1候補を不採用にした。Stage 4ではターゲットエッセイIDが一致しない1エッセイの所見を除外した。Stage 5ではrater_13のコードフェンス付き出力が厳密JSON不成立となった。全6名の統合要求は実行済みであり、この1名は未実行ではなく形式上の失敗である。各生出力・検査結果・失敗理由を保持し、修復や再生成を行っていない。

運用版1.2では共有GPUメモリへの約1.9GBの退避が確認されたため、gpu_memory_utilizationを0.9から0.8に変更した。モデル・正本・実入力・seed・サンプリング・出力上限は維持し、成功済み要求を再生成していない。割当とスケジュールが全要求で同一とは扱わず、ビット単位の実行間同一性は主張しない。

再構成の一部バッチでも共有メモリ退避に伴う遅延が見られたが、後続バッチは通常速度に戻り、追加の入力変更・再生成は行っていない。実測はgpu_memory_after_080.jsonとgpu_memory_stage3_delayed_batch.jsonに保存した。

マスク改訂とGPU割当変更で中断した生出力未保存の要求は、それぞれの改訂フォルダに区別して記録した。モデルの不正JSONや得点不一致を理由とした再生成は行っていない。

再実行コマンドとファイル契約は `docs/pair_feedback_20261126.md`、設定は `configs/pair_feedback_20261126.json`。実入力・生出力・構造化JSON・表示文・引用区間・採否・失敗理由は本出力フォルダに保存し、学生原文と巨大出力はGit対象外とした。

検証記録: `cpu_validation.json`

```json
{
  "passed": true,
  "check_count": 1996,
  "regression_tests": 10,
  "pair_stats": [
    {
      "pair_id": "pair_1",
      "common": 278,
      "gap3": 2,
      "gap2": 13
    },
    {
      "pair_id": "pair_2",
      "common": 209,
      "gap3": 2,
      "gap2": 11
    },
    {
      "pair_id": "pair_3",
      "common": 439,
      "gap3": 1,
      "gap2": 11
    }
  ],
  "invalid_records": 49,
  "excluded_prior_smoke_reconstruction_ids": [
    "rater_13__essay_3f4d5d459a296ccd2d5d0c8d__K1"
  ],
  "requests": 570,
  "failures": []
}
```

検証記録: `final_integrity.json`

```json
{
  "time": "2026-11-26T19:18:40.889044+09:00",
  "passed": true,
  "checks": 228,
  "failures": [],
  "output_files": 2864
}
```

検証記録: `smoke_reuse_checks.json`

```json
{
  "passed": true,
  "checked_files": 140,
  "changed": []
}
```

検証記録: `cost_summary.json`

```json
{
  "stages": {
    "1": {
      "actual_saved_requests": 240,
      "comparison_requests": 240,
      "diagnostic_requests": 0,
      "prompt_tokens": 1466394,
      "output_tokens": 315838,
      "truncated": 0,
      "allocation_request_counts": {
        "0.8": 108,
        "0.9": 132
      }
    },
    "3": {
      "actual_saved_requests": 233,
      "comparison_requests": 232,
      "diagnostic_requests": 1,
      "prompt_tokens": 1344153,
      "output_tokens": 54053,
      "truncated": 0,
      "allocation_request_counts": {
        "0.8": 221,
        "0.9": 12
      }
    },
    "4": {
      "actual_saved_requests": 89,
      "comparison_requests": 89,
      "diagnostic_requests": 0,
      "prompt_tokens": 236872,
      "output_tokens": 22559,
      "truncated": 0,
      "allocation_request_counts": {
        "0.8": 85,
        "0.9": 4
      }
    },
    "5": {
      "actual_saved_requests": 8,
      "comparison_requests": 6,
      "diagnostic_requests": 2,
      "prompt_tokens": 56439,
      "output_tokens": 2255,
      "truncated": 0,
      "allocation_request_counts": {
        "0.8": 6,
        "0.9": 2
      }
    }
  },
  "interrupted_requests_without_saved_output": 16,
  "interrupted_token_counts": "Unavailable; interrupted batch returned no persisted output. No successful saved request was regenerated."
}
```

