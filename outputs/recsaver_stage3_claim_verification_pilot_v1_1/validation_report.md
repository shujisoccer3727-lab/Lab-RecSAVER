# Stage 3C v1.1：人手相当の主張分割を使う1回の回帰診断

**最低ライン：合格。この1回で終了し、プロンプトの再調整・再生成を行わない。**

| 最低ライン | 判定 | 原文・処理との照合 |
|---|---|---|
| 予定LLM判定の欠落なし | 合格 | 20/20命題、正常表示4/4要求。 |
| 1868の位置誤認除去と冒頭所見保持 | 合格 | K05除去=True、K01/K02保持=True。 |
| 8699または2016の誤診修正 | 合格 | 8699の一般所見保持＋一致/冠詞診断除外=False、2016の誤診と依存確認点除外=True。 |
| 4902の有効所見保持 | 合格 | R01保持=True。既存3群の効果集計から除外。 |
| 新しい未支持主張を追加しない | 合格 | 固定候補・語義の局所化・前提依存・原文引用・本人得点・公式記述を照合。新規の未支持前提=[]。A由来の残存誤りとは区別。 |

| 群 | A 未支持/固定命題 | B 残存未支持/表示命題 | 正しい命題の保持/A | 残存命題ID |
|---|---|---|---|---|
| known | 4/10 | 1/7 | 6/6 | ['K06'] |
| contrast | 2/6 | 1/5 | 4/4 | ['C02'] |
| limited | 1/4 | 0/3 | 3/3 | [] |
| retention | 0/2 | 0/2 | 2/2 | [] |

件数は今回の固定した原子的命題単位。前回の複合主張単位の分母と直接比較しない。処理失敗は削減0件・全削除などと数えずNAとする。knownを含む既存3群すべてを回帰診断として集計し、retentionの4902工程保持確認はこの集計から除外する。未知答案の効果は推定しない。contrastで実際に選ばれた代表はGrammarであり、Cohesionの採点傾向を保持できた実験とは数えない。既存3群は正の採点傾向ではなく、傾向の保留を伴う事例として扱う。

既存3群（known / contrast / limited）の回帰集計はA=7/20、B=2/15。参照判定で支持された命題の保持は13/13。4902の保持確認はこの集計から除外した。claim_manifestのeffect_aggregateは旧パイロットの新規2群区分を残す未使用メタデータであり、今回の回帰集計には既存3群すべてを含める。

**残る誤りは2件。** K06は局所2文から答案全体の明確なfocusへ広げた評価、C02は助動詞後の動詞形などの問題を主語・動詞一致とする誤診。LLMが両方をsupportedとしたため、その前提を使うKN1_originalとCN1_agreementの確認指示も残った。冠詞診断C03と対応する確認点は除去されたが、8699は誤診の完全修正には至っていない。これらはAからの残存で、新しい主張の新設とは分けている。

## 固定元・正本・形式

比較元コミット `38697e9bc153f8824c5e62c394e44b5be73fe759` の `outputs/recsaver_stage3_claim_verification_pilot_v1_0/`。
Stage 1〜3Bは再実行せず、known / contrast / limitedの初稿・得点・公式基準・引用を保存元から再利用。Aは元ファイルとバイト同一。Traitは本人の記録値で、固定引用の観点と得点をコード照合した。比較元は実行前後でハッシュ不変。

実際に使った正本は `prompts/en/recsaver_03c_verify_atomic_claims_v1_1.txt`、SHA-256は `90881d68203d28ea6852eca8534d482b9462c6ca732b22f1fecfed2c91b17626`。指定英文を保存し、実行時は{{INPUT_JSON}}のみを置換した。

現行vLLM 0.6.6.post1のGuidedDecodingParamsとoutlinesバックエンドによるJSON制約を適用。各要求のID集合・件数・3ラベル・必須フィールドをschemaに固定し、CPUで全4制約をコンパイル。正常例受理、ID欠落・重複・未知ID・未定義ラベル・余分フィールドの拒否を含む43件を通した。IDの一意性は生成後にも厳密検査する。JSON制約が使えるため、外側Markdown枠を除去する方式は使わず、厳密JSONだけを採用。本文修復・再生成なし。

