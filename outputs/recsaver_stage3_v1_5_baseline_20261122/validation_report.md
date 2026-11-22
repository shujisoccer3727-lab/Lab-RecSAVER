# Stage 3 v1.5：統合手法比較に進む最低ラインの判定

## 判定

**今回は未達。基準方式として確定しない。追加生成・自動調整は終了した。**

| ユーザー指定基準 | 合否 | 根拠 |
|---|---|---|
| A | 未達 | 4902の賛同理由の明示は支持されるが、1868の唯一の生成所見は第1段落中の文を結論扱いし、opening/closingから全体のfocusへ広げる。確認可能な冒頭主題の部分はあるが、生成所見単位では局所根拠に収まらない。 |
| B | 合格 | 選択index0/1の原文、同じ所見の1868:1、元Cohesion=3と公式Cohesion:3を正確に表示。原文一致と、その全主張を支持するかは別。後者の結論位置の誤りはCで不合格。 |
| C | 未達 | pattern=nullとindeterminateは妥当で、別帯や得点支持の矛盾はない。しかしtextual_findingのessay concludesが原文位置に反し、根拠を超える評価が最終文へ残った。段落間接続を点検するという確認課題はあるが、この誤りが合格を妨げる。 |

Aは生成所見を単位に判定した。1868の「冒頭で継続学習を主張する」という部分は確認できるが、所見全文に結論位置の誤認と全体のfocusの説明が混在する。人がその部分を削って新たな所見にすれば通せる、という救済は主結果に数えない。確認可能な断片は両答案2/2、根拠範囲に収まった生成局所所見がある答案は4902のみ1/2と区別する。Bの表示合格は、引用が結論に関する主張まで支持するという意味ではない。

実行は3A各答案1回と通し3B1回、計3要求。固定入力3Bの追加比較は0回。誤った位置づけが3Aから3Bへ引き継がれたことを原文で直接追えるため、切り分け用の追加モデル呼び出しは不要と判断した。文章の好み・監査網羅性・pattern生成件数を理由に不合格にしたのではない。

内容評価はCodexによる暫定判断で、人手評価ではない。機械検査と区別して保存した。固定2答案の既知例による回帰検証であり、一般性能を示さない。

## 固定元・正本・設定

比較コミット `1a0015a865b210a084ef08e9d0017f967eedc5de` は実行前HEADと一致。比較元は `outputs/recsaver_stage3_v1_4_validation_20261121/`。

| 使用物 | SHA-256 |
|---|---|
| fixed_input.json | `dca75b64bfdcd05c49ecbc50560529337073e32846ffaff682d378a80ca27b0e` |
| recsaver_03a_case_evidence_review_v1_5.txt | `1813e147c76a8c46585187b30e7d7a972a90a23188939f651ac000cfc10574f8` |
| recsaver_03b_integrated_feedback_v1_5.txt | `eacaf6257f8860d00b3359297d669c38240533893aa717dde4ac1b34107367da` |

正本実パスは `C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/` 以下。WSLで読んだパス・同名検索結果（各1件）もmanifestに記録した。原文区間表2件は保存済み表をバイト同一で再利用し、各ハッシュ・元パスをmanifestに保存。正本は `{{INPUT_JSON}}` だけを置換した。Stage 1・2、マスク、採用条件は変更・再実行していない。

モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。既存vLLM0.6.6.post1・torch2.5.1+cu121・transformers4.48.3、RTX6000 Adaを使用。各要求temperature0.2、top_p0.8、max_tokens5000、seed925847335で前回と同じ。既定system・chat templateも一致。新しいsystem指示・guided decoding・出力修復・出力選別の再生成なし。全要求stop終了、切り詰めなし。GPU実行順序によるトークン単位の完全再現性は保証しない。

| 主要求 | 入力tokens | 出力tokens | 厳密JSON | 構造 |
|---|---|---|---|---|
| stage3a/1868_1 | 11314 | 296 | True | True |
| stage3a/4902_1 | 4145 | 202 | True | True |
| stage3b/rater_7 | 1837 | 274 | True | True |

既存Engineを再利用。変更点は3Aの入力から候補文・得点を外したこと、候補監査の隔離、3Bの構造化判断とコード表示である。プロンプト文面単体の効果を測る実験ではない。

## 3Aと候補監査の分離

3Aの実入力はtarget_essay_id、target_text、evidence_spans、dimension_namesのみ。候補・観測点・公式基準・監査自由文は渡していない。対象ごとに区間ID、観点、所見IDを検査し、原文スライスからquotesを復元した。2/2所見が原文照合を通り、両答案2/2が3Bに届いた。復元した4区間の原文と位置はrestored_quotes.jsonへ保存した。

3Bの実入力はrater_id、accepted_target_ids、verified_observations、rubric_entries、evidence_limitationsだけ。観測点と基準は元データから添付し、候補監査自由文は混入していない。同一答案の複数引用は独立した複数答案として数えない。

