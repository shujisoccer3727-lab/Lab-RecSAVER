# ELLIPSE Trait profile基礎分析レポート

## 1. データセット概要

`data/processed/rater_essay_wide.csv`の17,780サンプルから、Overallと6 Traitがすべて1～5の17,731サンプルを主要分析に使用した。除外は49サンプルで、内訳はOverall範囲外44件、Trait profile範囲外41件（重複あり）、必要スコア欠損0件だった。元値は変更していない。有効データには8,876件のsource essay、8,866件のユニークFilename、27名の採点者が含まれる。

採点者別の有効件数は最小27、中央値607.0、平均656.7、最大1602だった。採点者別件数は`[{'rater_id': 'rater_1', 'valid_sample_count': 857, 'valid_unique_essay_count': 857, 'excluded_sample_count': 3}, {'rater_id': 'rater_2', 'valid_sample_count': 1602, 'valid_unique_essay_count': 1602, 'excluded_sample_count': 7}, {'rater_id': 'rater_3', 'valid_sample_count': 325, 'valid_unique_essay_count': 325, 'excluded_sample_count': 6}, {'rater_id': 'rater_4', 'valid_sample_count': 607, 'valid_unique_essay_count': 607, 'excluded_sample_count': 2}, {'rater_id': 'rater_5', 'valid_sample_count': 225, 'valid_unique_essay_count': 225, 'excluded_sample_count': 1}, {'rater_id': 'rater_6', 'valid_sample_count': 1336, 'valid_unique_essay_count': 1336, 'excluded_sample_count': 4}, {'rater_id': 'rater_7', 'valid_sample_count': 1211, 'valid_unique_essay_count': 1211, 'excluded_sample_count': 2}, {'rater_id': 'rater_8', 'valid_sample_count': 359, 'valid_unique_essay_count': 359, 'excluded_sample_count': 1}, {'rater_id': 'rater_9', 'valid_sample_count': 745, 'valid_unique_essay_count': 745, 'excluded_sample_count': 3}, {'rater_id': 'rater_10', 'valid_sample_count': 781, 'valid_unique_essay_count': 781, 'excluded_sample_count': 1}, {'rater_id': 'rater_11', 'valid_sample_count': 1367, 'valid_unique_essay_count': 1367, 'excluded_sample_count': 3}, {'rater_id': 'rater_12', 'valid_sample_count': 1220, 'valid_unique_essay_count': 1220, 'excluded_sample_count': 2}, {'rater_id': 'rater_13', 'valid_sample_count': 889, 'valid_unique_essay_count': 889, 'excluded_sample_count': 1}, {'rater_id': 'rater_14', 'valid_sample_count': 31, 'valid_unique_essay_count': 31, 'excluded_sample_count': 0}, {'rater_id': 'rater_15', 'valid_sample_count': 988, 'valid_unique_essay_count': 988, 'excluded_sample_count': 3}, {'rater_id': 'rater_16', 'valid_sample_count': 447, 'valid_unique_essay_count': 447, 'excluded_sample_count': 0}, {'rater_id': 'rater_17', 'valid_sample_count': 119, 'valid_unique_essay_count': 119, 'excluded_sample_count': 0}, {'rater_id': 'rater_18', 'valid_sample_count': 1060, 'valid_unique_essay_count': 1060, 'excluded_sample_count': 2}, {'rater_id': 'rater_19', 'valid_sample_count': 1041, 'valid_unique_essay_count': 1041, 'excluded_sample_count': 2}, {'rater_id': 'rater_20', 'valid_sample_count': 75, 'valid_unique_essay_count': 75, 'excluded_sample_count': 0}, {'rater_id': 'rater_21', 'valid_sample_count': 358, 'valid_unique_essay_count': 358, 'excluded_sample_count': 1}, {'rater_id': 'rater_22', 'valid_sample_count': 241, 'valid_unique_essay_count': 241, 'excluded_sample_count': 0}, {'rater_id': 'rater_23', 'valid_sample_count': 774, 'valid_unique_essay_count': 774, 'excluded_sample_count': 4}, {'rater_id': 'rater_24', 'valid_sample_count': 260, 'valid_unique_essay_count': 260, 'excluded_sample_count': 0}, {'rater_id': 'rater_25', 'valid_sample_count': 27, 'valid_unique_essay_count': 27, 'excluded_sample_count': 0}, {'rater_id': 'rater_26', 'valid_sample_count': 199, 'valid_unique_essay_count': 199, 'excluded_sample_count': 1}, {'rater_id': 'rater_27', 'valid_sample_count': 587, 'valid_unique_essay_count': 587, 'excluded_sample_count': 0}]`で、詳細は`rater_sample_counts.csv`に示す。

