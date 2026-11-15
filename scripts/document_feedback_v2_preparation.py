"""生成前の状況を明記。生成例や推定傾向を代作しない。"""
import collections
import io
import json
import unittest
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    cfg=load(ROOT/'configs/rater_feedback_pilot_v2.json');out=ROOT/cfg['output_dir']
    assert not (out/'pilot_results.json').exists(),'Generated results exist: use pipeline report instead'
    items=load(out/'inputs.json');selection=load(out/'selection.json');preflight=load(out/'preflight_checks.json')
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_rater_feedback_pilot_v2','tests.test_rater_feedback_pilot'])
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    save(out/'test_summary.json',dict(timestamp=now(),tests_run=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),passed=tests.wasSuccessful()))
    blocker=dict(timestamp=now(),pid=340794,script='/home/guestuser/lab-jobs/k1/smoke.py',working_directory='/home/guestuser/lab-jobs/k1',model_argument='olmo2_7b',log='/home/guestuser/lab-jobs/tf-k1-smoke-a6.log',process_started_approximately='2026-11-15T17:36:37+09:00',not_stopped_or_modified=True)
    save(out/'gpu_blocker.json',blocker)
    summary=[]
    for rater in ['rater_7','rater_17','rater_4']:
        rows=[i for i in items if i['rater_id']==rater]
        distribution=dict(sorted(collections.Counter(i['target']['overall'] for i in rows).items()))
        summary.append(dict(rater_id=rater,unique_targets=len(rows),overall_distribution=distribution))
    save(out/'preparation_summary.json',dict(timestamp=now(),target_summary=summary,pilot_ids=selection['pilot_ids'],conditions=['A','B'],prepared_candidate_entries=108,distinct_generation_inputs=54,model_calls_made=0,phase='waiting for GPU; no generated reasoning/feedback yet'))
    revisions=[dict(version='1.0',output='v1',status='GPU busy before model load; no calls',changes=['New paired A/B pipeline and atomic structured reasons','Portable stage cache filenames'],failure_file='v1/status.json'),dict(version='1.1',output='v1_1',status='preparation only; no calls',changes=['Deduplicated repeated quote metadata in integration and text input; no evidence truncated']),dict(version='1.2',output='v1_2',status='prepared and waiting for GPU; no calls at documentation time',changes=['Additional Japanese/English score expressions masked','Counterevidence IDs checked within the referenced essay','GPU threshold follows configured allocation','Independent audit, preserved input manifest and 18 regression tests','scripts namespace collides with installed package; scripts invoked with runpy from repository root'])]
    save(out.parent/'revision_history.json',revisions)
    commands='''```bash
# リポジトリ直下・既存WSL qwen3環境で実行
python -m src.recsaver.rater_feedback_pilot_v2 prepare
python -c "import runpy; runpy.run_path('scripts/check_feedback_v2.py', run_name='__main__')"
python -m src.recsaver.rater_feedback_pilot_v2 pilot-and-full
```
'''
    readme=f'''# 採点者フィードバック予備実験v2：準備済み・GPU待機

版: {cfg['version']}。更新日時: {now()}。
**新規モデル生成は0件。A/B比較結果・生成例はまだ存在しない。**
旧参照推論を新規生成結果として流用していない。

- [入力確認と実行状況](report.md)、[未確認事項と改善点](assessment.md)
- inputs.json: 同じ3名27答案と本人履歴3件、本人Overallと6Trait、本文の位置付き参照単位
- input_checks.json / independent_audit.json / preflight_checks.json / tests.txt: 元データ照合・出典不変・位置・マスク・54入力の長さ検査
- generation_input_manifest.json: 108候補の入力ID、履歴ID、seed、入力・プロンプトのハッシュ
- conditions/A/generation_inputs/、conditions/B/generation_inputs/: 実生成に使う54入力。AにTrait値なし、Bには本人のTraitだけ
- conditions.json / rubric.json: 公式転記原文と81条件のID、原文位置、親段階全文
- resolved_config.json / code/: モデル・設定・日時・出典ハッシュ・実行コードとプロンプト
- gpu_blocker.json / gpu_wait_history.jsonl / gpu_wait_status.json: GPU使用元と待機履歴
- ../revision_history.json、../v1/status.json: 修正履歴と初回GPU起動失敗（旧版も保持）

GPU待機処理は空き容量が設定上の必要量45,250MiB以上になるまで最大30分待つ。
既存プロセスは停止しない。待機状態はgpu_wait_status.jsonの日時とstatusを参照。
空きができたら3答案のA/B全段階を実行し、27答案への展開前にレビュー用ゲートで停止する。
生成後にreport.mdとassessment.mdは実測の結果に更新される。

## 実行と再開

{commands}
既に待機プロセスが動いている場合、二重起動しない。
pilot-and-fullはPILOT_READY表示後、pilot_results.jsonを点検したうえで
pilot_review.jsonにproceed=trueとpilot_sha256（実ファイルSHA256）を保存する。
このゲートはユーザー承認要求ではなく、固定3答案の出力確認を先に行うための処理上の制御。
比較段階以降も含め、中間結果はstages/に保存され、同じ入力の完了段階を再利用する。
入力・プロンプト等の変更時は新しい版の出力先を使用する。
全実行後の監査:
`python -c "import runpy; runpy.run_path('scripts/audit_feedback_v2.py', run_name='__main__')"`
'''
    (out/'README.md').write_text(readme,encoding='utf-8')
    report=['# v2実行状況：生成前', '',f'記録日時: {now()}。対象固定・前処理済み。GPU空き不足により新規生成は0件。', '', '|採点者|ユニーク対象数|観測Overallの分布|', '|---|---|---|']
    report += [f"|{s['rater_id']}|{s['unique_targets']}|{s['overall_distribution']}|" for s in summary]
    report += ['',f"最初の3答案: {selection['pilot_ids']}（rater_7内、source_row_id数値順→rater_position順）。結果で差し替えない。", '',f"A/B共通ルーブリックはOverall＋6観点。入力長の最大値は{preflight['max_prompt_tokens']}トークン、生成上限1800、モデル上限32768。切り詰めなし。", '', 'Aは本人Overallのみ、Bは本人Overall＋6Trait。対象・履歴・ルーブリック・形式・モデル・候補数2・対になるseedを固定。欠損・無効値は対象／履歴とも今回の27対象では検出なし。', '', '## 未生成の成果物', '', '個別理由原本・得点除去後の実検証入力・自己検証結果・意味的支持点検・答案別候補整理・採点者別統合・④⑤比較・5要素の本文は、モデルが動いた後に保存する。現在の時点で生成例、共通傾向、A/Bの通過率差を提示することはできない。', '', 'GPUを使用しているのは別ジョブの/home/guestuser/lab-jobs/k1/smoke.py（--models olmo2_7b、PID 340794）。停止・設定変更は行っていない。', '', '## 検査', '', '元データと旧入力の本文・Overall・本人ID・履歴3件の一致、6Traitの本人一致、全spanの位置と全文保持、条件の原文位置、AにTrait値がないこと、直接得点表現と条件IDの除去、数量とspan IDの保持、同一答案の候補を独立2件と数えないこと、非隣接段階の選択許可を検査。新規7件＋既存11件の18テスト成功。', '']
    (out/'report.md').write_text('\n'.join(report),encoding='utf-8')
    assessment='''# v2の準備段階の所見

実生成前なので、理由の具体性、支持されない主張の割合、A/Bの採否差、共通傾向、④⑤の内容の改善は未確認。
これらを検証済みとは扱わない。

実装上の改善:
- 理由をscope・答案ID・原子的主張・span・方向・定性的な得点関係・公式条件ID・限界に分ける。
- 個別理由を新規生成し、直接得点を除いた新規呼出しでOverall再構成一致を採否とする。
- 対象得点・Trait・条件IDはwhitelist方式で除き、引用の数量と履歴Overallは保持する。
- 採否と引用の実在・意味的支持を分け、本文から支持できない主張は統合に使わない。
- 答案内の候補間比較を先に行い、共通傾向は異なる対象2件以上とする。
- 公式条件は自由に選択し、全文を見た答案別の④から、区別・場所・行動を持つ⑤を作る。

実出力で確認が必要な点:
- 4主張／理由と生成上限1800トークンでJSONが完結するか。打切りや不正出力はcalls.jsonlに残す。
- 得点一致しても本文の意味的支持や評価の適切さが保証されない。支持判定はモデルの暫定判断。
- 「誤りの存在」「頻度」「伝達阻害」を本当に区別し、一般論や指示の復唱を避けられるか。
- 公式条件の名前の引用で終わらず、妥当と考えられる局所評価と別解釈まで説明できるか。
- ⑤が④の論点に結びつき、システム自身で確認できることを採点者へ丸投げしていないか。
- 統合・文章化でも全入力長を都度検査する。重複引用はID対応を保って一箇所にまとめ、黙って切らない。
- 保存済み公式転記は利用できたが、原本DOCXは不在で真正性を独立確認していない。

GPU未確保を理由とする準備段階の報告であり、有効性・バイアス是正・真の採点理由・Trait重みを実証する結論は出していない。
'''
    (out/'assessment.md').write_text(assessment,encoding='utf-8')
    (out.parent/'README.md').write_text('# 採点者フィードバック予備検証v2\n\n現在の版は[v1_2/README.md](v1_2/README.md)。生成前の検査は完了、GPU待機中。\n旧v1はGPU起動失敗、v1_1は前処理のみ。旧実験rater_feedback_pilotは変更していない。\n修正履歴はrevision_history.json。\n',encoding='utf-8')
    assert tests.wasSuccessful()
    print('Prepared status reports saved; no generated findings asserted.',flush=True)


if __name__=='__main__':
    main()