モデル・system・チャットテンプレート・seed・通常sampling設定は保存元と同じ。Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。追加変更は3CのJSON制約。実際のschema、実入力、messages、sampling、生出力、解析結果を各群へ保存。

| 3C要求 | 入力tokens | 出力tokens | 厳密JSON | ID・構造 | 終了 |
|---|---|---|---|---|---|
| known | 2400 | 236 | True | True | stop |
| contrast | 1612 | 203 | True | True | stop |
| limited | 1214 | 133 | True | True | stop |
| retention | 781 | 83 | True | True | stop |

要求は計4回。外枠除去後の成立は非適用（除去回数0）。厳密JSON成立は4/4。予定したLLM判定は20/20件。事後機械検査は134/134。生出力は変更していない。

## 分割・位置検査・表示

claim_manifest.jsonは推論前 `2026-11-24T14:33:43.951225+09:00` に固定した22命題、元フィールド、主張ID、英文、選択引用、固定表示候補、確認点の事実前提と依存IDを持つ。分割はCodexによる人手相当の作業で、自動分割の性能ではない。語の切り出しだけで独立しない場合の主語・照応の補足、修正後に残せる局所表現、確認指示の前提を持たない問いへの限定を、出力を見る前に記録した。

位置2命題はコード、それ以外20命題はLLM。S004を段落末とするK05は実際の引用end=610とparagraph_end=765を比較してcontradicted。境界が不明ならinsufficient。thesisなどの修辞機能は位置判定から支持扱いせず、独立したK03としてLLMに渡した。

LLM入力は各claim_id・claim・その主張の選択引用と必要な基準/記録値だけ。上流解釈、採点理由、前回の判定、修正例、固定表示候補、コード判定を含めない。主張ごとの理由は保存するが表示文に使わない。独立参照判定はindependent_reference_review.jsonへ推論前に別保存し、モデルには渡していない。

Bは支持された命題だけを固定候補・順序で組み立てる。claim_manifestのdisplay_orderは命題の照合・記録順で、本文は推論前に実装した固定レイアウト（傾向保留→固定引用→局所所見→記録点/公式基準→限界/帯の保留→確認点）を使う。出力を見た並べ替えは行わない。否定された診断を前提とするsimilar errors等の確認候補も除く。既存の全体focusを既成事実にしない中立の確認候補と、文法問題一般の確認候補も事前固定し、その局所前提が支持されたときだけ残す。局所所見がなければ保留とし、別の候補所見や元初稿で補わない。引用を表示しても、それ自体を代替の所見とは数えない。記録得点・公式記述は原典から引用し、得点帯の妥当性の判断と区別した。

## 独立照合の範囲

評価者は実装を担当した同じCodex。主張ごとの参照判定はモデル出力を見る前に固定し、生成後は固定候補の表示、原文位置、得点・公式基準との対応を照合した。3C自己判定を正解に使わない。既知例の回帰診断であり、独立汎化評価・盲検評価ではない。位置検査、人手相当の分割、LLM判定、JSON制約の変更を組み合わせたため、各変更の効果を個別に識別できない。

主張別のコード判定、LLM判定・理由、採否、参照判定と原文はclaim_comparison.csvへ分けて保存。残存誤りや正しい内容の除外は、最低ラインの総合判定と別に以下へ記載する。

## known

既知例の回帰診断。採点傾向は保留の事例。

**Aの代表所見（保存済み原文）**

> The essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph, showing a clear focus on the importance of continuous learning.

Aの和訳：答案は明確な主張で始まり、段落末で中心的な考えを繰り返し、継続学習の重要性に明確な焦点を当てている。

**固定した命題・原文照合・採否**

| ID / 元フィールド | 判定対象英文／和訳 | コード | LLM | 表示 | 独立照合 |

|---|---|---|---|---|---|

