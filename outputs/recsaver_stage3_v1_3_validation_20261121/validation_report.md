# Stage 3 v1.3 固定入力検証（A・B・C分離）

## 結論

**原文復元は改善した。3Bの内容は一部改善したが、両3Bの最終段落の引用欠落と、基準・意味の問題が残った。**

Aは6/6所見・2/2答案が機械検査を通過し、前回の3/6所見・1/2答案から改善。4902:1の引用符直後の空白も原文どおり復元した。ただし、有効なIDは意味の支持を保証しない。所見全文を妥当とみなせる所見を持つ答案はCodex暫定評価で1/2のまま。狭い局所特徴だけを使用できる答案は2/2になった。

Bは同じ入力で、観測Cohesion 3と妥当性の区別、および論理的な順序を確認する再考条件が改善。一方、最終段落の原文引用は旧版1/1から新版0/1に悪化し、機械検査は13/14通過で不合格。

Cは両答案の所見を受け取り、個別キーにも両答案を挙げたが、弱いCohesion所見を使い続けた。patterns=[]という保留は妥当。比較帯4と論理的破綻の課題との対応には問題がある。最終引用も欠け、機械検査14/15通過で不合格。出力の書き換え・再生成は行っていない。

これは同じ2答案による既知失敗の再検証であり、一般的な採点傾向抽出能力を測定していない。意味評価はCodexの暫定判断であって、人手評価ではない。

## 条件と保存元

比較コミット `10a0f0a0486114aa9bdc7b94358072a55e86feb1` は実行前HEADと一致。比較元は `outputs/recsaver_stage3_v1_2_pipeline_20261121/`。

| 固定元 | SHA-256 |
|---|---|
| fixed_input.json | `dca75b64bfdcd05c49ecbc50560529337073e32846ffaff682d378a80ca27b0e` |
| handoff/input_3b.json（Bの入力） | `fac2b84d805c671cf89ff1bd4c43aacb8b61ded28fd740bb52c64a03fed09563` |
| prompts/en/recsaver_03a_case_evidence_review_v1_3.txt | `c3e3f9af503adb7d2d0dd415bc0eb6edba1602b347d2c9380e47a9018fc10e9c` |
| prompts/en/recsaver_03b_integrated_feedback_v1_3.txt | `93eb151ad33be6f142a0bbbe51e80637fcd76d8bfcb991b63d3388c4d433cebd` |

正本実パスは `C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/` 以下。実際のWSLパス、同名検索結果（各1件）もrun_manifest.jsonに保存。本文は変更せず `{{INPUT_JSON}}` のみ置換。固定元と正本は実行前後でハッシュ不変。

モデルQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。vLLM0.6.6.post1・torch2.5.1+cu121・transformers4.48.3、既存RTX6000 Ada。各要求temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335。chat templateと既定systemは比較元と一致し、追加指示・guided decodingなし。全要求stopで終了、切り詰めなし。バッチ構成の差によるトークン単位の再現性は保証しない。

Stage 1・2、マスキング、採用条件は再実行・変更していない。固定対象1868:1・4902:1、各候補2件の本文・観測値・候補を保持。原文区間・受け渡し以外の元データを変えていない。

| 要求 | 入力tokens | 出力tokens | 厳密JSON | 構造 |
|---|---|---|---|---|
| stage3a/1868_1 | 13527 | 790 | True | True |
| stage3a/4902_1 | 7600 | 626 | True | True |
| stage3b_fixed/rater_7 | 2693 | 474 | True | True |
| stage3b_pipeline/rater_7 | 3732 | 623 | True | True |

実行回数はAの3Aが2、Bの同一入力3Bが1、Cの更新後3Bが1、合計4。AとBは独立した固定要求として同じEngineでバッチ処理し、Cは監査後に独立要求。結果を見て設定を変更していない。

## A：区間方式・機械検査

