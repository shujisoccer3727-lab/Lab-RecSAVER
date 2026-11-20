# 個別理由と統合の暫定内容点検

点検者はCodex。人手評価・独立評価・確定正解ではない。機械的事実は`mechanical_audit.json`・各候補の`mechanical_checks.json`、意味判断は本ファイルと`content_review.json`に分ける。引用の実在は主張の正しさや採点者の実際の思考を保証しない。

全生成6候補を対象に点検。採用0候補のため、採用後の内容品質・選別改善は評価できない。以下の出典は当実験ディレクトリからの相対パスとJSON pointer。

## rater_7 / 1514:1 / 1514_1__K1

出力: `stage1/1514_1__K1/parsed.json`。入力: `stage1/1514_1__K1/input.json`。対象Overall=3。履歴ID: 217:1, 1440:1, 8745:1。

**根拠となる生成原文**

- pattern: "The rater appears to evaluate essays with a mix of strengths and weaknesses, often giving scores that reflect a balance between effective use of language and noticeable errors."
- target feature: "The essay demonstrates a mix of effective and less effective language use, with some errors in syntax and cohesion."
- decision: "The rater appears to have evaluated the essay based on its balance of strengths and weaknesses, giving it a score that reflects a moderate level of proficiency. The essay demonstrates a mix of effective and less effective language use, with some errors in syntax and cohesion, which aligns with the rubric descriptors for Overall score 3. This interpretation is supported by the rater's history of evaluating essays with a mix of strengths and weaknesses."
- score-free rubric connection: "The rubric descriptors for Overall score 3 indicate a mix of effective language use and noticeable errors, which aligns with the observed features of the essay."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_assessable|`target_evidence/0`。具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 7/7件が完全一致。
得点分離点検: target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。

## rater_7 / 1514:1 / 1514_1__K2

出力: `stage1/1514_1__K2/parsed.json`。入力: `stage1/1514_1__K2/input.json`。対象Overall=3。履歴ID: 217:1, 1440:1, 8745:1。

**根拠となる生成原文**

- pattern: "The rater appears to evaluate essays with a mix of strengths and weaknesses, often giving scores that reflect a balanced consideration of the essay's overall quality. The rater seems to appreciate essays with a clear structure and varied vocabulary but penalizes for grammatical errors and awkward phrasing."
- target feature: "The essay demonstrates a clear structure and varied vocabulary but also contains grammatical errors and awkward phrasing."
- decision: "The rater likely evaluated the target essay based on a balanced consideration of its strengths and weaknesses. The essay demonstrates a clear structure and varied vocabulary, which aligns with the rater's appreciation for these features. However, the presence of grammatical errors and awkward phrasing may have led the rater to penalize the essay, resulting in an Overall score that reflects a balanced evaluation."
- score-free rubric connection: "The rubric for Overall score 3 indicates facility limited to the use of common structures and generic vocabulary; organization generally controlled although connection sometimes absent or unsuccessful; errors in grammar and syntax and usage."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_assessable|`target_evidence/0`。具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 8/8件が完全一致。
得点分離点検: target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。

## rater_7 / 1868:1 / 1868_1__K1

出力: `stage1/1868_1__K1/parsed.json`。入力: `stage1/1868_1__K1/input.json`。対象Overall=3。履歴ID: 5783:1, 239:1, 8666:1。

**根拠となる生成原文**

- pattern: "The rater appears to evaluate essays with a generally controlled organization, a sufficient range of vocabulary, and an evident use of phrases, but with some noticeable repetitions and misuses."
- target feature: "The essay demonstrates a generally controlled organization, a sufficient range of vocabulary, and an evident use of phrases, but with some noticeable repetitions and misuses."
- decision: "The target essay demonstrates a generally controlled organization, a sufficient range of vocabulary, and an evident use of phrases, but with some noticeable repetitions and misuses. This aligns with the rater's historical pattern of evaluating essays with these characteristics. The repetition of phrases such as 'keep learning' may be a limitation, but the overall control of organization and vocabulary range supports a score that reflects these strengths."
- score-free rubric connection: "The rubric for a score of 3 in Cohesion, Vocabulary, and Phraseology aligns with this evaluation."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|partially_met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_assessable|`target_evidence/0`。具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 4/5件が完全一致。
得点分離点検: target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。

