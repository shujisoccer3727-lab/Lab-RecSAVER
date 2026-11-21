# 英文プロンプトv1.1 有効性検証

2026-11-20 JST。比較元コミット：`078ae7e912a42e4f3c2f97b5ecd9ed752a583052`。比較元：`outputs/recsaver_prompt_v1_0_initial_20261118/`。

**結論：Stage 2のコード枠なしJSONは改善した。一方、Stage 1の得点分離と根拠を超える説明、Stage 2の汚染時停止は改善を確認できなかった。6候補すべてが事前点検で除外され、採用0件。Stage 3の初回評価には進めなかった。**

## 条件と実行範囲

モデルは既存のQwen/Qwen2.5-32B-Instruct-GPTQ-Int4（同一キャッシュsnapshot、GPTQ Marlin）、WSL2/Conda qwen3、vLLM 0.6.6.post1、RTX 6000 Ada。temperature=0.2、top_p=0.8、context=32768、生成上限Stage 1=6500、Stage 2=1200、Stage 3=5000。旧版と同じchat template、tokenizerの既定system文を使用し、追加指示・guided decoding・出力修復は使わなかった。

対象はrater_7の1514:1、1868:1、4902:1、各2候補、同一履歴各3件。Stage 1の実入力JSONは旧版と完全一致。seedは旧版の`SHA256(20261118:stageN:candidate_id)`割当を維持し、別seed候補の追加・都合のよい出力が出るまでの再生成はない。診断の両版にも同じ候補由来seedと同一入力を使用した。別バッチでのGPUスケジューリング差や確率的独立は保証しない。

正本は`prompts/en/recsaver_01_reference_rationale_v1_1.txt`、`recsaver_02_overall_reconstruction_v1_1.txt`、`recsaver_03_integrated_feedback_v1_0.txt`。診断だけStage 2 v1.0も使用。リポジトリ内を同名検索し、各ファイルは選択した`prompts/en/`の1件のみだった。実パス・SHA-256前後値は`run_manifest.json`に記録。英語本文を変更せず、`{{INPUT_JSON}}`だけをJSONシリアライズした値で置換した。正本・比較元全成果物の不変性を検査した。

再利用した構造検査はv1.0の必要キー・型・一部値/ID検査であり、完全な意味検査ではない。v1.1もschema_version=1.0で同じ構造のため、この部分は変更しなかった。観測得点の全項目保持、得点分離、履歴IDの役割は別途検査した。

Stage 1の6件と、Stage 2診断A/B/C×2版の6件を新規生成した。主実行のStage 2・3は未実施。通信再試行・形式再試行・途切れ・context超過はいずれも保存済み12呼出しで0件。比較元のStage 1/2出力は再生成していない。

## 1. Stage 1：同じ6候補の比較

### 形式、得点転記、分離

|共通基準の指標|v1.0|v1.1|判定|
|---|---|---|---|
|厳密JSON・既存構造検査|6/6|6/6|同程度|
|観測Overall＋全Traitsの完全保持|4/6|6/6|改善|
|値が誤って転記された候補|0/6|0/6|同程度|
|Traits項目が欠落した候補|2/6（計4項目）|0/6|改善|
|対象への番号付き帯・範囲の適用|6/6|6/6|改善なし|
|観測対象得点の直接開示を明確に確認した候補|0/6|少なくとも3/6|悪化|
|対象自身を履歴支持例として使用|0/6|1/6|悪化|

直接開示は「観測された対象Overall」と明示して値を記した場合を保守的に数えた。番号付き帯を対象へ当てはめることは、それだけで別の仕様違反として全件に記録した。履歴得点・ID・原文中の数字・通常の定性的特徴を数値があるだけで違反にはしていない。「直接開示未確認」は、安全であることの証明ではない。

v1.0の保存値はconfirmed_leak=5/6だったが、そこでは番号付き帯の適用と直接開示を混合し、4902/K2の複数帯は一意の観測値を復元できないため漏洩未確認とした。今回の共通基準では**直接開示と帯適用を分離**し、4902/K2も後者に含めたため帯適用は6/6になる。旧成果物は書き換えていない。この差は新たな生成上の悪化ではなく、判定項目・仕様の差である。

