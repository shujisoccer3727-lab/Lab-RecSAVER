"""Japanese report, literal final-feedback translations and provisional content review."""
import sys
sys.dont_write_bytecode=True
import run as r
from collections import Counter
fixed=r.read(r.OUT/'fixed_input.json');old=r.read(r.BF/'parsed.json');b=r.read(r.OUT/'stage3b/rater_7/parsed.json');a={eid:r.read(r.OUT/'stage3a'/eid.replace(':','_')/'parsed.json') for eid in ['1868:1','4902:1']};h=r.read(r.OUT/'handoff/input_3b.json');summary=r.read(r.OUT/'handoff/audit_summary.json');m=r.read(r.OUT/'run_manifest.json');req=r.read(r.OUT/'request_summary.json')
ratings=[dict(item='① ID・出典の正確さ',judgment='改善',evidence='旧版の履歴8722:1の対象反例への混入がなくなり、3Bのキー・帯・引用の出典はすべて入力集合に一致。4902の引用不一致は修復せず除外。ただしissueは引用一致を通っただけで問題分類の妥当性は別。'),dict(item='② 引用と主張の対応',judgment='改善（限定的）',evidence='最終段落は1868:1の実在引用とIDを伴い、主題提示という局所所見と全体評価の未確定を残した。旧版の語彙幅・構成の断定を縮小したが、3A O2の語彙4点支持、3Bのgenerally controlled organization等は1文では未支持。'),dict(item='③ 傾向の判断または保留',judgment='改善',evidence='支持不十分な旧patternを生成せず、insufficient_evidence・patterns=[]。通過所見は1答案だけなので2独立答案の支持条件を満たさず、保留は妥当。主題提示の個別所見と追加確認が残り、空出力ではない。'),dict(item='④ 基準との対応と見直しの具体性',judgment='同程度',evidence='観測Cohesion:3・比較Cohesion:2のID対応は正確で、retain/reconsiderの別欄がある。一方、1文から構成や結束表現の種類を評価し、limited devicesを再考条件にする問題が残る。確認する追加箇所も具体性不足。')]
obs_reviews=[dict(key='1868:1::O1',judgment='部分的に支持',reason='継続学習を主題として提示する文であることは確認可能。文間・段落間の結束や答案全体の3点妥当性は示さない。'),dict(key='1868:1::O2',judgment='所見の一部が過大',reason='key/professionals/recognition/masterの語があるのは事実だが、1文から十分な語彙幅・Vocabulary 4の妥当性を説明できない。直後のlimitationとも緊張する。'),dict(key='1868:1::O3',judgment='部分的に支持',reason='母親が学び続ける具体例は見える。ただし一般論から例への移行をいうには前段が必要で、原文では育児例は引用より前に導入済み。2文をsingle sentenceと呼ぶ不正確さもある。')]
r.save(r.OUT/'content_review.json',dict(evaluator='Codex provisional semantic/content judgment, not human evaluation',ratings=ratings,observation_reviews=obs_reviews,issue_review=[dict(record_id='1868_1__K1',judgment='断定不可',reason='consistent with a score of 3はOverall 3を指す読みがあり、Vocabulary 3の直接表明とは限らない。'),dict(record_id='1868_1__K2',judgment='実在する矛盾を部分的に検出',reason='OverallとTraitsがともに3という記述に対しVocabulary 4を指摘。Phraseology 4も矛盾するが言及しなかった。'),dict(record_id='4902_1__K1',judgment='分類と説明に問題',reason='minor errorsとOverall 3の記述だけでCohesion 2との数値矛盾とは断定できない。some repetitive/mechanicalの表現は公式Cohesion 3に属し、2の説明として扱うのも不正確。')],overall='Procedure partially improved provenance and grounded abstention; semantic support and band interpretation remain unresolved.',generalization='Known failure retest on the same two essays only. Performance on another case with a supported pattern is untested.'))
rows=[]
for eid,v in a.items():
    gate=r.read(r.OUT/'stage3a'/eid.replace(':','_')/'mechanical_checks.json')
    for c in gate['observation_checks']:rows.append(dict(target_essay_id=eid,observation_id=c['observation_id'],pass_=c['pass_'],distinct_evidence_locations=c['distinct_evidence_locations'],exclusion_reasons='; '.join(c['reasons'])))