個別の重要点: 観測Traits辞書が全入力と一致しないのは省略による。K1はSyntax、K2はSyntax/Grammar/Conventionsが欠ける。**記載された得点値が誤っているという意味ではない。** K1のrubric_connectionはVocabulary/Phraseologyにも3の帯を当てる一方、本人の対象Vocabulary/Phraseologyは4。この不整合を未解決として扱えていない。

## rater_7 / 1868:1 / 1868_1__K2

出力: `stage1/1868_1__K2/parsed.json`。入力: `stage1/1868_1__K2/input.json`。対象Overall=3。履歴ID: 5783:1, 239:1, 8666:1。

**根拠となる生成原文**

- pattern: "The rater appears to evaluate essays that show a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology."
- target feature: "The essay demonstrates a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology."
- decision: "The target essay demonstrates a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology. This aligns with the rater's historical pattern of evaluating essays that show a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology. The rater may evaluate this essay as showing a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology."
- score-free rubric connection: "The rubric for a score of 3 indicates a generally controlled organization with a range of vocabulary and phraseology, but with some limitations in cohesion and occasional inaccuracies in phraseology."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|partially_met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_assessable|`target_evidence/0`。具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 4/5件が完全一致。
得点分離点検: target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。

個別の重要点: 観測Traits辞書が全入力と一致しないのは省略による。K1はSyntax、K2はSyntax/Grammar/Conventionsが欠ける。**記載された得点値が誤っているという意味ではない。** K1のrubric_connectionはVocabulary/Phraseologyにも3の帯を当てる一方、本人の対象Vocabulary/Phraseologyは4。この不整合を未解決として扱えていない。

## rater_7 / 4902:1 / 4902_1__K1

出力: `stage1/4902_1__K1/parsed.json`。入力: `stage1/4902_1__K1/input.json`。対象Overall=3。履歴ID: 8630:1, 1462:1, 8722:1。

**根拠となる生成原文**

- pattern: "The rater tends to score essays lower when there are significant issues with cohesion, syntax, and grammar, even if vocabulary and phraseology are adequate."
- target feature: "The essay has clear ideas but struggles with cohesion and syntax, with repetitive and unclear ideas."
- decision: "The target essay demonstrates clear ideas and adequate vocabulary, but it struggles with cohesion and syntax, leading to a lower score. This aligns with the historical pattern observed in the rater's scoring, where essays with significant issues in cohesion and syntax receive lower scores despite having adequate vocabulary and phraseology."
- score-free rubric connection: "The rubric for a score of 3 indicates limited facility in sentence formation, word choice, and mechanics, with communication impeded in some cases."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|partially_met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_met|`target_evidence/0`。rubric_connectionに“communication impeded in some cases”とあるが、どこで何が読めなくなるかの分析がなく、引用への結び付けが不足。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 2/4件が完全一致。
得点分離点検: target_evidence/T1のrubric_connectionが対象に数値3の帯を適用・整合させる。履歴得点でも答案内の数字でもなく、対象のscore-free部分への番号付き帯の持込みと判断。

個別の重要点: 履歴8630:1はOverall=3、Syntax=2、Phraseology=1、1462:1はOverall=3、Syntax=3、Phraseology=3、8722:1はOverall=5。これらの併存だけで本人がCohesion/Syntaxを他観点より優先したとは確定しない。数値重みはないが、優先度の推定を過度に一般化している。

## rater_7 / 4902:1 / 4902_1__K2

出力: `stage1/4902_1__K2/parsed.json`。入力: `stage1/4902_1__K2/input.json`。対象Overall=3。履歴ID: 8630:1, 1462:1, 8722:1。

**根拠となる生成原文**

