"""Separate code display tests, paired 3B and full pipeline; provisional semantic review."""
import sys
sys.dont_write_bytecode=True
import run as r
r.configure()
fixed=r.read(r.OUT/'fixed_input.json');old=r.read(r.BASE/'stage3b_pipeline/rater_7/parsed.json');b=r.read(r.OUT/'stage3b_fixed/rater_7/parsed.json');c=r.read(r.OUT/'stage3b_pipeline/rater_7/parsed.json');a={eid:r.read(r.OUT/'stage3a'/eid.replace(':','_')/'parsed.json') for eid in r.TARGETS};g={eid:r.read(r.OUT/'stage3a'/eid.replace(':','_')/'mechanical_checks.json') for eid in r.TARGETS};h=r.read(r.OUT/'handoff/input_3b.json');ba=r.read(r.OUT/'stage3b_fixed/rater_7/assembly_result.json');ca=r.read(r.OUT/'stage3b_pipeline/rater_7/assembly_result.json');m=r.read(r.OUT/'run_manifest.json');req=r.read(r.OUT/'request_summary.json');tests=r.read(r.OUT/'A_display_tests.json')
reviews=[dict(key='1868:1::O1',full_supported=True,narrow_part_usable=True,judgment='概ね妥当（留保あり）',reason='is believe / have learnの形は実在し、Grammarとの関連と単文の限界が整合。明瞭さへの具体的影響は説明不足だが、全体頻度や数値帯は支持していない。'),dict(key='4902:1::O1',full_supported=False,narrow_part_usable=True,judgment='局所的な関係確認のみ使用可能',reason='引用に賛同理由を続ける明示的な関係は実在する。しかしsophisticatedを必要条件とする説明と、弱い・反復的という評価はこの2文だけでは十分に支持されない。')]
ratings=[dict(item='観測得点と妥当性の区別',judgment='悪化',reason='旧v1.3は観測3点と未検査範囲を分離したが、新Bはindeterminateなのにconsistent with the rubric、This supports the observed scoreと肯定。'),dict(item='比較帯・方向と見直し条件',judgment='改善確認できず',reason='Bは比較帯null・noneで機械的に整合するが、上方/下方の比較自体を選ばなかった。一般的なclear/unclear条件は3点が許容する一部の不成功と持続的破綻を区別しない。'),dict(item='最終引用・IDと具体性',judgment='同程度の未達',reason='旧版も最終引用なし。新Bは既知キー・index0・placeholder1個だが句点付きで独立文スロット契約に違反し、組み立て失敗。追加確認箇所も一般的。')]
r.save(r.OUT/'content_review.json',dict(evaluator='Codex provisional content evaluation; not human evaluation',observation_reviews=reviews,B_same_input_comparison=ratings,C=dict(assembly_quote_supports_recorded_band=False,indeterminate_consistent=False,null_comparison_prose_consistent=False,none_direction_prose_consistent=False,reason='C endorses Cohesion 2, attributes repetitive/mechanical criterion to band2 instead of band3, and discusses a higher band despite null/none.',pattern_supported=False,abstention_appropriate=True),issues=[dict(record_id='1868_1__K1',classification_supported=False,reason='Unlabeled score of 3 does not explicitly assert Vocabulary=3.'),dict(record_id='1868_1__K2',classification_supported=True,detected_dimensions=['Vocabulary'],missed_dimensions=['Phraseology']),dict(record_id='4902_1__K1',classification_supported=False,reason='Candidate explicitly states Overall=3, not Cohesion=3. Repetitive/mechanical wording is in official Cohesion3, not the claimed band2 description.')],generalization='Regression test on the same two targets only; general performance and supported-pattern cases untested.'))
rows=[]
for eid in r.TARGETS:
    for check in g[eid]['observation_checks']:
        o=a[eid]['observations'][check['index']];review=next(x for x in reviews if x['key']==eid+'::'+o['observation_id'])
        rows.append(dict(target_essay_id=eid,observation_id=o['observation_id'],mechanical_pass=check['pass_'],full_supported=review['full_supported'],narrow_part_usable=review['narrow_part_usable'],span_ids=';'.join(o['evidence_span_ids']),reason=review['reason']))