元文字列を正規化せず、PythonのUnicodeコードポイント位置[start,end)を使った。UTF-8バイト位置やUTF-16単位ではない。実改行と原文に含まれる文字どおりの\r\n区切りを識別し、段落全文を残した。段落内では句読点で分けた短い連続区間（最大360文字）と隣接区間（最大720文字）を用意。空白を区間境界から除く場合も位置を移動するだけで、切り出した文字列自体は変更しない。

1868:1は84区間・12段落、4902:1は34区間・5段落。すべてのスライスと原文が一致。IDは答案を含む接頭辞で一意。未知・他答案ID、同一所見内の重複IDを拒否し、multiple_passages/whole_essayには2つ以上の非重複区間を要求した。段落とその中の文を重複した独立証拠には数えない。

| A指標 | v1.2 | v1.3 |
|---|---|---|
| 厳密JSON・構造 | 各2/2 | 各2/2 |
| 所見の機械通過 | 3/6 | 6/6 |
| 通過所見を持つ異なる対象 | 1/2 | 2/2 |
| 所見全文が概ね妥当な通過所見を持つ対象（Codex暫定） | 1/2 | 1/2 |
| 通過所見の狭い局所特徴が使える対象（Codex暫定） | 1/2 | 2/2 |
| 選択IDが既知・当該答案・重複なし | 対象外 | 13/13 |
| 復元引用と元スライスの一致 | 対象外 | 13/13 |
| 既知K2得点矛盾の検出（Vocabulary・Phraseology） | 1/2観点 | 0/2観点 |

「全文が妥当」はfeatureだけでなくscoring_relevance・limitation・next_checkが証拠範囲と整合し、根拠のない帯支持を含まないこととした。「狭い局所特徴」は帯支持等を採用せず、実在する語形・綴り等だけを取り出せる場合。後者を完全に妥当な所見数に加算していない。旧版は機械通過後の所見を同じ基準で点検し、1868/O1の主題提示を1答案の根拠とした。この暫定二値化には評価者依存性がある。

### 4902:1で復元できた例：英語原文 → 和訳 → 照合

| 選択ID | 段落ID | Unicode位置 | 復元した英語原文 |
|---|---|---|---|
| E4902_1_P001_S001 | E4902_1_P001 | [0, 149) | I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment." |
| E4902_1_P001_S002 | E4902_1_P001 | [150, 243) | The reason why i agree with this quote is because people now a day don't try to be them self. |

和訳：私は作家ラルフ・ワルド・エマーソンの「あなたを別の何かに変えようとする世界で自分自身でいることは、最も偉大な達成だ」という引用に賛成します。この引用に賛成する理由は、今の人々が自分自身であろうとしないからです。

照合：前回欠落した引用符直後の空白を含み、[0,149)と[150,243)が原文に完全一致した。今回の4902の選択はO1が2区間、O2が別の1区間、O3が第4段落の1区間で、合計4つの異なる非重複区間。前回の同一引用を3所見で使う構成から変わったが、所見数と独立支持答案数は区別する。3所見を3答案とは数えない。

O1のscoring_relevance原文は “The lack of a smooth transition between the quote and the explanation of agreement indicates a repetitive and mechanical use of cohesive devices, which is consistent with a Cohesion score of 2.”。和訳は「引用と賛同の説明の間に滑らかな移行がないことは、結束表現の反復的で機械的な使用を示し、Cohesion 2と整合します」。実際には“The reason why”が引用と賛同理由を明示的につなぐ。滑らかさの問題から反復・機械性・2点の妥当性までを支持していない。公式Cohesion 3にも反復的・機械的使用があり、2点と一意に対応しない。区間が正しくても内容改善とは数えない。

より狭い所見として、O3の原文は “in conucluesion”、[ 1288, 1303 )。和訳は「結論として」（原文の綴りはconucluesion）。綴りの誤りは確認できるが、その1語でConventions 3や「時に気を散らす」という答案全体の影響を確認できない。O2のthem selfも形は確認できるがGrammar 3の妥当性までは不明。

