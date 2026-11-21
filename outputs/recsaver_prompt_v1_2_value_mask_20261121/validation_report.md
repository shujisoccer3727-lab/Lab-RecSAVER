# v1.2 対象得点の値だけをマスクする方式：検証報告

2026-11-21 JST。比較元コミットは`c52617a669149b895c412165591d71257e4c0e8c`、保存元は`outputs/recsaver_prompt_v1_1_validation_20261120/`。新実験内に原出力とマスクコピーを分け、比較元の成果物は上書きしていない。

## 結果の要点

保存済みv1.1の6候補では、6/6候補の計15値をマスクし、5/6候補が入力検査を通過した。1514/K1の対象自身による履歴支持は数値マスクと別に隔離した。新v1.2では6/6候補の計15値をマスクし、全6件をStage 2へ渡した。厳密JSON・有効推定は6/6、Overall一致・採用は4/6、異なる採用答案は2/3。したがってStage 3の初回評価に進む条件を満たした。

マスクで文・節・引用を削除せず、明示的な対象得点値を入力から除くことはできた。一方、1868の局所的な1文から全体構成・語彙幅を説明する問題や、原理由の誤ったTrait説明は残っている。**マスク成功、再構成一致、内容の有用性は別の結果である。**

## 1. 正本・設定・実装

使用正本は以下。実パス・SHA-256前後値・検索場所は`run_manifest.json`。

- `prompts/en/recsaver_01_reference_rationale_v1_2.txt`
- `prompts/en/recsaver_02_overall_reconstruction_v1_1.txt`
- `prompts/en/recsaver_03_integrated_feedback_v1_0.txt`

v1.2は配置済みだったため旧版の代用はしていない。正本の英文は変更せず、`{{INPUT_JSON}}`だけをシリアライズしたJSONで置換した。Stage 1には対象の観測Overall・全Traitを渡す。v1.2正本には上部で実得点を明示して後段でマスクする説明がある一方、末尾に得点帯比較をobserved_score_alignmentへ移す指示が残っている。この併存はそのまま記録し、一方を削除していない。

対象はrater_7の1514:1、1868:1、4902:1、各2候補、同じ本人履歴各3件。モデルは既存Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、GPTQ Marlin、context=32768、temperature=0.2、top_p=0.8。生成上限は6500/1200/5000、seedは前回と同じ20261118を基準とする段階・候補ID別SHA-256割当。Stage 1の実入力とsampling設定は比較元と同一である。tokenizerのchat templateと既定system文を維持し、追加のsystem指示、形式制約、修復プロンプト、得点不一致による再生成は行っていない。新規契約・モデルダウンロードなし。

### 値だけの置換と隔離

`code/masking.py`はscore_free_analysisをdeep copyして全フィールドを走査する。対象に帰属する得点/帯/範囲の数字・英語数詞だけを`□`へ置換する。変更するJSON path、元/変更後の全文、値の文字位置、判定理由を`mask_audit.json`に保存する。句や節を落としたり、引用の空白を修復したりはしない。

実際の履歴ID集合に属する履歴本文・得点は保持する。履歴パターン内の得点も、支持IDが実際の履歴に帰属し歴史的な得点記述である場合は保持する。本文引用とIDはコピーしたまま。正規のルーブリックと得点仕様はマスク処理の対象外である。同じ数字だから伏せる処理はしていない。

明示的な「履歴と同じ得点」、計算、固有の帯名称、対象/履歴の帰属不明は隔離する。対象を履歴として引用したレコードは、偽の履歴得点ブロックを正規化して救済せず隔離する。このため隔離コピーに数値が残る場合があるが、Stage 2へ渡さない。

特徴の類似性による推論と、得点が等しいという明示的な関係は区別した。歴史的得点を保持すればモデルがそこから予測することは可能であり、任意の間接的な推論や未知の符号化まで防いだという保証ではない。機械検出に加え、Codexが全体を点検した結果を`replay_review.json`・`main_mask_review.json`に記録した。これは独立の人手評価ではない。

### 実装修正の履歴

GPU生成前に、`limited history`という一般的な制約説明を帰属不明と誤認したケースと、後続のhistory言及により対象の明示得点を誤って保持したケースを修正した。修正前を`implementation_revision_0/1`に保存した。

