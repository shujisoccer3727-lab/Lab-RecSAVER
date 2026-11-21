# Stage 3 英文プロンプトv1.1 検証（2026-11-21）

## 結論

v1.1を保存済みと完全に同じ入力で1回実行した。厳密JSON・v1.1構造は通過したが、履歴答案8722:1を採用対象の反例とする違反が残り、統合結果は検査不合格。引用の実在性と意味的な支持は別であり、内容面でも採点者フィードバックとして妥当とは判断しない。Vocabulary 4への参照帯は正しくなったが、引用から支えられない答案全体の説明は残った。

この比較は既知の失敗を、同じ2答案で再検証したもの。採点傾向の一般的な抽出能力向上を示さない。内容判定はCodexの暫定判断であり、人手評価ではない。

## 固定条件と実装

比較コミット: `d5eee9a20dfd066496ffb84f60271a830e501ba0`（実行前HEADと一致）。比較元: `outputs/recsaver_prompt_v1_2_value_mask_20261121/`。正本は `C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/recsaver_03_integrated_feedback_v1_1.txt`。SHA-256: `84966a3204f67fe8096072a32441504b742d14775be01f085cc12a6e2aa47715`。リポジトリ内の同名ファイルはこの1件のみ。正本本文は変更せず、`{{INPUT_JSON}}`だけを置換した。

Stage 1・2は生成していない。採用レコードは1868_1__K1、1868_1__K2、4902_1__K1、4902_1__K2の順。独立した対象は1868:1と4902:1の2件で、同一答案の候補2件を別の支持答案には数えない。対象・履歴を含むsource_essays 8件、本文、観測得点、ルーブリック、全配列の順序を固定した。input.jsonのバイト単位SHA-256も旧版と一致: `dca75b64bfdcd05c49ecbc50560529337073e32846ffaff682d378a80ca27b0e`。

モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、既存ローカルsnapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。既存Engineを再利用し、同じchat template・既定systemを維持（追加指示なし）。変更はStage 3正本文とスキーマ検査・監査コード。guided decoding、形式修復、再生成なし。GPU実行順序による完全なトークン再現性は保証しない。

新リクエスト1回、出力1374トークン、finish_reason=stop、切り詰めなし。入力トークンは旧13599→新13782（プロンプト変更による）。原出力・parsed・resultを保存し、失敗を修正して通過させていない。旧版もschema_version=1.0のまま既存構造検査を適用し、新版は1.1の追加フィールド・型を識別して検査した。JSON形式通過と根拠照合の合格は分ける。

## 機械検査

| 検査 | v1.0 | v1.1 |
|---|---|---|
| 厳密JSON | 1/1 | 1/1 |
| 各版スキーマ | 1/1 | 1/1 |
| コード枠 | 0/1 | 0/1 |
| 採用レコード数・異なる対象数 | 4・2、入力一致 | 4・2、入力一致 |
| target_essay_ids集合 | 1868:1・4902:1、一致 | 同左 |
| 支持する異なる採用答案 | 2/2 | 2/2 |
| 機械的な根拠照合の全通過 | 0/1 | 0/1 |
| 生成されたpatterns | 1 | 1 |
| 内容点検で支持十分と判断したpatterns | 0/1 | 0/1 |
| 最終段落の本文引用＋出典ID | 0/1 | 0/1 |

根拠照合の内訳（検査対象フィールド数に基づく。異なる版でフィールド数が違うため、総通過率だけで性能比較しない）:

| 検査種別 | v1.0 通過/対象 | v1.1 通過/対象 |
|---|---|---|
| accepted_target_role | 3/4 | 5/6 |
| candidate_target_mapping | 4/4 | 4/4 |
| count | 2/2 | 2/2 |
| first_ref_consistency | 評価不能（該当フィールドなし） | 1/1 |
| legacy_claimed_band_matches_quote | 0/1 | 評価不能（該当フィールドなし） |
| legacy_quote_located | 1/1 | 評価不能（該当フィールドなし） |
| observed_band_cited | 評価不能（該当フィールドなし） | 1/1 |
| observed_score | 21/21 | 12/12 |
| representative_identity | 評価不能（該当フィールドなし） | 1/1 |
| rubric_band_role | 評価不能（該当フィールドなし） | 1/1 |
| rubric_dimension | 評価不能（該当フィールドなし） | 1/1 |
| rubric_dimension_band_quote | 評価不能（該当フィールドなし） | 1/1 |
| source_quote_exact | 3/3 | 5/5 |
| target_set | 1/1 | 1/1 |

旧版35/37、新版35/36の個別チェックが通過。旧版の失敗は①反例target_essay_id=8722:1が採用対象集合にない、②Overall 3を説明するrubric_quoteの実際の出典はOverall 4。出典は1箇所で曖昧ではなかった。新版の失敗は①の継続。comparison_bandは0件で、比較帯を正しく使えるかは評価不能。新しいobserved_bandはVocabulary・4・代表1868:1の観測4に一致し、rubric_quoteは最初のref.quoteと完全一致した。

