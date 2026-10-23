# Trait-free Rater Profile MVP（1,000 fixed targets）

**状態：全条件の推論完了**

## 目的
Essay本文＋Overallに採点者固有の予測情報が含まれるか、自然言語Profileへの明示化・圧縮が未知Essayの予測に有用かを検証する。

## 対象抽出
最新版5条件共通N=17,725からGold Overall×target_raterで比例配分。floor後の残数は小数部分が大きい層に配分（同率は層名順）。NumPy default_rng(20261012)で各層から無作為抽出、target_id順に固定。sampling_strata.csvに配分を保存。

## 条件
A: 既存本人K=3本文＋Overall＋6 Trait scores、Overall rubric、Target本文。既存予測再利用。
B_correct/B_wrong: 同じmanifestの本人／他者K=3本文＋Overall、Overall rubric、6観点rubric定義、Target本文。predicted_overall＋reasoning。
B_nohistory: 既存Rubric Only予測再利用。6観点の別ブロックを追加しておらず、履歴なしbaselineとして扱う。
C: B_correctと同じ入力、rater_tendency＋predicted_overall＋reasoning。
D_correct/D_wrong: Overall rubric、6観点rubric定義、本人／他者Profile、Target本文。raw履歴なし。predicted_overall＋reasoning＋used_profile_tendencies。

## Trait除去・rubric
新規history formatterはid/essay/overallのみをホワイトリストで渡す。Profile historyも同様。Target入力はTextのみ。rubrics/ellipse_rubric_structured.jsonの全レベル6観点記述とkey_terms_and_definitionsをそのまま使用（新作文なし）。内容はrubric_definitions_used.md参照。共通rubricのレベル番号は観測Trait scoreではない。

## Profile履歴
PROFILE_K=20。全target sourceを全rater候補から除外、同じFilename・exact textも除外。共通利用可能最大K=26。件数はprofile_history_availability.csv参照。候補は有効Overall＋非空本文、Traitの有効性では絞らない。固定seedからrater別seedを導出して固定抽出。

## モデルと生成
Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4、vLLM、gptq_marlin。Prediction engineのmax_model_len=8192。Profile生成専用engineのmax_model_len=16384（2026-10-12にユーザーが明示承認）。Profile engine終了後にPrediction engineをロードする。Prediction: temperature=.2/top_p=.8/max_tokens=384。Profileのみ768 tokens：8つの記述欄、配列と根拠IDを含むため。request seedはbase seed＋condition＋target/rater＋attemptのSHA256。parse retry最大3回、履歴の短縮・対象除外はしない。

## 全条件の最終指標（主比較はcommon_all_seven）

```csv
condition,scope,N,missing,parse_errors,retry_count,Accuracy,MAE,RMSE,QWK
A_current_trait_history,available_only,1000,0.0,0.0,0.0,0.538,0.484,0.726636084983398,0.35043206109875313
A_current_trait_history,common_all_seven,1000,,,,0.538,0.484,0.726636084983398,0.35043206109875313
B_traitfree_direct_correct,available_only,1000,0.0,0.0,0.0,0.498,0.548,0.8,0.3327105298278392
B_traitfree_direct_correct,common_all_seven,1000,,,,0.498,0.548,0.8,0.3327105298278392
B_traitfree_direct_wrong,available_only,1000,0.0,0.0,0.0,0.467,0.586,0.8330666239863411,0.2965797966365571
B_traitfree_direct_wrong,common_all_seven,1000,,,,0.467,0.586,0.8330666239863411,0.2965797966365571
B_nohistory_rubric,available_only,1000,0.0,0.0,0.0,0.539,0.491,0.7422937423958255,0.17348677578840777
B_nohistory_rubric,common_all_seven,1000,,,,0.539,0.491,0.7422937423958255,0.17348677578840777
C_traitfree_joint_profile,available_only,1000,0.0,0.0,1.0,0.482,0.556,0.7949842765740717,0.2879033711916339
C_traitfree_joint_profile,common_all_seven,1000,,,,0.482,0.556,0.7949842765740717,0.2879033711916339
D_twostage_correct_profile,available_only,1000,0.0,0.0,0.0,0.555,0.465,0.7106335201775947,0.36088893388680787
D_twostage_correct_profile,common_all_seven,1000,,,,0.555,0.465,0.7106335201775947,0.36088893388680787
D_twostage_wrong_profile,available_only,1000,0.0,0.0,2.0,0.525,0.501,0.7436396977031283,0.27729800936767945
D_twostage_wrong_profile,common_all_seven,1000,,,,0.525,0.501,0.7436396977031283,0.27729800936767945
```

