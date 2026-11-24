# 統合フィードバックの主張単位自己検証：1回の小規模パイロット

**次の比較へ進む目安：満たしたとは判定しない。プロンプトは再調整せず、このパイロットで終了。**

未達。Aは3/3群で表示できたが、Bは3群ともMarkdownコードフェンス付きで厳密JSON契約を満たさず、正常表示0/3群。新規2群のAには未支持主張が3/10件あり、修正対象は存在したが、Bの主張数・保持・改善効果は評価不能。診断目的の隔離解析でも3Cは3群とも初稿を変更せず、既知の段落末誤認も支持扱いした。

問いは「同じ統合初稿を主張ごとに根拠と照合すると、支持された所見を保持しつつ、根拠のない主張を減らせるか」。Aは直接統合、BはAの構造化判断に原文位置情報付き3Cを1回追加したもの。追加モデル呼び出しと追加位置情報の寄与は、この比較では個別に識別できない。

| 群 | A 未支持/全主張 | B 未支持/全主張 | 支持所見の同内容保持/A | 支持所見の置換 | Bの新規未支持 | B根拠付き局所所見 | B具体的確認点 |
|---|---|---|---|---|---|---|---|
| known | 3/7 | NA | NA（A分母=0） | NA | NA | NA | NA |
| contrast | 2/6 | NA | NA（A分母=0） | NA | NA | NA | NA |
| limited | 1/4 | NA | NA（A分母=0） | NA | NA | NA | NA |

既知ペアは動作確認専用で新規群の効果集計から除外。新規2群だけではA=3/10、Bは未支持件数・全主張数ともNA。正常なA/B対比較は0/2群で、改善の有無を評価できなかった。Aには修正対象があったが、改善を確認できた群は0群であり、処理失敗を未支持主張の削減や新設0件と数えない。Aの完全支持所見・正の傾向は各群0件で、部分的に支持される命題は別記した。分母0は保持成功の実証と解釈しない。少数群の記述的な件数であり、一般性能・採点者間のズレの改善は結論づけない。

## 選定と比較の固定

比較元コミット `2d49a6f4b635cedece5fdf25eda9d2ac9c48cb3d`、成果物 `outputs/recsaver_stage3_v1_6_baseline/`。
選定固定時刻は `2026-11-24T06:09:09.842442+09:00`。全ての新しい3A・3B・3C出力より前にselection_manifest.jsonを保存。

| 群 | 採点者 | 答案 | 選定理由 |
|---|---|---|---|
| contrast | rater_7 | 8699:1, 873:1 | 同一rater_7、Cohesion=2対3。8699にはHowever/Rather than等の接続と断片化、873にはFirstly/Secondly/Thirdlyと理由・例示があり、局所の接続特徴と本人得点を対照できる。得点差の原因や採点規則の同定はできない。 |
| limited | rater_7 | 2016:1, 3650:1 | 同一rater_7、両答案Cohesion=3、Grammar=2。著者の言葉への反対と列挙・理由を含み、局所所見は点検可能だが、共通特徴・得点だけから採点傾向を支持する対照がない。 |

全4答案は本人のraw得点・採点者列・本文と照合した。開発用対象・履歴との重複は各false。保存採用プールでの過去露出はあり、未使用の最終評価群とは呼ばない。旧採用プールの検証基準は現行v1.2と同一ではない。既存verifiedかつOverall再構成一致を採用根拠として再利用し、候補解釈・候補監査自由文はモデルへ渡していない。Stage 1/2再実行なし。

既知群はrater_7の1868:1・4902:1。保存済み3B実入力・解析JSON・最終文をバイト同一で再利用し、3Cだけ新規1回。過去の失敗ラベル・正解例・修正例は3C入力へ追加しなかった。

## 実装と機械検査

3A/3B正本はv1.6、3Cはユーザー指定英文をそのまま保存。{{INPUT_JSON}}のみを置換し、旧3B schema_version=1.5を維持。実際に使用した3本のファイル名・SHA-256は次のとおり。