### 1868:1と全所見の意味評価

| 所見 | 暫定評価 | 原文との照合 |
|---|---|---|
| 1868:1::O1 | 部分的 | learningの主題の反復・例示は読めるが、選んだ文をtransitional phrasesと総称して文間・段落間の明瞭な接続を確認したことにはならない。 |
| 1868:1::O2 | 過大・引用範囲との不一致 | 4箇所選択で単文からの一般化は避けたが、extra years for collegeは選択区間にない。語句の存在からwhole_essayの十分な語彙幅・適切性を確定できない。 |
| 1868:1::O3 | 概ね妥当 | is believe / have learnの形態・補文の問題は指定文に実在。局所に限定し、同様の問題と明瞭さを他文で確認する課題を残し、帯は支持しない。 |
| 4902:1::O1 | 解釈・帯支持が不十分 | 引用→The reason whyで賛同理由を示すことは確認可能。しかし接続が不滑らかというだけで反復的・機械的とし、Cohesion 2に整合すると断定できない。 |
| 4902:1::O2 | 局所特徴のみ使用可能 | them selfという非標準的な形は実在するが、1文だけでGrammar 3の妥当性は支持できない。 |
| 4902:1::O3 | 局所特徴のみ使用可能 | conucluesionの綴りは実在するが、1語からConventions 3やsometimes distractingは判断できない。 |

1868/O3の原文は “The most common mistake that someone can make is believe that they have learn enough to the point where is nothing else to learn.”。和訳は「人が犯し得る最もよくある間違いは、もう学ぶことがないほど十分に学んだと信じることです」。is believe、have learn等の問題は原文で確認できる。これは語形・文構造の局所確認として使用可能で、観測Grammar=3を妥当と確定していない。

1868/O2は1文ではなく4区間を選んだので、前回と同じ「1文だけ」の失敗とは区別した。しかし十分な語彙幅の主張は依然未支持で、例示したextra years for collegeは選んだ4区間に含まれない。複数区間があるという形式だけでwhole_essayを合格にしていない。

### issueの分類と既知矛盾

両3Aのsource_analysis_issuesは[]で、issue生成0件。引用一致率・問題分類精度は分母0のため評価不能。ただし既知の検出対象は評価できる。1868/K2の “consistent with the observed scores of 3 for both Overall and Traits”（OverallとTraitsの両方の観測3点と整合する）は元候補に存在し、Vocabulary=4・Phraseology=4の両方と矛盾する。今回は0/2観点しか拾わず、既知矛盾の検出は未達。前回はVocabularyのみを拾っていたため、この既知例では悪化した。

1868/K1の観点が明示されないscore of 3をVocabulary 3だと誤分類する出力は今回はなかった。ただし曖昧参照としての指摘もなく、全issueを省略したため、正しく読み分けた能力の改善とは結論づけない。score_conflictsの観点・元観測値の検査、候補引用一致検査は実装し、合成テストで両Trait不一致を通し誤った観測値を拒否したが、モデルの検出成功に加算していない。

## B：同一入力による3B単体比較

前回handoff/input_3b.jsonと実リクエストのinput.jsonはバイト同一で、観測値・所見・順序・基準は固定。この入力には1868:1の所見しかない。傾向抽出力ではなく、説明・基準・見直し条件を比較する。

### 旧v1.2の最終フィードバック：英語原文 → 和訳 → 照合

> Based on the observations, there is insufficient evidence to establish a pattern in how the rater evaluates essays. For example, in the essay with ID 1868:1, the sentence 'The main piece to improve your skills is during the process of keep learning.' sets up the essay's central theme, contributing to the essay's cohesion. However, this single sentence does not provide enough evidence to fully assess the essay's cohesion. The observed score for cohesion is 3, which aligns with the rubric entry for Cohesion:3, but it is indeterminate whether this score should be higher or lower without reviewing additional sentences. The next scoring check should involve inspecting additional sentences to see if they consistently support the central theme and use a range of cohesive devices. This would help in retaining or reconsidering the judgment.