v1.1では1514/K1、1868/K1、4902/K1のdecision_explanationに、対象の“observed Overall score of 3”が残った。他の候補にもevaluative_interpretation、rubric_connection、uncertainty等で数値帯を適用した文がある。rubric_connectionだけの検査では見逃す。全score_free_analysisを確認した原文・JSON pointerは`preflight_review.json`、機械的な疑いは`common_mechanical_audit.json`に分離保存した。

### 引用と内容

|引用照合|v1.0|v1.1|
|---|---|---|
|完全一致|27/33（81.8%）|17/20（85.0%）|
|空白・改行だけの差|5/33|3/20|
|空白以外の語句・句読点等の差|1/33|0/20|
|全引用が完全一致した候補|2/6|4/6|

引用数と選択区間が変わったため、85.0%への変化を理由品質の一般的改善とはしない。1514/K1の3/3一致には、**対象を履歴例として誤帰属した引用**も含む。文字列の実在と、履歴の証拠としての適格性は別である。4902/K2の履歴引用は両版とも2件で空白差が残った。差の分類は同じルールで再計算し、原出力は変更していない。

両版とも各候補のhistory_patternsは1件、target_evidenceは1件。v1.1でも1つの対象引用で複数観点・答案全体の構成・語彙幅を説明する傾向が残った。v1.1はexplanatory_statusをpartly_supportedに変えたが、6/6でinsufficient_evidenceが空。1868の2候補と4902/K1ではuncertaintyもlimitationsも空で、部分支持というラベルだけでは具体的な保留になっていない。

|答案・候補|内容の総合比較（Codex暫定）|主な根拠|
|---|---|---|
|1514:1/K1|悪化|観測得点の直接開示に加え、対象1514:1を履歴支持例に混入|
|1514:1/K2|同程度|全体品質への拡張、数値帯、高品質な高得点例を反例扱いする問題が継続|
|1868:1/K1|悪化|転記は改善したが、1文から全体構成・語彙幅を断定し、不足の記述が消えた|
|1868:1/K2|悪化|転記は改善したが、1文からの一般化と判断保留の欠落|
|4902:1/K1|悪化|直接開示、全観点をminor errorsと一括し、Cohesionの帯対応も不整合|
|4902:1/K2|同程度|元の2/3帯の混同文は消えたが、3点帯への適用・抽象的説明と空白差が残存|

これは各論点を合わせた暫定内容比較であり、独立の人手評価ではない。以下に改善した部分と残った問題を、指定順で示す。

### 例1：1514:1 / K1 — 分離と履歴支持の悪化

**英語原文（v1.0）**： “The essay demonstrates a mix of effective and less effective language use, with some errors in syntax and cohesion, which aligns with the rubric descriptors for Overall score 3.”

**英語原文（v1.1）**： “The target essay demonstrates controlled organization and a minimally adequate range of vocabulary, consistent with the observed Overall score of 3.”

**和訳（v1.0）**：「この答案は効果的な言語使用とそれほど効果的でない言語使用が混在し、統語と結束性にいくつか誤りがあり、Overall 3点のルーブリック記述と一致する。」

**和訳（v1.1）**：「対象答案は統制された構成と最低限十分な語彙の幅を示し、観測されたOverall 3点と整合する。」

**照合**：旧新版とも`score_free_analysis/decision_explanation`。新出力のhistory_patterns/H1/support/1はhistory_essay_id=`1514:1`で、対象の本文・本人得点を履歴支持として使用した。実入力の履歴は217:1、1440:1、8745:1のみ。引用自体の実在が、この役割の誤りを解消するわけではない。短い冒頭引用から答案全体の構成や語彙幅まで説明している点も残る。

**判定**：分離・根拠の扱いは悪化。旧版も帯適用で失敗していたが、新版は観測値を直接明示し、対象自身による循環的な履歴支持も加わった。

### 例2：1868:1 / K1 — 転記は改善、過剰な説明は未改善

**英語原文（v1.0）**： “The essay demonstrates a generally controlled organization, a sufficient range of vocabulary, and an evident use of phrases, but with some noticeable repetitions and misuses.” / “The rubric for a score of 3 in Cohesion, Vocabulary, and Phraseology aligns with this evaluation.”