| 正本 | SHA-256 |
|---|---|
| prompts/en/recsaver_03a_case_evidence_review_v1_6.txt | `c4012bcf6f22b084dda239bc9b8988407d9ea55a763607800aa84e00704826e2` |
| prompts/en/recsaver_03b_integrated_feedback_v1_6.txt | `ceea422f7c58ab6e6f73f94b49fcdff06421f575b262325793f98f12c2f9c82b` |
| prompts/en/recsaver_03c_verify_integrated_claims_v1_0.txt | `3cd0042513dea5a4290833ee9d13bf3eb912acdedf876bb8401b109a6b9abdd7` |

モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、既存snapshot・vLLM・量子化・GPU設定を再利用。全要求temperature=0.2、top_p=0.8、max_tokens=5000、seed=925847335、既定system・チャットテンプレートを維持。実行環境・sampling・テンプレート・実入力は機械検査で照合。

既存v1.6の3Aゲート・スコア/公式基準の付加・3Bスキーマ/参照/表示処理を再利用。新群についてだけ、旧ランナーの「両方Overall=3」という固定説明を正確な中立の2答案説明に置き換えた。既知群の入力は変更しない。3Cではsource_excerptsとsource_positionをコードで復元し、upstream_interpretationという提案の解釈と分離した。Unicodeの[start,end)、段落ID、段落/答案境界、および境界と接するかの真偽を、未正規化の原文と照合した。位置一致からthesis/conclusionという機能を自動認定しない。

3Cのrevised_decisionは既存3Bのスキーマ・同群の引用index・観点・本人得点・公式参照を検査してから、同じコードで表示する。候補にない引用/別群の観測キー/不正index/追加の位置フィールドは拒否。3Cの自由文の意味は機械検査で保証せず独立内容評価へ回す。不正ならBは処理失敗で、Aへの差し替えなし。

生成前の19検査は通過。事後の機械検査は131/131。これは位置・参照・不正出力の拒否を含む制御の成功であり、3CのJSONや内容の成功を意味しない。正常表示はA=3/3群、B=0/3群。厳密JSON成立は6/9要求で、3Cはすべて失敗。生出力は変更せず保存し、成立した6要求だけに正式parsed.jsonがある。3Cのdiagnostic_only.jsonは外側コードフェンスを除く診断用の隔離解析であり、正式parsed.jsonやB表示には昇格させていない。実際の新規要求は9（3A×4、3B×2、3C×3）、上限11以内。再生成・追加自動採点モデル・SLM改稿なし。

| 要求 | 入力tokens | 出力tokens | 厳密JSON | スキーマ | 終了 |
|---|---|---|---|---|---|
| groups/known/stage3c | 2883 | 770 | False | False | stop |
| groups/contrast/stage3a/8699_1 | 5137 | 260 | True | True | stop |
| groups/contrast/stage3a/873_1 | 5381 | 413 | True | True | stop |
| groups/limited/stage3a/2016_1 | 3743 | 191 | True | True | stop |
| groups/limited/stage3a/3650_1 | 6231 | 228 | True | True | stop |
| groups/contrast/A | 2313 | 259 | True | True | stop |
| groups/limited/A | 1970 | 235 | True | True | stop |
| groups/contrast/stage3c | 2702 | 537 | False | False | stop |
| groups/limited/stage3c | 2188 | 545 | False | False | stop |

3Cの3応答はいずれも先頭がMarkdownのコードフェンスで、JSON解析はline 1 column 1で失敗した。全要求stop終了で、長さによる切り詰めではない。3C応答を修復してBに採用することは今回行っていない。

モデルロード中に旧群専用説明へ気づき、推論開始前に初期化を1回中断した。出力破棄0・推論0で、履歴と証拠はinitialization_interruption.jsonに保存。モデル呼び出し後の修正や選別ではない。

