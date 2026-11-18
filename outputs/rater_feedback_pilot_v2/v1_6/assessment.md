# 予備実験v2の所見

実行・出力内容の確認に限定する。最終評価方法の設計・新たな評価モデルの学習・有効性評価は行わない。

## 条件別の候補採否

```json
{
  "A": {
    "targets": 27,
    "candidates": 54,
    "generated": 53,
    "verified_calls": 53,
    "accepted": 35,
    "accepted_unique_targets": 20,
    "eligible_claims": 129,
    "integrations_completed": 3,
    "feedback_texts_completed": 3,
    "comparison_targets_completed": 11
  },
  "B": {
    "targets": 27,
    "candidates": 54,
    "generated": 53,
    "verified_calls": 53,
    "accepted": 34,
    "accepted_unique_targets": 19,
    "eligible_claims": 135,
    "integrations_completed": 3,
    "feedback_texts_completed": 3,
    "comparison_targets_completed": 13
  }
}
```

Aのみ自己検証で一致した対象: ['2444:1', '5627:1', '8608:1']
Bのみ自己検証で一致した対象: ['2775:2', '318:2']
条件で自己検証の通過対象が異なるため、傾向の差をTrait情報の因果的効果と断定しない。

## 確認事項と残る制約

- 個別理由は新規生成。旧inputsから復元したのは本文・履歴ID・観測値だけで、旧参照推論は入力していない。
- 引用はspan IDから原文・文字位置を取得。全文を保持し、分割不能な文章も固定長の位置で追跡。
- マスクは直接得点・段階表現と条件IDに限定。答案の数量、履歴Overall、span IDは削除しない。実検証payloadを別ファイルに保存。
- 採否はOverall再構成一致。証拠・scopeの機械検査と、意味的支持の暫定モデル判定を分離。得点一致は説明の正しさを保証しない。
- 同一答案の候補は答案単位に整理し、支持は異なる対象を最低2件必要とする。
- 公式条件の選択を観測段階・固定方向の隣接段階から解放。各条件は公式原文の文字位置・親段階全文へ戻れる。限定を省略して新規基準を作らない。
- ④は対象全文と採用理由を答案ごとに読み、本文の特徴・推定判断・基準から妥当な評価・不一致／不明点を分離。⑤は区別・場所・行動を構造化。
- 機械的なIDの有効性だけでは、具体性、誤り判定、理解阻害の強さ、行動の有用性の妥当性は分からない。一般論や指示の復唱は内容レビューで確認する。
- 元DOCXは不在。保存済み公式転記を使用し、真正性を原本から独立確認していない。
- 本人の真の理由、採点者固有性、Traitの重み、フィードバックの有効性、バイアス是正効果を実証していない。

## 実測の検査・内容点検

機械監査: True（失敗0件）。意味的支持の正解性はこの監査に含まない。

### 暫定的な意味的支持の内訳

```json
{
  "A": {
    "claims": 201,
    "history_claims": 0,
    "mechanically_invalid": 0,
    "reviewed_claims": 130,
    "semantic_support_counts": {
      "supported": 129,
      "uncertain": 1
    },
    "eligible_claims": 129
  },
  "B": {
    "claims": 210,
    "history_claims": 0,
    "mechanically_invalid": 0,
    "reviewed_claims": 136,
    "semantic_support_counts": {
      "supported": 135,
      "uncertain": 1
    },
    "eligible_claims": 135
  }
}
```

### 生成形式の失敗