所見に基づくと、採点者が答案をどう評価するかについての傾向を確立するには証拠が不十分です。例えばID 1868:1の答案では、「The main piece to improve your skills is during the process of keep learning.」（技能を向上させる主な要素は、学び続ける過程にあります）という文が答案の中心的な主題を提示し、答案の結束性に寄与しています。ただし、この1文では答案の結束性を十分に評価するだけの証拠にはなりません。結束性の観測得点は3で、これはCohesion:3のルーブリック項目と整合しますが、追加の文を確認しなければ、この得点を上げるべきか下げるべきかは未確定です。次の採点確認では、追加の文が中心的な主題を一貫して支え、さまざまな結束表現を使っているかを調べるべきです。これは判断の維持または再考に役立ちます。

原文・観測値・基準との照合：原文引用と1868:1はある。観測Cohesion=3は正しいが、「基準と整合する」という肯定とindeterminateが緊張する。公式3点は結束表現の種類が限られても許容するのに、旧reconsider_ifはlimited cohesive devicesを再考条件とした。単一文から一般的な構成や結束表現の種類を確認したとは言えない。

### 新v1.3 Bの最終フィードバック：英語原文 → 和訳 → 照合

> Based on the evidence provided, there is insufficient evidence to support a consistent pattern in your scoring. The representative observation from essay 1868:1 introduces a central idea, but the links across the essay remain unexamined. To better assess the cohesion, please review additional sentences to see if they consistently support the central theme. The use of cohesive devices and logical sequencing of ideas will help distinguish between the observed band and the comparison band. If the essay consistently uses cohesive devices and maintains logical sequencing of ideas, the current score can be retained. However, if there is a sustained breakdown in logical sequencing or a lack of cohesive devices, reconsideration of the score may be necessary.

提示された証拠に基づくと、あなたの採点に一貫した傾向があることを支持するには証拠が不十分です。答案1868:1の代表所見は中心的な考えを提示していますが、答案全体にわたるつながりは未確認です。結束性をより適切に評価するため、追加の文が中心的な主題を一貫して支えているか確認してください。結束表現の使用と考えの論理的な順序は、観測帯と比較帯を区別する助けになります。答案が結束表現を一貫して使い、考えの論理的な順序を保っているなら、現在の得点を維持できます。しかし、論理的な順序に持続的な破綻がある、または結束表現が欠けているなら、得点の再考が必要かもしれません。

照合：代表1868:1::O1とCohesion:3への参照は正しい。explanationは “The recorded Cohesion score is 3. This excerpt introduces a central idea, while the links across the essay remain unexamined. Additional evidence is needed to judge the observed band or distinguish it from the comparison band.”。和訳は「記録されたCohesionの得点は3です。この抜粋は中心的な考えを提示していますが、答案全体のつながりは未確認です。観測帯を判断したり比較帯と区別したりするには追加の証拠が必要です」。記録値と適切性を分離し、未検査箇所を読んだとは主張しない。indeterminateとの結論は整合する。

一方、comparison_band_ref_idはnullなのに「比較帯」との区別を述べ、どの帯との比較かを特定していない。再考条件は種類の限定から持続的な論理順序の破綻へ改善したが、追加で読む箇所は「追加の文」と一般的。何でも一貫していなければ再考、という硬い運用を避け、3点で許容される一部の不成功と持続的な破綻を区別する余地も残る。

最終段落にIDはあるが原文引用はない。必須の原文コピーを欠き、13/14機械検査で失敗。原出力を修正しなかった。