## 評価方法と限界

review_blind.csv / .jsonに、比較条件名と3C自身のclaim_checksを伏せた出力表を作成。原文・本人得点・公式基準を参照し、Codex（実装を担当した同じassistant）が別工程で暫定レビューした。ただし実装者は条件と既知例を知っているため、真の条件盲検は実現できなかった。3Cの判定を正解や件数に使っていない。独立レビューはreview_judgments.json、対応表はreview_key.json、保持・置換の比較はretention_reviews.json。

主張の単位は独立に照合できる実質的命題。同義の反復は1件とし、複合所見を分割。傾向保留・帯の判断も各1件。コードが忠実に表示する引用・ID・得点・公式記述の単なる転載は機械検査へ分離し、純粋な将来の指示は主張数へ入れず確認点の有用性として判定する。contradictedとinsufficientを未支持に含める。分母や単位の詳細はreview_protocol.json、全命題の英文・和訳・出典・理由はclaim_comparison.csv。

## known：A/B比較

Aは保存済み直接統合を再利用。Bはコードフェンス付き応答で厳密JSON不成立。診断上も、3CはS004の段落末という誤りをsupportedとし、初稿を変更していない。

### A：代表所見の英文原文と和訳

> The essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph, showing a clear focus on the importance of continuous learning.

和訳：答案は明確な主張で始まり、段落末で中心的な考えを繰り返し、継続学習の重要性に明確な焦点を当てている。

> Review the transitions between paragraphs to ensure they maintain the same focus on the importance of continuous learning.

和訳：段落間の移行を見直し、継続学習の重要性という同じ焦点を保っているか確認する。

> Check if the writer maintains the connection and develops the argument consistently throughout the essay.

和訳：書き手が答案全体を通じて結び付きを保ち、一貫して議論を展開しているか確認する。

**選択引用の原文と位置**

`1868:1` / `E1868_1_P001_S001` / Unicode [0,77) / 段落 `E1868_1_P001` [0,765) / at_paragraph_end=False

> The main piece to improve your skills is during the process of keep learning.

`1868:1` / `E1868_1_P001_S004` / Unicode [368,610) / 段落 `E1868_1_P001` [0,765) / at_paragraph_end=False

> I strongly agree with the words that Author Ralph Waldo Emerson wrote, people that have got the title of professional and keep being successful in their daily are the ones that are still adding productive information to their life and career.

**独立に分解した実質的主張**

| ID | 英文命題／和訳 | 暫定判定 | 原文・基準との照合 |

|---|---|---|---|

| K1 | The essay starts with a thesis about improving skills through continued learning.<br>答案は、学び続けることで技能を向上させるという主張で始まる。 | supported | S001[0,77)は答案先頭で、技能向上と継続学習の関係を主張する。本文の文脈でもその立場が展開されることを原文で照合した。 |

| K2 | The selected reiteration occurs at the end of the paragraph.<br>選択された主張の繰り返しは段落末にある。 | contradicted | 選択S004=[368,610)、第1段落=[0,765)。同段落にS005[611,765)が続く。段落末ではない。 |

| K3 | The essay shows a clear focus on the importance of continuous learning.<br>答案は継続学習の重要性に明確な焦点を当てている。 | insufficient | 両抜粋に学習という関連話題があることは支持されるが、選択外を含む答案としての明確なfocusの評価をこの2文だけから確立できない。『選択2文で関連する話題を繰り返す』という局所記述へ人が直して数えることはしない。 |

| K4 | The observations do not establish the essay's overall coherence.<br>所見は答案全体の一貫性を確立しない。 | supported | 5509文字の答案の第1段落内2抜粋のみであり、全体の移行・構成を評価していない留保は適切。 |

