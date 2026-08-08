# データプロファイル

## Raw

- ファイル: `data/ellipsis_raw_rater_scores_anon_all_essay.csv`
- 形式: UTF-8、カンマ区切り
- 形状: 8,890行 × 21列
- ユニークFilename: 8,880
- 元ファイルは変更しない。

## Processed wide

- ファイル: `data/processed/rater_essay_wide.csv`
- 単位: 1行＝1エッセイ×1採点者
- 形状: 17,780行 × 21列
- 採点者: 27名
- Overallと6 Traitがすべて1～5: 17,731サンプル
- 主要分析からの除外: 49サンプル
- 有効データのsource essay: 8,876件
- 有効データのユニークFilename: 8,866件

無効値はprocessedデータから削除・補正せず、主要分析時にマスクする。新しい分析表は`outputs/basic_analysis/tables/`に保存する。