| K01 / textual_finding | The first selected passage occurs at the start of the essay.<br>最初の選択区間は答案の先頭にある。 | supported | 対象外/未処理 | 保持 | supported：S001のstart=0で答案先頭=0。位置だけの命題として一致する。 |

| K02 / textual_finding | The first selected passage presents continued learning as a way to improve skills.<br>最初の選択区間は、継続学習を技能向上の方法として示している。 | 対象外 | supported | 保持 | supported：The main piece to improve your skills ... keep learningは、技能向上と学び続けることを明示的に結ぶ。 |

| K03 / textual_finding | The first selected passage functions as a thesis statement.<br>最初の選択区間は中心的主張として機能している。 | 対象外 | insufficient | 除外 | insufficient：この文の一般的主張の内容は確認できるが、独立に渡す抜粋だけで答案内のthesisという機能を確定しない。冒頭にあるというコード判定だけでも修辞機能は保証されない。前回の全原文文脈を含む複合評価とは根拠範囲を区別した。 |

| K04 / textual_finding | The second selected passage reiterates the first passage's idea of continued learning.<br>2番目の選択区間は、最初の区間の継続学習という考えを繰り返している。 | 対象外 | supported | 保持 | supported：S001はkeep learning、S004は成功し続ける専門家が生活や仕事にproductive informationを加え続けることを述べる。学び続ける考えの局所的な繰り返しとして支持される。末尾位置を主張してはいない。 |

| K05 / textual_finding | The second selected passage occurs at the end of its paragraph.<br>2番目の選択区間は段落末にある。 | contradicted | 対象外/未処理 | 除外 | contradicted：選択S004のend=610に対し第1段落のend=765。後続S005[611,765)がある。 |

| K06 / textual_finding | The essay maintains a clear focus on the importance of continuous learning.<br>答案は継続学習の重要性に明確な焦点を保っている。 | 対象外 | supported | 保持 | insufficient：第1段落内2抜粋の関連話題から、答案全体のfocusの明確さを評価できない。 |

| K07 / evidence_limit | The selected passages do not establish the overall coherence of the essay.<br>選択区間だけでは答案全体の一貫性を確立できない。 | 対象外 | supported | 保持 | supported：選択2抜粋だけでは段落間接続・答案全体の構成を確立できず、全体の一貫性の留保は適切。 |

| K08 / evidence_limit | The selected passages establish cohesion within the first paragraph.<br>選択区間は第1段落内の結束性を確立する。 | 対象外 | insufficient | 除外 | insufficient：選択2文で関連話題があることと、間の文・後続文を含む第1段落内の結束性が確立することは別である。 |

| K09 / pattern_status; pattern_limit | The supplied local evidence does not establish a repeated scoring behavior across essays.<br>提示された局所根拠では複数答案に共通する反復的な採点行動を確立できない。 | 対象外 | supported | 保持 | supported：異なる答案の局所特徴と記録得点だけでは、同じ比較可能な特徴の採点での扱いを反復して示せない。既存の傾向保留を支持する。 |

| K10 / rubric_review.band_assessment | The selected excerpts do not establish whether the recorded Cohesion band is appropriate.<br>選択抜粋だけでは記録されたCohesionの帯の妥当性を確立できない。 | 対象外 | supported | 保持 | supported：公式Cohesion:3は構成や結束表現の全体的な範囲・程度を含む。2抜粋からその帯の妥当性は判断できない。 |

**選択原文と出典位置（Aと同じ固定代表）**

`1868:1` / `E1868_1_P001_S001` / [0,77) / 段落 [0,765)

> The main piece to improve your skills is during the process of keep learning.

`1868:1` / `E1868_1_P001_S004` / [368,610) / 段落 [0,765)

> I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career.

**Bの表示文（生成モデルの文章ではなく、固定候補からの組立て）**