- pattern: "The rater appears to evaluate essays with limited cohesion and syntax negatively, often assigning lower scores when the text lacks clear organization and has frequent errors in sentence structure."
- target feature: "The essay demonstrates limited cohesion and syntax, with frequent errors in sentence structure and vocabulary usage."
- decision: "The target essay demonstrates limited cohesion and syntax, with frequent errors in sentence structure and vocabulary usage. This aligns with the rater's historical pattern of evaluating essays with similar issues negatively. The rater appears to consider the lack of clear organization and frequent errors in sentence structure as significant factors in assigning lower scores."
- score-free rubric connection: "The rubric for scores 2 and 3 indicates that communication is impeded by language inaccuracies and that there are many sentence structure problems."

|項目|暫定判定|出力箇所（score_free_analysis以下）と入力根拠・限界|
|---|---|---|
|B1.1 特徴と評価の仕方|partially_met|`history_patterns/0/pattern`。評価語はあるが、一般的な特徴・基準の反復が中心で、本人の判断がどう異なるかの説明は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.2 履歴本文と得点の支持|partially_met|`history_patterns/0/support`。履歴2例と本人得点を挙げるが、引用箇所から全体の構成・語彙範囲・減点や優先度まで導く根拠が弱い。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.3 対象だけから恒常傾向を作らない|met|`history_patterns/0/support`。異なる履歴答案2件が明示され、対象だけを根拠にはしていない。ただしこれだけで恒常的傾向は確立しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B1.4 反例と不足の扱い|partially_met|`history_patterns/0/counterevidence`。第三の履歴とlimitationsはあるが、何を反証するか・説明をどこまで弱めるかが具体的でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.1 引用の原文一致|partially_met|`target_evidence/0/quotes`。完全一致は機械検証の結果を併記。空白・改行の差も不一致と数え、生成原文を修復しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.2 引用の意味的支持|partially_met|`target_evidence/0`。対象引用はあるが、一つの証拠T1に広い観点をまとめ、引用からの推論と全体評価を十分に区別しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.3 文法・意味分析の妥当性|partially_met|`target_evidence/0/observable_feature`。awkwardnessや文形成上の問題を示唆する本文はあるが、特定の構造・読み・分布を精査せず全体の頻度や程度へ広げる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B2.4 誤りと理解への影響の区別|not_assessable|`target_evidence/0`。具体的にどの解釈が成立せず意味が不明になるかを分析していない。誤り存在だけで意味妨害を認定できない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.1 履歴・本文・評価判断の接続|partially_met|`decision_explanation`。履歴と対象を接続する文はあるが、特徴の同名反復が中心で、観測Overallを説明する判断関係は限定的。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.2 長短所列挙を超える説明|partially_met|`decision_explanation`。balance、penalize、prioritizeなどを用いるが、何をどの証拠から許容・重視したと読めるかの裏付けが十分でない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.3 欠点・重み・計算の捏造回避|partially_met|`decision_explanation`。数式・数値重みの捏造は見当たらないが、減点・優先度・低得点への因果説明は履歴だけでは確定しない。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|
|B3.4 説明できない点の明示|partially_met|`insufficient_evidence`。不確実性欄は存在するが、どの説明が支持不足なのかより、品質混在や標本不足の一般論にとどまる。 入力は同候補の`history`・`target`・`rubric`。完全な出力・入力側根拠は`content_review.json`の当該項目。|

機械的引用検査: 2/4件が完全一致。
得点分離点検: “The rubric for scores 2 and 3 ...”は対象の観測値を一意に復元する開示とは確認できない。複数bandの数値を含むことは別途指示遵守上の懸念として残す。

個別の重要点: 履歴8630:1はOverall=3、Syntax=2、Phraseology=1、1462:1はOverall=3、Syntax=3、Phraseology=3、8722:1はOverall=5。これらの併存だけで本人がCohesion/Syntaxを他観点より優先したとは確定しない。数値重みはないが、優先度の推定を過度に一般化している。

## 統合フィードバック（C1〜C8）

採用0件によりStage 3を仕様どおり省略した。複数答案の傾向、代表例、ルーブリック比較、具体的な採点チェック、採点者向けか、一致/ずれ/不明の区別、一般化、元理由との整合の8項目はすべて`not_assessable`。`stage3/skip.json`が根拠。統合プロンプトの内容品質は未検証であり、改善・劣化を判定しない。