## 2. Overall・Traitスコア分布

- Overall: 平均 3.128、中央値 3.0、標準偏差 0.758
- Cohesion: 平均 3.135、中央値 3.0、標準偏差 0.811
- Syntax: 平均 3.049、中央値 3.0、標準偏差 0.784
- Vocabulary: 平均 3.246、中央値 3.0、標準偏差 0.718
- Phraseology: 平均 3.129、中央値 3.0、標準偏差 0.797
- Grammar: 平均 3.072、中央値 3.0、標準偏差 0.844
- Conventions: 平均 3.122、中央値 3.0、標準偏差 0.813

Overallの平均は3.128、標準偏差は0.758だった。尺度が同じでも各Traitの評価内容は異なるため、平均値だけで単純比較しない。

## 3. 採点者ごとの基本的な採点傾向

Overall平均が低い側の3名は`[{'rater_id': 'rater_9', 'count': 745, 'mean': 2.667}, {'rater_id': 'rater_14', 'count': 31, 'mean': 2.806}, {'rater_id': 'rater_8', 'count': 359, 'mean': 2.886}]`、高い側の3名は`[{'rater_id': 'rater_19', 'count': 1041, 'mean': 3.456}, {'rater_id': 'rater_17', 'count': 119, 'mean': 3.345}, {'rater_id': 'rater_23', 'count': 774, 'mean': 3.341}]`だった。スコア3の使用割合が最も高い採点者はrater_25（81.5%）、1または5の使用割合が最も高い採点者はrater_17（10.9%）だった。Overall標準偏差はrater_25の0.424からrater_8の0.894まで分布した。これらは担当答案の難易度や構成を統制していない未調整の評価傾向であり、採点者の厳しさ・甘さを示す確定的な結果ではない。

## 4. 採点者ごとのTrait profile

採点者内部の6 Trait平均からの差が大きい例は`[{'rater_id': 'rater_21', 'trait': 'Vocabulary', 'mean': 3.411, 'rater_six_trait_mean': 2.999, 'relative_trait_tendency': 0.412}, {'rater_id': 'rater_27', 'trait': 'Conventions', 'mean': 3.513, 'rater_six_trait_mean': 3.131, 'relative_trait_tendency': 0.382}, {'rater_id': 'rater_25', 'trait': 'Syntax', 'mean': 3.519, 'rater_six_trait_mean': 3.142, 'relative_trait_tendency': 0.377}, {'rater_id': 'rater_17', 'trait': 'Conventions', 'mean': 3.731, 'rater_six_trait_mean': 3.381, 'relative_trait_tendency': 0.35}, {'rater_id': 'rater_27', 'trait': 'Vocabulary', 'mean': 2.785, 'rater_six_trait_mean': 3.131, 'relative_trait_tendency': -0.346}, {'rater_id': 'rater_3', 'trait': 'Vocabulary', 'mean': 3.394, 'rater_six_trait_mean': 3.087, 'relative_trait_tendency': 0.307}, {'rater_id': 'rater_26', 'trait': 'Cohesion', 'mean': 3.307, 'rater_six_trait_mean': 3.001, 'relative_trait_tendency': 0.306}, {'rater_id': 'rater_27', 'trait': 'Grammar', 'mean': 3.426, 'rater_six_trait_mean': 3.131, 'relative_trait_tendency': 0.295}]`だった。`relative_trait_tendency`は採点者内部の相対的なTrait profileを記述する探索的指標であり、答案構成を統制していない。

## 5. TraitとOverallの関係

- Cohesion: Pearson 0.705、Spearman 0.692
- Syntax: Pearson 0.729、Spearman 0.716
- Vocabulary: Pearson 0.685、Spearman 0.667
- Phraseology: Pearson 0.717、Spearman 0.703
- Grammar: Pearson 0.685、Spearman 0.669
- Conventions: Pearson 0.662、Spearman 0.650
- trait_mean: Pearson 0.874、Spearman 0.865
- trait_min: Pearson 0.733、Spearman 0.714
- trait_max: Pearson 0.732、Spearman 0.718
- trait_std: Pearson 0.024、Spearman 0.031

