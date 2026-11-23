# Stage 3 v1.6：固定2答案・最低ライン1回検証

**判定：未達。比較ベースラインとして確定しない。**

| 基準 | 判定 | 根拠 |
|---|---|---|
| A | 未達 | 1868の唯一の所見は選択外S005の文を引用し、選択S004との局所接続を正しく説明していない。4902はO1が有効だがO2は主語・動詞一致の誤診を含む。完全な局所所見がある答案は1/2で未達。 |
| B | 未達 | 引用・答案ID・本人Cohesion=3・公式Cohesion:3の文字列と参照は一致する。しかし代表1868のS004は段落末ではなく、最終所見のat the end of the paragraphを意味的に支持しない。文字列一致=true、意味的支持=falseのためB未達。 |
| C | 合格 | 傾向はinsufficient_evidence、得点帯はindeterminateとして適切に保留。別帯なし。段落間の移行で継続学習という話題の接続・議論の展開を確認する1件の行動を示す。位置に関する誤りはBの意味的支持の未達として別記し、保留自体は合格とした。 |

Bの文字列・参照一致：True。意味の裏づけ：False。両方を必要条件として判定した。Aは生成所見全体を単位とし、一部だけ正しい所見は数えない。

内容判定はCodexによる暫定評価で、人手による確定評価でも追加モデル判定でもない。機械検査とは独立して `content_review.json` に記録。固定2答案の回帰確認であり、一般性能・複数seed安定性・文章の洗練・前回と同じ引用の再現・積極的な傾向提示は追加条件にしない。

## 比較元と変更範囲

比較元はコミット `bc5d15e3a8a840fb58bc86fa1e9b112c23f6d6ac` の `outputs/recsaver_stage3_v1_5_baseline_20261122/`。
README、manifest、decision、report、保存済み実入力・原文区間表を確認した。
指定英文だけを正本2本の指定箇所に挿入。schema_versionは「1.5」、プレースホルダーは各1個を維持。
新しい英文に過去の誤答・判定基準・答案固有の正解例を追加していない。

| 実際に使用した正本 | SHA-256 |
|---|---|
| C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/recsaver_03a_case_evidence_review_v1_6.txt | `c4012bcf6f22b084dda239bc9b8988407d9ea55a763607800aa84e00704826e2` |
| C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/recsaver_03b_integrated_feedback_v1_6.txt | `ceea422f7c58ab6e6f73f94b49fcdff06421f575b262325793f98f12c2f9c82b` |

3Aの実入力2件は前回とバイト同一。fixed_inputと区間表もバイト同一。採用候補・Stage 1/2結果は保存データを再利用し、再実行しなかった。3Aは本文・区間表・観点名だけを受け取る。3Bは今回の3A所見を既存の機械ゲートで原文照合後に受け取り、本人の観測点・公式基準を付加する。候補監査自由文と新しい位置メタデータは3Bに渡していない。

raw CSVのRater_1が両答案でrater_7であること、本文、Overallおよび全6 Traitを照合。1868:1はOverall=3、Cohesion=3、Syntax=3、Vocabulary=4、Phraseology=4、Grammar=3、Conventions=3。4902:1はOverall=3、Cohesion=2、他Trait=3。出典行と列は `source_checks.json` に記録。

既存ランナーのprepare以外の全関数・表示処理はASTで同一。prepareは参照元コミット、正本名、出力先と差分記録のみを更新。検証コードは比較元3Bの保存パスとチェックアウト改行の扱いを更新した。モデルに渡す内容には影響しない。

比較コミットに管理された保存物は内容一致。ローカルの4ファイル（outputs/recsaver_stage3_v1_5_baseline_20261122/observation_results.csv, outputs/recsaver_stage3_v1_5_baseline_20261122/stage3a/1868_1/rendered_chat.txt, outputs/recsaver_stage3_v1_5_baseline_20261122/stage3a/4902_1/rendered_chat.txt, outputs/recsaver_stage3_v1_5_baseline_20261122/stage3b/rater_7/rendered_chat.txt）はWindowsチェックアウトのCRLF/LF差だけがあり、両ハッシュと改行差を記録した。再利用する実入力・区間表にその差はない。比較元の全ローカル保存物は実行前後ハッシュ不変。

## 実行条件と機械検査

Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。モデル設定・system指示・チャットテンプレート・生成設定を前回manifestと照合。実runtimeと各要求のsampling・テンプレートも保存物で照合した。

| 要求 | 入力tokens | 出力tokens | 終了 | 厳密JSON | 構造 | transport attempt |
|---|---|---|---|---|---|---|
| stage3a/1868_1 | 11534 | 261 | stop | True | True | 0 |
| stage3a/4902_1 | 4365 | 386 | stop | True | True | 0 |
| stage3b/rater_7 | 2331 | 289 | stop | True | True | 0 |