| K5 | The observation establishes cohesion within the first paragraph.<br>所見は第1段落内の結束性を示す。 | insufficient | only the cohesion within the first paragraphは全体留保と同時に段落内結束性を確定する読みを生む。選択2文の関連テーマと、段落内の構成・接続を評価したことは区別すべきで、間にあるS002/S003や後続S005を当該所見の引用として用いていない。 |

| K6 | The available cases do not establish a generalizable repeated scoring behavior.<br>利用できる事例では一般化できる反復的採点行動は確立できない。 | supported | 局所の学習話題と、別答案の引用への賛同理由では特徴の扱いを統制して比較できない。共通得点・共通観点だけを正の傾向にしていない。 |

| K7 | The selected evidence cannot establish whether Cohesion:3 is appropriate.<br>選択根拠だけではCohesion:3の妥当性は確立できない。 | supported | 公式基準は構成・結束表現の全体的な使い方を含む。局所2文からその程度を判定せずindeterminateとしている。 |

傾向の保留：採点傾向の保留は妥当。記録得点と局所的な共通話題だけでは、採点での特徴の扱いが比較可能とは言えない。

局所所見と確認点：冒頭の学習に関する主張と、選択2文に学習の話題があることは確認できるが、段落末位置と全体的な焦点・段落内結束性まで述べた所見全体は支持されない。段落間の話題接続を調べる行動は具体的な確認として残る。

### B：処理失敗

厳密JSON契約が不成立のため正式なB最終文はない。Aへの差し替えは行わず、Bの未支持件数・全主張数・保持・新設はNAとする。

**採用しない診断用の3C修正案（Bの表示文ではない）**

> The essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph, showing a clear focus on the importance of continuous learning.

和訳：答案は明確な主張で始まり、段落末で中心的な考えを繰り返し、継続学習の重要性に明確な焦点を当てている。

外側コードフェンスを診断用にだけ除いた隔離解析ではrevised_decisionはAと完全一致。正式parsed.jsonやB表示に昇格させていない。この文をBの比較件数・保持数に使わない。

**保持・置換・新規未支持主張**

Aの代表所見全体は位置誤認を含むので完全支持の所見には数えない。Aで支持された4命題と確認行動はあるが、正式なB出力がないため保持・置換・新規未支持主張・有効な確認点の保持は評価不能。診断用のunchangedな構造を正式なBとして数えない。

Aの完全支持所見=0、支持された正の傾向=0、支持命題=4。Bへの同内容保持・置換・新規未支持・局所所見/確認点の保持は、Bが処理失敗のためすべてNA。

## contrast：A/B比較

新規群。Aの文法誤り一般は支持されるが、主語・動詞一致と冠詞という種類の診断は支持されない。Bは厳密JSON不成立。診断用の修正案もAと同一で、正式な比較結果には採用しない。

### A：代表所見の英文原文と和訳

> The sentence contains grammatical errors, including subject-verb agreement issues and incorrect use of articles.

和訳：この文には、主語と動詞の一致の問題や冠詞の誤用を含む文法的誤りがある。

> Other sentences in the essay to check for similar grammatical errors, particularly subject-verb agreement and article usage.

和訳：答案内のほかの文を読み、同様の文法的誤り、特に主語と動詞の一致や冠詞の使い方を確認する。

> The frequency and impact of grammatical errors on the overall clarity and coherence of the essay.

和訳：文法的誤りの頻度と、答案全体の明瞭さ・一貫性への影響を確認する。

**選択引用の原文と位置**

`8699:1` / `E8699_1_P003_S001` / Unicode [30,228) / 段落 `E8699_1_P003` [30,271) / at_paragraph_end=False

> Today We are constantly that technology can affect us some day and there will be nothing we can do about it, even if someone dedicates his lives trying to find the problem We will not ever found it.

**独立に分解した実質的主張**

| ID | 英文命題／和訳 | 暫定判定 | 原文・基準との照合 |

|---|---|---|---|

