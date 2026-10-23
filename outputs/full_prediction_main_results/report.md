# Full-scale Prediction Main Results：5条件共通N

## Common target construction

共通N = 17,725。manifestの17,731 target中、除外6件。Gold不一致0件、重複key 0件。

target_idを使用し、manifestのsource_row_id（essay）×target_raterとの一対一対応を全条件で検証した。保存済みparse_successがtrue、predictionとGoldが整数1〜5のtargetだけを共通集合に採用。raw出力の再parseは行わない。

Valid predictionsはparse成功・prediction有効・Gold有効の件数。Missing from intersectionは各条件Valid N − Common N。

| condition | original_rows | unique_target_keys | duplicate_target_keys | duplicate_essay_rater_keys | parse_success_rows | missing_prediction_rows | invalid_predicted_overall_rows | gold_available_rows | valid_gold_rows | valid_predictions | gold_mismatch_rows | identity_mismatch_rows | missing_from_5condition_intersection | common_N |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| k0 | 17731 | 17731 | 0 | 0 | 17728 | 3 | 0 | 17731 | 17731 | 17728 | 0 | 0 | 3 | 17725 |
| raw_k3 | 17731 | 17731 | 0 | 0 | 17728 | 3 | 0 | 17731 | 17731 | 17728 | 0 | 0 | 3 | 17725 |
| k0_rubric | 17731 | 17731 | 0 | 0 | 17731 | 0 | 0 | 17731 | 17731 | 17731 | 0 | 0 | 6 | 17725 |
| wrong_k3_rubric | 17731 | 17731 | 0 | 0 | 17731 | 0 | 0 | 17731 | 17731 | 17731 | 0 | 0 | 6 | 17725 |
| correct_k3_rubric | 17731 | 17731 | 0 | 0 | 17731 | 0 | 0 | 17731 | 17731 | 17731 | 0 | 0 | 6 | 17725 |

除外targetと理由：

| target_key | source_row_id | target_rater | gold_overall | target_id | available_k0 | available_raw_k3 | available_k0_rubric | available_wrong_k3_rubric | available_correct_k3_rubric | included_in_common_set | exclusion_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1932:2 | 1932 | rater_24 | 3 | 1932:2 | True | False | True | True | True | False | raw_k3:parse_failure;raw_k3:missing_prediction |
| 2317:2 | 2317 | rater_2 | 4 | 2317:2 | True | False | True | True | True | False | raw_k3:parse_failure;raw_k3:missing_prediction |
| 3499:2 | 3499 | rater_9 | 2 | 3499:2 | False | True | True | True | True | False | k0:parse_failure;k0:missing_prediction |
| 3572:2 | 3572 | rater_1 | 4 | 3572:2 | True | False | True | True | True | False | raw_k3:parse_failure;raw_k3:missing_prediction |
| 3703:1 | 3703 | rater_6 | 4 | 3703:1 | False | True | True | True | True | False | k0:parse_failure;k0:missing_prediction |
| 5595:2 | 5595 | rater_5 | 3 | 5595:2 | False | True | True | True | True | False | k0:parse_failure;k0:missing_prediction |

## Main 5-condition results

| Condition | N | Accuracy | MAE | RMSE | QWK |
| --- | --- | --- | --- | --- | --- |
| K=0 | 17725 | 0.5361 | 0.4993 | 0.7550 | 0.2650 |
| Correct Raw K=3 | 17725 | 0.5386 | 0.4930 | 0.7460 | 0.3141 |
| K=0 + Overall Rubric | 17725 | 0.5414 | 0.4886 | 0.7407 | 0.1783 |
| Wrong K=3 + Overall Rubric | 17725 | 0.5314 | 0.5022 | 0.7549 | 0.3178 |
| Correct K=3 + Overall Rubric | 17725 | 0.5492 | 0.4780 | 0.7301 | 0.3556 |

## Paired comparisons

差の向き：Accuracy/MAE/RMSE/QWK deltaはto − from。paired AE differenceはfrom − to（正が改善）。improved/worsenedは絶対誤差の減少/増加。

| comparison | from_condition | to_condition | N | accuracy_delta | mae_delta | rmse_delta | qwk_delta | improved | unchanged | worsened | mean_paired_ae_difference | median_paired_ae_difference |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | K=0 | Correct Raw K=3 | 17725 | 0.0025 | -0.0063 | -0.0090 | 0.0491 | 2050 | 13737 | 1938 | 0.0063 | 0.0000 |
| B | K=0 | K=0 + Overall Rubric | 17725 | 0.0054 | -0.0107 | -0.0143 | -0.0868 | 1022 | 15871 | 832 | 0.0107 | 0.0000 |
| C | K=0 + Overall Rubric | Wrong K=3 + Overall Rubric | 17725 | -0.0100 | 0.0137 | 0.0143 | 0.1395 | 1441 | 14602 | 1682 | -0.0137 | 0.0000 |
| D | K=0 + Overall Rubric | Correct K=3 + Overall Rubric | 17725 | 0.0078 | -0.0106 | -0.0106 | 0.1773 | 1635 | 14643 | 1447 | 0.0106 | 0.0000 |
| E | Wrong K=3 + Overall Rubric | Correct K=3 + Overall Rubric | 17725 | 0.0178 | -0.0242 | -0.0249 | 0.0378 | 2290 | 13563 | 1872 | 0.0242 | 0.0000 |
| F | Correct Raw K=3 | Correct K=3 + Overall Rubric | 17725 | 0.0106 | -0.0150 | -0.0159 | 0.0414 | 1134 | 15722 | 869 | 0.0150 | 0.0000 |