3A各答案1回、通し3B1回の計3要求。追加生成・再生成による選別・追加モデル判定・生出力/解析JSONの手修正なし。統合の自己検証とSLM改稿は未実装・未実行。GPUの実行順序によるトークン単位の再現性は評価しない。

| 機械検査 | 結果 |
|---|---|
| 生成前の既存表示・参照検査 | 11/11 |
| コミット・正本・入力・本人得点・コード同一性 | 106/106 |
| 実入力・引用・公式基準・表示・設定・生出力ハッシュ | 50/50 |

機械検査は引用文字列・ID・参照の正確さを示す。意味の裏づけと採点判断の適切さは以下の暫定内容判定で別に確認した。

## A：1868:1

O1のみ生成され、その全体が選択原文に収まらないためAの有効所見に数えない。S001の冒頭位置と継続学習の主張は確認できるが、それだけを切り出して救済しない。

### O1 / Cohesion / 完全な局所所見：未達

**feature（生成英文）**

> The essay starts with a clear thesis statement: 'The main piece to improve your skills is during the process of keep learning.' This statement is reiterated at the end of the paragraph with 'The actual key that makes people become professionals everyday and give them the recognition of master is through the process of keep learning new things.'

和訳：答案は『技能を向上させる主な要素は、学び続ける過程にある』という明確な主張で始まる。この主張は段落末の『人々が日々専門家となり達人と認められる実際の鍵は、新しいことを学び続ける過程にある』という文で繰り返されている。

**scoring_relevance（生成英文）**

> This feature demonstrates the writer's ability to maintain a clear focus and reiterate the main idea, which is a key aspect of cohesion.

和訳：この特徴は、書き手が明確な焦点を保ち、中心的な考えを繰り返す能力を示しており、結束性の重要な側面である。

**limitation（生成英文）**

> This observation does not establish the overall coherence of the essay, only the cohesion within the first paragraph.

和訳：この所見は答案全体の一貫性を示すものではなく、第1段落内の結束性のみを示す。

**next_check（生成英文）**

> Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning.

和訳：段落間の移行を見直し、継続学習の重要性という同じ焦点を保っているか確認する。

**選択原文との照合**

evidence_span_idsはS001とS004。しかしfeatureの第2引用『The actual key ... keep learning new things.』は選択外のS005の全文。S005は第1段落の末文だが、それが段落末であるという事実を、選択S004の根拠として数えられない。S004自体は[368,610)、段落は[0,765)であり、後続S005がある。scoring_relevanceの明確なfocusを維持する能力という説明も、実際に選んだ2文の何がどう接続するかに限定されていない。limitationの『第1段落内の結束性』という留保でも選択と引用の不一致は解消しない。

| 区間ID | 段落 | Unicode位置 [start,end) | 原文 |

|---|---|---|---|

| E1868_1_P001_S001 | E1868_1_P001 | [0, 77) | The main piece to improve your skills is during the process of keep learning. |

| E1868_1_P001_S004 | E1868_1_P001 | [368, 610) | I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career. |

## A：4902:1

O1は引用の紹介・賛同と、その理由を結ぶ局所的なCohesion所見として有効。O2は一部に実際の代名詞の問題があるが、主語・動詞一致の誤診を含むため所見全体は数えない。少なくとも1件というAの答案単位条件は満たす。

### O1 / Cohesion / 完全な局所所見：合格

**feature（生成英文）**

> The essay begins with a direct reference to Ralph Waldo Emerson's quote and explicitly states the reason for agreeing with it.

和訳：答案はラルフ・ウォルドー・エマーソンの引用への直接の言及で始まり、それに賛成する理由を明示している。

**scoring_relevance（生成英文）**

> This feature demonstrates a clear connection between the quote and the writer's stance, which is relevant to the cohesion dimension as it shows a logical progression from the introduction of the quote to the writer's agreement.

和訳：この特徴は引用と書き手の立場の明確な結び付きを示している。引用の導入から書き手の賛同へ論理的に進んでいるため、結束性の観点に関係する。

**limitation（生成英文）**

> This observation does not establish the overall coherence of the essay, only the initial connection between the quote and the writer's stance.

和訳：この所見は答案全体の一貫性を示すものではなく、引用と書き手の立場との最初の結び付きのみを示す。

**next_check（生成英文）**

> Review the subsequent paragraphs to see if the writer maintains this connection and develops the argument consistently.

和訳：後続段落を読み、書き手がこの結び付きを保ち、一貫して議論を展開しているか確認する。

**選択原文との照合**

