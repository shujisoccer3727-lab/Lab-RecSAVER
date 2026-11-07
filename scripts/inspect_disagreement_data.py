"""Read-only inspection before defining essay identity and duplicate handling."""
import json
import difflib
from pathlib import Path
import pandas as pd

root = Path(__file__).resolve().parents[1]
raw = pd.read_csv(root/'data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv')
out = root/'outputs/human_score_disagreement'
out.mkdir(parents=True, exist_ok=True)
duplicates = raw[raw.Filename.duplicated(False)]
duplicates.to_json(out/'filename_duplicates_inspection.json', orient='records', force_ascii=False, indent=2)
print('raw', len(raw), 'unique filename/text/kaggle', raw.Filename.nunique(), raw.Text.nunique(), raw.text_id_kaggle.nunique())
for key, g in duplicates.groupby('Filename'):
    print('duplicate', key, 'rows', len(g), 'texts', g.Text.nunique(), 'kaggle', g.text_id_kaggle.tolist(),
          'raters', g[['Rater_1','Rater_2']].values.tolist(), 'overall', g[['Overall_1','Overall_2']].values.tolist())
    print('text_similarity', difflib.SequenceMatcher(None, *g.Text.tolist()).ratio(), 'lengths', g.Text.str.len().tolist())
for col in ['Filename','text_id_kaggle','Text']:
    print('missing', col, int(raw[col].isna().sum()))
valid = raw.Overall_1.isin(range(1,6)) & raw.Overall_2.isin(range(1,6))
print('row pair gap valid', (raw.loc[valid,'Overall_1']-raw.loc[valid,'Overall_2']).abs().value_counts().to_dict())
print('gap>=3 including invalid',raw[(raw.Overall_1-raw.Overall_2).abs()>=3][['Filename','Overall_1','Overall_2']].to_dict('records'))