## 予測分布
prediction_distribution.csv参照。Score 3 concentrationは全条件共通集合で比較し、MAE改善だけで成功と判断しない。全条件の分布を取得済み。

## Paired比較・95% CI
差はleft - right。Accuracy/QWKは正、MAE/RMSEは負がleft優位。target単位paired percentile bootstrap、2000回、seed=20260914。両条件・全比較に同じindexを使用。同一sourceの複数raterは独立targetとして扱い、essay/rater cluster CIは本MVPでは実施しない。

```csv
left,right,difference_direction,metric,N,difference,left_better_when,ci_lower,ci_upper,samples,seed,method
B_traitfree_direct_correct,A_current_trait_history,B_traitfree_direct_correct - A_current_trait_history,Accuracy,1000,-0.040000000000000036,positive,-0.06300000000000006,-0.016000000000000014,2000,20260914,paired percentile
B_traitfree_direct_correct,A_current_trait_history,B_traitfree_direct_correct - A_current_trait_history,MAE,1000,0.06400000000000006,negative,0.038000000000000034,0.08899999999999997,2000,20260914,paired percentile
B_traitfree_direct_correct,A_current_trait_history,B_traitfree_direct_correct - A_current_trait_history,RMSE,1000,0.073363915016602,negative,0.0488837986110616,0.09608107496751643,2000,20260914,paired percentile
B_traitfree_direct_correct,A_current_trait_history,B_traitfree_direct_correct - A_current_trait_history,QWK,1000,-0.017721531270913915,positive,-0.055447847593466305,0.021086281284763458,2000,20260914,paired percentile
B_traitfree_direct_correct,B_traitfree_direct_wrong,B_traitfree_direct_correct - B_traitfree_direct_wrong,Accuracy,1000,0.030999999999999972,positive,0.0010000000000000009,0.063,2000,20260914,paired percentile
B_traitfree_direct_correct,B_traitfree_direct_wrong,B_traitfree_direct_correct - B_traitfree_direct_wrong,MAE,1000,-0.03799999999999992,negative,-0.07399999999999995,-0.0040000000000000036,2000,20260914,paired percentile
B_traitfree_direct_correct,B_traitfree_direct_wrong,B_traitfree_direct_correct - B_traitfree_direct_wrong,RMSE,1000,-0.03306662398634108,negative,-0.06460756651055778,-0.0018231230343585263,2000,20260914,paired percentile
B_traitfree_direct_correct,B_traitfree_direct_wrong,B_traitfree_direct_correct - B_traitfree_direct_wrong,QWK,1000,0.03613073319128213,positive,-0.012322262610768084,0.08560304097030798,2000,20260914,paired percentile
B_traitfree_direct_correct,B_nohistory_rubric,B_traitfree_direct_correct - B_nohistory_rubric,Accuracy,1000,-0.041000000000000036,positive,-0.07099999999999995,-0.013000000000000012,2000,20260914,paired percentile
B_traitfree_direct_correct,B_nohistory_rubric,B_traitfree_direct_correct - B_nohistory_rubric,MAE,1000,0.05700000000000005,negative,0.026000000000000023,0.08699999999999997,2000,20260914,paired percentile
B_traitfree_direct_correct,B_nohistory_rubric,B_traitfree_direct_correct - B_nohistory_rubric,RMSE,1000,0.05770625760417458,negative,0.030300805287061618,0.08579764736476879,2000,20260914,paired percentile
B_traitfree_direct_correct,B_nohistory_rubric,B_traitfree_direct_correct - B_nohistory_rubric,QWK,1000,0.15922375403943145,positive,0.11147639550751809,0.20735140362320922,2000,20260914,paired percentile
C_traitfree_joint_profile,B_traitfree_direct_correct,C_traitfree_joint_profile - B_traitfree_direct_correct,Accuracy,1000,-0.016000000000000014,positive,-0.044999999999999984,0.01200000000000001,2000,20260914,paired percentile
C_traitfree_joint_profile,B_traitfree_direct_correct,C_traitfree_joint_profile - B_traitfree_direct_correct,MAE,1000,0.008000000000000007,negative,-0.02300000000000002,0.03799999999999992,2000,20260914,paired percentile
C_traitfree_joint_profile,B_traitfree_direct_correct,C_traitfree_joint_profile - B_traitfree_direct_correct,RMSE,1000,-0.005015723425928376,negative,-0.03276341181711469,0.02120856718224838,2000,20260914,paired percentile
C_traitfree_joint_profile,B_traitfree_direct_correct,C_traitfree_joint_profile - B_traitfree_direct_correct,QWK,1000,-0.044807158636205324,positive,-0.08692113624337204,-0.001492264258541282,2000,20260914,paired percentile
D_twostage_correct_profile,D_twostage_wrong_profile,D_twostage_correct_profile - D_twostage_wrong_profile,Accuracy,1000,0.030000000000000027,positive,0.0020000000000000018,0.05599999999999994,2000,20260914,paired percentile
D_twostage_correct_profile,D_twostage_wrong_profile,D_twostage_correct_profile - D_twostage_wrong_profile,MAE,1000,-0.035999999999999976,negative,-0.065,-0.008000000000000007,2000,20260914,paired percentile
D_twostage_correct_profile,D_twostage_wrong_profile,D_twostage_correct_profile - D_twostage_wrong_profile,RMSE,1000,-0.033006177525533587,negative,-0.060641584538720594,-0.005458278578613955,2000,20260914,paired percentile
D_twostage_correct_profile,D_twostage_wrong_profile,D_twostage_correct_profile - D_twostage_wrong_profile,QWK,1000,0.08359092451912842,positive,0.02713088567454512,0.13897696593622047,2000,20260914,paired percentile
D_twostage_correct_profile,B_traitfree_direct_correct,D_twostage_correct_profile - B_traitfree_direct_correct,Accuracy,1000,0.05700000000000005,positive,0.027975000000000028,0.08699999999999997,2000,20260914,paired percentile
D_twostage_correct_profile,B_traitfree_direct_correct,D_twostage_correct_profile - B_traitfree_direct_correct,MAE,1000,-0.08300000000000002,negative,-0.11602500000000004,-0.050000000000000044,2000,20260914,paired percentile
D_twostage_correct_profile,B_traitfree_direct_correct,D_twostage_correct_profile - B_traitfree_direct_correct,RMSE,1000,-0.08936647982240531,negative,-0.12183218025476171,-0.05836959475510952,2000,20260914,paired percentile
D_twostage_correct_profile,B_traitfree_direct_correct,D_twostage_correct_profile - B_traitfree_direct_correct,QWK,1000,0.028178404058968654,positive,-0.02690489173181018,0.08363858780757719,2000,20260914,paired percentile
```

