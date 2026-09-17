## 実測結果の解釈

固定100-target V1の生成・検証・評価処理は完了した。Predictionは再生成せず、既存Accuracy 0.56、MAE 0.48、RMSE 0.7483、QWK 0.2899の出力をそのまま評価した。Reference生成・Self-verificationは2026-09-12に完了し、保存済み結果のmetric計算と最終確認は2026-09-14に実施した。

Verified Referenceを確保できたのは84/100 target（84%）、計212件。平均2.12件、中央値3件で、0/1/2/3件のtarget数は16/8/24/52だった。未coverageの16件は、漏洩なし候補を1件も確保できなかった11件と、候補は確保できたが検証を通過しなかった5件に分かれる。

生成821 attempt中、Goldの直接明示は586件（71.38%）と多かった。初回300 attemptから採用できた111候補に、追加521 attemptによる123候補が加わり、漏洩なし候補234件を確保した。初回に漏洩なし候補が0件だったtargetのうち22件で、retryにより1件以上を確保した。3候補を揃えられたのは61 target、上限到達時に不足が残ったのは39 target。他score明示5件はGold明示との重複4件を含むため、除外attempt総数は587件である。

漏洩なし候補のSelf-verification通過率は212/234 = 90.60%。スコア明示を除外しても定量評価は84件で成立しており、提示された分類ではPattern Bの「retryによる回復」に対応する。ただし全targetをカバーできておらず、運用上のReference生成コストと不足が残る。単一実行のため、反復実験における安定性までは確認していない。

特にGold score別coverageは、Gold 2が9/18（50%）、Gold 3が48/54（88.89%）、Gold 4が24/25（96%）、Gold 5が3/3（100%）だった。84件の平均metricを無条件に100件全体へ一般化しない。Gold 5はn=3の小標本である。

正解群48件と不正解群36件では、BLEU・ROUGE-1・METEOR・BERTScoreのtarget内max/meanのすべてで正解群が高かった。例えばtarget内meanの群平均は、BERTScore 0.9161対0.8938、ROUGE-1 0.5692対0.4813、METEOR 0.4005対0.3211。Pattern Dに対応する探索的な正の関連が見られる。ただし因果関係や統計的有意差を示した結果ではなく、Gold-conditioned referenceと共通モデル・Rubricによる評価設計の影響を受ける可能性がある。

Score error別にも、error 0 → 1 → 2以上で全metricのmax/meanが順に低下した。BERTScoreのtarget内meanは0.9161 → 0.8950 → 0.8845。ただし評価件数は48 → 32 → 4件であり、特にerror 2以上の結果は小標本の探索的結果として扱う。

Verified Referenceが複数ある76 target、180ペアのlexical Jaccardは平均0.5721、中央値0.5443。完全一致は4ペア、Jaccard 0.9以上は15ペアだった。同一文のみのpoolではない一方、語彙的に非常に近いReferenceもあり、意味的な多様性は別途確認が必要である。

採点者のpersonality/background等に関するkeyword warningは0件だった。これは属性hallucinationが存在しない証明ではない。Parse/context errorはいずれも0件。保存済み全Self-verification PromptをGold引数なしで再構成して一致を確認し、元prediction・Rubric・parser・dataset等のSHA-256も一致した。未処理の生成requestはない。

結論として、Reasoning Evaluation V1は実装・100-target実行を完了し、84 targetを4指標で評価できた。一方で、漏洩率の高さとGold 2のcoverage不足が改善課題として残る。Verified Referenceは人間のGold Reasoningではなく、モデルの自己整合性で選別した参照説明として扱う。
