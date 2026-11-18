# 予備実験v2の所見

実行・出力内容の確認に限定する。最終評価方法の設計・新たな評価モデルの学習・有効性評価は行わない。

## 条件別の候補採否

```json
{
  "A": {
    "targets": 3,
    "candidates": 6,
    "generated": 5,
    "verified_calls": 5,
    "accepted": 3,
    "accepted_unique_targets": 2,
    "eligible_claims": 10,
    "integrations_completed": 0,
    "feedback_texts_completed": 1,
    "comparison_targets_completed": 0
  },
  "B": {
    "targets": 3,
    "candidates": 6,
    "generated": 5,
    "verified_calls": 5,
    "accepted": 3,
    "accepted_unique_targets": 2,
    "eligible_claims": 12,
    "integrations_completed": 0,
    "feedback_texts_completed": 1,
    "comparison_targets_completed": 0
  }
}
```

Aのみ統合可能な対象: []
Bのみ統合可能な対象: []
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