## Profile評価
本人／他者Profileの予測性能でutilityを評価する。profile_similarity.csvはTF-IDF cosineによる表層的多様性、joint_profile_stability.csvは同rater内傾向文の類似度。異なるK=3履歴による変動とtargetによる変動は分離できない。人手grounding確認資料はprofiles/profile_examples_for_manual_review.md。人手での正しさの判定は自動実行しない。

## Integrity
integrity_audit.csv、history_overlap_audit.csv、input SHA256を参照。構造的auditと推論後auditを区別する。当初GPUは別研究Ministralジョブで使用中だったが、その後空きを確認。既存ジョブは停止せず、別モデルへ変更しない。K=20のProfile生成は変更前に27件すべて8,192-token上限を超えた（最大15,451＋768）。Profile生成のみcontextを16,384へ拡張することをユーザーが承認、再auditでは全27件が上限内。変更前auditはprompt_token_audit_8192.csvに保存。

## Parser修復
初回Profile生成はMarkdown JSON fenceを厳密JSONパーサーが受理せず、各raterで不要な3回retryが発生した。2026-10-14にfenceだけを除去するパーサーへ修正し、全27 Profileを保存済み応答から復旧した。各raterの最初のschema-valid attemptを採用し、内容・スコアは変更していない。元応答・全attemptはrater_profiles_pre_fence_repair.jsonlとrater_profiles.jsonlに保存。profile_parse_repair_audit.csvに採用attemptと実際のretryを記録。

