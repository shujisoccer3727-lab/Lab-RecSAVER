"""Render the current run's separate Codex provisional review; never edit model outputs."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.recsaver.pair_feedback import read, save, sha, load_dataset, spans, DIMS, number

ap = argparse.ArgumentParser()
ap.add_argument('--config', type=Path, required=True)
ap.add_argument('--annotations', type=Path, required=True)
args = ap.parse_args()
cfg = read(args.config)
out = ROOT / cfg['output_dir']
annotations = read(args.annotations)
manifest = read(out / 'manifest.json')
rubric = read(out / 'rubric.json')
_, rows, _ = load_dataset(cfg)
summary = read(out / ('final_summary.json' if (out / 'final_summary.json').exists() else 'summary.json'))
reviews = {x['rater_id']: x for x in annotations['feedback_reviews']}
raters = [r for p in cfg['pairs'] for r in p['raters']]
assert set(reviews) == set(raters)
lines = ['# 採点者3組の履歴件数を揃えたフィードバック生成', '',
    '未使用エッセイを用いた事後的な事例分析。3点差の事例を選んだ分析である。採点時刻はデータ列に存在せず、行順・ID順は採点時系列として扱っていない。', '',
    '比較用5エッセイを全6名の全生成段階から除外し、本人の別エッセイ20件をseed 20261126で事前固定した。各ターゲットエッセイには残る19件から固定した本人履歴3件を使い、理由候補2件を生成した。個別理由とフィードバックは英語の生成原文を保持している。', '',
    '本人の真の採点理由、採点上の因果的な重み、再採点での点差縮小、一般的な性能は検証していない。引用の出典一致と意味的な支持を区別する。Stage 6のモデル検証は実施していない。以下の内容点検は、この実行に対するCodexの暫定レビューであり、独立した人手評価ではない。', '',
    annotations.get('review_scope', ''), '',
    '## 段階別集計', '',
    '|採点者|対象|出力候補|JSON通過|スキーマ通過|マスク通過|完全一致|採用エッセイ|有効所見付き|統合M|状態|',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
for row in summary:
    lines.append('|' + '|'.join(str(row[k]) for k in ['rater_id', 'targets', 'output_candidates', 'json_pass', 'schema_pass', 'mask_pass',
        'exact_matches', 'accepted_essays', 'stage4_essays', 'stage5_M', 'stage5_status']) + '|')
lines += ['', 'JSON通過はStage 1の厳密JSON解析、完全一致はマスク入力検査とStage 3の値検査を通り、観測Overallと完全一致した候補数。採用エッセイは少なくとも1候補が通ったエッセイ数である。', '',
          'renderedは英語表示文の成立、strict_json_failedは厳密JSON不成立を表す。表示成立は意味的な正しさの認定ではない。', '',
          '有効所見付きは少なくとも1件の出典照合が通ったエッセイを指し、意味的な支持の認定ではない。統合対象は再構成の完全一致で選ばれた部分集合であり、本人の全採点履歴を代表する標本とは扱わない。', '',
          '## 件数合わせ', '']
for pair in read(out / 'equalization.json'):
    cap = 'なし' if pair['capacity_cap'] is None else str(pair['capacity_cap'])
    lines += [f'- {pair["pair_id"]}: 所見付きエッセイ {pair["n_left"]} / {pair["n_right"]} 件から双方 M={pair["M"]} 件。容量による上限: {cap}。']
lines += ['', '抽出は生成前の固定順位による。未使用の所見も全て保存している。M=1では評価傾向を保留し、M=0では証拠不足を記録する。', '', '## 固定した英語フィードバックと暫定点検', '']
for rater in raters:
    folder = out / 'stage5' / rater
    source = next(folder / n for n in ['parsed.json', 'skip.json', 'raw.txt', 'result.json', 'error.json'] if (folder / n).exists())
    assert sha(source) == reviews[rater]['feedback_sha256'], 'Review no longer matches the fixed output'
    lines += [f'### {rater}', '']
    if (folder / 'feedback.txt').exists():
        lines += [(folder / 'feedback.txt').read_text(encoding='utf-8').strip(), '']
    else:
        lines += ['英語表示文は未成立。構造化出力または失敗記録を参照。', '']
    if (folder / 'parsed.json').exists() and (folder / 'input_3b.json').exists():
        generated = read(folder / 'parsed.json')
        payload = read(folder / 'input_3b.json')
        rep = next((o for o in payload['verified_observations'] if o['observation_key'] == generated.get('representative_observation_key')), None)
        if rep:
            source_target = next(t for t in manifest['fixed_targets'] if t['rater_id'] == rater and t['target']['essay_id'] == rep['target_essay_id'])
            src = source_target['source']
            lines += [f'代表所見の出典: `{src["Filename"]}` / source_row_id={src["source_row_id"]} / {rep["dimension"]}。行番号は出典識別に用い、採点時系列とは扱わない。', '']
    lines += ['暫定点検: ' + reviews[rater]['judgment'] + '。' + reviews[rater]['notes_ja'], '']
lines += ['## 比較用5エッセイとの照合', '',
          '以下の比較は生成後の別監査である。比較用エッセイの得点と原文を、生成済みのフィードバックへ追加したり、生成文を手直ししたりしていない。局所的な確認点としての対応を記録し、Overallの3点差の原因とは扱わない。', '']
case_results = []
keys = set()
for pair in cfg['pairs']:
    for case in pair['cases']:
        lines += [f'### {case["filename"]}（Overall {case["overall"][0]} / {case["overall"][1]}）', '']
        for rater in pair['raters']:
            key = (case['filename'], rater)
            assert key not in keys
            keys.add(key)
            a = next(x for x in annotations['cases'] if (x['filename'], x['rater_id']) == key)
            row = next(r for r in rows if r['Filename'] == case['filename'] and r['rater_id'] == rater
                       and int(r['source_row_id']) == case['source_row_id'])
            catalog = {s['span_id']: s for s in spans(row['Text'])}
            selected = [catalog[s] for s in a['span_ids']]
            assert all(row['Text'][s['start']:s['end']] == s['text'] for s in selected)
            dim = a['dimension']
            assert dim in DIMS
            score = number(row[dim])
            ref = dict(rubric_ref_id=f'{dim}:{score}', descriptor=rubric['scores'][str(score)][dim])
            f = out / 'stage5' / rater / 'parsed.json'
            feedback = read(f) if f.exists() else None
            result = dict(filename=case['filename'], rater_id=rater, source_row_id=int(row['source_row_id']),
                          essay_id=row['essay_id'], observed_overall=number(row['Overall']), dimension=dim,
                          recorded_dimension_score=score, quotes=selected, rubric=ref,
                          fixed_feedback_next_check=feedback.get('next_check') if feedback else None,
                          correspondence=a['correspondence'], assessment_ja=a['assessment_ja'],
                          semantic_review='Codex provisional; source matching is separately checked')
            case_results.append(result)
            lines += [f'**{rater} — {dim}（記録得点 {score}）**', '']
            if feedback:
                nc = feedback['next_check']
                lines += ['固定フィードバックの確認点（英語原文）: ' + nc['inspect'] + ' ' + nc['distinguish'], '']
            else:
                lines += ['比較に使用できる固定フィードバックの確認点は未成立。', '']
            for s in selected:
                lines += [f'原文根拠 {s["span_id"]} [{s["start"]}:{s["end"]}]: “{s["text"]}”', '']
            lines += [f'対応する公式基準 {ref["rubric_ref_id"]}: “{ref["descriptor"]}”', '',
                      '対応判定: ' + a['correspondence'] + '。' + a['assessment_ja'], '']
assert len(keys) == 10 and len(annotations['cases']) == 10
save(out / 'comparison_case_review.json', dict(annotation_sha256=sha(args.annotations), reviewer=annotations['reviewer'], review_scope=annotations.get('review_scope'), cases=case_results))
save(out / 'feedback_content_review.json', dict(annotation_sha256=sha(args.annotations), reviewer=annotations['reviewer'], review_scope=annotations.get('review_scope'), reviews=list(reviews.values())))
lines += ['## 実行上の記録と制約', '',
    '元データはraw 8,890行、wide 17,780行、有効17,731件・27名。固定5件の行番号・Filename・本文・両者のOverallと6 Trait・空欄Kaggle IDを照合した。', '',
    'Filename、空欄以外のKaggle ID、空白・改行のみ正規化した本文ハッシュの連結成分で除外する。同一性衝突は別途監査し、モデルには原文を渡す。rater_2では同一エッセイの2レコードでTraitプロフィールが矛盾していたため、そのエッセイを候補プールから隔離した。集計定義の違いにより候補プールは指定時点の1,601件に対し1,599件となった。他の5名は指定件数を再現した。全員の20件は確保できた。', '',
    '検査版1.1で、数値を含まない固有帯ラベルnative-likeを隔離する修正を行った。旧監査と原出力を保存し、以前の小規模確認で再構成済みだった影響候補1件は比較用採用集計から除外した。生成文は変更していない。', '',
    'Stage 3では不正な履歴IDを出力した1候補を不採用にした。Stage 4ではターゲットエッセイIDが一致しない1エッセイの所見を除外した。Stage 5ではrater_13のコードフェンス付き出力が厳密JSON不成立となった。全6名の統合要求は実行済みであり、この1名は未実行ではなく形式上の失敗である。各生出力・検査結果・失敗理由を保持し、修復や再生成を行っていない。', '',
    '運用版1.2では共有GPUメモリへの約1.9GBの退避が確認されたため、gpu_memory_utilizationを0.9から0.8に変更した。モデル・正本・実入力・seed・サンプリング・出力上限は維持し、成功済み要求を再生成していない。割当とスケジュールが全要求で同一とは扱わず、ビット単位の実行間同一性は主張しない。', '',
    '再構成の一部バッチでも共有メモリ退避に伴う遅延が見られたが、後続バッチは通常速度に戻り、追加の入力変更・再生成は行っていない。実測はgpu_memory_after_080.jsonとgpu_memory_stage3_delayed_batch.jsonに保存した。', '',
    'マスク改訂とGPU割当変更で中断した生出力未保存の要求は、それぞれの改訂フォルダに区別して記録した。モデルの不正JSONや得点不一致を理由とした再生成は行っていない。', '',
    '再実行コマンドとファイル契約は `docs/pair_feedback_20261126.md`、設定は `configs/pair_feedback_20261126.json`。実入力・生出力・構造化JSON・表示文・引用区間・採否・失敗理由は本出力フォルダに保存し、学生原文と巨大出力はGit対象外とした。', '']
for name in ['cpu_validation.json', 'final_integrity.json', 'smoke_reuse_checks.json', 'cost_summary.json']:
    if (out / name).exists():
        lines += [f'検証記録: `{name}`', '', '```json', json.dumps(read(out / name), ensure_ascii=False, indent=2), '```', '']
(out / 'results_ja.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Rendered review:', out / 'results_ja.md', 'case-rater entries:', len(case_results))
