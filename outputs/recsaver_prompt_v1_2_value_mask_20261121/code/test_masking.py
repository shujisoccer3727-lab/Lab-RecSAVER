"""Meaningful safety/regression controls; no model call and no output repair."""
from pathlib import Path
import copy,json
from masking import mask_analysis
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];BASE=ROOT/'outputs/recsaver_prompt_v1_1_validation_20261120'
inp=json.loads((BASE/'stage1/1514_1__K1/input.json').read_text());h=inp['history'];t=inp['target'];results=[]
def check(name,analysis,expected=None,quarantine=None):
    original=copy.deepcopy(analysis);v=mask_analysis(analysis,h,t);assert analysis==original
    if expected is not None:assert v['masked_analysis']==expected,(name,v['masked_analysis'])
    if quarantine is not None:assert bool(v['audit']['quarantine'])==quarantine,(name,v['audit'])
    assert v['audit']['value_only_invariant'];results.append(dict(name=name,passed=True,original=original,masked=v['masked_analysis'],audit=v['audit']));return v
check('digits_and_number_words',{'decision_explanation':'The observed Overall score is three. Syntax level 2 and 3 fits.'},{'decision_explanation':'The observed Overall score is □. Syntax level □ and □ fits.'},False)
check('word_range',{'decision_explanation':'The target fits levels two or four.'},{'decision_explanation':'The target fits levels □ or □.'},False)
check('no_global_same_digit_replacement',{'decision_explanation':'There are 3 paragraphs; the Overall score is 3.'},{'decision_explanation':'There are 3 paragraphs; the Overall score is □.'},False)
check('history_and_quote_and_id',{'history_patterns':[{'pattern_id':'H1','pattern':'The history essays received Overall scores of 3.','support':[{'history_essay_id':h[0]['essay_id'],'quotes':['So principal i think policy 1 is better for the students.'],'relevant_observed_history_scores':{'Overall':3},'interpretation':'The Overall score of 3 belongs to this history essay.'}],'counterevidence':[]}],'target_evidence':[{'evidence_id':'T1','quotes':['3 is a number from a source'],'observable_feature':'There are 3 items.'}]},quarantine=False)
check('history_equivalence_not_salvaged',{'decision_explanation':'The target received the same Overall score as history essay 217:1.'},quarantine=True)
check('arithmetic_not_salvaged',{'decision_explanation':'The target Overall is 2 + 1.'},quarantine=True)
check('unique_band_not_salvaged',{'decision_explanation':'The target fits the highest band.'},quarantine=True)
check('ambiguous_role_not_rewritten',{'decision_explanation':'It is unclear whether the score of three refers to the target or history.'},{'decision_explanation':'It is unclear whether the score of three refers to the target or history.'},True)
v=check('target_as_history_detected',{'history_patterns':[{'support':[{'history_essay_id':t['essay_id'],'relevant_observed_history_scores':{'Overall':3}}],'counterevidence':[]}]},quarantine=True)
check('limited_history_is_not_ambiguous_score_role',{'target_evidence':[{'uncertainty':"The essay's control is consistent with an Overall score of 3, but the pattern is not definitive due to the limited history."}]},{'target_evidence':[{'uncertainty':"The essay's control is consistent with an Overall score of □, but the pattern is not definitive due to the limited history."}]},False)
check('history_mention_later_does_not_protect_target',{'decision_explanation':"The essay's minor errors align with the observed Overall score of 3, consistent with the pattern observed in the history essays."},{'decision_explanation':"The essay's minor errors align with the observed Overall score of □, consistent with the pattern observed in the history essays."},False)
check('explicit_generic_history_value_preserved',{'decision_explanation':'The target shares features with the pattern observed in the history where similar essays received an Overall score of 3.'},{'decision_explanation':'The target shares features with the pattern observed in the history where similar essays received an Overall score of 3.'},False)
check('mixed_clear_history_and_target',{'decision_explanation':'History essay 217:1 received an Overall score of 3 but the target Overall score is four.'},{'decision_explanation':'History essay 217:1 received an Overall score of 3 but the target Overall score is □.'},False)
check('scoring_history_as_value_preserved',{'decision_explanation':"This is supported by the rater's history of scoring similar essays with a mix of minor errors as Overall 3."},{'decision_explanation':"This is supported by the rater's history of scoring similar essays with a mix of minor errors as Overall 3."},False)
check('historical_essays_receiving_value_preserved',{'decision_explanation':"The essay's features align with the historical pattern observed in essays receiving an Overall score of 3."},{'decision_explanation':"The essay's features align with the historical pattern observed in essays receiving an Overall score of 3."},False)
for rid in ['1514_1__K1','1514_1__K2','1868_1__K1','1868_1__K2','4902_1__K1','4902_1__K2']:
    source=json.loads((BASE/'stage1'/rid/'parsed.json').read_text());input_=json.loads((BASE/'stage1'/rid/'input.json').read_text())
    result=mask_analysis(source['score_free_analysis'],input_['history'],input_['target'])
    if rid=='1514_1__K1':assert not result['audit']['automatic_pass']
    else:assert result['audit']['automatic_pass'],rid
    results.append(dict(name='saved_'+rid,passed=True))
(OUT/'masking_tests.json').write_text(json.dumps(dict(passed=True,tests=results),indent=2)+'\n')
print('Masking controls passed:',len(results))