## 解釈
全7条件の同一1,000 targetで最終比較を行った。具体的な解釈は以下に示す。本人が他者より高性能なら、本文とOverallの対応に固有予測情報が含まれる可能性を述べられる。AとBはTrait除去に加え共通Trait定義の明示も異なるため、完全な単一要因比較ではない。

## 現時点で主張できないこと
LLMが真の人間認知過程を再現した、Profileが真の採点方針である、特定TraitがOverallに因果的に影響する、とは主張しない。target bootstrapは複数比較補正を含まず、探索的MVPとして解釈する。

## 再実行
リポジトリroot、WSL qwen3で以下を実行。GPU使用中はrunが明示的に拒否する。
```bash
python -m src.recsaver.rater_profile_mvp_1000 prepare
python -m src.recsaver.rater_profile_mvp_1000 token-audit
python -m src.recsaver.rater_profile_mvp_1000 profiles
python -m src.recsaver.rater_profile_mvp_1000 dry
python -m src.recsaver.rater_profile_mvp_1000 full
python -m src.recsaver.rater_profile_mvp_1000 analyze
```

## 作成・変更ファイル
新規src/recsaver/rater_profile_mvp_1000.py、4つの新規prompt（experiment_config.json参照）、outputs/rater_profile_mvp_1000/以下。既存研究コード・data・既存experiment outputは変更していない。git_status_before.txtには作業前からの3つのmodifiedと既存untrackedを記録、git_status_after.txtで今回分を確認可能。

## 最終結果の解釈と出力例

| condition | N | Accuracy | MAE | RMSE | QWK |
| --- | --- | --- | --- | --- | --- |
| A_current_trait_history | 1000 | 0.5380 | 0.4840 | 0.7266 | 0.3504 |
| B_traitfree_direct_correct | 1000 | 0.4980 | 0.5480 | 0.8000 | 0.3327 |
| B_traitfree_direct_wrong | 1000 | 0.4670 | 0.5860 | 0.8331 | 0.2966 |
| B_nohistory_rubric | 1000 | 0.5390 | 0.4910 | 0.7423 | 0.1735 |
| C_traitfree_joint_profile | 1000 | 0.4820 | 0.5560 | 0.7950 | 0.2879 |
| D_twostage_correct_profile | 1000 | 0.5550 | 0.4650 | 0.7106 | 0.3609 |
| D_twostage_wrong_profile | 1000 | 0.5250 | 0.5010 | 0.7436 | 0.2773 |


### 主要6比較：差と95% paired bootstrap CI

