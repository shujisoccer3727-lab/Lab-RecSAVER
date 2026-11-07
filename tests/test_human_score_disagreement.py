"""データ単位・重複・履歴リーク防止を小さな反例で検証する。"""
import unittest
import pandas as pd
from src.recsaver.data import TRAITS
from src.recsaver.human_score_disagreement import extract, eligible_history
from src.recsaver.reasoning_eval_v1 import verification_prompt


def record(text='essay', filename='file', raters=('rater_1','rater_2'), scores=(1,4)):
    row=dict(Filename=filename,text_id_kaggle=None,Text=text)
    for position in [1,2]:
        row[f'Rater_{position}']=raters[position-1]
        row[f'Overall_{position}']=scores[position-1]
        row[f'Identifying_Info_{position}']=0
        for trait in TRAITS:row[f'{trait}_{position}']=3
    return row


class HumanDisagreementTests(unittest.TestCase):
    def test_unordered_three_rater_pairs_and_identical_duplicate(self):
        raw=pd.DataFrame([record(),record(raters=('rater_2','rater_3'),scores=(4,3))])
        wide,pairs,excluded,duplicates=extract(raw)
        self.assertEqual(len(pairs),2) # 1–4 and 1–3; 4–3 is outside target gaps
        self.assertEqual({p['gap'] for p in pairs},{2,3})
        self.assertTrue(all(p['rater_count']==3 for p in pairs))
        self.assertEqual(len(duplicates),1)
        self.assertEqual(len({p['essay_key'] for p in pairs}),1)

    def test_conflicting_same_rater_is_never_silently_selected(self):
        raw=pd.DataFrame([record(),record(raters=('rater_2','rater_3'),scores=(3,3))])
        with self.assertRaisesRegex(ValueError,'矛盾'):
            extract(raw)

    def test_zero_missing_fractional_out_of_range_not_valid_pairs(self):
        rows=[record(text=str(i),filename=str(i),scores=(x,4)) for i,x in enumerate([0,None,1.5,6])]
        _,pairs,excluded,_=extract(pd.DataFrame(rows))
        self.assertEqual(pairs,[])
        self.assertEqual(len(excluded),4)

    def test_unrelated_filename_collision_requires_resolution(self):
        raw=pd.DataFrame([record(),record(text='different text'),record(text='valid history',filename='other')])
        with self.assertRaisesRegex(ValueError,'unrelated texts'):
            extract(raw)

    def test_anonymization_variant_merged_and_excluded_from_history(self):
        original='An essay about school and my friend John. It is a long story.'
        anonymized=original.replace('John','NAME')
        raw=pd.DataFrame([record(text=original),record(text=anonymized,raters=('rater_3','rater_4'),scores=(3,3)),
                          record(text='valid history',filename='other')])
        wide,pairs,_,_=extract(raw)
        self.assertEqual(len({p['essay_key'] for p in pairs}),2)
        self.assertEqual(sum(p['rater_count']==4 for p in pairs),3)
        self.assertTrue(all(p['essay']==anonymized for p in pairs if p['rater_count']==4))
        target=wide.iloc[0]
        pool=eligible_history(wide,target)
        self.assertEqual(set(pool.Text),{'valid history'})
        self.assertEqual(set(pool.rater_id),{'rater_1','rater_2'})

    def test_verification_does_not_receive_gold_metadata(self):
        item=dict(rubric='rubric',history_text='history',essay='target',gold_overall='SENTINEL_GOLD',
                  prediction={'predicted_overall':'SENTINEL_PRED'})
        rendered=verification_prompt('{overall_rubric}\n{rating_history}\n{target_essay}\n{reference_reasoning}',item,'reason')
        self.assertEqual(rendered,'rubric\nhistory\ntarget\nreason')


if __name__=='__main__':unittest.main()