| C1 | The selected sentence contains grammatical errors.<br>選択文には文法的誤りがある。 | supported | E8699_1_P003_S001[30,228)のWe will not ever found itでは、modal willの後に原形findではなくfoundを用いる。一般的な文法的問題があるという範囲なら原文で確認できる。 |

| C2 | The selected sentence has subject-verb agreement issues.<br>選択文には主語と動詞の一致の問題がある。 | contradicted | We are、technology can affect、someone dedicates、We willは主語に対応する形であり、will ... foundは主語との一致ではなく助動詞後の動詞形の問題。文に別種の誤りがあることは、この種類の診断を支持しない。next_checkのsimilarも同じ前提の反復なので追加1件には数えない。 |

| C3 | The selected sentence has incorrect article use.<br>選択文には冠詞の誤用がある。 | insufficient | 選択文のthe problemや無冠詞のtechnologyから冠詞誤用は特定できない。どの冠詞がなぜ不正かの直接根拠がない。文の不自然さ全般でこの具体的診断を補えない。 |

| C4 | This one-sentence observation does not establish overall grammatical accuracy.<br>1文の所見だけでは答案全体の文法的正確さは確立できない。 | supported | 代表の根拠は本文1476文字のうち[30,228)のみ。全体の頻度・影響を確定しない留保は適切。 |

| C5 | The available observations do not establish a consistent cross-essay scoring pattern for the same feature.<br>利用できる所見から同じ特徴に対する複数答案共通の採点傾向は確立できない。 | supported | 異なる局所文と記録得点を並べただけでは、比較可能な誤りが採点にどう反映されたかの関係を確定できない。意図・因果規則の断定はなく、保留は妥当。 |

| C6 | The local evidence is insufficient to judge whether the recorded Grammar:2 band is appropriate.<br>局所根拠だけでは記録されたGrammar:2の妥当性は判断できない。 | supported | Grammar:2のMany errors in grammar and usageという全体的な程度は1文から評価できない。indeterminateと比較帯なしは根拠範囲に収まる。 |

傾向の保留：保留は妥当。8699のGrammar=2と873のGrammar=3だけでは、同じ種類・程度の特徴が採点でどう扱われたかを特定できない。選定意図はCohesionの対照だったが、実際の代表はGrammarとなり、Cohesionに関する正の採点傾向の評価材料になったとは言えない。

局所所見と確認点：will not ever foundはmodal willの後の形として非標準で、文法の局所的問題は実在する。しかしその種類を主語・動詞一致と冠詞へ広げた所見全体は支持されない。ほかの文で頻度・影響を調べる行動は具体的だが、特に一致・冠詞という着目点の前提はこの引用に裏づけられない。

### B：処理失敗

厳密JSON契約が不成立のため正式なB最終文はない。Aへの差し替えは行わず、Bの未支持件数・全主張数・保持・新設はNAとする。

**採用しない診断用の3C修正案（Bの表示文ではない）**

> The sentence contains grammatical errors, including subject-verb agreement issues and incorrect use of articles.

和訳：この文には、主語と動詞の一致の問題や冠詞の誤用を含む文法的誤りがある。

外側コードフェンスを診断用にだけ除いた隔離解析ではrevised_decisionはAと完全一致。正式parsed.jsonやB表示に昇格させていない。この文をBの比較件数・保持数に使わない。

**保持・置換・新規未支持主張**

Aには支持された一般的な文法問題という局所命題と、適切な傾向・帯の留保があるが、代表所見全体は複合誤診を含む。正式なBの最終文がないので、保持・置換・新規未支持主張はNA。0件削減や0件新設として扱わない。

Aの完全支持所見=0、支持された正の傾向=0、支持命題=4。Bへの同内容保持・置換・新規未支持・局所所見/確認点の保持は、Bが処理失敗のためすべてNA。

## limited：A/B比較