| 差の向き | Accuracy (pp) | MAE | RMSE | QWK |
| --- | --- | --- | --- | --- |
| B_traitfree_direct_correct − A_current_trait_history | -4.000 [-6.300, -1.600] | +0.064 [+0.038, +0.089] | +0.073 [+0.049, +0.096] | -0.018 [-0.055, +0.021] |
| B_traitfree_direct_correct − B_traitfree_direct_wrong | +3.100 [+0.100, +6.300] | -0.038 [-0.074, -0.004] | -0.033 [-0.065, -0.002] | +0.036 [-0.012, +0.086] |
| B_traitfree_direct_correct − B_nohistory_rubric | -4.100 [-7.100, -1.300] | +0.057 [+0.026, +0.087] | +0.058 [+0.030, +0.086] | +0.159 [+0.111, +0.207] |
| C_traitfree_joint_profile − B_traitfree_direct_correct | -1.600 [-4.500, +1.200] | +0.008 [-0.023, +0.038] | -0.005 [-0.033, +0.021] | -0.045 [-0.087, -0.001] |
| D_twostage_correct_profile − D_twostage_wrong_profile | +3.000 [+0.200, +5.600] | -0.036 [-0.065, -0.008] | -0.033 [-0.061, -0.005] | +0.084 [+0.027, +0.139] |
| D_twostage_correct_profile − B_traitfree_direct_correct | +5.700 [+2.797, +8.700] | -0.083 [-0.116, -0.050] | -0.089 [-0.122, -0.058] | +0.028 [-0.027, +0.084] |


Accuracyはpercentage points、MAE/RMSEはscore単位、QWKは係数差。個別95% CIであり、多重比較補正なし。

1. **Trait除去（B本人−A）**：Accuracy −4.0pp、MAE +0.064。QWK差のCIは0を含む。Aより同等とは言えない。共通Trait定義をBに追加しており、純粋なTrait除去だけの差ではない。

2. **Trait-free本人−他者履歴**：Accuracy +3.1pp、MAE −0.038、RMSE −0.033。これらの個別CIは0を含まない。QWK +0.036のCIは0を含む。本人履歴固有の予測情報が残る可能性を支持する。

3. **Trait-free本人−履歴なし**：Accuracy −4.1pp、MAE +0.057、RMSE +0.058だがQWK +0.159。履歴の追加価値を全指標で支持する結果ではない。履歴なしはScore 3が93.5%に集中する。共通Trait定義の有無も異なる。

4. **Joint−Direct本人**：Accuracy −1.6pp、MAE +0.008、RMSE −0.005はCIが0を含む。QWK −0.0448のCIは0を含まない。Jointでの改善は確認できず、QWKは低下した。

5. **本人−他者Profile**：Accuracy +3.0pp、MAE −0.036、RMSE −0.033、QWK +0.0836。4指標の個別CIはすべて0を含まず、Profileの採点者固有の予測utilityを支持する。真の方針の同定ではない。

6. **本人Profile−Direct本人**：Accuracy +5.7pp、MAE −0.083、RMSE −0.089は改善。QWK +0.0282のCIは0を含む。ProfileはK=20、DirectはK=3であり、圧縮・言語化そのものの効果と履歴件数の効果を切り分けられない。


### 予測分布（N=1,000なので各count÷10が%）

| condition | Score 1 count | Score 2 count | Score 3 count | Score 4 count | Score 5 count | Score 3 % |
| --- | --- | --- | --- | --- | --- | --- |
| A_current_trait_history | 6 | 125 | 808 | 61 | 0 | 80.8 |
| B_traitfree_direct_correct | 12 | 226 | 710 | 52 | 0 | 71.0 |
| B_traitfree_direct_wrong | 9 | 248 | 673 | 70 | 0 | 67.3 |
| B_nohistory_rubric | 2 | 53 | 935 | 10 | 0 | 93.5 |
| C_traitfree_joint_profile | 2 | 142 | 700 | 156 | 0 | 70.0 |
| D_twostage_correct_profile | 0 | 120 | 805 | 75 | 0 | 80.5 |
| D_twostage_wrong_profile | 0 | 103 | 827 | 70 | 0 | 82.7 |


