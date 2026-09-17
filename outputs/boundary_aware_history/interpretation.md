## 結果の解釈と次段階

今回の100件では、Boundary-awareの明確な優位性は確認できなかった。Accuracyは1 percentage point低下、MAEは0.01増加、RMSEは0.0067増加し、QWKのみ0.0116改善した。予測一致は91/100件で、変更9件のうち改善4件・悪化5件だった。

提示された分類ではPattern Dに近い小差・混合の結果と解釈する。ただし統計的同等性を検定したわけではない。Score 3への集中が少し緩む一方でAccuracy/MAE/RMSEが悪化するという、Pattern Cの軽微な傾向もある。Pattern Aのような複数主要指標の改善はなく、Historyを境界として比較させるinstructionがcalibrationを改善したとは結論できない。

Score 3比率は79%から76%へ3 percentage points低下したが、Goldの54%よりまだ22 points高い。使用スコアは両条件とも2/3/4の3種類で、Score 5は依然0%。3→2はGold方向1件・逆方向2件、3→4はGold方向2件・逆方向1件と相殺している。さらに2→3が2件（改善1・悪化1）、4→3が1件（悪化）あり、全体で絶対誤差が1点増加した。

Rater別MAEでは改善2・同じ16・悪化3。改善raterはrater_19（n=3）とrater_24（n=1）で、ともに小標本。rater_7はMAEが同じでもAccuracyが0.60→0.50と低下しており、MAEによるsameを全指標の不変と解釈しない。

本結果を次段階へ進む根拠として十分に有望とは判断せず、Wrong-rater条件は実行していない。今回の結論は固定100件・単一生成実行の範囲に限定する。

## Reasoningの目視確認メモ（探索的）

予測変化が9件のみだったため、reasoning_examples.jsonと本レポートには変更全9件のExisting / Boundary-aware説明を保存した。正式なReasoning評価ではない。

- 1881:2（Gold 2、3→2、改善）：ExistingはScore 3記述への適合を説明。Boundary-awareはScore 2と3を明示比較したが、履歴の具体的参照はない。
- 2016:1（Gold 3、3→2、悪化）：Boundary-awareは過去のScore 3例より言語・構成の問題が大きいと説明。履歴比較の言及があっても正解につながるとは限らない。
- 2840:1（Gold 4、3→4、改善）：Boundary-awareは過去のScore 3例に対して構文の多様さと誤りの少なさを比較し、4を選択した。
- 2615:2（Gold 2、2→3、悪化）：Boundary-awareはHistory ID=5269:2を挙げ、主に3対4を比較している。元の予測である2との境界説明は不足している。
- 4718:2（Gold 5、4→3、悪化）：Boundary-awareはHistory 3のScore 4、History 2のScore 2の間として3を説明したが、Goldからは離れた。

隣接スコアや履歴を比較する表現は確認できるが、Rubricに沿った一般的な言語・構成の説明が多く、具体的なEssayの箇所を示す説明は乏しい。履歴への言及や出力された説明だけから、実際の内部的な履歴活用やScore 3を機械的に選んだかどうかは判定できない。

自動監査はhistory言及74%、rubric明示言及12%、隣接比較検出33%。rubricという語がない説明でもRubricの表現を使っている場合があり、12%はRubric利用率ではない。1881:2の「Score 2 than a Score 3」は実際には比較表現だが、今回の保守的heuristicは単独のthanを対比語に含めないため見逃す。33%も実際の比較率とは区別する。