新規群。Aは標準的なyou will never growを非標準動詞形と誤診。Bは厳密JSON不成立。診断用の修正案もAと同一であり、形式上の問題だけを外せば改善したと推測する根拠もない。

### A：代表所見の英文原文と和訳

> The sentence contains a nonstandard verb form: 'you will never grow.'

和訳：この文には『you will never grow』という非標準の動詞形が含まれている。

> Other sentences for similar grammatical issues, particularly the use of verbs and auxiliary verbs.

和訳：ほかの文にも同様の文法的問題がないか、特に動詞と助動詞の使い方を確認する。

> The frequency and type of grammatical errors.

和訳：文法的誤りの頻度と種類を確認する。

**選択引用の原文と位置**

`2016:1` / `E2016_1_P002_S001` / Unicode [32,149) / 段落 `E2016_1_P002` [32,377) / at_paragraph_end=False

> Author Ralph Waldo wrote, "unless you try to do something beyond what you have already mastered, you will never grow.

**独立に分解した実質的主張**

| ID | 英文命題／和訳 | 暫定判定 | 原文・基準との照合 |

|---|---|---|---|

| L1 | 'You will never grow' is a nonstandard verb form.<br>『you will never grow』は非標準の動詞形である。 | contradicted | S001[32,149)のwillは助動詞、growは原形で通常の組合せ。neverもその間に置ける。原文の周辺に別の不自然さがあっても、この指摘は支持されない。similar grammatical issuesという後続指示の同じ前提は1件にまとめる。 |

| L2 | The observation does not establish how frequent grammatical errors are throughout the essay.<br>所見だけでは答案全体の文法誤りの頻度は確立できない。 | supported | 本文1999文字の一部[32,149)だけを引用しており、頻度の留保は適切。元の具体的誤診を正当化はしない。 |

| L3 | The observations do not establish a consistent cross-essay scoring pattern for the same feature.<br>所見から同じ特徴に対する複数答案共通の採点傾向は確立できない。 | supported | rawの両答案Grammar=2という共通性だけでは傾向を確定できず、実際に渡された局所所見も2016のGrammarと3650のCohesionという異なる観点。反復した同じ特徴の扱いを比較できないため、保留は妥当。 |

| L4 | The local evidence does not establish whether the observed Grammar:2 band is appropriate.<br>局所根拠だけでは観測Grammar:2の妥当性は確立できない。 | supported | この抜粋からMany errors in grammar and usageという答案全体の程度を評価できず、indeterminateと別帯なしは適切。 |

傾向の保留：保留は妥当。2016と3650は同じGrammar=2でも、局所特徴の同等性や、採点者がどう重視したかの対照がない。

局所所見と確認点：you will never growは通常のmodal will＋never＋原形growであり、この動詞形の誤りという所見は誤診。ほかの文で動詞・助動詞の頻度と種類を点検するという手順は観察可能だが、この引用を『同様の誤り』の例とは扱えない。

### B：処理失敗

厳密JSON契約が不成立のため正式なB最終文はない。Aへの差し替えは行わず、Bの未支持件数・全主張数・保持・新設はNAとする。

**採用しない診断用の3C修正案（Bの表示文ではない）**

> The sentence contains a nonstandard verb form: 'you will never grow.'

和訳：この文には『you will never grow』という非標準の動詞形が含まれている。

外側コードフェンスを診断用にだけ除いた隔離解析ではrevised_decisionはAと完全一致。正式parsed.jsonやB表示に昇格させていない。この文をBの比較件数・保持数に使わない。

**保持・置換・新規未支持主張**

Aの代表所見は誤診なので完全支持所見0。頻度・傾向・帯の保留3命題は支持されるが、正式なBがないのでその保持は評価不能。原文に存在する3650の反対理由という候補へ切り替えたとは扱わない。

Aの完全支持所見=0、支持された正の傾向=0、支持命題=3。Bへの同内容保持・置換・新規未支持・局所所見/確認点の保持は、Bが処理失敗のためすべてNA。