Gold distribution: {"1": 6, "2": 183, "3": 521, "4": 261, "5": 29}

D本人はB本人よりScore 3が71.0%→80.5%へ増えるが、QWKは0.3327→0.3609で、点推定では「MAE改善とQWK低下」の組合せではない。ただしQWK差のCIは0を含む。D本人と他者では本人の方がScore 3集中が低く、QWKも高い。全条件でScore 5予測が0件、DはScore 1も0件で、両端scoreの予測不足が残る。


### Profile多様性・Joint安定性

{
  "profile_n": 27,
  "distinct_exact_profiles": 27,
  "between_rater_profile_tfidf": {
    "pairs": 351,
    "mean": 0.425152640994747,
    "min": 0.1943142275822069,
    "max": 0.8131597958967751
  },
  "joint_within_rater_tfidf": {
    "raters_with_at_least_2_targets": 26,
    "pairs": 26771,
    "pair_weighted_mean": 0.1879684064348236,
    "rater_mean_range": [
      0.0,
      0.3866625137572227
    ]
  }
}

27 Profileに完全一致はないが、TF-IDFは表層的語彙類似度であり、generic rubric paraphraseでないことの証明にはならない。Profileのschemaキーも類似度計算に含む。同rater内のJoint傾向の類似度は低いが、targetごとにK=3履歴も異なるためtarget依存と履歴依存を分離できない。1件しかないrater_25はwithin-rater評価不能。


### 実際の出力例
同一targetの全7条件の英文JSONとEssay全文は[prediction_output_examples.md](prediction_output_examples.md)に保存。先頭target=1005:2（Gold=4）は全7条件が3と予測し不正解だった。これは改善例だけを選ばないための固定規則による例。

Profileの3例と根拠・反例候補は[profile_grounding_observations.md](profiles/profile_grounding_observations.md)、全20履歴は[manual review](profiles/profile_examples_for_manual_review.md)。出力はモデルが述べた説明であり、説明の忠実性・妥当性のGoldはない。

**実際に見つかったgrounding問題**：rater_1の「2と4が多く3は少ない」という説明は、実際の20件（2=7、3=7、4=6）と不整合。Profileは予測に有用でも、文章の事実性が保証されるわけではない。例を除外・再生成して改善はしていない。

Profile内で明示されたhistory IDは42参照、選択履歴外のIDは0参照。IDの実在・履歴内包含の検査であり、Traitの重要性や引用したEssayの解釈が正しいことを保証しない。


#### Profile例：rater_1

```json
{
  "overall_scoring_tendency": "rater_1 tends to assign scores of 2 and 4 more frequently, with fewer instances of scores 1, 3, and 5.",
  "evaluation_aspects": {
    "cohesion": "rater_1 appears to focus on the logical sequencing and use of cohesive devices, with some essays receiving lower scores due to repetitive or unsuccessful use of cohesive devices.",
    "syntax": "rater_1 tends to evaluate the variety and complexity of sentence structures, with higher scores given to essays that demonstrate a range of syntactic structures.",
    "vocabulary": "rater_1 seems to consider the range and appropriateness of vocabulary used, with higher scores given to essays that use a wide range of vocabulary effectively.",
    "phraseology": "rater_1 appears to value the use of idioms, collocations, and lexical bundles, with higher scores given to essays that use these effectively.",
    "grammar": "rater_1 tends to focus on the accuracy of grammar and usage, with higher scores given to essays that demonstrate minimal errors.",
    "conventions": "rater_1 appears to consider the consistency of conventions, with higher scores given to essays that demonstrate consistent and appropriate use of conventions."
  },
  "other_observed_patterns": [
    "rater_1 tends to assign a score of 4 when essays demonstrate a range of vocabulary and syntactic structures, with occasional inaccuracies.",
    "rater_1 tends to assign a score of 2 when essays show inconsistent facility in sentence formation, word choice, and mechanics."
  ],
  "uncertainties": [
    "insufficient evidence to determine rater_1's scoring tendency for essays with scores of 1, 3, and 5.",
    "insufficient evidence to determine rater_1's specific criteria for evaluating phraseology."
  ]
}
```


