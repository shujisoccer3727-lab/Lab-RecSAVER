"""既存の報告・参照監査を別版の保存先へ適用する。旧成果物は上書きしない。"""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for old,new in [('audit_feedback_v21_three.py','audit_feedback_v22_three.py'),('report_feedback_development_v21.py','report_feedback_development_v22.py')]:
    source=(root/'scripts'/old).read_text(encoding='utf-8')
    source=source.replace('v2_1','v2_2')
    # 元の処理関数は版2.1のまま。実行configと報告先だけを版2.2へ切替。
    line="CONFIG=ROOT/'configs/rater_feedback_development_v22.json'\n"
    marker='\n\ndef '
    source=source.replace(marker,'\n\n'+line+marker,1)
    source=source.replace('report_feedback_development_v21.py','report_feedback_development_v22.py')
    source=source.replace('python -m src.recsaver.rater_feedback_development_v21 one', '# 上流は版2.1の同一入力・成功済み結果を再利用')
    source=source.replace('python -m src.recsaver.rater_feedback_development_v21 three', "python -c \"import runpy; runpy.run_path('scripts/resume_feedback_v22.py',run_name='__main__')\"")
    (root/'scripts'/new).write_text(source,encoding='utf-8')