r.p.csvsave(r.OUT/'observation_results.csv',rows,list(rows[0]))
summary=dict(A_display_tests=dict(passed=tests['passed'],total=tests['total'],actual_model_calls=0,not_model_success=True),B=dict(assembly_pass=ba['pass_'],mechanical=r.read(r.OUT/'stage3b_fixed/rater_7/mechanical_checks.json'),direction=b['rubric_comparison']['comparison_direction'],comparison=b['rubric_comparison']['comparison_band_ref_id']),C=dict(generated_observations=2,passed_observations=2,targets_reached=2,targets_with_full_supported_observations=1,targets_with_usable_narrow_parts=2,generated_issues=3,quote_verified_issues=3,confirmed_issue_classifications=1,K2_Vocabulary_detected=1,K2_Phraseology_detected=0,K1_false_Vocabulary_conflict=1,assembly_pass=ca['pass_'],mechanical=r.read(r.OUT/'stage3b_pipeline/rater_7/mechanical_checks.json'),direction=c['rubric_comparison']['comparison_direction'],comparison=c['rubric_comparison']['comparison_band_ref_id'],pattern_status=c['pattern_status']),actual_model_requests=4)
r.save(r.OUT/'summary.json',summary)
old_jp='提示された証拠に基づくと、あなたの採点に一貫した傾向を確立するには証拠が不十分です。答案1868:1の代表所見は、この答案が文と段落をつなぐ移行表現と考えを使っていることを示しますが、答案全体の一貫性を証明するものではありません。記録されたCohesionの得点は3ですが、この得点がCohesion:3のルーブリック記述と整合するか判断するには証拠が不十分です。次の採点確認では、段落間の移行が段落内の移行と同じくらい明瞭で効果的か調べてください。観測帯と比較帯の違いは、考えのつながりが追跡可能か、論理的な順序に持続的な破綻があるかです。段落間の移行が明瞭で効果的なら判断を維持し、論理的な順序に持続的な破綻があれば再考してください。'
b_jp='あなたの採点判断に一貫した傾向を確立するには証拠が不十分です。ただし、役立つ所見として、この答案は文と段落をつなぐ移行表現を使っており、例えば[REPRESENTATIVE_EVIDENCE]です。これはCohesionの観測3点を支持しますが、帯との整合を判断するには証拠の範囲が狭すぎます。今後の採点では、段落間の移行が段落内と同じくらい明瞭で効果的か調べてください。移行が明瞭で効果的なら得点を維持し、不明瞭または効果的でなければ再考してください。'
c_template_jp='あなたの採点判断に傾向を確立するには証拠が不十分です。証拠はID 4902:1の答案のCohesionの観測2点を支持しますが、答案が上位帯の基準を満たすかまでは証明しません。[REPRESENTATIVE_EVIDENCE] この所見は最初の2文に限られ、答案全体の結束性を扱うものではありません。今後の採点では、他の移行表現も反復的なのか、より洗練された移行表現が他にあるかを調べてください。他の移行表現も反復的で洗練さに欠けるなら現在の得点を維持し、より洗練され多様であれば再考してください。'
c_jp=c_template_jp.replace('[REPRESENTATIVE_EVIDENCE]','答案4902:1の該当抜粋は「この引用に賛成する理由は、今の人々が自分自身であろうとしないからです」です。')
test4902=next(x for x in tests['cases'] if x['name']=='4902 exact opening-quote whitespace')['assembly'];req_table='\n'.join('| '+x['request']+' | '+str(x['prompt_tokens'])+' | '+str(x['output_tokens'])+' | '+str(x['json_valid'])+' | '+str(x['schema_valid'])+' |' for x in req)
report=f'''# Stage 3 v1.4 固定2答案での回帰検証

## 結果

新規モデル要求は計4件（3A×2、固定入力3B×1、通し3B×1）を事前設定どおり実行。旧結果は変更していない。

1. **両答案で意味的に使える所見があるか：部分的。** 両答案2/2に機械通過所見は届いた。1868のGrammar所見は概ね有用。4902は引用と賛同理由の明示的なつながりを確認できるが、所見全文の評価判断は未支持。完成した所見として概ね妥当なものを持つ答案は1/2、狭い局所部分が使える答案は2/2という区別を置く。
2. **引用・IDをコードで正確に挿入できたか：Cで1/1成功、Bで0/1。** GPU前の合成表示検証は15/15成功だがモデル成功に加算しない。Bは句点付きプレースホルダーで組み立てを拒否。Cは4902のindex1をそのまま引き、原文とIDを挿入した。ただしCの生テンプレートにもIDがあり、重複記述を避ける追加の契約は未達。
3. **比較帯・方向・見直し条件が合ったか：未達。** B・Cとも比較帯null/方向noneは機械的に2/2一致。ただしCは上位帯を述べ、内容上のnoneに反する。B・Cともindeterminateと観測帯の肯定が矛盾する。上下比較の実出力は0件なので、higher/lowerの内容成功率は評価不能。
4. **傾向を支持できたか：いいえ。** 両3Bのpatterns=[]は妥当。具体的な局所所見を伴う保留の入口はあるが、本文・基準との不整合があり、内容合格とは扱わない。

機械検査と意味評価を分けた。意味・問題分類の評価はCodexの暫定判断であり、人手評価ではない。これは固定2答案の既知失敗に対する回帰検証で、一般性能や傾向が支持される別案件の性能は未検証。

## 比較元・正本・事前固定

比較コミット `{r.COMMIT}` は実行前HEADと一致。比較元は `outputs/recsaver_stage3_v1_3_validation_20261121/`。fixed_input.json、区間表、prepared_3aの各input.jsonはバイト同一でコピー。Bの実input.jsonも比較元stage3b_pipeline/rater_7/input.jsonと同一内容・同一順序・同一バイトだった。

| 使用物 | SHA-256 |
|---|---|
| 固定元fixed_input.json | `{m['fixed_input_sha256']}` |
| Bの固定3B入力 | `{m['fixed_3b_input_sha256']}` |
| recsaver_03a_case_evidence_review_v1_4.txt | `{m['prompts']['a']['sha256']}` |
| recsaver_03b_integrated_feedback_v1_4.txt | `{m['prompts']['b']['sha256']}` |

正本実パスは `C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/prompts/en/` 以下。同名正本は各1件で、WSLの実読込パスと検索結果もmanifestに保存。原文区間表2件の元パス・ハッシュも保存。正本は `{{{{INPUT_JSON}}}}` だけを置換した。

モデルQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。vLLM0.6.6.post1、torch2.5.1+cu121、transformers4.48.3、RTX6000 Ada。全要求temperature0.2、top_p0.8、max_tokens5000、seed925847335。既定system・chat templateは比較元と一致。入力・出力の切り詰め、guided decoding、追加system、良い結果を選ぶ再生成なし。バッチ構成による完全なトークン再現性は保証しない。

| 要求 | 入力tokens | 出力tokens | 厳密JSON | 構造 |
|---|---|---|---|---|
{req_table}

全要求stop終了。Stage 1・2、マスク、採用条件の実行・変更は0件。意味評価を見て所見を修正・選別したり、3Bを再生成したりしていない。

## A：GPU前のコードによる表示検証

保存済みv1.3の代表キーとquotesを使った。v1.3に存在しないrepresentative_quote_indexとプレースホルダー付きテンプレートは明示した**合成検証データ**。A_display_tests.jsonに生成成功と別に保存し、actual_model_calls=0とした。15件の検証終了時刻はモデルEngineの初期化・生成開始より前。

代表キーから同じ所見を引き、ゼロ始まりquote_indexでexact quoteを取り、同じ所見のtarget_essay_idからIDを取る。別の引用へフォールバックしない。代表ありはplaceholder1個、なしは0個。未知キー、負数・範囲外・bool・小数・nullの不正index、重複/欠落placeholder、余計な句点、囲み引用符を拒否した。代表なしとindex1選択も検証した。

### 英語原文（4902の検証用組み立て文）

> {test4902['evidence_sentence']}

和訳：答案4902:1の該当抜粋は、作家エマーソンの「あなたを別の何かに変えようとする世界で自分自身でいることは最も偉大な達成だ」という引用に賛成する、という文です。

照合：引用符直後の空白を含む原文切り出しが保存され、quoteの文字列は入力と完全一致した。これはコードの表示成功であり、v1.3のモデルがindexやplaceholderを正しく出したこと、また引用が任意の主張を支持することを意味しない。

新モデルの原出力raw.txt、解析済みparsed.json/parsed_template.json、assembly_result.jsonとassembled_feedback.txtを分離した。Bの組み立て失敗ではfeedback_paragraph=null、assembled_feedback.txtは作成しない。テンプレートの句点削除等をして救済しない。

## B：同一入力の3B比較

3Aの変更を混ぜていない。旧v1.3と新v1.4は同じ6所見・同じ基準を受けた。旧代表は1868/Cohesion3、比較帯4。新代表は同じ観察キー・引用index0だが比較帯はnull、comparison_direction=none。

### 旧v1.3の最終段落：英語原文 → 和訳 → 照合

> {old['feedback_paragraph']}

{old_jp}

照合：原文引用が欠ける。観測3点と妥当性の未確定は区別していた。Cohesion:4を比較に選びながら、見直し条件を持続的な論理順序の破綻という下方の論点にしていた点が不整合だった。

### 新v1.4のモデル生成テンプレート：英語原文 → 和訳 → 照合

> {b['feedback_paragraph_template']}

{b_jp}

照合：代表キーとindex0は有効でplaceholderも1個だが、`such as [REPRESENTATIVE_EVIDENCE].` と文中に埋め込み、句点を付けた。正本の独立文スロット・句点なしという契約に違反するため組み立てを失敗とし、完成した最終段落は生成していない。原出力を修復せず、**Bの引用表示成功は0/1**。

explanation原文は “{b['rubric_comparison']['explanation']}”。和訳は「証拠は文と段落をつなぐ移行表現の使用を支持するが、答案全体の一貫性までは証明しません。観測3点はルーブリックと整合しますが、帯との整合を判断するには証拠が狭すぎます」。indeterminateなのに観測帯を肯定する矛盾が再発した。元の抜粋が主題提示であることから、文・段落を結ぶ移行表現の有効性までは確認できない。

比較帯null/noneは機械的に正しい。B本文には比較帯そのものへの言及もない。ただし特定の上下比較を選ばなかったので、指定比較帯に応じて見直し方向を改善したという成功には数えない。clear/effectiveなら維持、unclear/ineffectiveなら再考という条件は一般的で、3点が許容する一部の不成功と継続的な論理順序の破綻を区別していない。

| B比較項目 | 判定 | 根拠 |
|---|---|---|
{chr(10).join('| '+x['item']+' | '+x['judgment']+' | '+x['reason']+' |' for x in ratings)}

## C：3A v1.4 → 3B v1.4

3Aは各答案1回で1所見ずつを返し、合計2/2件が機械通過、対象2/2が3Bに届いた。ID、観点、区間、候補所属と原文スライスは一致。v1.3の6/6所見に対し件数は減ったが、件数自体を品質と扱わない。原文区間は再生成・正規化していない。

| 所見 | Codex暫定評価 | 根拠と限界 |
|---|---|---|
{chr(10).join('| '+x['key']+' | '+x['judgment']+' | '+x['reason']+' |' for x in reviews)}

### 1868の局所所見：英語原文 → 和訳 → 照合

> {a['1868:1']['observations'][0]['feature']}

和訳：この文には文法的な誤りがあり、is believeはis to believe、have learnはhave learnedとする形が必要です。

照合：選択E1868_1_P001_S003に両方の形が実在する。元観測Grammar=3はプログラムで添付したが、所見はその帯を支持せず、頻度や深刻さは単文から不明とする。明瞭さに影響するという説明は何が回復困難かを具体化していないため、その影響まで確定しない。訂正例の存在だけで採点妥当性は決まらない。

### 4902の所見：英語原文 → 和訳 → 照合

> {a['4902:1']['observations'][0]['scoring_relevance']}

和訳：効果的な結束性には、考えの間の明瞭で洗練された移行が必要です。この反復的で単純な移行は、考えをつなぐ洗練さの不足を示しています。

照合：The reason why...becauseの冗長さを局所的に検討する余地はあるが、明示的な賛同理由の関係は追える。洗練さを結束性の必要条件とする説明は、論理的な関係の成立や公式基準の観点と同じではない。反復や種類の不足をこの2文から答案全体へ広げない。v1.3の数値帯支持は3Aの所見から消えたが、未支持の評価基準は残った。

### 候補の得点矛盾の監査

| 既知検査点 | v1.3 | v1.4 |
|---|---|---|
| 1868/K2 Vocabulary=4への矛盾検出 | 0/1 | 1/1 |
| 1868/K2 Phraseology=4への矛盾検出 | 0/1 | 0/1 |
| 1868/K1をVocabulary3と誤認 | 0件（issue全省略） | 1件 |

K2の “consistent with the observed scores of 3 for both Overall and Traits”（OverallとTraitsの両方の観測3点と整合する）は実在する。VocabularyとPhraseologyの両方が4であるが、新版はVocabularyのみを検出した。既知2観点の検出は1/2で、完全ではない。

issueは3件生成され、候補引用・元観測値照合は3/3通過した。しかしCodexが分類を支持できた数値矛盾はK2の1/3件のみ。K1の観点不明のscore of 3はVocabulary3の直接表明ではなく、4902/K1の候補はOverall3と述べていてCohesion3とは述べない。後者のissue説明がCohesion2をrepetitive/mechanicalと説明する点も、公式Cohesion3の表現の誤帰属である。引用の実在と分類の妥当性は独立に記録した。

主実行では、機械通過issueから候補ID・分類・短い説明だけを3Bへ渡した。候補生文・issue引用・score_conflicts原文は渡していない。意味評価を見てこれらを除いたり直したりしていない。合成データで両Trait矛盾を検出・検査できたことは、本実行の検出率には加算しない。

### 通し3Bのモデル生成テンプレート：英語原文 → 和訳

> {c['feedback_paragraph_template']}

{c_template_jp}

### 組み立て後：英語原文 → 和訳 → 照合

> {ca['feedback_paragraph']}

{c_jp}

照合：コードは代表4902:1::O1のindex1を選択どおり使用した。該当原文は[150,243)のE4902_1_P001_S002で、空白・句読点・綴りを保持し、同じ所見からIDを取得した。引用とIDの正確な挿入はコードの成功1/1。モデルがこの原文を自由生成で正しくコピーした成功には数えない。生テンプレートにID4902:1がすでにあるため、IDをテンプレート内で別途書かないという正本の追加指示は未達である。

ただし引用は賛同理由の明示を示すのであって、Cohesion2を妥当と確定しない。explanationの “The evidence supports this score” と最終文の “The evidence supports the observed score of 2” はindeterminateと矛盾する。さらにrepetitive/mechanicalはCohesion3の公式文面にあり、観測2点の記述として扱うのは不正確。

comparison_band_ref_id=null、comparison_direction=noneなのに、explanation・テンプレートでhigher bandを述べ、reconsider_ifもより洗練され多様な移行なら再考という上向き条件にした。ラベルは2/2機械一致でも、この内容矛盾は防げなかった。公式Cohesion2で確認すべき論理順序の欠落や関係の追いにくさを、この引用から特定していない。一般的なsophisticationではなく、どの考えのつながりが読めるか・読めないかを確認する課題が必要。

3Bは両答案キーを挙げるが、同じ特徴と評価の関係を両答案から説明していない。両方Overall3という事実だけで傾向とは言えず、patterns=[]は妥当。ただし保留の周囲に未支持の個別採点妥当性の肯定があり、保留したことだけで内容改善とは扱わない。

## 公式Cohesionとの照合

| 帯 | 保存済み公式原文 | 見直しの論点 |
|---|---|---|
| 2 | {fixed['rubric']['scores']['2']['Cohesion']} | 論理的順序の欠落、関係の追いにくさ。 |
| 3 | {fixed['rubric']['scores']['3']['Cohesion']} | 限られた種類・一部の反復や機械的使用だけで下方再考しない。 |
| 4 | {fixed['rubric']['scores']['4']['Cohesion']} | 多様な結束表現を適切に使い関係を示すか。 |

BとCは入力・代表所見・観測帯が違うため、その差を3Bプロンプト単体の効果には帰属させない。Bのみが旧v1.3と同一入力の比較である。

## 機械検査・保存・限界

| 項目 | 結果 |
|---|---|
| GPU前の表示検証（合成） | 15/15、モデル0回 |
| 追加CPU検査（合成） | 10/10、モデル0回 |
| 新規要求の厳密JSON・構造 | 各4/4 |
| Cの3A所見通過・対象カバレッジ | 2/2・2/2 |
| Cのissue引用・元値照合 | 3/3（分類妥当性は別） |
| Bの組み立て | 0/1 |
| Cの組み立て | 1/1 |
| Bの主要機械検査 | 13/16、引用・ID表示・組み立てが失敗 |
| Cの主要機械検査 | 16/16（内容合格ではない） |
| null比較帯とnone方向の一致 | 2/2 |
| 実モデルのhigher/lower条件の内容評価 | 評価不能（両方null/none） |
| Cの追加テンプレートID非重複契約 | 0/1 |
| 原入力・区間・生成条件・原出力・組み立て不変性 | 50/50 |

追加のtemplate_and_content_flags.jsonはIDの直接コピーと内容矛盾候補を記録する。語句の出現だけで意味評価を自動確定しない。Cの主検査16/16は限定された機械条件の通過であり、追加契約と内容評価の失敗を含む総合合格ではない。

検査用の旧スキーマ対応コピーにテンプレート欄が余分に残る実装上の不具合をCPUテストで検出して修正した。実行時検査は*_generation_time.jsonへ保持し、修正版で派生検査を再計算した。raw.txt・parsed.json・モデル入力・引用選択・生成回数は不変。これは生成出力の自動修復ではない。修正前の生成コードハッシュと最終コードハッシュをmanifestに分けて保存した。

保存先は `outputs/recsaver_stage3_v1_4_validation_20261121/`。原入力・区間表、各要求raw/parsed/parsed_template、handoff、組み立て成功文または失敗null、機械検査、生成時検査、A表示検証、合成検査、暫定内容評価、summary、manifest、追加コード、README、レポートを保存した。比較元と正本は実行前後で不変。再点検・再実行手順はREADME.md。

次に直すべき点は、独立文スロットをモデルが違反した場合の明確な表示契約、観点が明示された数値主張だけを対象にする全Trait監査、比較方向と具体的な論理関係・多様性の証拠を結ぶ内容検査である。今回は各条件1応答のみの固定2答案検証で、一般性能は未検証。代表なしや上下方向はコードの合成検査のみで、実モデルでの分岐性能は測っていない。
'''
(r.OUT/'validation_report.md').write_text(report,encoding='utf-8')
print('A/B/C report, semantic review and counts saved')