```json
[
  {
    "stage": "generate",
    "key": "A|1514:1|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 899
  },
  {
    "stage": "generate",
    "key": "B|1514:1|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 812
  },
  {
    "stage": "generate",
    "key": "A|1514:1|K2",
    "attempt": 1,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 928
  },
  {
    "stage": "generate",
    "key": "B|1514:1|K2",
    "attempt": 1,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 1078
  },
  {
    "stage": "compare",
    "key": "A|pilot_1514:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 673
  },
  {
    "stage": "compare",
    "key": "A|pilot_1868:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 781
  },
  {
    "stage": "compare",
    "key": "B|pilot_1514:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 916
  },
  {
    "stage": "compare",
    "key": "B|pilot_1868:1",
    "attempt": 0,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 1007
  },
  {
    "stage": "generate",
    "key": "A|5627:1|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 482
  },
  {
    "stage": "generate",
    "key": "A|5268:1|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 899
  },
  {
    "stage": "generate",
    "key": "A|474:1|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 824
  },
  {
    "stage": "generate",
    "key": "A|2853:2|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 780
  },
  {
    "stage": "generate",
    "key": "A|7418:2|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 639
  },
  {
    "stage": "generate",
    "key": "A|2420:1|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 830
  },
  {
    "stage": "generate",
    "key": "B|474:1|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 892
  },
  {
    "stage": "generate",
    "key": "B|2832:2|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 879
  },
  {
    "stage": "generate",
    "key": "B|7817:1|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 848
  },
  {
    "stage": "generate",
    "key": "B|61:1|K2",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 767
  },
  {
    "stage": "generate",
    "key": "B|515:1|K1",
    "attempt": 0,
    "error": "AssertionError: ",
    "finish_reason": "stop",
    "output_tokens": 987
  },
  {
    "stage": "ground",
    "key": "A|8487:1|K2",
    "attempt": 0,
    "error": "JSONDecodeError: Expecting ',' delimiter: line 18 column 52 (char 488)",
    "finish_reason": "stop",
    "output_tokens": 322
  },
  {
    "stage": "compare",
    "key": "A|full_2444:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1058
  },
  {
    "stage": "compare",
    "key": "A|full_4902:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 811
  },
  {
    "stage": "compare",
    "key": "A|full_1514:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 701
  },
  {
    "stage": "compare",
    "key": "A|full_2444:1",
    "attempt": 1,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 751
  },
  {
    "stage": "compare",
    "key": "A|full_1514:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 774
  },
  {
    "stage": "compare",
    "key": "A|full_474:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 537
  },
  {
    "stage": "compare",
    "key": "A|full_2853:2",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1541
  },
  {
    "stage": "compare",
    "key": "A|full_406:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 846
  },
  {
    "stage": "compare",
    "key": "A|full_2832:2",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 817
  },
  {
    "stage": "compare",
    "key": "A|full_61:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 816
  },
  {
    "stage": "compare",
    "key": "A|full_7836:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 667
  },
  {
    "stage": "compare",
    "key": "A|full_474:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 574
  },
  {
    "stage": "compare",
    "key": "A|full_406:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 647
  },
  {
    "stage": "compare",
    "key": "A|full_2832:2",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 867
  },
  {
    "stage": "compare",
    "key": "A|full_61:1",
    "attempt": 1,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 853
  },
  {
    "stage": "compare",
    "key": "A|full_7836:1",
    "attempt": 1,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 1646
  },
  {
    "stage": "compare",
    "key": "A|full_515:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1013
  },
  {
    "stage": "compare",
    "key": "A|full_2348:1",
    "attempt": 0,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 1072
  },
  {
    "stage": "compare",
    "key": "B|full_4902:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 788
  },
  {
    "stage": "compare",
    "key": "A|full_515:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 691
  },
  {
    "stage": "compare",
    "key": "A|full_2348:1",
    "attempt": 1,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 875
  },
  {
    "stage": "compare",
    "key": "B|full_1514:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1047
  },
  {
    "stage": "compare",
    "key": "B|full_2775:2",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1173
  },
  {
    "stage": "compare",
    "key": "B|full_318:2",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1191
  },
  {
    "stage": "compare",
    "key": "B|full_406:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 897
  },
  {
    "stage": "compare",
    "key": "B|full_2832:2",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1027
  },
  {
    "stage": "compare",
    "key": "B|full_1514:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1019
  },
  {
    "stage": "compare",
    "key": "B|full_318:2",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1206
  },
  {
    "stage": "compare",
    "key": "B|full_406:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 776
  },
  {
    "stage": "compare",
    "key": "B|full_2832:2",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1204
  },
  {
    "stage": "compare",
    "key": "B|full_2420:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 1124
  },
  {
    "stage": "compare",
    "key": "B|full_61:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 810
  },
  {
    "stage": "compare",
    "key": "B|full_7836:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 615
  },
  {
    "stage": "compare",
    "key": "B|full_2910:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 718
  },
  {
    "stage": "compare",
    "key": "B|full_2348:1",
    "attempt": 0,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 920
  },
  {
    "stage": "compare",
    "key": "B|full_61:1",
    "attempt": 1,
    "error": "AssertionError: analysis tokens must occur exactly in the selected span; do not invent or silently correct forms",
    "finish_reason": "stop",
    "output_tokens": 818
  },
  {
    "stage": "compare",
    "key": "B|full_2348:1",
    "attempt": 1,
    "error": "AssertionError: next_action.action is too vague: name the concrete relation or form to check",
    "finish_reason": "stop",
    "output_tokens": 790
  }
]
```

