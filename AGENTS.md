# ELLIPSE 採点分析プロジェクト

- 研究テーマは LLM を用いたエッセイ自動採点である。
- ELLIPSE Corpus の raw rater score を使用する。
- 採点者 ID は `Rater_1` と `Rater_2` 列の値から取得する。
- 主要 Trait は Overall、Cohesion、Syntax、Vocabulary、Phraseology、Grammar、Conventions とする。
- `data/` の元データを変更しない。
- 分析結果は再現可能な Python スクリプトとして残す。
- 採点者の単純平均差だけでバイアスと断定しない。
- 探索的分析と統計的なバイアス推定を区別する。
- Python 3.10、WSL2、Conda 環境 `qwen3` を使用する。
- 日本語のコメント・ドキュメントを使用してよい。
- 基礎分析はCPU専用とし、vLLM、PyTorch、Transformers、CUDAに依存させない。
- Windows、WSL2、Linuxで動く相対パスと `pathlib.Path` を使う。
- 基礎分析とGPU推論のモジュール・依存ファイルを分離する。
- rawデータ、モデル、巨大な出力をGit管理しない。
- Overall予測用データの単位は「1エッセイ×1採点者」とし、6 Traitを同じ行のTrait profileとして保持する。
- wide整形時もスコア0や欠損を補正・削除せず、無効フラグで識別する。