## Bootstrap CI

既存full_history_only_analysis.bootstrapを関数本体の変更なしで再利用し、比較リストのみA〜Fに指定。seed=20260914、2000回、target単位paired percentile 95% CI。

同じdrawで全条件を再標本化。これはCI計算用の再標本化であり、実験target/historyの再選択ではない。同一essay内の依存、生成・History drawの不確実性は含めず、多重比較補正は行っていない。

| analysis | statistic | n | point_estimate | ci_lower | ci_upper | confidence_level | bootstrap_seed | bootstrap_repetitions | resampling_unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | accuracy_delta | 17725 | 0.0025 | -0.0041 | 0.0093 | 0.9500 | 20260914 | 2000 | target_id |
| A | mae_delta | 17725 | -0.0063 | -0.0131 | 0.0005 | 0.9500 | 20260914 | 2000 | target_id |
| A | paired_ae_difference | 17725 | 0.0063 | -0.0005 | 0.0131 | 0.9500 | 20260914 | 2000 | target_id |
| A | qwk_delta | 17725 | 0.0491 | 0.0369 | 0.0615 | 0.9500 | 20260914 | 2000 | target_id |
| B | accuracy_delta | 17725 | 0.0054 | 0.0007 | 0.0102 | 0.9500 | 20260914 | 2000 | target_id |
| B | mae_delta | 17725 | -0.0107 | -0.0156 | -0.0059 | 0.9500 | 20260914 | 2000 | target_id |
| B | paired_ae_difference | 17725 | 0.0107 | 0.0059 | 0.0156 | 0.9500 | 20260914 | 2000 | target_id |
| B | qwk_delta | 17725 | -0.0868 | -0.0970 | -0.0775 | 0.9500 | 20260914 | 2000 | target_id |
| C | accuracy_delta | 17725 | -0.0100 | -0.0161 | -0.0038 | 0.9500 | 20260914 | 2000 | target_id |
| C | mae_delta | 17725 | 0.0137 | 0.0074 | 0.0200 | 0.9500 | 20260914 | 2000 | target_id |
| C | paired_ae_difference | 17725 | -0.0137 | -0.0200 | -0.0074 | 0.9500 | 20260914 | 2000 | target_id |
| C | qwk_delta | 17725 | 0.1395 | 0.1288 | 0.1511 | 0.9500 | 20260914 | 2000 | target_id |
| D | accuracy_delta | 17725 | 0.0078 | 0.0022 | 0.0135 | 0.9500 | 20260914 | 2000 | target_id |
| D | mae_delta | 17725 | -0.0106 | -0.0166 | -0.0045 | 0.9500 | 20260914 | 2000 | target_id |
| D | paired_ae_difference | 17725 | 0.0106 | 0.0045 | 0.0166 | 0.9500 | 20260914 | 2000 | target_id |
| D | qwk_delta | 17725 | 0.1773 | 0.1659 | 0.1895 | 0.9500 | 20260914 | 2000 | target_id |
| E | accuracy_delta | 17725 | 0.0178 | 0.0112 | 0.0244 | 0.9500 | 20260914 | 2000 | target_id |
| E | mae_delta | 17725 | -0.0242 | -0.0311 | -0.0170 | 0.9500 | 20260914 | 2000 | target_id |
| E | paired_ae_difference | 17725 | 0.0242 | 0.0170 | 0.0311 | 0.9500 | 20260914 | 2000 | target_id |
| E | qwk_delta | 17725 | 0.0378 | 0.0253 | 0.0505 | 0.9500 | 20260914 | 2000 | target_id |
| F | accuracy_delta | 17725 | 0.0106 | 0.0059 | 0.0152 | 0.9500 | 20260914 | 2000 | target_id |
| F | mae_delta | 17725 | -0.0150 | -0.0197 | -0.0100 | 0.9500 | 20260914 | 2000 | target_id |
| F | paired_ae_difference | 17725 | 0.0150 | 0.0100 | 0.0197 | 0.9500 | 20260914 | 2000 | target_id |
| F | qwk_delta | 17725 | 0.0414 | 0.0325 | 0.0501 | 0.9500 | 20260914 | 2000 | target_id |

## Prediction distribution

