# Rec-SAVER AES context length・history収容率分析

確認日: 2026-08-13

## 実行環境

- GPU: NVIDIA RTX 6000 Ada Generation
- VRAM: 49,140 MiB (`torch`: 47.9878 GiB)
- NVIDIA driver: 596.72
- `nvidia-smi`表示CUDA: 13.2
- 分析開始時GPU使用量: 799 MiB
- モデル: `Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4`
- vLLM: 0.6.6.post1、V0 engine
- quantization: `gptq_marlin`
- tensor parallel size: 1
- GPU memory utilization: 0.90

## max_model_lenロード・短文推論試験

各条件を独立プロセスで起動し、モデルロード後に短いpromptを1件生成した。

| max_model_len | ロード | 短文推論 | OOM | ロード後GPU使用量 (MiB) |
|---:|:---:|:---:|:---:|---:|
| 4,096 | 成功 | 成功 | なし | 45,213.1 |
| 8,192 | 成功 | 成功 | なし | 44,614.2 |
| 16,384 | 成功 | 成功 | なし | 42,522.6 |
| 32,768 | 成功 | 成功 | なし | 38,429.1 |

32,768ではvLLM初期化ログ上のactivation peakが8.02 GiB、KV cacheは16.83 GiB、
32,768 token要求に対する最大同時実行度は2.10だった。したがって32,768はロード・短文推論可能だが、
この試験だけでは長文を高並列で安定運用できることまでは確認していない。

## Token収容率の測定条件

- `data/processed/rater_essay_wide.csv`の有効スコア行を使用
- `min_rater_samples=100`: 24採点者、17,598 target
- seed: 20260808
- K: 1, 3, 5, 7, 10
- 現行のPhase 1/Reference/Self-Verification promptとQwen chat templateを使用
- Target自身のhistory混入は0件
- Gold Overall/TraitをPhase 1へ追加していない
- target/history本文はtruncateせず、K fallbackも使用していない
- Phase 1/Reference output budget: 384 token
- Self-Verification output budget: 64 token
- Self-Verification理由は既存MVPの実Reference Reasoning 15件を循環利用

収容判定は `prompt_tokens + phase固有output budget <= max_model_len` とした。

## Phase 1 token分布

| K | mean | p50 | p90 | p95 | max |
|---:|---:|---:|---:|---:|---:|
| 1 | 1,209.3 | 1,171.0 | 1,634.0 | 1,801.0 | 2,920 |
| 3 | 2,302.6 | 2,264.5 | 2,893.0 | 3,103.0 | 4,537 |
| 5 | 3,400.5 | 3,361.0 | 4,118.0 | 4,376.0 | 6,078 |
| 7 | 4,501.7 | 4,464.0 | 5,338.0 | 5,621.0 | 7,740 |
| 10 | 6,144.6 | 6,110.0 | 7,151.0 | 7,474.0 | 9,399 |

## Phase 1および全Phase worst-case収容率

このデータでは全Phaseを同時に満たす率はPhase 1の率と一致した。

| max_model_len | K=1 | K=3 | K=5 | K=7 | K=10 |
|---:|---:|---:|---:|---:|---:|
| 4,096 | 100.00% | 99.53% | 73.04% | 9.98% | 0.12% |
| 8,192 | 100.00% | 100.00% | 100.00% | 100.00% | 97.94% |
| 16,384 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| 32,768 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |

## Phase差

Self-Verification promptはPhase 1より平均116.5 token長く、差のp50は105、p90は173、
p95と最大は176 tokenだった。一方、Self-Verificationのoutput budgetは64 tokenで、Phase 1の384 tokenより
320 token小さい。そのため今回の合計context判定ではPhase 1の方が厳しかった。

Self-Verificationのprompt token p50/p90/p95/maxは、K=1で
1,288/1,753.3/1,919/3,067、K=3で2,381/3,012/3,221.15/4,607、
K=5で3,479/4,239/4,492/6,232、K=7で4,582/5,458/5,734/7,916、
K=10で6,223/7,266.3/7,589/9,575だった。

## 技術的なK候補

- 4,096を維持するなら、全target固定にはK=1、約99.5%を許容するならK=3が候補。K=5以上は固定利用に不向き。
- 8,192ならK=1～7は今回の17,598 targetすべてで収容でき、K=10も97.94%収容できる。
- 16,384ならK=10まで全targetで収容できる。
- context上限とGPU余裕のバランスだけを見る暫定候補は `max_model_len=8192, K=7`。これは性能上の最適値ではない。
- 全targetでK=10を固定する必要があるなら、今回の測定上は16,384が必要。
- 次段階ではK=1/3/5（必要なら7）を同じtarget集合で小規模推論比較し、予測性能・理由品質・速度を確認してからKを決定する。

詳細値は`outputs/context_analysis/context_fit_summary.csv`、target別token数は
`context_token_statistics.csv`、ロード試験は`max_model_len_test.csv`に保存した。これらは生成物のためGit管理外である。