S001[0,149)は冒頭でEmersonの引用とI agreeを提示する。S002[150,243)はThe reason why i agree ... is becauseと明示して理由を述べる。両文が選ばれており、引用導入から賛同理由へ進む接続をCohesionに関連付ける主張は局所原文で支持される。3Aは全文と位置を受け取っているのでbeginsも確認可能。全体の一貫性や得点を断定していない。

| 区間ID | 段落 | Unicode位置 [start,end) | 原文 |

|---|---|---|---|

| E4902_1_P001_S001 | E4902_1_P001 | [0, 149) | I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment." |

| E4902_1_P001_S002 | E4902_1_P001 | [150, 243) | The reason why i agree with this quote is because people now a day don't try to be them self. |

### O2 / Grammar / 完全な局所所見：未達

**feature（生成英文）**

> The sentence contains a nonstandard verb form: 'don't try to be them self.'

和訳：文には『don't try to be them self』という非標準の動詞形が含まれている。

**scoring_relevance（生成英文）**

> This feature is relevant to the grammar dimension as it indicates a grammatical error in subject-verb agreement and pronoun usage.

和訳：この特徴は主語と動詞の一致および代名詞使用の文法的誤りを示すので、文法の観点に関係する。

**limitation（生成英文）**

> This observation does not provide information about the frequency of such errors throughout the essay.

和訳：この所見だけでは、そのような誤りが答案全体でどの程度あるかは分からない。

**next_check（生成英文）**

> Check other sentences for similar grammatical errors to assess the overall grammatical accuracy of the essay.

和訳：ほかの文にも同様の文法的誤りがないか確認し、答案全体の文法的正確さを評価する。

**選択原文との照合**

them selfという再帰代名詞の表記・形の問題は実在する。しかし原文のpeople ... don't tryは複数主語peopleに対するdon'tで、主語・動詞一致の誤りではない。featureの『非標準の動詞形』という呼称とscoring_relevanceの『主語・動詞一致と代名詞の誤り』という複合主張は全体として支持されない。代名詞の問題だけを残して人が修正した所見としては数えない。

| 区間ID | 段落 | Unicode位置 [start,end) | 原文 |

|---|---|---|---|

| E4902_1_P001_S002 | E4902_1_P001 | [150, 243) | The reason why i agree with this quote is because people now a day don't try to be them self. |

## B：最終フィードバックの照合

代表：`1868:1::O1`、quote_indices=[0, 1]。
観測基準参照：`Cohesion:3`。
比較帯：`None`。

文字列・参照一致：既存表示コードが1868:1::O1のquote_indices=[0,1]を参照し、原文スライスS001[0,77)とS004[368,610)を一字も変えず表示した。答案IDは1868:1、本人の観測Cohesionは3、公式Cohesion:3のdescriptorもfixed_inputおよびraw本人得点に一致する。

意味の裏づけ：S001は学び続けることを技能向上と結ぶ。S004は学び続ける専門家と成功を結ぶ。この2文に関連する学習の話題はあるが、S004の後に同段落のS005[611,765)があり、S004を段落末とする最終所見は誤り。3Bに新しい位置情報は渡しておらず、出典が確かであることから段落末という機能・位置を推定してしまった。textual_findingのすべての事実部分が引用に裏づけられるという条件を満たさない。

**textual_finding（生成英文）**

> The essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph, showing a clear focus on the importance of continuous learning.

和訳：答案は明確な主張で始まり、段落末で中心的な考えを繰り返して、継続学習の重要性に明確な焦点を当てている。

**evidence_limit（生成英文）**

> This observation does not establish the overall coherence of the essay, only the cohesion within the first paragraph.

和訳：この所見は答案全体の一貫性を示すものではなく、第1段落内の結束性のみを示す。

### 既存コードが組み立てた最終フィードバック全文

> A scoring pattern cannot be established from these cases. The provided observations do not establish a consistent pattern of scoring behavior across multiple essays. Each observation highlights a specific feature of the essay but does not show a repeated scoring behavior that can be generalized. In essay 1868:1, the relevant excerpt is “The main piece to improve your skills is during the process of keep learning.” In essay 1868:1, the relevant excerpt is “I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career.” The essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph, showing a clear focus on the importance of continuous learning. The recorded Cohesion score is 3. The official descriptor for Cohesion:3 is “Organization generally controlled; cohesive devices used but limited in type; Some repetitive, mechanical, or faulty use of cohesion use within and/or between sentences and paragraphs.” This evidence alone does not establish whether that band is appropriate. This observation does not establish the overall coherence of the essay, only the cohesion within the first paragraph. Next inspect: Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning. Check: Check if the writer maintains the connection and develops the argument consistently throughout the essay.

和訳（生成文を修正しない）：