| Condition | score | count | proportion |
| --- | --- | --- | --- |
| Gold | 1 | 125 | 0.0071 |
| Gold | 2 | 3195 | 0.1803 |
| Gold | 3 | 9233 | 0.5209 |
| Gold | 4 | 4637 | 0.2616 |
| Gold | 5 | 535 | 0.0302 |
| K=0 | 1 | 21 | 0.0012 |
| K=0 | 2 | 2534 | 0.1430 |
| K=0 | 3 | 15170 | 0.8559 |
| K=0 | 4 | 0 | 0.0000 |
| K=0 | 5 | 0 | 0.0000 |
| Correct Raw K=3 | 1 | 25 | 0.0014 |
| Correct Raw K=3 | 2 | 2157 | 0.1217 |
| Correct Raw K=3 | 3 | 14080 | 0.7944 |
| Correct Raw K=3 | 4 | 1463 | 0.0825 |
| Correct Raw K=3 | 5 | 0 | 0.0000 |
| K=0 + Overall Rubric | 1 | 23 | 0.0013 |
| K=0 + Overall Rubric | 2 | 923 | 0.0521 |
| K=0 + Overall Rubric | 3 | 16646 | 0.9391 |
| K=0 + Overall Rubric | 4 | 133 | 0.0075 |
| K=0 + Overall Rubric | 5 | 0 | 0.0000 |
| Wrong K=3 + Overall Rubric | 1 | 80 | 0.0045 |
| Wrong K=3 + Overall Rubric | 2 | 2454 | 0.1384 |
| Wrong K=3 + Overall Rubric | 3 | 13994 | 0.7895 |
| Wrong K=3 + Overall Rubric | 4 | 1196 | 0.0675 |
| Wrong K=3 + Overall Rubric | 5 | 1 | 0.0001 |
| Correct K=3 + Overall Rubric | 1 | 70 | 0.0039 |
| Correct K=3 + Overall Rubric | 2 | 2342 | 0.1321 |
| Correct K=3 + Overall Rubric | 3 | 14065 | 0.7935 |
| Correct K=3 + Overall Rubric | 4 | 1247 | 0.0704 |
| Correct K=3 + Overall Rubric | 5 | 1 | 0.0001 |

## Score collapse

entropyはlog2（bits）。TV距離はGoldとの比率差の絶対値合計の1/2。

| Condition | most_frequent_score | most_frequent_score_ratio | score_3_ratio | unique_predicted_scores | prediction_entropy_bits | total_variation_distance_from_gold |
| --- | --- | --- | --- | --- | --- | --- |
| K=0 | 3 | 0.8559 | 0.8559 | 3 | 0.6049 | 0.3350 |
| Correct Raw K=3 | 3 | 0.7944 | 0.7944 | 4 | 0.9440 | 0.2735 |
| K=0 + Overall Rubric | 3 | 0.9391 | 0.9391 | 4 | 0.3725 | 0.4182 |
| Wrong K=3 + Overall Rubric | 3 | 0.7895 | 0.7895 | 5 | 0.9625 | 0.2686 |
| Correct K=3 + Overall Rubric | 3 | 0.7935 | 0.7935 | 5 | 0.9523 | 0.2726 |

## Gold-score analysis

| Condition | gold_overall | N | Accuracy | MAE |
| --- | --- | --- | --- | --- |
| K=0 | 1 | 125 | 0.0880 | 1.0640 |
| K=0 | 2 | 3195 | 0.4110 | 0.5890 |
| K=0 | 3 | 9233 | 0.8857 | 0.1144 |
| K=0 | 4 | 4637 | 0.0000 | 1.0155 |
| K=0 | 5 | 535 | 0.0000 | 2.0000 |
| Correct Raw K=3 | 1 | 125 | 0.0720 | 1.1440 |
| Correct Raw K=3 | 2 | 3195 | 0.3221 | 0.6883 |
| Correct Raw K=3 | 3 | 9233 | 0.8432 | 0.1570 |
| Correct Raw K=3 | 4 | 4637 | 0.1561 | 0.8715 |
| Correct Raw K=3 | 5 | 535 | 0.0000 | 1.6916 |
| K=0 + Overall Rubric | 1 | 125 | 0.1040 | 1.1840 |
| K=0 + Overall Rubric | 2 | 3195 | 0.1784 | 0.8216 |
| K=0 + Overall Rubric | 3 | 9233 | 0.9693 | 0.0308 |
| K=0 + Overall Rubric | 4 | 4637 | 0.0138 | 0.9888 |
| K=0 + Overall Rubric | 5 | 535 | 0.0000 | 1.9028 |
| Wrong K=3 + Overall Rubric | 1 | 125 | 0.2240 | 0.9680 |
| Wrong K=3 + Overall Rubric | 2 | 3195 | 0.3490 | 0.6629 |
| Wrong K=3 + Overall Rubric | 3 | 9233 | 0.8314 | 0.1696 |
| Wrong K=3 + Overall Rubric | 4 | 4637 | 0.1294 | 0.8989 |
| Wrong K=3 + Overall Rubric | 5 | 535 | 0.0000 | 1.7364 |
| Correct K=3 + Overall Rubric | 1 | 125 | 0.1680 | 0.9280 |
| Correct K=3 + Overall Rubric | 2 | 3195 | 0.3693 | 0.6357 |
| Correct K=3 + Overall Rubric | 3 | 9233 | 0.8525 | 0.1482 |
| Correct K=3 + Overall Rubric | 4 | 4637 | 0.1428 | 0.8782 |
| Correct K=3 + Overall Rubric | 5 | 535 | 0.0019 | 1.6561 |

全Gold別予測分布はgold_score_prediction_distribution.csvに保存。

## Rater-level analysis

calibration gap = mean prediction − mean Gold。採点者別の記述統計であり、平均差だけでbiasとは断定しない。