## 既知ペアの回帰確認

3Cが段落末の誤りを検出したか：False。

3Cの生出力中のclaim_checksは、段落末を含む複合主張を分割せずsupportedとし、reasonにもat the end of the paragraphを再掲。コードが渡したS004=[368,610)、paragraph_end=765、at_paragraph_end=falseと矛盾する。独立原文照合でもS005[611,765)が続くため、検出できたとは判定しない。外側コードフェンスを診断目的で隔離解析したが、正式parsed.jsonやB表示は作成せず、修復成功として扱わない。

**採用しない診断用の3C自己判定の英文（正解として使わない）**

> The observation key '1868:1::O1' with quote indices [0, 1] supports the claim that the essay starts with a clear thesis statement and reiterates the main idea at the end of the paragraph.

和訳：観測キー1868:1::O1の引用index [0,1]は、答案が明確な主張で始まり、段落末で中心的な考えを繰り返しているという主張を支持する。

独立照合：これはS004のend=610に対するparagraph_end=765、at_paragraph_end=falseと食い違う。3C自身のsupported判定をそのまま正解としなかった。3群とも診断用revised_decisionはAと同一であったが、これを正式なBの保持成功・改善なしの対比較件数へ算入しない。

最終文での変化：正式なB最終文なし（処理失敗）。診断上のrevised_decisionはAと完全一致で、言い換え・代表変更・削除はいずれもなし。。動作確認：False。この結果は新しい群の効果集計に含めない。

## 追加コスト

| 群 | A/B共通の新規3A | Aの新規3B | Bの追加3C | 段階別の観測経過時間・tokens |
|---|---|---|---|---|
| known | 0 | 0 | 1 | c: 91.59s, in=2883, out=770 |
| contrast | 2 | 1 | 1 | a: 60.32s, in=10518, out=673; b: 31.81s, in=2313, out=259; c: 64.11s, in=2702, out=537 |
| limited | 2 | 1 | 1 | a: 60.46s, in=9974, out=419; b: 31.90s, in=1970, out=235; c: 64.16s, in=2188, out=545 |

群の段階別時間は各要求の開始からバッチ結果保存までの観測経過時間。同時バッチ内の専用GPU時間ではなく、群間・段階内で単純加算しない。実際のバッチ壁時計とモデル読込込みの初回コストはbatch_costs.jsonへ分離。中断初期化は168.22秒以下（停止後の記録までを含む上限）で別計上し、推論要求数へ足さない。cost_summary.jsonに方式ごとの追加要求・入力tokens・出力tokens・処理時間を保存。

| 実際のバッチ | 壁時計（秒） | モデル初期化込み |
|---|---|---|
| groups/known/stage3c | 380.89 | True |
| groups/contrast/stage3a/8699_1, groups/contrast/stage3a/873_1, groups/limited/stage3a/2016_1, groups/limited/stage3a/3650_1 | 61.09 | False |
| groups/contrast/A, groups/limited/A | 32.18 | False |
| groups/contrast/stage3c, groups/limited/stage3c | 64.43 | False |

既知群3Cの応答生成区間は91.59秒で、初期化込みのバッチ壁時計は380.89秒。新規2群の追加3Cバッチは64.43秒。Aの新規3Bは2群同時に32.18秒で、3Aの61.09秒はA/B共通の前処理要求。専用GPU時間や単独実行時の速度は推定しない。

## 終了

次の比較に進む目安は満たしていない。残る障害は、3Cの厳密JSON契約の不成立と、主張を独立に分けず上流の解釈を追認して位置情報との矛盾を見落としたこと。今回はここで終了し、プロンプトの自動再調整・再生成を行わない。形式問題だけを解消すれば内容上の改善が得られるとは結論しない。

この1回のパイロットで終了した。結果を見てプロンプトを再調整せず、追加のモデル判定・再生成・SLM改稿は実施していない。