これらの事例から採点傾向を確立することはできない。提示された所見からは、複数答案にまたがる一貫した採点行動の傾向は確立できない。各所見は答案の特定の特徴を示すが、一般化できる反復的な採点行動を示していない。答案1868:1の該当抜粋は『技能を向上させる主な要素は、学び続ける過程にある』。答案1868:1のもう一つの該当抜粋は『私は作家ラルフ・ウォルドー・エマーソンの言葉に強く賛成する。専門家の称号を得て日々成功し続けている人々は、自分の生活や仕事に有益な情報を加え続けている人々である』。答案は明確な主張で始まり、段落末で中心的な考えを繰り返して、継続学習の重要性に明確な焦点を当てている。記録されたCohesion得点は3。Cohesion:3の公式記述は『構成は全般に統制されている。結束表現は使われるが種類は限られる。文や段落の内部または間で、反復的、機械的、または不適切な結束表現の使用がいくらかある』。この証拠だけでは、その帯が妥当かは判断できない。この所見は答案全体の一貫性を示すものではなく、第1段落内の結束性のみを示す。次に確認すること：段落間の移行を見直し、継続学習の重要性という同じ焦点を保っているか確認する。確認すること：書き手が答案全体を通じて結び付きを保ち、一貫して議論を展開しているか確認する。

## C：判断範囲と次の確認

**pattern_limit（生成英文）**

> The provided observations do not establish a consistent pattern of scoring behavior across multiple essays. Each observation highlights a specific feature of the essay but does not show a repeated scoring behavior that can be generalized.

和訳：提示された所見からは、複数答案にまたがる一貫した採点行動の傾向は確立できない。各所見は答案の特定の特徴を示すが、一般化できる反復的な採点行動を示していない。

**next_check.inspect（生成英文）**

> Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning.

和訳：段落間の移行を見直し、継続学習の重要性という同じ焦点を保っているか確認する。

**next_check.distinguish（生成英文）**

> Check if the writer maintains the connection and develops the argument consistently throughout the essay.

和訳：書き手が答案全体を通じて結び付きを保ち、一貫して議論を展開しているか確認する。

判定根拠：pattern_status=insufficient_evidence、pattern=nullは妥当。同一Overallや共通のCohesion観点だけでは、特徴が採点でどう扱われるかの傾向を確立できない。band_assessment=indeterminateは局所2文から答案全体のCohesion得点を判定できないという範囲に収まり、固定表示文とも矛盾しない。next_checkは段落間の移行という場所と、継続学習の話題の接続・議論の展開という観察対象を示す。特定段落の指定がさらに可能か、文章が洗練されているかは追加条件にしない。段落末との事実誤認は最終所見の意味的支持を損なうためBで未達とし、Cの傾向・得点帯の保留そのものと区別する。

隣接帯の方向・区別条件：comparison_band_ref_id=null、reconsider_if=null、コード上の方向=none。別帯を提示していないため、方向と区別条件の内容評価は対象外（分母0）。別帯への言及や得点の積極的な支持はない。

## 前回の問題と終了

1868の位置誤認：解消せず。v1.5のessay concludesという答案全体の結論ラベルは今回は消えたが、選択S004を段落末とする別の位置誤認が残った。3Aは本来S005にある文をfeatureに引用してS004を選択し、3Bは実際に渡されたS004のquotesを選びながらat the end of the paragraphを引き継いだ。S004は第1段落[0,765)内の[368,610)で、後続S005[611,765)がある。答案全長は5509文字。『前回と同じ結論語が消えた』だけで回帰解消としない。

3Aのfeatureが実際に引用した選択外S005の原文（文脈照合用。合格所見の根拠に追加しない）：

> The actual key that makes people become professionals everyday and give them the recognition of master is through the process of keep learning new things.

和訳：人々が日々専門家となり、達人と認められる実際の鍵は、新しいことを学び続ける過程にある。

S005=[611,765)、第1段落=[0,765)。この文が実際に段落末であることと、選択されたS004が段落末であることは別である。全段落・前後の正確な原文位置はposition_regression_1868.jsonに保存した。

4902の有効所見：O1に引用・賛同・理由の明示的な局所接続が残った。O2の文法誤診は数えず、それでも有効所見は1件ある。前回と同じ引用を選ぶこと自体は合格条件にしていない。

残った障害：['1868:1::O1のfeature内引用が選択S004でなく選択外S005に属するため、3A所見全体が選択根拠に収まらない。', '3Bが出典一致だけでは保証されない段落末位置を主張し、選択引用が最終所見を意味的に支持しない。']

未達でも今回の実行で停止する。追加生成・調整を行わない。

生出力・実入力・解析JSONはstage3aとstage3b、復元引用・Unicode出典位置はrestored_quotes.json、本人得点出典はsource_checks.json、判定はbaseline_decision.json、使用正本名・SHA-256・比較コミット・生成要求数はrun_manifest.jsonに保存した。