新Stage 1生成後の点検で、4902/K1・K2の「履歴で同様の答案が3点だった」という別表現まで伏せた誤りが2箇所見つかった。本実行Stage 2の開始前に修正し、元コード・コピーを`implementation_revision_2`に保存した。原出力・モデル・seedを変えずマスクコピーだけを再計算した。実行済み診断A/B/Cのリクエストがこの修正で変わらないことも確認した。最終集計は修正後であり、初版から無修正で成功したとは報告しない。

数字/数詞/範囲、同じ値の通常数字、履歴と対象の混在、引用・ID保持、等値、計算、固有帯、曖昧帰属、保存候補を含む21対照が通過。さらに実入出力のコピー・原出力ハッシュ・正本置換・Stage 2の入力分離を別途検証した。

## 2. 保存済みv1.1出力と診断コピー

既存6候補は再生成していない。

|候補|置換値数／変更フィールド数|入力検査|残った問題|
|---|---|---|---|
|1514/K1|3/3|隔離|対象1514:1が履歴支持IDに混入。対応する偽の履歴得点ブロックも信頼不可|
|1514/K2|2/2|通過|説明の根拠の弱さは残る|
|1868/K1|3/3|通過|1文から全体構成・語彙幅を説明する主張は残る|
|1868/K2|2/2|通過|同上。明示的に履歴へ帰属する3は保持|
|4902/K1|2/2|通過|全観点をminor errorsと括る問題は残る|
|4902/K2|3/3|通過|空白差や基準対応の問題は残る|
|合計|15値／15フィールド、6/6候補に適用|5/6通過|不正な履歴参照1/6で隔離|

通過した5件では、点検した範囲で残存する直接の対象得点値、適用した番号付き帯値、明示的な復元式は確認しなかった。これは文章の主張が正しいという判定ではない。隔離した1件は残存不備ありとして記録している。

### マスク後診断（本実行の採否とは別）

|対照|置換|厳密JSON|status / Overall|マスク自体を汚染としたか|
|---|---|---|---|---|
|A：旧1514/K1の単一対象帯|2値|1/1|estimated / 3|なし|
|B：旧4902/K2の複数対象帯|2値|1/1|estimated / 3|なし|
|C：前回作成した数値帯なし対照|0値、変更なし|1/1|insufficient_information / null|なし|
|D：履歴得点と等値の人工対照|変更せず隔離|未実行|復元可能なためStage 2へ渡さず|該当なし|

実行3件中3件が厳密JSON・構造検査通過、推定は2/3、証拠不足は1/3、contaminated_inputは0/3。実際に`□`を含むA/Bだけを分母にしても、マスクを理由とする汚染判定は0/2。Cの保留理由は局所所見だけでは本人の全体判断を説明しきれないというものだった。Cの歴史的得点や数字を理由に汚染扱いはしていない。

前回の未マスクA/Bでもモデルは本来止まるべき入力を無視して3点と推定していた。したがって今回の推定成功だけから「汚染検出が改善した」とは言えない。今回確認したのは、値を伏せたコピーを形式どおり受け取り、マスク自体を停止理由にしなかったことに限る。

## 3. 本実行：生成・マスク・再構成・採用

|指標|結果|
|---|---|
|生成候補|6/6|
|Stage 1厳密JSON・既存構造検査|6/6|
|観測Overall・全Traitの構造化転記が一致|6/6（自由文の正確さとは別）|
|マスク適用候補|6/6|
|置換値数／変更JSONフィールド数|15値／15フィールド|
|マスク後の確認済み残存入力違反|0/6（点検範囲内）|
|不正な履歴参照|0/6|
|入力検査通過／Stage 2実行|6/6、6/6|
|Stage 2厳密JSON・構造検査|6/6|
|許容Overallによる有効推定|6/6|
|Overall一致|4/6（66.7%）。全候補基準・有効推定基準とも分母6|
|採用候補|4/6（66.7%）|
|異なる採用対象答案|2/3（66.7%）|

|対象|各候補の置換値数|Stage 2予測|観測Overall|採用|
|---|---|---|---|---|
|1514:1|K1=2、K2=3|4、4|3|0/2|
|1868:1|K1=2、K2=3|3、3|3|2/2|
|4902:1|K1=3、K2=2|3、3|3|2/2|