| Condition | target_rater | N | Accuracy | MAE | mean_prediction | mean_gold | calibration_gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| K=0 | rater_1 | 856 | 0.5829 | 0.4322 | 2.8294 | 3.0164 | -0.1869 |
| K=0 | rater_10 | 781 | 0.5198 | 0.5160 | 2.8656 | 3.0026 | -0.1370 |
| K=0 | rater_11 | 1367 | 0.5772 | 0.4382 | 2.8691 | 2.9195 | -0.0505 |
| K=0 | rater_12 | 1220 | 0.5541 | 0.4631 | 2.8639 | 3.1385 | -0.2746 |
| K=0 | rater_13 | 889 | 0.5197 | 0.5591 | 2.8515 | 3.2868 | -0.4353 |
| K=0 | rater_14 | 31 | 0.7097 | 0.2903 | 2.9032 | 2.8065 | 0.0968 |
| K=0 | rater_15 | 988 | 0.5182 | 0.4868 | 2.8735 | 3.3198 | -0.4464 |
| K=0 | rater_16 | 447 | 0.5414 | 0.4966 | 2.8479 | 3.1834 | -0.3356 |
| K=0 | rater_17 | 119 | 0.4286 | 0.6639 | 2.9328 | 3.3445 | -0.4118 |
| K=0 | rater_18 | 1060 | 0.4915 | 0.5811 | 2.8689 | 3.1934 | -0.3245 |
| K=0 | rater_19 | 1041 | 0.4111 | 0.6407 | 2.8578 | 3.4563 | -0.5985 |
| K=0 | rater_2 | 1601 | 0.6240 | 0.3923 | 2.8426 | 3.1099 | -0.2673 |
| K=0 | rater_20 | 75 | 0.6000 | 0.4133 | 2.8800 | 3.0267 | -0.1467 |
| K=0 | rater_21 | 358 | 0.5922 | 0.4358 | 2.8743 | 3.0251 | -0.1508 |
| K=0 | rater_22 | 241 | 0.5975 | 0.4191 | 2.8382 | 3.0664 | -0.2282 |
| K=0 | rater_23 | 774 | 0.4574 | 0.6408 | 2.8682 | 3.3411 | -0.4729 |
| K=0 | rater_24 | 259 | 0.4749 | 0.5637 | 2.8764 | 3.0386 | -0.1622 |
| K=0 | rater_25 | 27 | 0.8148 | 0.1852 | 2.9259 | 3.1111 | -0.1852 |
| K=0 | rater_26 | 199 | 0.5779 | 0.4623 | 2.8945 | 3.0050 | -0.1106 |
| K=0 | rater_27 | 587 | 0.6422 | 0.3731 | 2.8705 | 3.0256 | -0.1550 |
| K=0 | rater_3 | 325 | 0.5169 | 0.5292 | 2.7785 | 3.1046 | -0.3262 |
| K=0 | rater_4 | 607 | 0.4695 | 0.5552 | 2.8138 | 3.3130 | -0.4992 |
| K=0 | rater_5 | 224 | 0.4821 | 0.5893 | 2.7411 | 3.2768 | -0.5357 |
| K=0 | rater_6 | 1335 | 0.5176 | 0.5071 | 2.8337 | 3.1566 | -0.3228 |
| K=0 | rater_7 | 1211 | 0.5681 | 0.4806 | 2.8464 | 3.0958 | -0.2494 |
| K=0 | rater_8 | 359 | 0.4596 | 0.5961 | 2.8914 | 2.8858 | 0.0056 |
| K=0 | rater_9 | 744 | 0.5349 | 0.4758 | 2.8804 | 2.6680 | 0.2124 |
| Correct Raw K=3 | rater_1 | 856 | 0.5269 | 0.4907 | 2.9089 | 3.0164 | -0.1075 |
| Correct Raw K=3 | rater_10 | 781 | 0.4930 | 0.5544 | 2.8809 | 3.0026 | -0.1216 |
| Correct Raw K=3 | rater_11 | 1367 | 0.5369 | 0.4828 | 2.8508 | 2.9195 | -0.0688 |
| Correct Raw K=3 | rater_12 | 1220 | 0.5410 | 0.4770 | 2.9762 | 3.1385 | -0.1623 |
| Correct Raw K=3 | rater_13 | 889 | 0.5354 | 0.5208 | 3.0090 | 3.2868 | -0.2778 |
| Correct Raw K=3 | rater_14 | 31 | 0.5484 | 0.4516 | 2.8710 | 2.8065 | 0.0645 |
| Correct Raw K=3 | rater_15 | 988 | 0.5992 | 0.4069 | 3.0870 | 3.3198 | -0.2328 |
| Correct Raw K=3 | rater_16 | 447 | 0.5391 | 0.4765 | 2.9933 | 3.1834 | -0.1902 |
| Correct Raw K=3 | rater_17 | 119 | 0.4622 | 0.5966 | 3.0504 | 3.3445 | -0.2941 |
| Correct Raw K=3 | rater_18 | 1060 | 0.4764 | 0.5792 | 2.9651 | 3.1934 | -0.2283 |
| Correct Raw K=3 | rater_19 | 1041 | 0.5082 | 0.5187 | 3.1604 | 3.4563 | -0.2959 |
| Correct Raw K=3 | rater_2 | 1601 | 0.6184 | 0.3966 | 2.9806 | 3.1099 | -0.1293 |
| Correct Raw K=3 | rater_20 | 75 | 0.5467 | 0.4800 | 2.9467 | 3.0267 | -0.0800 |
| Correct Raw K=3 | rater_21 | 358 | 0.5642 | 0.4693 | 2.9134 | 3.0251 | -0.1117 |
| Correct Raw K=3 | rater_22 | 241 | 0.5809 | 0.4398 | 2.9585 | 3.0664 | -0.1079 |
| Correct Raw K=3 | rater_23 | 774 | 0.4832 | 0.5904 | 3.0840 | 3.3411 | -0.2571 |
| Correct Raw K=3 | rater_24 | 259 | 0.4788 | 0.5869 | 2.8919 | 3.0386 | -0.1467 |
| Correct Raw K=3 | rater_25 | 27 | 0.8148 | 0.1852 | 3.0741 | 3.1111 | -0.0370 |
| Correct Raw K=3 | rater_26 | 199 | 0.5327 | 0.5075 | 2.9196 | 3.0050 | -0.0854 |
| Correct Raw K=3 | rater_27 | 587 | 0.6133 | 0.4003 | 2.9148 | 3.0256 | -0.1107 |
| Correct Raw K=3 | rater_3 | 325 | 0.5415 | 0.4954 | 2.8800 | 3.1046 | -0.2246 |
| Correct Raw K=3 | rater_4 | 607 | 0.5371 | 0.4745 | 3.0758 | 3.3130 | -0.2372 |
| Correct Raw K=3 | rater_5 | 224 | 0.4866 | 0.5714 | 2.9732 | 3.2768 | -0.3036 |
| Correct Raw K=3 | rater_6 | 1335 | 0.5251 | 0.4996 | 2.9730 | 3.1566 | -0.1835 |
| Correct Raw K=3 | rater_7 | 1211 | 0.5516 | 0.4971 | 2.9092 | 3.0958 | -0.1866 |
| Correct Raw K=3 | rater_8 | 359 | 0.4429 | 0.6323 | 2.7939 | 2.8858 | -0.0919 |
| Correct Raw K=3 | rater_9 | 744 | 0.5430 | 0.4812 | 2.6761 | 2.6680 | 0.0081 |
| K=0 + Overall Rubric | rater_1 | 856 | 0.6028 | 0.4089 | 2.9276 | 3.0164 | -0.0888 |
| K=0 + Overall Rubric | rater_10 | 781 | 0.4878 | 0.5378 | 2.9693 | 3.0026 | -0.0333 |
| K=0 + Overall Rubric | rater_11 | 1367 | 0.5479 | 0.4653 | 2.9707 | 2.9195 | 0.0512 |
| K=0 + Overall Rubric | rater_12 | 1220 | 0.5672 | 0.4467 | 2.9623 | 3.1385 | -0.1762 |
| K=0 + Overall Rubric | rater_13 | 889 | 0.5399 | 0.5321 | 2.9483 | 3.2868 | -0.3386 |
| K=0 + Overall Rubric | rater_14 | 31 | 0.6452 | 0.3548 | 2.9677 | 2.8065 | 0.1613 |
| K=0 + Overall Rubric | rater_15 | 988 | 0.5830 | 0.4190 | 2.9656 | 3.3198 | -0.3543 |
| K=0 + Overall Rubric | rater_16 | 447 | 0.5369 | 0.4855 | 2.9485 | 3.1834 | -0.2349 |
| K=0 + Overall Rubric | rater_17 | 119 | 0.4454 | 0.6471 | 2.9664 | 3.3445 | -0.3782 |
| K=0 + Overall Rubric | rater_18 | 1060 | 0.4774 | 0.5868 | 2.9613 | 3.1934 | -0.2321 |
| K=0 + Overall Rubric | rater_19 | 1041 | 0.4457 | 0.5937 | 2.9587 | 3.4563 | -0.4976 |
| K=0 + Overall Rubric | rater_2 | 1601 | 0.6446 | 0.3660 | 2.9425 | 3.1099 | -0.1674 |
| K=0 + Overall Rubric | rater_20 | 75 | 0.6267 | 0.4000 | 3.0000 | 3.0267 | -0.0267 |
| K=0 + Overall Rubric | rater_21 | 358 | 0.5782 | 0.4497 | 2.9721 | 3.0251 | -0.0531 |
| K=0 + Overall Rubric | rater_22 | 241 | 0.5892 | 0.4274 | 2.9544 | 3.0664 | -0.1120 |
| K=0 + Overall Rubric | rater_23 | 774 | 0.4561 | 0.6382 | 2.9664 | 3.3411 | -0.3747 |
| K=0 + Overall Rubric | rater_24 | 259 | 0.4440 | 0.6139 | 2.9807 | 3.0386 | -0.0579 |
| K=0 + Overall Rubric | rater_25 | 27 | 0.7778 | 0.2222 | 2.9630 | 3.1111 | -0.1481 |
| K=0 + Overall Rubric | rater_26 | 199 | 0.5729 | 0.4673 | 2.9598 | 3.0050 | -0.0452 |
| K=0 + Overall Rubric | rater_27 | 587 | 0.6371 | 0.3748 | 2.9710 | 3.0256 | -0.0545 |
| K=0 + Overall Rubric | rater_3 | 325 | 0.5662 | 0.4708 | 2.8800 | 3.1046 | -0.2246 |
| K=0 + Overall Rubric | rater_4 | 607 | 0.5206 | 0.4942 | 2.9143 | 3.3130 | -0.3987 |
| K=0 + Overall Rubric | rater_5 | 224 | 0.5179 | 0.5491 | 2.8438 | 3.2768 | -0.4330 |
| K=0 + Overall Rubric | rater_6 | 1335 | 0.5288 | 0.4884 | 2.9393 | 3.1566 | -0.2172 |
| K=0 + Overall Rubric | rater_7 | 1211 | 0.5665 | 0.4715 | 2.9447 | 3.0958 | -0.1511 |
| K=0 + Overall Rubric | rater_8 | 359 | 0.4345 | 0.6295 | 2.9638 | 2.8858 | 0.0780 |
| K=0 + Overall Rubric | rater_9 | 744 | 0.4718 | 0.5376 | 2.9798 | 2.6680 | 0.3118 |
| Wrong K=3 + Overall Rubric | rater_1 | 856 | 0.5479 | 0.4696 | 2.9159 | 3.0164 | -0.1005 |
| Wrong K=3 + Overall Rubric | rater_10 | 781 | 0.4942 | 0.5378 | 2.9513 | 3.0026 | -0.0512 |
| Wrong K=3 + Overall Rubric | rater_11 | 1367 | 0.5574 | 0.4572 | 2.9407 | 2.9195 | 0.0212 |
| Wrong K=3 + Overall Rubric | rater_12 | 1220 | 0.5615 | 0.4541 | 2.9369 | 3.1385 | -0.2016 |
| Wrong K=3 + Overall Rubric | rater_13 | 889 | 0.5174 | 0.5534 | 2.9044 | 3.2868 | -0.3825 |
| Wrong K=3 + Overall Rubric | rater_14 | 31 | 0.6452 | 0.3548 | 2.9032 | 2.8065 | 0.0968 |
| Wrong K=3 + Overall Rubric | rater_15 | 988 | 0.5476 | 0.4666 | 2.9241 | 3.3198 | -0.3957 |
| Wrong K=3 + Overall Rubric | rater_16 | 447 | 0.5324 | 0.4989 | 2.9306 | 3.1834 | -0.2528 |
| Wrong K=3 + Overall Rubric | rater_17 | 119 | 0.4454 | 0.6218 | 2.9748 | 3.3445 | -0.3697 |
| Wrong K=3 + Overall Rubric | rater_18 | 1060 | 0.4821 | 0.5745 | 2.9245 | 3.1934 | -0.2689 |
| Wrong K=3 + Overall Rubric | rater_19 | 1041 | 0.4448 | 0.6061 | 2.9289 | 3.4563 | -0.5274 |
| Wrong K=3 + Overall Rubric | rater_2 | 1601 | 0.6152 | 0.4041 | 2.9107 | 3.1099 | -0.1993 |
| Wrong K=3 + Overall Rubric | rater_20 | 75 | 0.5867 | 0.4533 | 2.8933 | 3.0267 | -0.1333 |
| Wrong K=3 + Overall Rubric | rater_21 | 358 | 0.5838 | 0.4441 | 2.9609 | 3.0251 | -0.0642 |
| Wrong K=3 + Overall Rubric | rater_22 | 241 | 0.5519 | 0.4689 | 2.9544 | 3.0664 | -0.1120 |
| Wrong K=3 + Overall Rubric | rater_23 | 774 | 0.4793 | 0.6021 | 2.9535 | 3.3411 | -0.3876 |
| Wrong K=3 + Overall Rubric | rater_24 | 259 | 0.5135 | 0.5212 | 2.9653 | 3.0386 | -0.0734 |
| Wrong K=3 + Overall Rubric | rater_25 | 27 | 0.6667 | 0.3333 | 2.9259 | 3.1111 | -0.1852 |
| Wrong K=3 + Overall Rubric | rater_26 | 199 | 0.5628 | 0.4673 | 2.9196 | 3.0050 | -0.0854 |
| Wrong K=3 + Overall Rubric | rater_27 | 587 | 0.6320 | 0.3833 | 2.9284 | 3.0256 | -0.0971 |
| Wrong K=3 + Overall Rubric | rater_3 | 325 | 0.5108 | 0.5200 | 2.8123 | 3.1046 | -0.2923 |
| Wrong K=3 + Overall Rubric | rater_4 | 607 | 0.4926 | 0.5354 | 2.8731 | 3.3130 | -0.4399 |
| Wrong K=3 + Overall Rubric | rater_5 | 224 | 0.4554 | 0.6205 | 2.7723 | 3.2768 | -0.5045 |
| Wrong K=3 + Overall Rubric | rater_6 | 1335 | 0.5019 | 0.5251 | 2.8876 | 3.1566 | -0.2689 |
| Wrong K=3 + Overall Rubric | rater_7 | 1211 | 0.5648 | 0.4781 | 2.8935 | 3.0958 | -0.2023 |
| Wrong K=3 + Overall Rubric | rater_8 | 359 | 0.4847 | 0.5766 | 2.9499 | 2.8858 | 0.0641 |
| Wrong K=3 + Overall Rubric | rater_9 | 744 | 0.4839 | 0.5363 | 2.9597 | 2.6680 | 0.2917 |
| Correct K=3 + Overall Rubric | rater_1 | 856 | 0.5432 | 0.4790 | 2.8762 | 3.0164 | -0.1402 |
| Correct K=3 + Overall Rubric | rater_10 | 781 | 0.5019 | 0.5275 | 2.8822 | 3.0026 | -0.1204 |
| Correct K=3 + Overall Rubric | rater_11 | 1367 | 0.5545 | 0.4594 | 2.8552 | 2.9195 | -0.0644 |
| Correct K=3 + Overall Rubric | rater_12 | 1220 | 0.5615 | 0.4549 | 2.9639 | 3.1385 | -0.1746 |
| Correct K=3 + Overall Rubric | rater_13 | 889 | 0.5242 | 0.5321 | 2.9798 | 3.2868 | -0.3071 |
| Correct K=3 + Overall Rubric | rater_14 | 31 | 0.7097 | 0.2903 | 2.7742 | 2.8065 | -0.0323 |
| Correct K=3 + Overall Rubric | rater_15 | 988 | 0.6053 | 0.3978 | 3.0354 | 3.3198 | -0.2844 |
| Correct K=3 + Overall Rubric | rater_16 | 447 | 0.5548 | 0.4564 | 2.9597 | 3.1834 | -0.2237 |
| Correct K=3 + Overall Rubric | rater_17 | 119 | 0.4958 | 0.5630 | 3.0336 | 3.3445 | -0.3109 |
| Correct K=3 + Overall Rubric | rater_18 | 1060 | 0.4868 | 0.5632 | 2.9264 | 3.1934 | -0.2670 |
| Correct K=3 + Overall Rubric | rater_19 | 1041 | 0.5245 | 0.4966 | 3.1018 | 3.4563 | -0.3545 |
| Correct K=3 + Overall Rubric | rater_2 | 1601 | 0.6140 | 0.3948 | 2.9288 | 3.1099 | -0.1811 |
| Correct K=3 + Overall Rubric | rater_20 | 75 | 0.5867 | 0.4400 | 2.9600 | 3.0267 | -0.0667 |
| Correct K=3 + Overall Rubric | rater_21 | 358 | 0.5782 | 0.4525 | 2.9078 | 3.0251 | -0.1173 |
| Correct K=3 + Overall Rubric | rater_22 | 241 | 0.5768 | 0.4440 | 2.9212 | 3.0664 | -0.1452 |
| Correct K=3 + Overall Rubric | rater_23 | 774 | 0.5078 | 0.5581 | 3.0362 | 3.3411 | -0.3049 |
| Correct K=3 + Overall Rubric | rater_24 | 259 | 0.4981 | 0.5405 | 2.8842 | 3.0386 | -0.1544 |
| Correct K=3 + Overall Rubric | rater_25 | 27 | 0.7407 | 0.2593 | 3.0000 | 3.1111 | -0.1111 |
| Correct K=3 + Overall Rubric | rater_26 | 199 | 0.5879 | 0.4472 | 2.8894 | 3.0050 | -0.1156 |
| Correct K=3 + Overall Rubric | rater_27 | 587 | 0.6320 | 0.3833 | 2.9114 | 3.0256 | -0.1141 |
| Correct K=3 + Overall Rubric | rater_3 | 325 | 0.5354 | 0.4923 | 2.8585 | 3.1046 | -0.2462 |
| Correct K=3 + Overall Rubric | rater_4 | 607 | 0.5239 | 0.4926 | 2.9918 | 3.3130 | -0.3213 |
| Correct K=3 + Overall Rubric | rater_5 | 224 | 0.4866 | 0.5759 | 2.9330 | 3.2768 | -0.3438 |
| Correct K=3 + Overall Rubric | rater_6 | 1335 | 0.5326 | 0.4891 | 2.9356 | 3.1566 | -0.2210 |
| Correct K=3 + Overall Rubric | rater_7 | 1211 | 0.5599 | 0.4839 | 2.8927 | 3.0958 | -0.2031 |
| Correct K=3 + Overall Rubric | rater_8 | 359 | 0.4652 | 0.5933 | 2.8050 | 2.8858 | -0.0808 |
| Correct K=3 + Overall Rubric | rater_9 | 744 | 0.5645 | 0.4583 | 2.7043 | 2.6680 | 0.0363 |