6 TraitのうちOverallとのPearson相関が最も強かったのはSyntax（0.729）だった。相関は関連を示すが、採点者がそのTraitを因果的に重視したことや、Overall決定時の重みを直接示すものではない。

## 6. Trait平均とOverallの関係

保存済み`trait_mean`と6 Traitからの再計算値の最大誤差は4.44e-16だった。Trait平均は平均3.126、標準偏差0.634である。OverallとのPearson相関は0.874、Spearman相関は0.865である。一方、四捨五入したTrait平均とOverallの一致率は82.6%、平均絶対差は0.306だった。Overall別のTrait平均分布は`[{'Overall': 1, 'count': 125, 'mean': 1.52, 'median': 1.5, 'std': 0.319, 'min': 1.0, 'max': 2.5}, {'Overall': 2, 'count': 3196, 'mean': 2.326, 'median': 2.333, 'std': 0.261, 'min': 1.333, 'max': 3.5}, {'Overall': 3, 'count': 9235, 'mean': 3.023, 'median': 3.0, 'std': 0.326, 'min': 2.0, 'max': 4.0}, {'Overall': 4, 'count': 4640, 'mean': 3.754, 'median': 3.667, 'std': 0.304, 'min': 2.5, 'max': 4.833}, {'Overall': 5, 'count': 535, 'mean': 4.593, 'median': 4.667, 'std': 0.249, 'min': 3.5, 'max': 5.0}]`だった。

同じTrait meanで異なるOverallが存在するサンプルは17,657件、6 Traitが完全に同じでOverallが異なるprofileは386組（該当15,785サンプル）あった。したがって、Trait平均とOverallには強い関連があっても、Trait平均の単純な四捨五入だけでは全サンプルのOverallを再現できない。

## 7. 採点者ごとのTrait→Overall関係

採点者別Pearson相関の範囲が最も広かった予測変数はConventionsで、最小0.309、最大0.763だった。採点件数やスコア分散が異なるため単純比較には注意が必要だが、TraitとOverallの関連パターンが採点者間で一様ではない可能性を探索する根拠になる。

採点者別の未調整`Overall - trait_mean`平均の下位・上位は`[{'rater_id': 'rater_9', 'count': 745, 'mean': -0.11}, {'rater_id': 'rater_27', 'count': 587, 'mean': -0.105}, {'rater_id': 'rater_12', 'count': 1220, 'mean': -0.091}]` / `[{'rater_id': 'rater_4', 'count': 607, 'mean': 0.103}, {'rater_id': 'rater_7', 'count': 1211, 'mean': 0.101}, {'rater_id': 'rater_11', 'count': 1367, 'mean': 0.098}]`だった。この差も担当答案を統制していない。

## 8. 担当答案構成の違い

採点者別の平均単語数はrater_5の311.2語からrater_14の477.0語まで分布した。本文長だけで答案難易度を説明することはできないが、採点者ごとに担当答案構成が完全には同一でない可能性を示す補助情報である。

## 9. 現時点で分かること

Overallと各TraitおよびTrait平均には統計的な関連があり、6 Traitを構造化された中間情報として分析する意味がある。同時に、同一Trait meanや同一Trait profileでもOverallが異なる実例が存在する。採点者別のTraitとの相関、Trait profile、`Overall - trait_mean`にも探索的な違いが観察された。

## 10. 現時点では言えないこと

採点者平均の高低だけから厳しさ・甘さを断定できない。TraitとOverallの相関を因果的な重みと解釈できない。担当答案の難易度、採点件数、スコア範囲などを統制していないため、観察差を採点者固有の効果として確定できない。

## 11. Rec-SAVER型実験への示唆

6 TraitはOverallと関連する構造化中間情報として利用候補になるが、単純なTrait平均だけではOverallを完全には説明できない。採点者別の関連パターンが一様でない探索的結果があるため、採点者IDや過去のTrait→Overall履歴を入力へ含める価値を比較実験で検証できる。次段階では、同じまたは近いTrait profileに対する採点者別Overall差、採点者履歴あり・なしの予測性能差、答案構成を統制した後にも関連パターン差が残るかを統計的に検証する必要がある。