r.p.csvsave(r.OUT/'observation_results.csv',rows,list(rows[0]))
metrics=dict(stage3a_requests=2,stage3a_strict_json=sum(x['json_valid'] for x in req if x['request'].startswith('stage3a')),generated_observations=summary['generated_observations'],passed_observations=summary['passed_observations'],excluded_observations=summary['excluded_observations'],accepted_target_count=2,targets_with_passed_observations=len({o['target_essay_id'] for o in h['verified_observations']}),generated_issues=sum(len(v['source_analysis_issues']) for v in a.values()),passed_issues=summary['issues_passed'],excluded_issues=summary['issues_excluded'],rubric_entries=len(h['rubric_entries']),stage3b_requests=1,stage3b_strict_json=r.read(r.OUT/'stage3b/rater_7/result.json')['json_valid'],pattern_status=b['pattern_status'],patterns=len(b['patterns']))
r.save(r.OUT/'summary.json',metrics)
req_table='\n'.join('| '+x['request']+' | '+str(x['prompt_tokens'])+' | '+str(x['output_tokens'])+' | '+str(x['json_valid'])+' | '+str(x['schema_valid'])+' | '+x['finish_reason']+' |' for x in req)
refs='\n'.join('| '+e['rubric_ref_id']+' | '+e['descriptor']+' |' for e in h['rubric_entries'])
old_jp='どちらもOverall 3点だった二つの対象答案の証拠に基づくと、全般に統制された構成と十分な語彙の幅を持つ答案には3点が付けられているように見えます。代表的な判断は答案「1868:1」によって支えられており、この答案は十分な語彙の幅と全般に統制された構成を示しています。Vocabularyのルーブリックとの比較は、観測された4点と整合しています。今後の採点では、答案で使われている語彙の幅を調べ、十分な幅と広い幅を区別してください。これが判断の維持または再考を支えるでしょう。'
new_jp='所見に基づくと、採点者が答案をどう評価するかについての傾向を確立するには証拠が不十分です。例えばID 1868:1の答案では、「The main piece to improve your skills is during the process of keep learning.」（技能を向上させる主な要素は、学び続ける過程にあります）という文が答案の中心的な主題を提示し、答案の結束性に寄与しています。ただし、この1文では答案の結束性を十分に評価するだけの証拠にはなりません。結束性の観測得点は3で、これはCohesion:3のルーブリック項目と整合しますが、追加の文を確認しなければ、この得点を上げるべきか下げるべきかは未確定です。次の採点確認では、追加の文が中心的な主題を一貫して支え、さまざまな結束表現を使っているかを調べるべきです。これは判断の維持または再考に役立ちます。'
q1=a['1868:1']['observations'][0]['quotes'][0];o2=a['1868:1']['observations'][1];issue=a['1868:1']['source_analysis_issues'][1]
report=f'''# Stage 3 v1.2「個別所見の確認 → 統合」固定入力検証

## 結果と解釈

3Aを2要求、機械検査後の3Bを1要求実行した。Stage 1・2の再生成は0件。3Aは6所見を生成し、3/6件が通過、3/6件が原文引用不一致で除外された。通過所見は1868:1の3件のみで、対象カバレッジは1/2答案。3Bは `pattern_status=insufficient_evidence`、`patterns=[]` とし、代表引用・ID付きの個別フィードバックを返した。空出力ではない。

ID・出典管理と根拠のある保留に改善を認める。一方、機械通過した所見にも証拠範囲を超える語彙評価があり、3Bの基準解釈にも問題が残る。全体を内容面まで合格とは扱わない。これは正本変更だけでなく、入力分離・3呼び出し・機械ゲート・公式基準付与を含むStage 3手順全体の比較である。文面単独の因果効果は測っていない。

内容評価はCodexの暫定判断であり、人手評価ではない。同じ2答案による既知失敗の再検証に限定する。**傾向が支持される別の案件での性能は未検証。**

## 比較元・正本・固定条件

比較元コミットは `5d24e8f589d651e8ae806d14c5afebd2599ea4ef`、実行前HEADと一致。比較元 `outputs/recsaver_stage3_v1_1_validation_20261121/` のstage3/rater_7/input.jsonをfixed_input.jsonへバイト同一で保存した。SHA-256は `{m['fixed_input_sha256']}`。旧版の最終出力は同ディレクトリのstage3/rater_7/raw.txtとparsed.jsonを参照した。

| 正本（リポジトリ相対パス） | SHA-256 |
|---|---|
| {m['prompts']['a']['relative_path']} | `{m['prompts']['a']['sha256']}` |
| {m['prompts']['b']['relative_path']} | `{m['prompts']['b']['sha256']}` |

実パスは `C:/Users/GUESTUSER/Desktop/tsuruoka/Lab-RecSAVER/` 以下の上記パス。WSLで実際に読み込んだパスと同名ファイル検索結果もrun_manifest.jsonに保存した。同名正本は各1件。正本文は変更せず `{{{{INPUT_JSON}}}}` だけを置換した。比較元と正本は実行前後でハッシュ不変。

モデルはQwen/Qwen2.5-32B-Instruct-GPTQ-Int4、quantization=gptq_marlin、snapshot c83e67dfb2664f5039fd4cd99e206799e27dd800。vLLM 0.6.6.post1、torch 2.5.1+cu121、transformers 4.48.3、RTX 6000 Ada。temperature=0.2、top_p=0.8、max_tokens=5000を各要求で維持した。seedは旧Stage3の925847335を3要求それぞれに固定。既定systemとchat templateは旧版と一致し、user内容以外に追加指示はない。GPUのバッチ構成・実行順序は変更されるため完全なトークン再現性は保証しない。

| 要求 | 入力tokens | 出力tokens | 厳密JSON | 構造 | 終了 |
|---|---|---|---|---|---|
{req_table}

全要求で切り詰めなし、出力修復なし、良い出力を選ぶ再生成なし。3Aの2要求は別入力を同じEngineでバッチ処理し、3Bはその完了・検査後の独立要求。旧版の1要求から合計3要求に増えたため、同一計算予算の比較ではない。

## 実装と受け渡し

既存 `outputs/recsaver_prompt_v1_1_validation_20261120/code/run.py` のEngineを再利用し、追加コードを本ディレクトリのcode/に保存した。候補IDは実入力ですでに1868_1__K1等の正規形であったため、同値正規化した。元の配列位置・ID・対象・レコードハッシュをrecord_id_mapping.jsonに保存した。

3Aの入力はtarget（ID・原文）、observed_scores（元Overall・全Traits）、当該対象の候補2件、dimension_namesだけ。1868の呼び出しに4902の候補や全文を渡していない。履歴全文・ルーブリック記述も渡していない。当該候補自身に元々含まれる履歴引用は、候補の未検証主張として保持した。

3Aの全体形式・対象IDと、所見単位のフィールド・観点・ID所属・引用一致を分けて検査した。重複observation_idは拒否。同一引用を複数回並べても1箇所とし、重なる抜粋も独立箇所に数えない。multiple_passages/whole_essayには2つ以上の独立抜粋を要求するが、意味的に十分な範囲を覆うことまで保証しない。

通過した3所見に `1868:1::O1`、`1868:1::O2`、`1868:1::O3` を付けた。観測点は順にCohesion=3、Vocabulary=4、Cohesion=3を元データから付与した。欠損時はnullにする実装だが、今回は欠損0/3件で、欠損分岐のモデル応答は未検証。

公式rubricの観測帯と直近の上下帯を取得し、6つの一意なrubric_ref_idを用意した。参照元は固定入力の `rubric.scores[帯][観点]`。原文、取得元ファイルのハッシュ、JSONパス、観点・帯をhandoff/rubric_provenance.jsonに保存した。2つのCohesion所見が同じ基準を使うため、来歴行は9行、一意な基準は6件である。

3Bにはverified_observations、rubric_entries、accepted_target_ids、accepted_record_count、rater_id、短いsource_analysis_issues、evidence_limitationsのみを渡した。候補の生文、issueのcandidate_excerpt、履歴答案全文、監査の置換・修復文は渡していない。3Bの候補数は4、採用対象集合は元の2件を維持し、4902に使用可能所見がないことを制約として渡した。

## 機械検査と除外

| 項目 | 結果 |
|---|---|
| 3A要求の厳密JSON・構造 | 各2/2 |
| 3A所見の形式・観点・所属・原文引用通過 | 3/6 |
| 通過した所見を持つ異なる対象 | 1/2 |
| issue引用・候補所属の通過 | 3/4 |
| 3B要求の厳密JSON・構造 | 各1/1 |
| 3B個別所見キーの入力所属 | 3/3 |
| 3B代表キーの入力所属・個別集合所属 | 各1/1 |
| 観測帯・比較帯参照の入力所属 | 2/2 |
| 観測帯の観点・得点一致 | 1/1 |
| 比較帯が同一観点の別帯 | 1/1 |
| 保留時patternsが空 | 1/1 |
| 最終段落の代表原文引用・ID | 各1/1 |
| 3B機械検査の全項目 | 15/15 |
| 入力・受け渡し・モデル・原出力不変性 | 48/48 |

supportedの出力は0件のため、実際のモデル出力について「2独立対象以上の支持」「代表が支持集合に属する」の率は評価不能。検査コードには条件を実装し、同一答案の重複支持を拒否する合成回帰テストで確認した。合成テスト14件はモデル結果に加算しない。通過所見0件でも3Bへ進む実装であり、空入力の検査分岐は合成テストで確認したが、今回の主実行は所見3件なので0件分岐のモデル挙動は未検証。

4902:1/O1～O3はすべて同じ引用を使った。原文は開始部分が `" To be yourself`、生成引用は `"To be yourself` で、引用符直後の空白が1個欠けていた。空白1個を診断上だけ挿入すると全文が一致することをrejected_quote_diagnostics.jsonに記録した。厳密一致は0/3のままで、修復文は3Bに渡していない。この3つは同一箇所の異なる所見であり、3箇所の独立証拠ではない。生の引用文字列は全6所見で4種類、うち完全一致は3種類だった。

4902/K2のissue引用も不一致で除外。生成は “{a['4902:1']['source_analysis_issues'][1]['candidate_excerpt']}”。実レコードに近い文は “{r.read(r.OUT/'rejected_issue_diagnostics.json')['closest_source_string']}”。これは空白差だけではなく主語・述語・傾向表現を変更した引用である。機械検査と除外理由は各mechanical_checks.jsonおよびexclusions/に保存した。

## 3Aの意味評価（機械検査とは別）

| 通過所見 | Codex暫定評価 | 根拠・限界 |
|---|---|---|
{chr(10).join('| '+x['key']+' | '+x['judgment']+' | '+x['reason']+' |' for x in obs_reviews)}

O2の英語原文は “{o2['scoring_relevance']}”。和訳は「これらの語の使用は十分な語彙の幅を示し、4点と整合します」。引用中に各語があることは確認できるが、語の存在と答案全体での柔軟性・精確さ・語彙幅を区別していない。機械的には通過したが内容改善には数えない。スコープlocalとlimitationを付けても、その間の過大主張は解消しない。

1868/K2のissue引用は “{issue['candidate_excerpt']}”。和訳は「この答案は全般に統制された構成と十分な語彙の幅を示し、OverallとTraitsの両方の観測3点と整合します」。Vocabulary=4と矛盾する点を拾ったことは旧版からの改善。ただしPhraseology=4との矛盾もあるのに、説明はVocabularyのみだった。

他の通過issueは意味的に慎重な扱いが必要。1868/K1の “consistent with a score of 3” はOverallを指す可能性があり、Vocabulary 3の直接表明と断定できない。4902/K1の「軽微な誤りの混在とOverall 3」の文だけでCohesion 2との数値矛盾とも断定できない。さらに3Aのissue説明はCohesion 2を “some repetitive and mechanical” と説明するが、その語を含む公式記述はCohesion 3である。3Aに公式rubric記述は渡していないため、こうした基準表現を自力で付け加えること自体に限界がある。通過issue3件を、確認済みの問題3件とは集計していない。

## 旧版Stage 3 v1.1の最終フィードバック

### 英語原文

> {old['feedback_paragraph']}

### 和訳（誤りを補正しない）

{old_jp}

### 根拠との照合

構造化代表引用は1868:1の “{q1}”。この1文は継続学習の主題提示や局所的な語法を検討できるが、十分な語彙幅や答案全体の構成を証明しない。旧版は同じOverall 3という事実を、構成・語彙と得点の関係に広げた。観測Cohesionは1868=3、4902=2、Vocabularyは1868=4、4902=3と異なり、同じ評価の仕方を支持する十分な比較がない。

旧Vocabulary 4へのrubric_refsと観測値は正しかったが、1文で帯の妥当性まで確定できない。最終段落には引用原文がない。別の構造化反例には、履歴にしか存在しない8722:1をtarget_essay_idとして入れていた。

## 新版Stage 3Bの最終フィードバック

### 英語原文

> {b['feedback_paragraph']}

### 和訳（誤りを補正しない）

{new_jp}

### 根拠との照合

代表は1868:1::O1で、原文引用とIDが最終段落に実在する。継続学習という主題の提示は確認でき、採点者の動機・安定した好み・その特徴が得点を引き起こしたという因果説明はしていない。通過所見が1答案だけなので、2答案を必要とするpatternの保留は妥当。1文では全体の結束性を評価できないと説明し、追加文の確認も残した点は有用である。8722:1は支持・代表・反例のいずれにも混入していない。

ただし、構造化rubric_comparison.explanationの冒頭は “{b['rubric_comparison']['explanation']}”。和訳は「証拠は、この答案が全般に統制された構成を示し、種類は限られるものの結束表現を使っており、それが3点と整合することを支持しています。ただし、この1文は答案の結束性を十分に評価するだけの証拠ではなく、得点を上げるべきか下げるべきかは未確定です」。主題を述べた1文から、構成や結束表現の種類まで確認したかのように説明しており、後半の保留と緊張する。relationship=indeterminateは適切だが、保留語だけで前半の過大主張は解消しない。

観測参照Cohesion:3・比較参照Cohesion:2は入力どおりで、最終段落に別帯の記述をその帯として取り違える明示的引用はない。しかし最終段落の「3点は基準と整合する」は、正しい帯IDへの対応と本文による採点妥当性の支持が曖昧。引用だけから整合性が証明されたと読むべきではない。最終段落は構造化出力よりさらに強い別の全体評価は加えていないが、構造化出力に残る過大主張を完全には解消していない。

next_scoring_checkは保持条件を “{b['next_scoring_check']['retain_if']}”、再考条件を “{b['next_scoring_check']['reconsider_if']}” とした。和訳は「追加の文が主題を一貫して支え、さまざまな結束表現を使っているなら維持」「主題の支持が一貫しない、または結束表現が限られるなら再考」。しかしCohesion 3は “cohesive devices used but limited in type” を許容する。限られた種類というだけで再考条件にするのは過剰で、単にrangeがあれば3を維持するという条件も、4点の適切な多様性との境界を整理していない。どの追加箇所を見るかも “Additional sentences” と一般的で、例えば育児例から教育・仕事の例への接続をどの文間で確かめるかまで指定していない。

## 公式基準の来歴と比較

以下はモデル生成ではなく保存済みrubricからプログラムで取得した原文。

| ID | 公式記述 |
|---|---|
{refs}

旧版が対象反例に使った8722:1の全文は3Bにはない。今回の比較帯はCohesion 2であり、Overall 3/4のrarelyとin some casesの識別を再びモデルに問う設計ではない。観点が変わっているため、この頻度表現の一般的な識別改善は評価不能。

## 四項目の比較

| 項目 | 判定 | 根拠 |
|---|---|---|
{chr(10).join('| '+x['item']+' | '+x['judgment']+' | '+x['evidence']+' |' for x in ratings)}

今回の改善は、検証可能な主題提示の所見を残しつつ、支持不十分な傾向を作らず保留した点にある。ただし、4902の所見が引用不一致で落ちたことが保留の一因であり、両答案の意味的比較を成功させたわけではない。3Aの内容失敗はゲートで全て防げず、3Bにも解釈上の問題が残った。

## 保存・再点検・限界

保存先: `outputs/recsaver_stage3_v1_2_pipeline_20261121/`。fixed_input.json、prepared_3a、stage3a/対象別のinput/messages/rendered_chat/sampling/raw/parsed/result/generation/integrity/mechanical_checks、stage3b/rater_7の同種ファイル、handoff、exclusions、record_id_mapping、observation_results.csv、summary、request_summary、invariant_checks、content_review、gate_tests、診断結果、run_manifest、追加コードを保存した。原出力は失敗分を含め保持し、比較元は変更していない。再実行・再点検手順はREADME.md。

意味評価を受けて主実行の所見を修正・除外したり、3Bを再生成したりしていない。各正本について1固定入力（3Aは2答案別）・1応答だけで、形式失敗率や一般性能は推定できない。支持される傾向がある別案件、全所見0件時のモデル応答、観測点欠損時のモデル応答は未検証である。

次に直すべき点は3つ。

1. 3Aの引用を原文から正確に選ぶ方法を改善する。空白差を自動修復して主結果に混ぜず、原文オフセットなどで出典を固定する案は別診断で検証する。
2. localな所見から語彙幅・構成全体・観測帯の妥当性を断定しない。issueの引用一致だけで問題分類を確定せず、OverallとTraitの読み分けと全Trait矛盾の網羅を点検する。
3. 3Bのretain/reconsiderを公式の観測帯・隣接帯の差に結び付ける。3点が許容するlimited in typeを単独の再考理由にせず、具体的な文間・段落間と、関係が追えるか・不成功がどこにあるかを確認条件にする。
'''
(r.OUT/'validation_report.md').write_text(report,encoding='utf-8')
print('Report, metrics and provisional semantic review saved')