## Same-essay analysis

既存same_essay_pairs関数を再利用。common set内の同一source_row_id・異なるraterの非順序pairを対象とする。方向再現率の分母はGold不一致pair全体（予測同点も不正解）。Gold一致時の予測不一致率の分母はGold一致pair全体。

| condition | same_essay_rater_pair_count | gold_disagreement_pair_count | gold_agreement_pair_count | prediction_disagreement_pair_count | gold_disagreement_direction_reproduced_count | gold_disagreement_direction_reproduced_rate | prediction_disagreement_rate_among_gold_agreement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| k0 | 8849 | 4161 | 4688 | 91 | 18 | 0.0043 | 0.0094 |
| raw_k3 | 8849 | 4161 | 4688 | 2514 | 735 | 0.1766 | 0.2794 |
| k0_rubric | 8849 | 4161 | 4688 | 39 | 10 | 0.0024 | 0.0045 |
| wrong_k3_rubric | 8849 | 4161 | 4688 | 2084 | 510 | 0.1226 | 0.2357 |
| correct_k3_rubric | 8849 | 4161 | 4688 | 2100 | 614 | 0.1476 | 0.2349 |

## Pilot vs Full-scale

Pilotは既存値をそのまま転載。Raw K3は既存CSVのuser supplied値（丸め済み）。samplingが異なるため、研究経緯を示す記述的併記のみで、Pilot対Full-scaleの統計比較は行わない。

