from pathlib import Path
import difflib
import pandas as pd

root=Path(__file__).resolve().parents[1]
raw=pd.read_csv(root/'data/raw/ellipsis_raw_rater_scores_anon_all_essay.csv')
for name,g in raw[raw.Filename.duplicated(False)].groupby('Filename'):
    print('\nFILENAME',name)
    a,b=g.Text.tolist()
    matcher=difflib.SequenceMatcher(None,a,b,autojunk=False)
    edits=[]
    for tag,i,j,k,l in matcher.get_opcodes():
        if tag!='equal':edits.append((tag,a[max(0,i-30):min(len(a),j+30)],b[max(0,k-30):min(len(b),l+30)]))
    print(repr(edits)[:2400])
    print(g[['Rater_1','Rater_2','Overall_1','Overall_2']].to_string(index=False))
    if name=='AAAUUP138180000193682125_OR':
        print(g.to_dict('records'))