1514の不一致2件は追加生成で救済していない。残る4件は指定の採用条件を満たしたため採用し、内容の弱さを理由に追加で落とすことはしなかった。独立した支持例は4件ではなく2答案である。

Stage 2の実リクエストはrater_id、rubric、score_specification、history、target（IDと本文のみ）、マスク後reference_analysisだけ。Stage 1生出力、観測target得点、observed_score_alignment、置換記録、採否記録を含めていない。呼出しは履歴会話を継がない独立chatである。

## 4. 代表例：英語原文 → マスク後 → 和訳 → 残ったもの

### A. 正しく値だけを置換：新1514:1/K2

**英語原文**： “The essay demonstrates a generally well-controlled organization and a range of cohesive devices, but the syntactic structures are limited, leading to a score of 3.”

**マスク後**： “The essay demonstrates a generally well-controlled organization and a range of cohesive devices, but the syntactic structures are limited, leading to a score of □.”

**和訳**：原文「答案は全体としてよく統制された構成と多様な結束装置を示すが、統語構造は限られており、3点となる。」→マスク後「答案は全体としてよく統制された構成と多様な結束装置を示すが、統語構造は限られており、□点となる。」

**残ったもの**：主張・接続・評価上の説明はそのまま。`masks/1514_1__K2/mask_audit.json`に位置を記録した。冒頭の1引用から全体構成・構造の幅まで導く根拠の弱さは残る。再構成は4となり観測3と不一致だった。値を隠せたことと本人判断を再現できたことは別である。

### B. 複数帯の値を置換：診断B

**英語原文**： “The rubric for scores 2 and 3 indicates that communication is impeded by language inaccuracies and that there are many sentence structure problems.”

**マスク後**： “The rubric for scores □ and □ indicates that communication is impeded by language inaccuracies and that there are many sentence structure problems.”

**和訳**：原文「2点と3点のルーブリックは、言語の不正確さで意思伝達が妨げられ、文構造上の問題が多いことを示す。」→マスク後「□点と□点のルーブリックは、言語の不正確さで意思伝達が妨げられ、文構造上の問題が多いことを示す。」

**残ったもの**：2つの帯を一括して説明する文章自体は残る。Overallの2と3では意味妨害の頻度が異なり、“many sentence structure problems”はSyntax 2側の記述。数値の置換でこの混同を訂正したわけではない。入力契約の検査と意味上の正しさを混同しない。

### C. 数値だけでは通せない：保存済み1514:1/K1

**英語原文**： “The target essay demonstrates controlled organization and a minimally adequate range of vocabulary, consistent with the observed Overall score of 3.”

**マスク後**： “The target essay demonstrates controlled organization and a minimally adequate range of vocabulary, consistent with the observed Overall score of □.”

**和訳**：原文「対象答案は統制された構成と最低限十分な語彙幅を示し、観測されたOverall 3点と整合する。」→マスク後「対象答案は統制された構成と最低限十分な語彙幅を示し、観測されたOverall □点と整合する。」

**残ったもの**：`history_patterns/0/support/1/history_essay_id`が対象自身の1514:1。実際の履歴は217:1、1440:1、8745:1。この原文・IDを削除/変更して履歴例に見せかけることはせず、コピー全体を隔離した。対応する誤帰属の得点ブロックは未認証のまま残すため、そのコピーをStage 2へは渡していない。

### D. 数字がなくても復元できる：等値対照

**英語原文**： “The target received the same Overall score as history essay 217:1.”

**マスク後**：変更なし・隔離。“The target received the same Overall score as history essay 217:1.”

**和訳**：「対象は履歴答案217:1と同じOverall得点だった。」

**残ったもの**：履歴217:1のOverall=3を使えば対象値が復元できる。数字だけを探す処理では防げないため、同じ得点という関係自体を検出して隔離した。式や固有帯名称の対照も同じ方針で、文を自動で書き換えて通過させていない。

### E. 1868:1で局所所見を残せたか

新1868/K1の対象引用は “The main piece to improve your skills is during the process of keep learning.”。