| scope | Condition | N | Accuracy | MAE | RMSE | QWK | provenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pilot | K=0 | 100 | 0.5500 | 0.4900 | 0.7550 | 0.2893 | outputs/rubric_rater_placebo/rubric_rater_placebo_summary.csv |
| Full-scale common N | K=0 | 17725 | 0.5361 | 0.4993 | 0.7550 | 0.2650 | main_5condition_results.csv |
| Pilot | Correct Raw K=3 | 100 | 0.5300 | 0.5400 | 0.8246 | 0.1536 | outputs/full_history_only_experiment/pilot_full_comparison.csv; user supplied; rounded existing values |
| Full-scale common N | Correct Raw K=3 | 17725 | 0.5386 | 0.4930 | 0.7460 | 0.3141 | main_5condition_results.csv |
| Pilot | K=0 + Overall Rubric | 100 | 0.5400 | 0.4800 | 0.7211 | 0.2100 | outputs/rubric_rater_placebo/rubric_rater_placebo_summary.csv |
| Full-scale common N | K=0 + Overall Rubric | 17725 | 0.5414 | 0.4886 | 0.7407 | 0.1783 | main_5condition_results.csv |
| Pilot | Wrong K=3 + Overall Rubric | 100 | 0.5200 | 0.5000 | 0.7348 | 0.3448 | outputs/rubric_rater_placebo/rubric_rater_placebo_summary.csv |
| Full-scale common N | Wrong K=3 + Overall Rubric | 17725 | 0.5314 | 0.5022 | 0.7549 | 0.3178 | main_5condition_results.csv |
| Pilot | Correct K=3 + Overall Rubric | 100 | 0.5600 | 0.4800 | 0.7483 | 0.2899 | outputs/rubric_rater_placebo/rubric_rater_placebo_summary.csv |
| Full-scale common N | Correct K=3 + Overall Rubric | 17725 | 0.5492 | 0.4780 | 0.7301 | 0.3556 | main_5condition_results.csv |