本文引用は旧3/3・新5/5が指定答案原文の完全一致。候補IDと対象IDは両版4/4一致。観測値も出力された項目はすべて一致。ただし、これらは引用が主張を支えることや、出力にない観点の検証を意味しない。新版の誤った履歴参照は除去せず原出力に保存した。最終段落の引用有無は構造化引用との一致検査に加え、原文をCodexが読んで確認した。

前回保存検査は旧版31/32通過で、ルーブリック引用の存在のみを通していた。今回は観点・帯まで照合し、旧版の帯取り違えを新たに失敗として記録した。チェック数・基準が違うため、前回の31/32と今回の35/37を直接比較しない。

## 旧版の最終フィードバック

### 英語原文

> In these supplied cases, you appear to assign an Overall score of 3 to essays that demonstrate a mix of minor errors in cohesion, syntax, vocabulary, phraseology, grammar, and conventions. For example, in essay 4902:1, the mix of minor errors is consistent with an Overall score of 3. The rubric requires occasional language inaccuracies that rarely impede communication, which aligns with your treatment of these errors. For future scoring, inspect the mix of minor errors and distinguish their severity and impact on communication to ensure consistency with the rubric.

### 和訳（原文の誤りを修正しない）

今回提示された事例では、あなたは結束性、統語、語彙、句、文法、表記に軽微な誤りが混在する答案にOverall 3点を付けているように見えます。例えば答案4902:1では、軽微な誤りの混在はOverall 3点と整合します。ルーブリックが要求するのは、意思伝達をめったに妨げない程度の時折の言語の不正確さであり、それはあなたのこうした誤りの扱いと一致します。今後の採点では、ルーブリックとの一貫性を確保するため、軽微な誤りの混在を調べ、その深刻さと意思伝達への影響を区別してください。

### 根拠との照合

代表引用は4902:1の冒頭 “I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment."”。引用は実在し、大文字・所有関係や引用導入の局所的な問題は検討できる。ただし、この1文から6観点すべての誤り、答案全体での頻度や意思伝達への影響を断定できない。最終段落にはこの引用自体がない。観測Cohesion=2を他の5観点=3と区別せず、一律に「軽微」と扱った。

引用したrubric_quoteはOverall 4の “occasional language inaccuracies that rarely impede communication.”（意思伝達をめったに妨げない、時折の言語の不正確さ）。Overall 3の正本は “Communication is impeded by language inaccuracies in some cases.”（場合によっては言語の不正確さにより意思伝達が妨げられる）。同じ基準ではない。引用の出典4と説明の3が不一致。

## 新版の最終フィードバック

### 英語原文

> Based on the evidence from two target essays, both with an Overall score of 3, it appears that essays with generally controlled organization and a sufficient range of vocabulary receive a score of 3. The representative decision is supported by the essay '1868:1', which demonstrates a sufficient range of vocabulary and generally controlled organization. The rubric comparison for Vocabulary is consistent with the observed score of 4. For future scoring, inspect the range of vocabulary used in the essay to distinguish between sufficient and wide range of vocabulary, which would support retaining or reconsidering the judgment.

### 和訳（原文の誤りを修正しない）

どちらもOverall 3点だった二つの対象答案の証拠に基づくと、全般に統制された構成と十分な語彙の幅を持つ答案には3点が付けられているように見えます。代表的な判断は答案「1868:1」によって支えられており、この答案は十分な語彙の幅と全般に統制された構成を示しています。Vocabularyのルーブリックとの比較は、観測された4点と整合しています。今後の採点では、答案で使われている語彙の幅を調べ、十分な幅と広い幅を区別してください。これが判断の維持または再考を支えるでしょう。

### 根拠との照合

代表1868:1の引用は “The main piece to improve your skills is during the process of keep learning.”（技能を向上させる主な要素は、学び続ける過程にあります）。この英文は原文に完全一致する。しかし “of keep learning” の形や “main piece” の語法の局所所見は可能でも、答案全体の構成や語彙の幅は、この1文だけでは裏づけられない。新版はその局所所見を残す代わりに、全体的な語彙4点の妥当性へ拡張した。

新しいrubric_refsはVocabulary 4の “Sufficient range of vocabulary to allow flexibility and precision; appropriate use of topic-related terms and less common lexical items”（柔軟性と精確さを可能にする十分な語彙の幅、話題に関係する語やより一般的でない語彙項目の適切な使用）。実際の該当帯に完全一致し、1868:1の観測Vocabulary=4とも一致する。これは参照先の改善であり、引用1文がこの基準の全要素を満たすと証明したわけではない。relationship=consistent_with_rubricと、uncertaintyの “aligns well” は、証拠不足を保留できていない。