候補得点の監査は決定的な別経路。明示的な “scores of 3 for both Overall and Traits” を各観点に照合し、1868/K2でVocabulary=4とPhraseology=4の2/2不一致を記録した。観点不明のscore of 3をVocabularyに自動帰属させないため、K1への誤ったVocabulary数値矛盾は0件。この結果はモデル3Aによる検出成功ではなく、保存済み候補に対するルールの回帰確認である。網羅的な意味監査とは主張しない。監査の未検出だけを単独の不合格理由にもしていない。

## Aの内容点検：英語原文 → 和訳 → 本文との照合

### 4902:1：局所所見は確認できる

> The essay explicitly links the author's agreement with the quote by providing a reason.

和訳：答案は、引用に賛成する理由を示すことで、筆者の賛同を引用と明示的に結び付けています。

選択区間は引用導入のE4902_1_P001_S001と、The reason why i agree...becauseで始まるE4902_1_P001_S002。双方を選び、賛同理由という関係を実際に追える。scoring_relevanceは考えの接続と理由提示をCohesionに関連付ける。頻度や答案全体での一貫性は未確定とし、数値帯を支持していない。ユーザーの例を固定正解として当てはめたのではなく、今回の生成主張を選択原文と照合した。

### 1868:1：部分的な確認と、所見単位での未達

> The essay begins with a clear thesis statement in span E1868_1_P001_S001, and it is reinforced with a concluding statement in span E1868_1_P001_S004. The thesis statement introduces the main idea that continuous learning is essential for skill improvement, and the concluding statement reiterates the importance of learning new things to grow as a professional.

和訳：答案はS001の明確な主張で始まり、S004の結論文でそれを補強しています。主張は、技能向上には継続学習が不可欠だという中心的な考えを導入し、結論文は専門家として成長するために新しいことを学ぶ重要性を繰り返しています。

原文位置との照合:

| 区間 | 段落 | Unicode位置[start,end) | 正確な原文 |
|---|---|---|---|
| E1868_1_P001_S001 | E1868_1_P001 | [0, 77) | The main piece to improve your skills is during the process of keep learning. |
| E1868_1_P001_S004 | E1868_1_P001 | [368, 610) | I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career. |

S001が継続学習という主題を提示することは確認できる。S004も学び続ける専門家に言及するが、第1段落内[ 368, 610 )にある。答案全長は5509文字、段落候補は12件。さらに同じ第1段落にはS004の後にE1868_1_P001_S005がある。したがって答案の締めくくりでも、第1段落の末文でもない。2文に関連する主題が現れることと、opening/closingが全体のfocusを保証することは別である。limitationで全体評価を保留しても、この位置・機能の誤認自体は修正されない。

## B：コード表示・出典と意味的支持を分離

GPU実行前、保存済みv1.4引用を使う11件の表示・参照検査を通した。新しい構造化判断フィールドは合成データと明記し、旧モデルの成功に加算していない。空白保持、代表なし、不正キー・負数/範囲外/bool/小数/空/重複index、非隣接帯を検査した。不正キーやindexを別引用で救済しない。

本実行の代表は1868:1::O1、quote_indices=[0,1]。両quoteは同じ所見から引き、IDも同じ所見から取得。元Cohesion=3とCohesion:3の公式記述を参照した。indeterminate時は固定の “This evidence alone does not establish whether that band is appropriate.” を表示。比較帯はnullで、方向はコード上none。別帯も比較条件も表示していない。

原文はそのまま保持し、引用が句点で終わる場合に外側の句点を足さない。今回の2引用と公式基準は句点を含むので、引用本文を変えずに重複句点を避けた。コードの参照・表示検査は8/8通過した。ただし、この成功は結論に関する主張を支持するという意味ではない。

## C：構造化判断と最終文

モデルのtextual_finding原文:

> The essay begins with a clear thesis statement and concludes with a statement that reinforces the central theme of continuous learning.

和訳：答案は明確な主張で始まり、継続学習という中心的な主題を補強する文で締めくくられています。

照合：このconcludesは、引用位置と矛盾する。3Aの誤認を3Bが狭めず継承した。固定のindeterminate文は得点の記録と帯の妥当性を分けるが、引用を超えた文書位置の評価を正当化しない。これがCの不合格理由である。

### コードで組み立てた最終文：英語原文

> A scoring pattern cannot be established from these cases. The provided observations do not establish a consistent pattern of scoring behavior across multiple essays. Each observation highlights a specific feature of cohesion but does not provide enough evidence to infer a broader pattern in the rater's scoring behavior. In essay 1868:1, the relevant excerpt is “The main piece to improve your skills is during the process of keep learning.” In essay 1868:1, the relevant excerpt is “I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career.” The essay begins with a clear thesis statement and concludes with a statement that reinforces the central theme of continuous learning. The recorded Cohesion score is 3. The official descriptor for Cohesion:3 is “Organization generally controlled; cohesive devices used but limited in type; Some repetitive, mechanical, or faulty use of cohesion use within and/or between sentences and paragraphs.” This evidence alone does not establish whether that band is appropriate. This observation does not establish the overall coherence of the essay or the effectiveness of the transitions between paragraphs. Next inspect: The transitions between paragraphs and the consistency of the argument to assess further cohesion. Check: The effectiveness of transitions and the consistency of the argument.

