"""成果物インデックスと入力一覧。モデル呼出しなし。"""
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.recsaver.rater_feedback_pilot import sha,digest,now,save
out=ROOT/'outputs/rater_feedback_pilot'
items=json.loads((out/'inputs.json').read_text())
rows=[]
for item in items:
    row={k:item[k] for k in ['target_id','target_rater','source_row_id','filename','text_id_kaggle','gold_overall','candidate_index','attempt_index','candidate_journal_present','selection_rank']}
    row.update(history_ids=json.dumps(item['history_ids']),target_text_sha256=digest(item['target_text']),reference_sha256=digest(item['reference_reasoning']))
    rows.append(row)
with (out/'selected_inputs.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]))
    writer.writeheader();writer.writerows(rows)
text='''# 採点者フィードバック予備検証

Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4で3名・27答案を実行済み。
rater_7: 10、rater_17: 7、rater_4: 10。seedは20261113。

- [採点者別フィードバック・5要素対応表](report.md)
- [問題点、実測集計、次回のプロンプト改善案](assessment.md)
- [機械可読の最終結果](feedback.json)
- [対象・候補・観測得点・履歴の一覧](selected_inputs.csv)
- [入力全文](inputs.json)、[選択条件と全採点者の利用可能数](selection.json)
- [出典と確認不能事項](provenance.json)、[実行config](resolved_config.json)
- [引用等の最終監査](final_audit.json)、[検査集計](checks.json)、[テスト](tests.txt)
- [修正履歴](execution_history.json)、原モデル出力と失敗はcalls.jsonlおよびrevisions/
- コード: rater_feedback_pilot.py、補助スクリプトはcode/、プロンプトは同ディレクトリのtxt

最終Cは、モデルが個別の照合説明と文章化を行い、本文引用・位置・ID・得点・公式原文は
プログラムが固定する。最初の一括生成の失敗と、根拠のない得点規則の除外も保存した。
意味的品質の問題はcontent_review.jsonに明記し、最終出力は要改善の予備生成例とする。
有効性、採点者バイアスの存在・是正効果、真の思考過程は実証していない。

過去の準備・保留状態はpreflight_report.mdに残す。現在の結果は上記report.mdとassessment.md。
旧実験ファイルは変更していない。参照推論生成・得点自己検証の再実行は0件。
'''
(out/'README.md').write_text(text,encoding='utf-8')
paths=sorted(p for p in out.rglob('*') if p.is_file() and p.name!='artifact_manifest.json')
save(out/'artifact_manifest.json',dict(timestamp=now(),sha256={str(p.relative_to(out)):sha(p) for p in paths}))
print('README.md, selected_inputs.csv, artifact_manifest.json saved')