4902:1の個別所見は “The essay demonstrates some repetitive and mechanical use of cohesive devices.”（この答案は結束表現の反復的で機械的な使用をいくらか示しています）と述べるが、根拠は同じ冒頭1文のみ。反復を示す複数箇所や、結束表現の具体的な比較がなく、Cohesion 2という観測値の正しさだけではこの説明を支持しない。支持例のevaluative_connectionには旧版同様6観点のminor errorsが残った。

新版も最終段落に本文引用がなく、構成・語彙の幅と「3点を受ける」という根拠不十分な関係を繰り返す。構造化出力より新たに強い命題を加えたわけではないが、構造化出力自体が証拠より強い。

## 四項目の比較と継続するID問題

| 内容評価項目 | 判定 | 根拠・限界 |
|---|---|---|
| 独立答案に基づく評価の仕方 | 同程度 | 両版とも支持不十分なpatternsを1件生成。新版も2答案の同じOverallから構成・語彙と3点の関係を主張し、観測Cohesion 3/2、Vocabulary 4/3の差を扱っていない。patterns=[]による保留は起きなかった。 |
| 引用と主張の範囲 | 同程度 | 全引用は実在するが、どちらも1文から複数観点・答案全体の性質を主張。新版の個別所見も語彙の幅や結束表現の反復を引用で支持できない。最終段落は両版とも本文引用なし。 |
| ルーブリック・観測値の正確さ | 改善 | 限定的改善。旧版Overall 4の記述をOverall 3に帰属した誤りは、新版のVocabulary 4の正しい明示参照では回避。ただしOverall帯の対照自体がなくなりrarely/in some casesの区別能力は評価不能。1868/K2の全Trait=3という矛盾はsource_analysis_issues=[]で未指摘。 |
| 次の採点確認と最終段落の強さ | 同程度 | 新版はsufficient/wideの区別を挙げるが、確認する具体的な箇所・広さ以外の語彙基準・判断維持条件が不足。最終段落も根拠不十分なpatternを繰り返す。 |

独立答案の支持は、同じ点数という事実と採点者が特徴をどう重視したかを区別する必要がある。新版のpatternは “Essays with generally controlled organization and a sufficient range of vocabulary receive a score of 3.”（全般に統制された構成と十分な語彙の幅を持つ答案は3点を受ける）。一方、4902:1の個別所見は「全般に統制された構成は証明されない」とし、観測Cohesionも2である。支持例を単に2件並べるだけでは同じ関係の支持にならない。今回はpatterns=[]を返していないため、適切な判断保留とその際の個別所見の保存という動作は未達。

1868/K2の元理由 “consistent with the observed scores of 3 for both Overall and Traits”（OverallとTraitsの両方の観測3点と整合する）は、Vocabulary=4・Phraseology=4と矛盾する。新版はstructured Vocabulary=4を正しく使い、全Trait=3の文を直接は再掲しないが、source_analysis_issues=[]のため元説明の矛盾を明示しなかった。Phraseology=4との照合を説明に残していない。

両版の反例は同じ “target_essay_id”: “8722:1”。これは4902:1に付随する履歴答案（Overall 5）であり採用対象ではない。原文 “This essay demonstrates a higher level of syntactic variety and fewer errors, which contrasts with the pattern of essays receiving an Overall score of 3.”（この答案は、より高い統語的多様性とより少ない誤りを示し、Overall 3点を受ける答案の傾向とは対照的です）を両版とも出力した。比較可能な文脈として履歴と明示することと、target_essay_idを持つ対象反例として扱うことは区別すべきで、今回は同程度の失敗である。

## 保存物・検証範囲・次の修正

このディレクトリにrun_manifest.json、stage3/rater_7のinput/messages/sampling/rendered_chat/raw/parsed/result/generation/integrity、両版のchecks、mechanical_summary.csv、content_review.json、invariant_checks.json、supplementary_checks.json、audit_tests.json、追加コードを保存した。旧版の生出力は比較元を参照し、変更していない。入力・sampling・chat template・モデルsnapshot一致、原出力ハッシュ、正本と比較元の不変性を確認済み。再点検手順はREADME.md。

構造・根拠検査は失敗を保存する実装であり、意味評価を自動検査が代替するものではない。両版は各1応答、2答案のみであり、生成のばらつき、他の点数・採点者、comparison_bandやpatterns=[]分岐の性能は評価不能。一般的な採点傾向抽出の成功率や因果的な向上は主張しない。

次に直すべき点は3つ。

1. 採用対象集合にないtarget_essay_idを生成後にも確実に拒否する。履歴への言及は役割を別に表し、対象反例に流用しない。
2. 原文の複数箇所で支持できない構成・語彙幅・反復・意味影響の主張を保留し、局所所見と追加比較を残す。元候補と観測Traitの矛盾を明記する。
3. 最終段落に検証済み短引用とIDを必須化し、具体的な確認箇所、基準の複数要素、判断維持・再考それぞれの根拠を示す。引用・帯検査の通過だけで内容合格にしない。