> The supplied local evidence does not establish a repeated scoring behavior across essays. In essay 1868:1, the reviewed excerpt is “The main piece to improve your skills is during the process of keep learning.” In essay 1868:1, the reviewed excerpt is “I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career.” The first selected passage occurs at the start of the essay. The opening passage presents continued learning as a way to improve skills. The selected passages repeat the idea of continued learning. The essay maintains a clear focus on the importance of continuous learning. The recorded Cohesion score is 3. The official descriptor for Cohesion:3 is “Organization generally controlled; cohesive devices used but limited in type; Some repetitive, mechanical, or faulty use of cohesion use within and/or between sentences and paragraphs.” The selected passages do not establish the overall coherence of the essay. This evidence alone does not establish whether that band is appropriate. Next inspect: Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning. Next inspect: Inspect the transitions between paragraphs and check whether the discussion of continued learning connects across them.

**Bに残った命題の和訳**

最初の選択区間は答案の先頭にある。

最初の選択区間は、継続学習を技能向上の方法として示している。

2番目の選択区間は、最初の区間の継続学習という考えを繰り返している。

答案は継続学習の重要性に明確な焦点を保っている。

選択区間だけでは答案全体の一貫性を確立できない。

提示された局所根拠では複数答案に共通する反復的な採点行動を確立できない。

選択抜粋だけでは記録されたCohesionの帯の妥当性を確立できない。

**確認点の保持・除外**

KN1_original：保持。前提=K06。英文：Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning.

KN2_neutral：保持。前提=K02。英文：Inspect the transitions between paragraphs and check whether the discussion of continued learning connects across them.

残存する未支持命題：['K06']。正しい命題の除外：[]。

## contrast

既知例の回帰診断。採点傾向は保留の事例。

**Aの代表所見（保存済み原文）**

> The sentence contains grammatical errors, including subject-verb agreement issues and incorrect use of articles.

Aの和訳：この文には、主語と動詞の一致の問題や冠詞の誤用を含む文法的誤りがある。

**固定した命題・原文照合・採否**

| ID / 元フィールド | 判定対象英文／和訳 | コード | LLM | 表示 | 独立照合 |

|---|---|---|---|---|---|

| C01 / textual_finding | The selected sentence contains grammatical errors.<br>選択文には文法的誤りがある。 | 対象外 | supported | 保持 | supported：We will not ever found itのmodal willの後に原形findでなくfoundを置くことや、We are constantly thatの構文に問題があり、文法的問題一般は支持される。 |

| C02 / textual_finding; next_check.inspect | The selected sentence contains subject-verb agreement errors.<br>選択文には主語と動詞の一致の誤りがある。 | 対象外 | supported | 保持 | contradicted：We are、technology can affect、someone dedicates、We willは主語に対応する。will ... foundは助動詞後の動詞形で、主語・動詞一致の問題ではない。 |

| C03 / textual_finding; next_check.inspect | The selected sentence contains incorrect use of articles.<br>選択文には冠詞の誤用がある。 | 対象外 | insufficient | 除外 | insufficient：the problemや無冠詞technologyを含むが、冠詞の誤用を直接特定できない。別種の構文の不自然さで冠詞診断は支持されない。 |

| C04 / evidence_limit | The selected sentence does not establish the overall grammatical accuracy of the essay.<br>選択文だけでは答案全体の文法的正確さを確立できない。 | 対象外 | supported | 保持 | supported：本文1476文字のうち1文[30,228)だけで、全体の文法的正確さ・頻度は分からない。 |

| C05 / pattern_status; pattern_limit | The supplied local evidence does not establish a repeated scoring behavior across essays.<br>局所根拠から複数答案共通の採点行動を確立できない。 | 対象外 | supported | 保持 | supported：代表は8699のGrammarであり、Cohesionの対照を意図した選定がCohesionの正の採点傾向を示したとは数えない。観点・局所特徴・得点を並べても扱いの反復は確定しない。 |

| C06 / rubric_review.band_assessment | The selected excerpt does not establish whether the recorded Grammar band is appropriate.<br>選択抜粋だけでは記録されたGrammarの帯の妥当性を確立できない。 | 対象外 | supported | 保持 | supported：Grammar:2のMany errorsという答案全体の程度は1文から確定できない。 |

