# Pilot report

状態: 30/30 targets checkpointed; valid JSON/schema 30/30 attempted targets.
Full 1,000件は未承認。Pilot完了後に停止し、明示承認を得る。

設定: {"temperature": 0.2, "top_p": 0.8, "max_tokens": 768}; max_model_len=8192; K=3; English.
Aのmax_tokens=384に対し、長いJSON用に768を初期候補として選択。最終推奨は実測後に判断。
選択: Gold proportional largest-remainder quotas; seeded shuffle; prefer least selected rater; seed=20260914。対象IDとGold/raterはpilot_targets.csv。

出力token数: [251, 242, 286, 344, 324, 298, 268, 288, 337, 270, 252, 285, 338, 301, 274, 265, 279, 275, 297, 271, 288, 322, 292, 358, 261, 272, 289, 337, 244, 319]
length終了attempt数: 0 / 30
retry総数: 0
失敗・除外: []

integrity_audit.csv: 1,000件の既存A再利用・履歴一致・重複Essay排除・Gold改変不変性を確認。
参照IDはparse()で提供済みK=3内に限定。全入出力・人手確認欄: reasoning_review_examples.md。
構造の出力率は内容の正しさを示さない。人手評価は未実施。


## Pilot完了時の確認

30件実行、schema有効 30/30。出力token min/median/max=242/287/358。
length終了=0/30 attempts。
retry総数=0。
不正な履歴ID・bool型scoreの拒否もCPUチェック済み。

生成されたA'のscore分布: {3: 23, 4: 7}。
「insufficient evidence」の文言は不確実性の留保としても使われるため、その出現率を「傾向推定を断念した率」と同一視できない。

### 推奨と停止点

現行Promptのまま1,000件へ進むことは推奨しない。下記のAI予備確認では一般的なRubric表現の反復、具体的根拠の弱さ、匿名化表記への反応が見られる。
Prompt改訂候補は、履歴の具体的な対照例と記録済みscoreの対応を求め、本文から短い引用で根拠を示し、匿名化placeholderを言語誤りに数えないと明記すること。
改訂版は別ファイル・別出力先で30件を再実行し、現行の失敗例も保持して比較する。
今回のmax_tokens=768は切断検査の実測に基づいて検討する。512は未検証であり確定設定とはしない。
入力K=3・temperature=.2・top_p=.8・max_model_len=8192は維持する。
ここで停止。本実験の最終Promptは未確定、承認前にfullを実行しない。

### 代表5例（AIによる予備確認。人手評価ではない）

| target_id | Gold | A | A' | 生成された評価傾向 | 新しい採点理由 | 気になる点 |
|---|---:|---:|---:|---|---|---|
| 7497:1 | 2 | 3 | 3 | The rater tends to assign an Overall score of 3 when the essay demonstrates some facility in language use, with occasional inaccuracies and errors that impede communication. The organization is generally controlled, but there are some issues with cohesion and syntax. | The target essay shows some facility in language use with occasional inaccuracies and errors that impede communication. There are issues with cohesion and syntax, but the organization is generally controlled. / The rater's tendency to assign a score of 3 aligns with the target essay's demonstrated language facility, occasional inaccuracies, and controlled organization. / Based on the rubric and the rater's tendency, the predicted Overall score is 3, as the essay demonstrates some facility in language use with occasional inaccuracies and errors that impede communication, and the organization is generally controlled. | 傾向とEssay evidenceがRubricの一般的表現に近く、固有の本文根拠が弱い。 |
| 6168:2 | 2 | 3 | 3 | The rater tends to assign an Overall score that aligns with the Trait scores, often giving a score of 3 when the Trait scores are generally around 3-4. | The essay demonstrates limited facility in sentence formation, word choice, and mechanics, with occasional errors in grammar and syntax. The organization is partially developed, and there are instances where the connection between ideas is absent or unsuccessful. / Given the rater's history of assigning Overall scores that align with the Trait scores, and the target essay's likely Trait scores around 3-4, the rater is likely to assign an Overall score of 3. / The essay's language inaccuracies and organizational issues impede communication in some cases, aligning with the rubric for a score of 3. | 未知の対象Traitを3–4程度と推測して説明している。Gold入力ではないが、根拠としての妥当性に注意。 |
| 4163:2 | 3 | 3 | 3 | The rater tends to assign an Overall score of 3 when the essay demonstrates a generally controlled organization and a mix of strengths and weaknesses in language use, with occasional errors in grammar and vocabulary. | The target essay demonstrates a generally controlled organization with clear sections and examples. However, there are occasional errors in grammar, vocabulary, and syntax, such as 'succesful', 'probable', and 'appropiate'. The essay also contains some awkward phrasing and minor inconsistencies. / The rater's tendency to assign a score of 3 for essays with controlled organization and occasional language inaccuracies aligns with the target essay's features. / Given the essay's controlled organization and a mix of strengths and weaknesses in language use, with occasional errors that sometimes impede communication, the predicted Overall score is 3. | 具体的な単語を挙げる比較的具体的な例。ただし綴りの誤りをgrammar等と混同していないか要確認。 |
| 8814:1 | 3 | 3 | 3 | The rater tends to assign a score of 3 when the essay demonstrates some facility in language use, with occasional errors in grammar and syntax, and generally controlled organization, but with some communication impeded by language inaccuracies. | The target essay demonstrates some facility in language use with occasional errors in grammar and syntax, such as 'videi' instead of 'video', 'nany' instead of 'many', and 'Generic_City' which seems out of place. The organization is generally controlled, but there are some communication issues due to language inaccuracies. / The rater's tendency to assign a score of 3 aligns with the target essay's demonstrated language facility, occasional errors, and generally controlled organization, but with some communication impeded by language inaccuracies. / Based on the rubric and the rater's tendency, the predicted Overall score is 3, as the essay shows some facility in language use with occasional errors and generally controlled organization, but communication is impeded in some cases. | Generic_Cityという匿名化表記を不自然さとして扱っており、匿名化処理への誤反応が疑われる。 |
| 1637:1 | 3 | 3 | 3 | The rater tends to assign a score of 3 when the essay shows some facility in language use, with occasional inaccuracies that impede communication, and generally controlled organization. | The essay demonstrates some facility in language use with occasional inaccuracies, such as 'some people argue that there should be year-round schools' and 'they might have an accident due to the weather.' The organization is generally controlled, with clear reasons provided for why a longer summer vacation is beneficial. / The essay's language facility and occasional inaccuracies align with the rater's tendency to assign a score of 3, as seen in the historical examples. / Given the essay's controlled organization and occasional language inaccuracies that sometimes impede communication, a score of 3 is consistent with the rater's historical scoring pattern and the rubric. | 引用した英文をinaccuraciesと呼ぶが、引用自体がどの誤りを示すのか不明確。 |

### Rec-SAVER参照の照合

既存verified_reference_poolとのtarget重複は 2 件、そのうちhistory IDsが順序も含め一致するtargetは 2 件。
参照の生成元はoutputs/overall_rubric_ablationであり、対象と履歴の一致だけで全面再利用可能とは断定できない。Rubric/本文/参照生成条件のhash照合を追加して採否を判断する。
既存評価値の転記は行っていない。新規比較時はreasoningの3要素のみ文章化し、tendencyを含むJSON全体は比較しない。
追加所要時間は未実測。新規参照が必要な対象数と検証retry数を確定し、小規模実測後に見積もる。