**英語原文（v1.1）**： “The essay demonstrates a generally controlled organization and a sufficient range of vocabulary.” / “The essay uses a range of cohesive devices and demonstrates a sufficient range of vocabulary, which aligns with the rubric for an Overall score of 3.”

**和訳（v1.0）**：「答案は全体として統制された構成、十分な語彙の幅、明らかな句の使用を示すが、目立つ反復と誤用もある。」「Cohesion、Vocabulary、Phraseologyの3点のルーブリックは、この評価と一致する。」

**和訳（v1.1）**：「答案は全体として統制された構成と十分な語彙の幅を示す。」「答案は多様な結束装置を使い、十分な語彙の幅を示しており、Overall 3点のルーブリックと一致する。」

**照合**：旧版は“keep learning”を含む2文、新版は “The main piece to improve your skills is during the process of keep learning.” の1文がT1の全引用。この1文だけでは答案全体の構成、結束装置の多様性、語彙幅は示せない。本人のVocabulary/Phraseologyはどちらも4。新出力は全6Traitを正しく保存し、旧版K1のSyntax欠落を解消した。また、Vocabulary/Phraseologyを3点帯に当てる旧文は消えた。

しかし、Phraseologyの所見と反復の具体的な論点自体も消え、局所的反復という確認可能な所見を残した適切な判断保留にはなっていない。新版はuncertainty、limitations、insufficient_evidenceを空にし、全体品質の断定と対象Overall=3の適用を残した。語彙基準の帯対応を正しく説明し直したという意味ではない。

**判定**：観測得点の保存精度は改善。元の誤ったTrait帯対応は削除されたが、狭い証拠からの広い説明は未改善で、具体的な局所所見・保留を失った点を含め内容総合は悪化。

### 例3：4902:1 / K2 — 元の混同文は消失、別の帯適用と基準の誤対応が残る

**英語原文（v1.0）**： “The rubric for scores 2 and 3 indicates that communication is impeded by language inaccuracies and that there are many sentence structure problems.”

**英語原文（v1.1）**： “The essay demonstrates a mix of structural and linguistic features with some errors and generally controlled organization, which aligns with the rubric's description of an Overall score of 3.”

**和訳（v1.0）**：「2点と3点のルーブリックは、言語の不正確さで意思伝達が妨げられ、文構造上の問題が多いことを示す。」

**和訳（v1.1）**：「答案は構造的・言語的特徴の混在、いくつかの誤り、全体として統制された構成を示し、Overall 3点のルーブリック記述と一致する。」

**照合**：保存ルーブリックのOverall 2は “Communication impeded in many instances”、Overall 3は “Communication is impeded ... in some cases.”。Syntax 2は “many sentence structure problems”、Syntax 3は “some apparent errors in sentence formation”。旧文は帯と観点の違いをまとめすぎていた。

新出力はこの文を削除したが、対象3点帯への適用が残った。またobserved_score_alignmentのSyntax説明は “an appropriate use of a variety of syntactic structures with occasional errors” を本人Syntax=3と整合させた。これは保存ルーブリックのSyntax 4の “Appropriate use of a variety ... occasional errors” に近い記述で、3側との差を説明していない。元の誤った意味妨害の断定を、具体的で慎重な意味分析に置き換えたわけでもない。

履歴引用8722:1の冒頭は両版とも “Dear Principle, If our school ...”。入力は`Dear Principle,\r\n\r\nIf our school ...`（原改行を可視化）。8630:1引用も両版で空白差が残り、K2の完全一致は両版2/4で同程度。

**判定**：元の2/3帯・意味妨害の混同文自体は消えたが、得点分離・基準対応・原文保持の解決は確認できず、内容総合は同程度。これは明示的な判断保留への改善とは扱わない。

### 残った別の失敗：4902:1 / K1

