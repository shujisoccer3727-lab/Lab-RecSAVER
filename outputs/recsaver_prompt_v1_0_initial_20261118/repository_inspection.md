# 既存環境・出典確認

2026-11-18 JST。`AGENTS.md`とREADME、`configs/rater_feedback_development_v22.json`、`src/recsaver/model.py`、`src/config.py`、`src/transform_data.py`、最新の`outputs/rater_feedback_pilot_v2/v2_2/report.md`・`assessment.md`・`audit.json`・`three_audit.json`・`inputs.json`を確認した。

- 環境はWSL2 Ubuntu、Conda `/home/guestuser/miniforge3/envs/qwen3`、Python 3.10。Windowsのpython aliasと通常権限のWSL呼出しは実行できず、許可されたWSL経由で既存環境を使用した。初期探索で推測したminicondaパスは不存在で、環境一覧からminiforgeの実体を確認した。新規インストールなし。
- 既存モデルは`Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4`、GPTQ Marlin、32768 context、temperature=0.2、top_p=0.8、履歴3件・2候補。既存user-only APIと同じchat template方式を使用。自動挿入される既定system文は `You are Qwen, created by Alibaba Cloud. You are a helpful assistant.`。一般的な役割指示で、今回の仕様と課題固有の競合は認めない。
- 本人の得点はrawの`Rater_1/2`と同じpositionの`Overall_1/2`・6Trait列。wideの`source_row_id`はrawの0始まり論理行番号、ID末尾はrater positionで、別の答案を意味しない。対象・履歴全12レコードをraw/wide/旧保存入力で再照合し一致。
- 公式ルーブリックの保存版は`rubrics/ellipse_rubric_structured.json`。タイトルは *English Proficiency Scoring Rubric for English Language Learners*、出典は`ELL_Rubrics (1).docx`と記録。JSON末尾には改行・空白のみ正規化した旨がある。元DOCXに対する今回の再転記監査は行わない。ルーブリック保存版をそのまま入力する。
- 許容得点は既存`src/config.py`の1,2,3,4,5、刻み1。Overallはholistic、他6Traitはanalytic（ルーブリックstructure）。TraitからOverallを計算する規則は与えられていない。READMEもOverall再計算を禁止している。
- 固定の既存調整セットはrater_7の1514:1 / 1868:1 / 4902:1。以前の処理成功6/6・Overall一致6/6と、内容上の未達が共存する。良否の異なる主張を含み、既知失敗だけから対象を抽出したセットではない。ただし過去に利用済み、全Overall=3。
- 旧仕様は形式失敗1回再試行とguided decoding、証拠eligibilityなどを使用。今回の仕様ではこれらを採用せず、形式再試行0、追加の意味品質フィルタなし、正本3段階のみ。

旧問題の出典は`outputs/rater_feedback_pilot_v2/v2_2/assessment.md` R1〜R9。R1は24/24主張で対象全文span列挙、R2は1868:1/K2/C3の “The Vocabulary score of 3 ...” が本人のVocabulary=4と不一致、R3は誤りと意味妨害の混同、R8は最終文の具体例・引用の欠落。これは旧版に対するCodex開発レビューであり、今回v1.0の観測結果とは分ける。旧版と今回ではプロンプト・段階・再試行・出力形式が異なり、単純な改善率を計算しない。

保留候補8540:1 / 8612:1は今回の入力から除外。追加の過去利用検索では、両IDが`outputs/full_prediction_main_results/common_targets.csv` 16707行・16865行に存在し、8612:1は`outputs/rater_tendency_joint_mvp_1000_grounded_v2/target_history_manifest.jsonl`668行の履歴にも存在した。したがって過去未利用とは認定しない。真に未使用の最終確認標本の確保は未完了で、今回の生成は行わない。選択後にこの限界を隠して「最終確認用」と呼び替えない。
