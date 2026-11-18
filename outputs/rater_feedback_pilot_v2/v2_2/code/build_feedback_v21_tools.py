"""同じ実行・監査補助を別版設定に向ける。モデルや旧出力は変更しない。"""
from src.recsaver.rater_feedback_pilot_v2 import ROOT


def main():
    pairs=[('launch_feedback_development.py','launch_feedback_development_v21.py'),
        ('check_feedback_development_guidance.py','check_feedback_development_guidance_v21.py'),
        ('report_feedback_development.py','report_feedback_development_v21.py')]
    for old,new in pairs:
        path=ROOT/'scripts'/new;assert not path.exists()
        source=(ROOT/'scripts'/old).read_text(encoding='utf-8')
        source=source.replace('recsaver.rater_feedback_development','recsaver.rater_feedback_development_v21')
        source=source.replace('recsaver.feedback_development_schema','recsaver.feedback_development_schema_v21')
        source=source.replace('v2_0','v2_1').replace('版2.0','版2.1')
        source=source.replace('scripts/check_feedback_development_guidance.py','scripts/check_feedback_development_guidance_v21.py')
        if new.startswith('report_'):
            source=source.replace('from src.recsaver.rater_feedback_pilot_v2 import LEAK_PATTERNS',
                "from src.recsaver.rater_feedback_pilot_v2 import LEAK_PATTERNS\nfrom src.recsaver.rater_feedback_development_v21 import DIRECT_SCORE_PATTERN\nLEAK_PATTERNS=[*LEAK_PATTERNS,('unseparated_score_label',DIRECT_SCORE_PATTERN)]")
        path.write_text(source,encoding='utf-8')
    print('Created v2.1 launch, guidance check and reporting tools')


if __name__=='__main__':main()