**選択原文と出典位置（Aと同じ固定代表）**

`8699:1` / `E8699_1_P003_S001` / [30,228) / 段落 [30,271)

> Today We are constantly that technology can affect us some day and there will be nothing we can do about it, even if someone dedicates his lives trying to find the problem We will not ever found it.

**Bの表示文（生成モデルの文章ではなく、固定候補からの組立て）**

> The supplied local evidence does not establish a repeated scoring behavior across essays. In essay 8699:1, the reviewed excerpt is “Today We are constantly that technology can affect us some day and there will be nothing we can do about it, even if someone dedicates his lives trying to find the problem We will not ever found it.” The selected sentence contains grammatical errors. The selected sentence contains subject-verb agreement errors. The recorded Grammar score is 2. The official descriptor for Grammar:2 is “Many errors in grammar and usage.” The selected sentence does not establish the overall grammatical accuracy of the essay. This evidence alone does not establish whether that band is appropriate. Next inspect: Inspect other sentences for subject-verb agreement errors similar to those in the selected sentence. Next inspect: Inspect other sentences for grammatical errors and check their frequency and effect on clarity.

**Bに残った命題の和訳**

選択文には文法的誤りがある。

選択文には主語と動詞の一致の誤りがある。

選択文だけでは答案全体の文法的正確さを確立できない。

局所根拠から複数答案共通の採点行動を確立できない。

選択抜粋だけでは記録されたGrammarの帯の妥当性を確立できない。

**確認点の保持・除外**

CN1_agreement：保持。前提=C02。英文：Inspect other sentences for subject-verb agreement errors similar to those in the selected sentence.

CN2_articles：除外。前提=C03。英文：Inspect other sentences for article errors similar to those in the selected sentence.

CN3_general：保持。前提=C01。英文：Inspect other sentences for grammatical errors and check their frequency and effect on clarity.

残存する未支持命題：['C02']。正しい命題の除外：[]。

## limited

既知例の回帰診断。採点傾向は保留の事例。

**Aの代表所見（保存済み原文）**

> The sentence contains a nonstandard verb form: 'you will never grow.'

Aの和訳：この文にはyou will never growという非標準の動詞形が含まれている。

**固定した命題・原文照合・採否**

| ID / 元フィールド | 判定対象英文／和訳 | コード | LLM | 表示 | 独立照合 |

|---|---|---|---|---|---|

| L01 / textual_finding; next_check.inspect | The phrase "you will never grow" is a nonstandard verb form.<br>you will never growは非標準の動詞形である。 | 対象外 | contradicted | 除外 | contradicted：you will never growは助動詞will、never、原形growの標準的な構造である。 |

| L02 / evidence_limit | The selected excerpt does not establish the frequency of grammatical errors throughout the essay.<br>選択抜粋だけでは答案全体の文法誤りの頻度を確立できない。 | 対象外 | supported | 保持 | supported：局所抜粋だけでは答案全体の文法誤りの頻度を確立できない。 |

| L03 / pattern_status; pattern_limit | The supplied local evidence does not establish a repeated scoring behavior across essays.<br>局所根拠から複数答案共通の採点行動を確立できない。 | 対象外 | supported | 保持 | supported：2016のGrammar所見と3650のCohesion所見は同じ特徴の扱いの対照にならず、傾向の保留は妥当。 |

| L04 / rubric_review.band_assessment | The selected excerpt does not establish whether the recorded Grammar band is appropriate.<br>選択抜粋だけでは記録されたGrammarの帯の妥当性を確立できない。 | 対象外 | supported | 保持 | supported：この抜粋だけではGrammar:2のMany errorsという範囲・程度を確立できない。 |

**選択原文と出典位置（Aと同じ固定代表）**

`2016:1` / `E2016_1_P002_S001` / [32,149) / 段落 [32,377)

> Author Ralph Waldo wrote, "unless you try to do something beyond what you have already mastered, you will never grow.

**Bの表示文（生成モデルの文章ではなく、固定候補からの組立て）**