### 和訳（原文の誤りを修正しない）

これらの事例から採点傾向を確立することはできません。提示された所見は、複数答案にまたがる一貫した採点行動の傾向を示していません。各所見は結束性の特定の特徴を取り上げますが、採点者のより広い採点行動の傾向を推定する十分な証拠はありません。答案1868:1の該当抜粋は「技能を向上させる主な要素は、学び続ける過程にあります」です。答案1868:1の別の該当抜粋は「私は作家エマーソンの言葉に強く賛成します。専門家という称号を得て日々成功し続ける人々は、自分の生活や仕事に有益な情報を加え続けている人々です」です。この答案は明確な主張で始まり、継続学習という中心的主題を補強する文で締めくくられています。記録されたCohesionの得点は3です。Cohesion:3の公式記述は「構成は全般に統制されている。結束表現は使われるが種類は限られる。文や段落の内部または間で、反復的、機械的、または不適切な結束表現の使用がいくらかある」です。この証拠だけでは、その帯が妥当かは判断できません。この所見は、答案全体の一貫性や段落間移行の有効性を示すものではありません。次に確認するのは、さらに結束性を評価するための段落間移行と議論の一貫性です。移行の有効性と議論の一貫性を確認してください。

### 原文・観測値・公式基準との照合

表示順は、傾向の保留理由→ID・引用・所見→観測点・公式基準・判断範囲→次の確認、である。観測Cohesion=3は正しい。公式Cohesion3は構成が全般に統制され、結束表現の種類が限られ、一部の反復・機械的・不適切な使用があることを許容する。原文の主題提示と継続学習への言及はその観点を考える手掛かりになるが、答案全体の構成やその帯の妥当性を示す証拠ではない。その点を固定文で保留したことは適切である。

pattern_status=insufficient_evidence、pattern=nullは妥当。同じOverall3や、異なる答案にCohesion所見があることだけでは「特徴と評価の関係」の共通性は確立できない。別帯は選ばれていないので、上下方向と条件の内容評価は対象外で、分母0なら評価不能とする。比較帯がないのに別帯へ言及する矛盾や、観測帯を積極的に支持する表現は今回の構造化判断にない。

next_checkは段落間の移行を見る場所と、つながりの有効性・議論の一貫性という確認内容を示す。より精密な箇所指定の余地はあるが、その文章の好みや詳細度を別の不合格理由にはしない。今回の決定的な障害は、明確に誤った結論位置の主張が最終文に残ったこと。

## 集計と記録

| 項目 | 結果 |
|---|---|
| 主モデル要求 | 3/3実行、追加固定3B 0回 |
| 厳密JSON・構造 | 各3/3 |
| 3A原文照合通過 | 2/2所見、2/2答案 |
| 所見全体が根拠範囲に収まる局所所見を持つ答案（Codex暫定） | 1/2 |
| 確認できる局所部分がある答案 | 2/2（主結果を人手で修正していない） |
| 表示の参照・構造検査 | 8/8 |
| 選択した引用と原文・IDの一致 | 2/2 |
| 代表観点の観測点・公式基準参照 | 各1/1 |
| 候補監査の既知K2不一致 | 2/2観点（別経路） |
| 入力・監査隔離・原出力・表示の不変性 | 45/45 |
| 最低ライン | A未達、B合格、C未達 → 不合格 |

原入力、原出力、復元引用、最終文、原文位置、機械検査、暫定内容評価、判定を `outputs/recsaver_stage3_v1_5_baseline_20261122/` に保存した。raw.txt/parsed.jsonは変更せず、最終文は別ファイル。比較元と正本は前後でハッシュ不変。コードと実行条件はmanifest、再点検手順はREADMEに記録。baseline_decision.jsonのaccepted_as_baselineはfalseで、合格済みの基準方式として登録していない。

## 最小修正は1件のみ

位置・機能の主張（結論・末尾など）を原文の段落/オフセットで裏付けられる場合だけ許可し、裏付けがなければ選択文の内容だけを述べるよう、3Aと3Bの所見を局所範囲に限定する。今回は変更・再生成しない。

この修正を今回の出力へ適用したり、再実行して結果を選び直したりしない。既知例の原因が追跡できているため、追加3B比較も行わない。

## 次の比較群の選定条件（準備メモのみ）

評価傾向を支持する比較材料のある群は、同一採点者の異なる答案2件以上で、同じ観点の比較可能な特徴と評価の仕方を結ぶ原文根拠、さらに解釈を支持・反証する対照を持つこと。同じ得点・同じ特徴だけを支持材料にしない。候補の重複は独立答案に数えない。

保留が妥当な群は、個別の局所特徴は確認できるが、観点・特徴の比較ができない、対照が足りない、複数の評価解釈が残る群とする。個別所見と追加確認を残せるかを評価する。選定は出力を見る前に条件化し、方式間では同じ検証済み所見・観測値・基準を固定する。

今回は新しい答案群の選定や新たな統合手法の実装へは進んでいない。基準方式は未確定であり、一般性能も未検証。