旧版は “the rater tends to prioritize cohesion and syntax.” と本人の優先度を根拠不足のまま述べた。新版は “The essay demonstrates a mix of minor errors in cohesion, syntax, vocabulary, phraseology, grammar, and conventions.” と全観点を一括して軽微な誤りとし、Cohesionでは “generally controlled organization ... limited in type” を本人Cohesion=2と整合させた。訳はそれぞれ「採点者は結束性と統語を優先する傾向がある」「答案は結束性、統語、語彙、句、文法、表記に軽微な誤りが混在する」。優先度の断定をやめたことだけでは、全観点をminorとする範囲・程度の過剰説明は解消しない。Cohesionの一般に統制された構成という記述は3側で、2側のpartially developedとの差が未説明。旧新版の別々の誤りを区別する。

## 2. Stage 2：同一入力でのプロンプト比較

診断A/Bは旧版保存済みStage 2入力を変更せず使用した。Cは全v1.1候補が帯適用違反だったため、許可された**診断用に作成した対照**である。対象・全履歴本文/得点・ルーブリックを保持し、対象の正確な1文に対する局所的・定性的なSyntax所見を与えた。候補の自動修復やモデル生成出力とは扱わず、本実行・採否に一切使っていない。作成手順と原文は`diagnostic_control/input.json`と`preflight_review.json`にある。

|入力|v1.0の厳密形式|v1.0の診断読取のみ|v1.1の厳密形式|v1.1のstatus/Overall|判断|
|---|---|---|---|---|---|
|A：対象Overall帯が明示|失敗・コード枠あり|estimated / 3|通過|estimated / 3|形式は改善、汚染停止は未達|
|B：対象へ2/3帯を適用|失敗・コード枠あり|estimated / 3|通過|estimated / 3|形式は改善、v1.1の厳しい契約への適合は未達|
|C：帯なしの診断対照|失敗・コード枠あり|insufficient_information / null|通過|insufficient_information / null|形式は改善。履歴得点や原文中の数字だけでは汚染扱いしない|

厳密JSONは旧版0/3→新版3/3、コード枠は旧版3/3→新版0/3。他の構造・ID検査は新版3/3通過。A/Bの期待はcontaminated_input、Overall=null、問題箇所をreference_analysis_issuesに示すことだったが、**新版の期待達成は0/2件で、2件とも推定を続け、issuesも空**。数値を返せたことを成功とはしない。

旧版A/Bも診断的に読んだstatusでは停止0/2。Bについて旧版との差が仮に出てもv1.1で厳しくした契約への適合と呼ぶべきだが、今回はその適合自体が得られなかった。

### 診断Aの英語原文と和訳

v1.0： “The essay demonstrates a mix of effective and less effective language use, with some errors in syntax and cohesion, which aligns with the rubric descriptors for Overall score 3.”

v1.1： “The essay demonstrates a mix of effective and less effective language use, with some errors in syntax and cohesion, aligning with the rubric descriptors for Overall score 3.”

旧訳：「答案は効果的な言語使用とそれほど効果的でない言語使用が混在し、統語と結束性にいくつか誤りがあり、Overall 3点のルーブリック記述と一致する。」

新訳：「答案は効果的な言語使用とそれほど効果的でない言語使用が混在し、統語と結束性にいくつか誤りがあり、Overall 3点のルーブリック記述に沿っている。」

入力の`reference_analysis/decision_explanation`と`target_evidence/0/rubric_connection`に数値帯がある。新正本はその例を停止対象として明記しているが、実出力はその内容を要約して推定に使った。問題はJSON形式ではなく、推定前の入力契約チェックが実行されていないこと。issues=[]は問題箇所の説明もないことを示す。

### 診断Cの判断の妥当性

新版原文： “The local evidence does not establish how the rater balanced all dimensions, and no defensible feature-to-score relationship has been established from the supplied history.”

和訳：「局所的な証拠だけでは採点者が全観点をどう釣り合わせたかは分からず、提示された履歴から、特徴と得点の間に擁護可能な関係も確立されていない。」

Cは “This shows that with hard work you can accomplish any goal and letting yourself grow.” という実在する1文の非並列構造と、意図の回復可能性を指摘した。全体評価や本人の重みづけを支持する比較は作っていないため、insufficient_informationは保守的には妥当な読み。ただし本文・ルーブリック・履歴の他の部分を使えば推定可能かは今回の1対照で確定しない。**汚染の偽陽性を起こさなかったことと、推定能力が十分であることは分ける。** 新版はused_history_essay_idsに3履歴を列挙したが、どの比較が判断に効いたかは説明していない。