#### Profile例：rater_10

```json
{
  "overall_scoring_tendency": "Tends to score essays in the range of 2 to 4, with a slight preference for 3.",
  "evaluation_aspects": {
    "cohesion": "In these examples, rater_10 appears to consider organization and logical sequencing of ideas, but does not consistently penalize repetitive or mechanical use of cohesive devices.",
    "syntax": "Tends to recognize a range of syntactic structures, but occasionally notes errors or inappropriateness in sentence formation.",
    "vocabulary": "Appears to value a sufficient range of vocabulary, but does not consistently reward the use of less common words or topic-related terms.",
    "phraseology": "Observes the use of phrases such as idioms and collocations, but does not consistently reward variety or penalize inaccuracies.",
    "grammar": "Tends to penalize errors in grammar and usage, but does not consistently reward minimal errors.",
    "conventions": "Considers the use of appropriate conventions, but does not consistently penalize minor errors in spelling, capitalization, and punctuation."
  },
  "other_observed_patterns": [
    "Tends to score higher when essays show a clear structure and logical flow of ideas.",
    "Tends to score lower when essays contain numerous grammatical errors and lack variety in sentence structures."
  ],
  "uncertainties": [
    "Insufficient evidence to determine if rater_10 consistently rewards the use of sophisticated vocabulary.",
    "Insufficient evidence to determine if rater_10 consistently penalizes the use of memorized chunks of language."
  ]
}
```


#### Profile例：rater_15

```json
{
  "overall_scoring_tendency": "tends to assign scores in the 3-4 range, with occasional 4 scores for essays that show slightly better control over language and structure",
  "evaluation_aspects": {
    "cohesion": "appears to focus on the logical sequencing of ideas and the use of cohesive devices, with scores of 3 often given when ideas are not well connected or organized",
    "syntax": "tends to consider sentence structure and variety, with scores of 4 given when there is a mix of simple, compound, and complex sentences, even with some errors",
    "vocabulary": "considers the range and appropriateness of vocabulary, with scores of 3 given when vocabulary is limited or used inappropriately",
    "phraseology": "evaluates the use of idioms, collocations, and lexical bundles, with scores of 3 given when phrases are used but with some repetition or misuse",
    "grammar": "focuses on the accuracy of grammar and usage, with scores of 4 given when there are minimal errors",
    "conventions": "considers spelling, capitalization, and punctuation, with scores of 3 given when there are some distracting errors"
  },
  "other_observed_patterns": [
    "tends to give a score of 4 when the essay demonstrates a good range of vocabulary and appropriate use of cohesive devices, as seen in essays 5362:1 and 6106:2",
    "scores of 3 are often given when the essay lacks clear organization or has significant language inaccuracies, as seen in essays 337:2 and 613:1"
  ],
  "uncertainties": [
    "insufficient evidence to determine a clear pattern for scores of 2 or 5",
    "insufficient evidence to determine if there is a preference for certain topics or writing styles"
  ]
}
```


### Gitと保存状態
実験前から3 tracked filesがmodified。途中のsnapshotでは.gitignoreもmodifiedとして現れたが、最終確認では現れていない。本実験の編集操作では.gitignoreを変更・復元していない。git_status_before.txtは出力先ディレクトリ作成直後の記録である。今回の編集対象は新規experiment script、4つの新規prompt、今回専用outputディレクトリ内のファイル。