| Bの評価点 | 判定 | 根拠 |
|---|---|---|
| indeterminateと説明・最終結論 | 改善 | v1.2のaligns with a score of 3という肯定から、記録値3・局所主題・未検査の接続に分離した。 |
| 公式基準に沿う保持・再考条件 | 改善（限定的） | limited devicesだけを再考理由にせず、sustained breakdown in logical sequencingへ変更。ただしcomparison_band_ref_id=nullなのに比較帯を説明し、追加で見る箇所は一般的。 |
| 最終段落の引用・出典・追加確認 | 悪化 | IDはあるが旧版にあった原文引用が欠落。未確認の接続を未確認とする点は改善したが、具体的な箇所指定も十分でない。 |

## C：新3A → 3B v1.3の通し検証

復元quotesを既存の3B入力形式へ変換し、6所見に元観測点を添付した。1868はCohesion3・Vocabulary4・Grammar3、4902はCohesion2・Grammar3・Conventions3。各観測帯と存在する直近の上下帯を固定rubricから取得し、一意な観点:帯のIDと取得元を保存した。生候補・履歴本文・issue原文は3Bへ渡していない。今回issue自体は0件。意味評価による所見の書き換え・除外を主実行に加えていない。

入力の通過対象は2/2、出力個別キーは1868:1::O1と4902:1::O1の2/2件が入力に属する。代表は1868:1::O1。observed_band_ref_id=Cohesion:3は観点・観測3と一致し、comparison_band_ref_id=Cohesion:4は同一観点の別帯。patterns=[]の保留は、2答案で同じ「特徴と評価の関係」を示す証拠がないため妥当。同じOverall=3や引用付き2答案だけで合格にはしていない。

### Cの最終フィードバック：英語原文 → 和訳 → 照合

> Based on the evidence provided, there is insufficient evidence to establish a consistent pattern in your scoring. The representative observation from essay 1868:1 shows that the essay uses transitional phrases and ideas to connect sentences and paragraphs, but this does not establish the overall coherence of the essay. The recorded Cohesion score is 3, but the evidence is not sufficient to determine if this score aligns with the rubric descriptor for Cohesion:3. For your next scoring check, inspect the transitions between paragraphs to see if they are as clear and effective as those within paragraphs. The distinction between the observed band and the comparison band is whether the links between ideas remain traceable and if there is a sustained breakdown in logical sequencing. Retain the judgment if the transitions between paragraphs are clear and effective, and reconsider if there is a sustained breakdown in logical sequencing.

提示された証拠に基づくと、あなたの採点に一貫した傾向を確立するには証拠が不十分です。答案1868:1の代表所見は、この答案が文と段落をつなぐ移行表現と考えを使っていることを示しますが、答案全体の一貫性を証明するものではありません。記録されたCohesionの得点は3ですが、この得点がCohesion:3のルーブリック記述と整合するか判断するには証拠が不十分です。次の採点確認では、段落間の移行が段落内の移行と同じくらい明瞭で効果的か調べてください。観測帯と比較帯の違いは、考えのつながりが追跡可能か、論理的な順序に持続的な破綻があるかです。段落間の移行が明瞭で効果的なら判断を維持し、論理的な順序に持続的な破綻があれば再考してください。

照合：採点の安定した好みや、特徴が得点を生んだという因果は断定していない。「整合するか判断するには証拠不十分」という否定・保留の文は、aligns withという語を含むだけで肯定の帯支持とは判定しない。しかし、代表の主題提示をtransitional phrasesによる接続と呼ぶ主張はAから継承し、4902についても弱いCohesion O1を個別所見に挙げた。使えるGrammar・Conventionsの局所部分を選び直してはいない。両答案の意味的に有用な部分が存在することと、Cが実際に適切な部分を使ったことは別で、後者は十分ではない。

最終段落にIDはあるが代表原文引用はなく、14/15機械検査で失敗した。explanationには原文断片があるが、最終段落の要件を満たしたことにはしない。