旧版のコード枠内読取は`diagnostic_reading.json`に、枠除去という変更とともに保存した。strictなparsed/resultとは別であり、主比較の形式通過・採用へ加えていない。実装側の形式制約による追加生成は行っていない。

## 3. v1.1本実行の流れと統合可否

|段階|件数・分母|
|---|---|
|Stage 1生成候補|6/6|
|Stage 1厳密JSON・既存構造検査|6/6|
|Stage 2事前点検通過|0/6|
|Stage 2本実行|0件（通過候補0件）|
|Stage 2本実行の厳密JSON通過|0/0：評価不能|
|有効推定|0/0：評価不能|
|Overall一致|有効推定0/0：評価不能|
|採用候補|0/6（0%）|
|採用された異なる対象答案|0/3（0%）|
|Stage 3|未実施。異なる採用答案0件で、必要な2件に届かず|

不通過理由は番号付き対象帯の適用6件。そのうち少なくとも3件は観測対象得点の明示もあり、1件は対象自身を履歴支持例として使用していた。理由は重複を許して記録し、足し合わせて6件超の候補数とはしない。内容の良否ラベルを追加の採否条件にはしていない。

Stage 2本実行リクエストは0件なので、実際に呼んだ本実行targetの得点分離を実証したとは言わない。コードの構築経路ではtargetをID/本文のみにし、observed_score_alignmentを渡さない。診断A/B/Cの実リクエストでもこの構造を確認した。`invariant_checks.json`はStage 1の6入力と診断の3ペアに関する検査通過を保存する。

Stage 3正本は変更していないが、受け入れられた2答案を用いる生成・本文引用・ルーブリック比較・次回採点チェックの初回評価はすべて未実施（`stage3/skip.json`）。今回の結果をStage 3の成功/失敗や改訂効果とは呼ばない。

## 4. 解釈の限界

- 全対象の観測Overallが3である。同じ数値を再構成しただけで、理由の有用性、得点帯全体の性能、本人の実際の判断への忠実性は主張できない。
- Stage 1の版間比較は同じ対象/seedだが、生成テキストの変化による証拠選択の差もある。引用率の上昇だけで内容改善としない。結果はこの固定6候補での観測に限る。
- 同一入力診断の形式改善はStage 2プロンプト単体の比較として解釈できる範囲があるが、各入力1回ずつで一般化できない。Cは候補由来ではなく、狭い局所根拠の診断対照である。
- 内容判定はCodexの暫定意味判断。独立した人手評価や追加LLM評価APIではない。機械照合、機械的疑い、原文点検の判定を分離した。
- 旧版の保存済みconfirmed_leakと今回の帯/直接開示の分類は異なる。比較表は今回の共通基準で両版を再点検した結果である。
- 未使用の最終確認用標本は確保できておらず、旧case_manifestの保留答案は今回も入力・生成に使っていない。

## 5. 次に直すべき点（最大3件）

1. **Stage 1の情報分離と証拠の役割を優先する。** 対象得点を見せた説明から、数値を含む全フィールドが後段へ漏れている。履歴パターンに対象自身を入れた循環も検出した。次はscore-free出力の全フィールド検査と、許された履歴IDへの帰属を明示する限定改訂・実装検査を検討する。自動で数値を消して救済した出力をプロンプト単体の成功として数えない。
2. **Stage 2の汚染チェックを推定から分けて検証する。** JSON契約の改善は維持し、A/Bのような同一入力を固定して、問題フィールドを特定してnullで止めるかを独立に確認する。プロンプト変更だけで保証せず、必要なら上流の決定的な入力検査を別条件として比較する。
3. **Stage 1の主張を引用範囲へ制限し、基準と観測を分ける。** 1文から全体構成/語彙幅を述べず、局所的な反復や文形成の所見は残す。裏付けのない評価関係は具体的な不足として保留する。Cohesion/Syntaxの2/3/4側記述を、本人得点を正当化するために混同しない。

採用に届いていないため、Stage 3を同時に改訂することは既定にしない。今回以外の自動調整ループや候補追加は行っていない。