原出力と再試行をcalls.jsonlに残した。得点不一致の候補を合格まで再生成していない。

### 内容上の要確認フラグ

```json
{
  "frequency_label_requires_review": 94,
  "language_mismatch_flag": 18,
  "atomic_judgment_requires_review": 44
}
```

content_review_flags.jsonの言語・原子的主張・頻度分類のフラグは、主張が誤りという自動判定ではない。該当箇所を読むための記録。

### 次の個別理由プロンプトで改善する点

- 抽象的な「構造」「文法」「語彙が限定的」の説明だけでなく、どの構文・語の使い方・指示関係を判断したかを記す。引用は引き続きspan IDから取得する。
- 誤りの存在・分布・理解を妨げる具体的な命題の不確定さを別々の主張とし、組織と文法も分ける。
- 日本語の文章欄、分類enum、文字列／配列の型を明確にし、形式違反の再試行には失敗フィールド名と許容値を返す。
- 高得点の説明を無理に整えず、観測Overallを再構成できない場合は候補不足として残す。
- ④では全文の局所証拠と程度・頻度・伝達阻害の条件を対応させ、⑤では同じ論点の区別・位置・行動を明示する。意味的な正しさは別途内容確認が必要。

実行は予備的な動作・出力確認。最終評価設計、代表性のある標本評価、本人の心理の復元、有効性やバイアス是正効果の結論は対象外。

## 固定3答案で確認した具体的な問題

```json
{
  "timestamp": "2026-11-15T18:53:17.146020+09:00",
  "status": "preliminary content observations; not efficacy evaluation",
  "observations": [
    {
      "kind": "citation_semantic_alignment_gap",
      "candidate": "A|1514:1|K1",
      "claim_id": "C2",
      "selected_span_ids": [
        "1514:1@U003",
        "1514:1@U014"
      ],
      "grounding_review": {
        "claim_id": "C2",
        "support": "supported",
        "explanation": "文章中に文法と慣用句の誤用が見られる。例えば、\"In the other hand\" は \"On the other hand\" の誤用であり、\"he fail the first time\" は \"he failed the first time\" の誤用である。これらの誤用は全体的な意味の理解を妨げないが、文法的な正確さには影響を与える。",
        "counter_span_ids": []
      },
      "phrase_location_in_full_target": [
        "1514:1@U004"
      ],
      "finding": "The grounding explanation mentions In the other hand found in the full target, but this phrase is outside the selected evidence spans. The same claim also contains a tense example actually in the selected spans. Existence of support somewhere in full text does not validate every selected citation or every combined subclaim.",
      "next_prompt_change": "Require separate support decision for each atomic proposition and each selected evidence span; additions of evidence IDs must be explicit and checked separately."
    },
    {
      "kind": "generic_patterns",
      "finding": "Pilot patterns include broad structures/grammar descriptions. Two distinct target IDs establish a count condition, not the semantic specificity or validity of a shared pattern."
    },
    {
      "kind": "language_mismatch",
      "finding": "Some generated high-score explanations are Chinese despite Japanese instructions. These high-score candidates failed Overall reconstruction and were not used as adopted evidence."
    },
    {
      "kind": "grounding_overaffirmation_risk",
      "finding": "All pilot reviewed claims were labeled supported by the same local model. This is a provisional model judgment, not independently measured support accuracy."
    }
  ],
  "comparison_observations": [
    {
      "target_id": "1868:1",
      "condition": "A",
      "issue": "The model calls main a noun in The main piece, and interprets professional as a direct adjective modifying people. These lexical analyses require correction; valid word positions did not ensure correct grammatical interpretation."
    },
    {
      "target_id": "1868:1",
      "condition": "A",
      "issue": "Changing keep learning to keep on learning does not address the form after process of in the actual sentence; the proposed correction is not established as suitable feedback."
    },
    {
      "target_id": "1514:1",
      "condition": "A",
      "issue": "A global score-level proposal is given without explaining the full conditions or distribution of features; local anchors do not by themselves justify this scope."
    },
    {
      "target_id": "1514:1",
      "condition": "B",
      "issue": "apply vs applied provides a concrete local tense question, but the action is phrased as editing the essay rather than a check for a rater future scoring decision."
    }
  ],
  "quality_status": "generated pilot examples with known semantic and rater-action problems; not validated feedback"
}
```