**英語原文（evaluative_interpretation）**： “The essay's organization is generally controlled, and it uses a sufficient range of vocabulary, which is consistent with a score of 3.”

**マスク後**： “The essay's organization is generally controlled, and it uses a sufficient range of vocabulary, which is consistent with a score of □.”

**和訳**：原文「答案の構成は全体として統制され、十分な語彙幅を使っており、3点と整合する。」→マスク後「答案の構成は全体として統制され、十分な語彙幅を使っており、□点と整合する。」

**残ったもの**：引用と非数値の説明は保持したが、元から局所的な構文・反復・意味回復の分析が乏しく、1文では全体構成や語彙幅を支えられない。マスクは確認可能な所見を消してはいないが、局所所見を適切に生成・接続できたとも言えない。

新1868/K2では “consistent with the observed scores of 3 for both Overall and Traits” が “consistent with the observed scores of □ for both Overall and Traits” になる。訳は「OverallとTraitの両方で観測された3点と整合する」→「OverallとTraitの両方で観測された□点と整合する」。実際のVocabulary/Phraseologyは4。構造化observed_target_scoresは正しくても、この自由文の誤りは置換後も残る。再構成は両候補とも3で採用されたが、内容が改善・正当化されたとは扱わない。

新6候補の引用は19/20が完全一致、1/20が空白差。保存済みv1.1は17/20完全一致、3/20空白差だった。マスク前後で引用はすべて同一であり、この差はStage 1の別生成によるもの。マスクによる引用品質の改善ではない。

## 5. Stage 3：統合の初回評価

**初回生成を実施し、厳密JSON・既存構造検査に通過した。ただし内容上の未達があり、採点者へ提示する完成稿としては採用しない。** v1.1では統合を生成していなかったため、統合プロンプトの版間改善比較ではない。

入力のaccepted_recordsは1868/K1・K2、4902/K1・K2のマスク前の完全なStage 1レコード4件。source_essaysは対象2件と対応する履歴6件を含む。実入力の各レコードが原出力と同一であることを検査した。マスク前の観測得点とobserved_score_alignmentはこの段階では利用した。

出力のaccepted_record_count=4、distinct_target_essay_count=2、target_essay_ids=[1868:1,4902:1]は正しい。候補を4つの独立答案と数えたわけではない。次の4点を暫定評価した。

|評価点|Codex暫定判定|根拠|
|---|---|---|
|複数答案から、その採点者が特徴をどう評価したか|partially_met|2答案を挙げるが、同じOverall=3とminor errorsという特徴の反復が中心。本人の評価関係は十分に区別できない|
|代表例で本文引用・推定判断・観測得点が接続|not_met|4902のEmerson引用への賛同文だけで、6観点のminor errors全体とOverall3を説明。最終段落には本文引用自体がない|
|ルーブリックの観点・帯の違いを正確に扱う|not_met|Overall4の実在する記述を引用してOverall3と整合すると説明。意味妨害の頻度差も混同|
|次回に何を確認し何を区別するかが具体的|partially_met|深刻さと意思伝達への影響を区別する方向はあるが、特定箇所・確認すべき解釈・保持/再考の判断証拠が抽象的|

さらに、counterexamples_and_scopeのtarget_essay_idに8722:1がある。これは4902の履歴であって採用対象ではない。scopeの2答案という件数は守ったが、根拠の役割ラベルを混同している。また1868の個別理由は主にCohesion/Vocabularyを扱ったのに、統合は6観点すべてのminor errorsへ主張を拡張した。source_analysis_issuesは空で、1868/K2の誤った全Trait=3の説明も点検上の問題として挙げていない。

### 統合本文の英語原文

> In these supplied cases, you appear to assign an Overall score of 3 to essays that demonstrate a mix of minor errors in cohesion, syntax, vocabulary, phraseology, grammar, and conventions. For example, in essay 4902:1, the mix of minor errors is consistent with an Overall score of 3. The rubric requires occasional language inaccuracies that rarely impede communication, which aligns with your treatment of these errors. For future scoring, inspect the mix of minor errors and distinguish their severity and impact on communication to ensure consistency with the rubric.

### 和訳（原文の誤りは修正しない）

