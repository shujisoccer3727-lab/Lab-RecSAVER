"""保存済み失敗と修正・段階再利用を実行履歴へ集約する。"""
from src.recsaver.rater_feedback_pilot_v2 import ROOT,load,save,now


def main():
    parent=ROOT/'outputs/rater_feedback_pilot_v2'
    reasons={
        'v1':'GPU busy before model load; no inference output',
        'v1_1':'preparation-only revision: preserve input joins and remove repeated quote metadata',
        'v1_2':'model generation ran after GPU became free; stopped because unexplained was a list during masking',
        'v1_3':'complete 3-target trial; merge/integration/comparison format errors; not expanded',
        'v1_4':'guided JSON schema added; xgrammar/vLLM API mismatch during actual inference; environment unchanged',
        'v1_5':'existing outlines backend passed complete JSON/EOS tests; complete 3-target trial revealed vague actions and duplicate issues',
        'v1_6':'one relationship per essay, real-word anchors/offsets, vague-action checks, compact comparison payload; fixed-sample expansion for content inspection',
    }
    revisions=[]
    for name,reason in reasons.items():
        path=parent/name
        row=dict(directory=name,reason=reason,old_outputs_retained=True)
        if (path/'status.json').exists(): row['execution_status']=load(path/'status.json')
        if (path/'pilot_review.json').exists(): row['pilot_review']=load(path/'pilot_review.json')
        if (path/'upstream_reuse.json').exists():
            reuse=load(path/'upstream_reuse.json')
            row['reuse']=dict(source_version=reuse['source_version'],entries=len(reuse['entries']),manifest=name+'/upstream_reuse.json')
        if (path/'full_summary.json').exists(): row['final_summary']=load(path/'full_summary.json')
        revisions.append(row)
    save(parent/'revision_history.json',dict(timestamp=now(),revisions=revisions,selection_replacement=False,unbounded_regeneration=False,library_installation_or_upgrade=False))
    print('Revision history updated',flush=True)


if __name__=='__main__': main()