これらは機械監査とは別の内容上の問題。原文に語があること、引用が支持すること、文法分析が正しいこと、ルーブリックの条件を満たすこと、採点者に有用な行動になることを順に区別する必要がある。

<!-- saved-state-resume-audit -->
## 保存済み状態からの再開監査

本処理は2026-11-15 20:54 JSTに終了済み。今回の再開ではモデルを起動せず、全件を再集計・監査して最終文書を確定した。

|条件|生成成功／予定候補|生成失敗|検証実行成功|Overall一致候補|統合入力のユニーク答案|傾向の支持に列挙されたユニーク答案|④⑤成功／対象|④⑤失敗|
|---|---|---|---|---|---|---|---|---|
|A|53/54|1|53|35|20|11|11/20|9|
|B|53/54|1|53|34|19|12|13/19|6|

統合入力は、採用候補に本文に対応する暫定支持主張がある答案数。傾向の支持として実際に列挙された答案数とは別に集計した。候補の複数件を独立した答案として数えていない。

各条件で生成失敗は1514:1のK2。生成後の自己検証は全106件が形式上成功し、Overall不一致37候補は不採用で保持した。生成失敗と得点不一致を混同しない。

④⑤は39対象中24件が成功、15件は既定の形式再試行を使い切った終端失敗。未処理バッチはない。採点者別の統合・最終文章は各条件3件が成功したが、失敗した答案の④⑤を補完できたことは意味しない。失敗対象とキャッシュはresume_completion.json、各試行の原出力・エラーはcalls.jsonlに保持する。

引用・単語の文字位置は24件すべて照合済み。ただし4件は補助的な観点別基準だけを選び、Overall条件を明示していない（anchor_audit.json）。機械検査の成功は基準対応の十分性を意味しない。

観測Overall=5の2答案（条件ごと4候補）は、A/Bとも一致候補0件だった。このため統合は高得点答案の評価を説明できていない。採用範囲の偏りを含む予備出力であり、A/B差をTrait情報の因果的効果と扱わない。

具体例（A・5627:1）では、本文の「My Mom, she」と「whats」を取り上げた一方、「whats」を指示代名詞とする分析、組織に関するOverall.S3.C02との対応、理解阻害の程度の根拠には問題がある。⑤「冗長性と誤用を確認し、その影響を評価する」は④の語には対応するが、次の採点で何を区別するかは十分に具体化されていない。これは改善課題を確認する生成例であり、妥当な助言と認定した例ではない。

次回は個別理由の1主張を1つの検証可能な判断に分け、正しい用法との区別、複数箇所での頻度、理解への影響、判断保留を明示する。④はその証拠を公式条件の程度・頻度と結び、⑤はその未解決点を次回採点で見分ける手順にする。文法分析の正しさは文字列照合とは別に点検する。今回のプロンプトや研究条件は変更していない。

前回のdocument_feedback_v2_revisions.pyは、利用上限で自動承認審査が完了せず実行されなかった。今回も同コマンドの実行や別経路による履歴集約は行っていない。旧版・既存の版別ログ・再利用証明は保持し、本処理と独立した文書化として残す。

再開監査の詳細: [resume_completion.json](resume_completion.json)。引用検査: [independent_audit.json](independent_audit.json)、[anchor_audit.json](anchor_audit.json)、[verification_input_audit.json](verification_input_audit.json)。