## Interpretation notes

以下は上記の事実に対する解釈である。AはRaw History追加の比較、BはRubric単独追加、Cはwrong-rater履歴追加、Dは本人履歴追加、Eは同一Rubric下の比較的クリーンなpersonalization比較、FはCorrect History下のRubric-associated improvementである。

FではPrompt指示文にも差があるため、Rubricだけの純粋な因果効果とは断定できない。

比較A: Accuracy差 +0.002539、MAE差 -0.006319、QWK差 +0.049109。指標別の方向と上記CIを併読する。

比較B: Accuracy差 +0.005360、MAE差 -0.010719、QWK差 -0.086773。指標別の方向と上記CIを併読する。

比較C: Accuracy差 -0.010042、MAE差 +0.013653、QWK差 +0.139518。指標別の方向と上記CIを併読する。

比較D: Accuracy差 +0.007786、MAE差 -0.010550、QWK差 +0.177324。指標別の方向と上記CIを併読する。

比較E: Accuracy差 +0.017828、MAE差 -0.024203、QWK差 +0.037806。指標別の方向と上記CIを併読する。

比較F: Accuracy差 +0.010606、MAE差 -0.014951、QWK差 +0.041443。指標別の方向と上記CIを併読する。

Raw History（A）はQWKを改善し、その95% CIはゼロを跨がない。一方、AccuracyとMAEのCIはゼロを含むため、これらの改善を明確とは判断しない。