今回提示された事例では、あなたは結束性、統語、語彙、句、文法、表記に軽微な誤りが混在する答案にOverall 3点を付けているように見えます。例えば答案4902:1では、軽微な誤りの混在はOverall 3点と整合します。ルーブリックが要求するのは、意思伝達をめったに妨げない程度の時折の言語の不正確さであり、それはあなたのこうした誤りの扱いと一致します。今後の採点では、ルーブリックとの一貫性を確保するため、軽微な誤りの混在を調べ、その深刻さと意思伝達への影響を区別してください。

### 原文・ルーブリックとの照合

`stage3/rater_7/parsed.json#/patterns/0/rubric_comparison/rubric_quote`は “Facility in the use of language with syntactic variety and range of words and phrases; controlled organization; accuracy in grammar and conventions; occasional language inaccuracies that rarely impede communication.”。これは保存ルーブリックの**Overall 4**と完全一致する。

同出力のcomparisonは “The essay's mix of minor errors aligns with the rubric descriptors for an Overall score of 3, as the errors do not significantly impede communication.”。原文の訳は「答案の軽微な誤りの混在は、誤りが意思伝達を大きく妨げないため、Overall 3点のルーブリック記述と一致する」。実際のOverall 3は “Communication is impeded by language inaccuracies in some cases.” を含み、4の “rarely impede communication” と同じ条件ではない。

代表引用は “I agree with Author Ralph waldo Emerson quote, " To be yourself in a world that is trying to make you something else is the greatest accomplishment."”。本文に実在するが、これだけで6観点すべての軽微な誤りや頻度・意味影響を確認できない。引用の文字列一致と主張への意味的支持を区別する。

マスク後再構成が一致した候補でも、元の広すぎる説明や誤った基準対応が統合へ伝播することを、この初回評価で確認した。数値マスクはこれらを修復する処理ではない。

## 6. 何が確認でき、何が残ったか

- **根拠の保持**：検査したコピーでは変更は得点値のみ。引用・ID・文・節は削除していない。対象得点と同じ数字の歴史的得点、原文中の数字、正規ルーブリックを保持した。ただし元から所見が浅い場合、その弱さも保持する。
- **入力違反の防止**：保存済みの対象自身による履歴支持と、等値・計算・固有帯・曖昧帰属の対照を隔離した。新6候補では点検した範囲で残存する直接の対象数値・復元式はなく、実リクエストへ置換監査や原得点を渡していない。自然言語すべての符号化や誤帰属を検出できる保証はない。
- **統合の初回評価**：採用4レコード・2答案で実施できた。形式成功と件数の区別は確認したが、引用の支持範囲・帯の正確さ・採点チェックの具体性は未達。
- **性能の解釈**：全対象Overall=3、3答案の開発標本。4/6一致を一般的性能や理由の有用性の改善としない。1514が4に変わったことも、別の未マスク対照を新規実行していないため、マスク単独の因果効果とは断定しない。
- **比較条件**：保存済み6候補の検証はマスク単体。本実行はStage 1正本もv1.2へ変更しているため、v1.1との差をすべてマスクへ帰属させない。正本内の指示の併存も解釈上の限界である。

機械照合・実入力検査は`masking_tests.json`、`invariant_checks.json`、`source_and_quote_audit.json`、`stage3/mechanical_checks.json`。自然言語の根拠・内容判断は`content_review.json`と本報告で分ける。Codexの点検を人手評価や確定的な正解とは呼ばない。追加の評価LLM、形式修復、候補追加、連続したプロンプト調整ループは行っていない。

## 7. 次の優先事項

1. **Stage 1の根拠範囲を改善する。** 局所所見を保ち、1文から全体構成・語彙幅・全観点の程度まで広げない。構造化得点の正しさと、自由文中の得点/評価判断の正しさを別に照合する。
2. **Stage 3のルーブリック対応を検査する。** 実在する引用でも別の帯を説明していれば失敗とする。観点・帯・程度/頻度・観測判断を対応づけ、差を強引に正当化しない。
3. **マスクの役割判定と隔離を継続検証する。** 新しい履歴表現や復元表現を対照に追加し、対象自身の履歴参照や曖昧な帰属を救済しない。マスク成功を内容上の採用可能性と混同しない。
