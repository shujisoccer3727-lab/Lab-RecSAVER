# 研究コンテキスト

本研究は、採点者ごとのOverall評価の違いと、Cohesion、Syntax、Vocabulary、Phraseology、Grammar、Conventionsから成るTrait profileとの関連を探索し、最終的にRec-SAVER型LLM手法で採点理由を言語化することを目指す。

分析単位は「1エッセイ×1採点者」である。6 Traitは別サンプルではなく、Overallを説明する構造化された中間評価情報として同じ行に保持する。Overallは人間採点値をそのまま使用し、Trait平均から再計算しない。

現在の基礎分析は、採点者別の記述統計、Trait profile、Overallとの相関、`Overall - trait_mean`、担当答案の本文長を扱う。単純平均差は答案難易度や担当答案構成を統制していないため「未調整の評価傾向」として解釈する。相関は因果的な重みを意味しない。

基礎分析はWindowsを含むCPU環境で完結させる。GPU推論は研究室PCへ移行後、別モジュール・別依存環境で行う。