> The supplied local evidence does not establish a repeated scoring behavior across essays. In essay 2016:1, the reviewed excerpt is “Author Ralph Waldo wrote, "unless you try to do something beyond what you have already mastered, you will never grow.” No verified local finding remains. The recorded Grammar score is 2. The official descriptor for Grammar:2 is “Many errors in grammar and usage.” The selected excerpt does not establish the frequency of grammatical errors throughout the essay. This evidence alone does not establish whether that band is appropriate. No next check survived the claim prerequisites.

**Bに残った命題の和訳**

選択抜粋だけでは答案全体の文法誤りの頻度を確立できない。

局所根拠から複数答案共通の採点行動を確立できない。

選択抜粋だけでは記録されたGrammarの帯の妥当性を確立できない。

**確認点の保持・除外**

LN1：除外。前提=L01。英文：Other sentences for similar grammatical issues, particularly the use of verbs and auxiliary verbs.

LN2：除外。前提=L01。英文：The frequency and type of grammatical errors.

残存する未支持命題：[]。正しい命題の除外：[]。

## retention

4902:1の既存有効所見の保持確認。既存3群の改善集計・未知答案の効果推定から除外。

**Aは保持確認用の既存4902所見。新しい3B生成ではない。**

> The essay begins with a direct reference to Ralph Waldo Emerson's quote and explicitly states the reason for agreeing with it.

Aの和訳：答案はエマーソンの引用への直接の言及で始まり、それに賛成する理由を明示している。

**固定した命題・原文照合・採否**

| ID / 元フィールド | 判定対象英文／和訳 | コード | LLM | 表示 | 独立照合 |

|---|---|---|---|---|---|

| R01 / existing_observation.feature; existing_observation.scoring_relevance | The selected excerpts explicitly connect the writer's agreement with the quotation to a stated reason.<br>選択抜粋は引用への賛同を明示された理由に結び付けている。 | 対象外 | supported | 保持 | supported：4902のS001は引用とI agree、S002はThe reason why i agree ... is becauseを明示し、賛同から理由への局所的接続を2引用が支える。 |

| R02 / existing_observation.limitation | The selected excerpts do not establish the overall coherence of the essay.<br>選択抜粋だけでは答案全体の一貫性を確立できない。 | 対象外 | supported | 保持 | supported：この2引用だけでは答案全体の構成・一貫性は確立できない。 |

**選択原文と出典位置（Aと同じ固定代表）**

`4902:1` / `E4902_1_P001_S001` / [0,149) / 段落 [0,489)

> I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment."

`4902:1` / `E4902_1_P001_S002` / [150,243) / 段落 [0,489)

> The reason why i agree with this quote is because people now a day don't try to be them self.

**Bの表示文（生成モデルの文章ではなく、固定候補からの組立て）**

> In essay 4902:1, the reviewed excerpt is “I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment."” In essay 4902:1, the reviewed excerpt is “The reason why i agree with this quote is because people now a day don't try to be them self.” The writer explicitly states a reason for agreeing with the quotation. The recorded Cohesion score is 2. The official descriptor for Cohesion:2 is “Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition.” The selected excerpts do not establish the overall coherence of the essay. Next inspect: Review the subsequent paragraphs to see if the writer maintains this connection and develops the argument consistently.

**Bに残った命題の和訳**

選択抜粋は引用への賛同を明示された理由に結び付けている。

選択抜粋だけでは答案全体の一貫性を確立できない。

**確認点の保持・除外**

RN1：保持。前提=R01。英文：Review the subsequent paragraphs to see if the writer maintains this connection and develops the argument consistently.

残存する未支持命題：[]。正しい命題の除外：[]。

## 終了

対象観点を事前に固定した新しい答案群で、採点傾向の支持と保留を比較する。

この既知例での調整は終了する。新しい群の比較では対象観点を事前固定し、採点傾向を支持する材料がある場合と、保留が妥当な場合を分ける。今回の結果から自動分割・未知答案・採点者間のズレの改善を主張しない。