比較帯4は、種類が限られる3に対し適切な多様な結束表現を求める。Cのdistinguish前半はこの差を正しく述べた。しかし後半と最終段落は「追跡できるか／持続的な論理順序の破綻」を3対4の違いのように述べる。後者はむしろ2点のlogical sequencingの欠如に近い下方再考の論点で、4との比較だけでは位置づけが不十分。3点が許容する一部のfaulty useと、持続的破綻の違いはなお具体化が必要である。

追加確認は「段落間の移行を段落内と比較」とBより絞られたが、どの段落・文間かは指定されない。段落内をすでにclear and effectiveと確認済みのように基準に置く点にも注意が必要。例えば、確認対象として育児例の導入前後と教育・仕事の例への移行を探すことはできるが、その確認を実施したとは今回の所見からは言えない。

### 公式Cohesionの対照（保存済みrubricから）

| 帯 | 英語原文 | 今回の論点 |
|---|---|---|
| 2 | Organization only partially developed with a lack of logical sequencing of ideas; some basic cohesive devices used but with inaccuracy or repetition. | logical sequencingの欠如は下方見直しの論点。 |
| 3 | Organization generally controlled; cohesive devices used but limited in type; Some repetitive, mechanical, or faulty use of cohesion use within and/or between sentences and paragraphs. | limited in typeや一部の反復・機械的・不適切な使用を許容。 |
| 4 | Organization generally well controlled; a range of cohesive devices used appropriately such as reference and transitional words and phrases to connect ideas; generally appropriate overlap of ideas | 適切な多様な結束表現と概ね適切な考えの重なりを確認。 |

BとCの差は入力所見・基準集合の更新を伴う。Cでcomparison=4になったことや両答案キーが出たことを、3B文面単体の効果には帰属させない。

## 機械検査と保存

全4要求は厳密JSON4/4・各v1.3構造4/4通過。Aは6/6所見が通過し除外0件、除外理由は各mechanical_checksの空配列で記録した。Bは13/14、Cは14/15で、どちらも最終引用欠落が失敗。ID・観測帯・比較帯は対応可能な全項目が通ったが、意味的正しさを保証しない。

入力・復元・受け渡し・生成条件・原出力の不変性は71/71通過。初回の再検査では、既存検査がset順序で出す独立な対象IDチェックの並び順だけが異なった。初回記録をinvariant_checks_initial.jsonに残し、検査結果の照合だけを独立項目の順序不問にした。モデル入力の配列順序はバイト単位の同一性で検査しており、不問にしていない。生成・採否・モデル原出力は変えていない。

追加コードは既存Engine、観測点・公式基準の付与、3B機械検査を再利用した。保存先は `outputs/recsaver_stage3_v1_3_validation_20261121/`。固定入力、evidence_spans、各要求のinput/messages/rendered_chat/sampling/raw/parsed/result/generation/integrity、handoff、原文復元と区間監査、除外理由、A比較CSV、summary、content_review、request_summary、run_manifest、テスト、追加コード、READMEを保存した。元の生出力とparsedは書き換えていない。

## 三つの問いへの回答と次の課題

1. **両答案の所見が届いたか：はい、2/2。** 区間選択で4902の引用欠落を解消し、両答案を比較できる入力状態になった。
2. **意味的に使えたか：部分的。** 両答案に使える狭い局所特徴はあるが、所見全文が妥当な所見を持つ対象は1/2。Cは弱いCohesion所見を採用し、原文引用も最終段落に残せなかった。
3. **採点傾向を支持できたか：いいえ。** B・Cともpatterns=[]は妥当。同じOverall=3や引用の存在から、評価の仕方の共通性は導けない。

次は、最終引用を出典キーから確実に表示する方法、3Aの局所特徴と帯支持の分離および全Trait矛盾監査、3Bの上方・下方比較と具体的な文間確認の区別を修正する。今回は1応答ずつの既知例検証であり、傾向が支持される別案件・他採点者・他得点帯の性能は未検証である。