Rubric単独（B）はAccuracyとMAEを改善するが、QWKは低下する。Score 3集中が強まるため、Accuracyだけでは性能を評価できない。Wrong履歴追加（C）はQWKを改善する一方、AccuracyとMAEを悪化させる。

本人履歴＋Rubricは5条件中でAccuracy/QWKが最高、MAE/RMSEが最低である。EではAccuracy・MAE・QWKの改善方向に95% CIがゼロを跨がず、同一Rubric下で本人履歴の追加価値を支持する。ただしこのCIはtarget単位bootstrapに基づく。

FでもAccuracy・MAE・QWKのCIは改善方向でゼロを跨がないが、Prompt指示文の差を含む関連的な改善であり、Rubricだけの因果効果とは解釈しない。

History条件でも予測はScore 3に強く集中している。Correct＋RubricのGold分布とのTV距離はWrong＋Rubricより小さくないため、Correctの改善を分布拡大だけで説明することはできない。

Correct＋Rubricのsame-essay方向再現率はWrong＋Rubricより高いが、Raw Historyより低い。Gold不一致の方向再現は限定的で、Gold一致pairにも予測不一致が生じる。集計指標の改善は個別採点者差の十分な再現を保証しない。

## Reproducibility

既存入力のSHA-256、環境、bootstrap設定をmetadata.jsonに保存。GPU推論・model loading・予測再生成・retry・parser/Prompt変更・history/実験targetのresampling・dataset変更・既存output上書き・git commit/pushは実施していない。
