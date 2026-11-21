"""Common mechanical audit for both versions; heuristic flags are not verdicts."""
from pathlib import Path
import importlib.util,json,re,difflib
OUT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('experiment',OUT/'code/run.py');r=importlib.util.module_from_spec(sp);sp.loader.exec_module(r)
def fields(v,path=''):
    if isinstance(v,dict):
        for k,x in v.items():
            if k not in ['quotes','relevant_observed_history_scores']:yield from fields(x,path+'/'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):yield from fields(x,path+'/'+str(i))
    elif isinstance(v,str):yield path,v
def scan(v):
    rules=[r'\b(?:score|band|level)s?\s*(?:of|is|was|=|:)?\s*(?:[1-5]|one|two|three|four|five)\b',r'\b(?:overall|cohesion|syntax|vocabulary|phraseology|grammar|conventions)\s*(?:score\s*)?(?:of|is|was|=|:)?\s*[1-5]\b',r'\b(?:same|equal|matches|higher|lower).{0,70}(?:score|history|level|band)',r'\b(?:observed|assigned|target).{0,80}\b(?:[1-5]|one|two|three|four|five)\b']
    return [dict(path=p,text=t,rule=rule) for p,t in fields(v) for rule in rules if re.search(rule,t,re.I)]
def metric(root,rid):
    f=root/'stage1'/rid;inp=r.read(f/'input.json');res=r.read(f/'result.json')
    if not (f/'parsed.json').exists():return dict(strict_json=res['json_valid'],structure=res['schema_valid'],quotes=[],score_missing=[],score_wrong=[],score_extra=[])
    v=r.read(f/'parsed.json');sources={e['essay_id']:e['text'] for e in [inp['target']]+inp['history']};quotes=[];history_score_errors=[];history_role_errors=[]
    def quotecheck(q,eid,path):
        src=sources.get(eid,'');nw=lambda s:re.sub(r'\s+',' ',s).strip()
        typ='exact' if q and q in src else 'whitespace_only' if q and nw(q) in nw(src) else 'escaped_character_representation' if q and nw(q.replace('\\u0027',"'")) in nw(src) else 'wording_or_punctuation_change'
        match=difflib.SequenceMatcher(None,q,src,autojunk=False).find_longest_match(0,len(q),0,len(src))
        quotes.append(dict(path=path,essay_id=eid,quote=q,category=typ,source_context=src[max(0,match.b-30):min(len(src),match.b+match.size+100)],source_exists=eid in sources))
    def walk(x,path='',eid=inp['target']['essay_id']):
        if isinstance(x,dict):
            eid=x.get('history_essay_id',eid)
            if 'history_essay_id' in x and eid not in {h['essay_id'] for h in inp['history']}:
                history_role_errors.append(dict(path=path+'/history_essay_id',essay_id=eid,reason='Not a supplied history essay'))
            if 'relevant_observed_history_scores' in x:
                hs=next((e for e in inp['history'] if e['essay_id']==eid),None)
                if hs:
                    ss=x['relevant_observed_history_scores']
                    for k,z in [('Overall',ss.get('Overall'))]+list(ss.get('Traits',{}).items()):
                        actual=hs['Overall'] if k=='Overall' else hs['Traits'].get(k)
                        if z!=actual:history_score_errors.append(dict(path=path,dimension=k,value=z,expected=actual))
            for k,z in x.items():
                if k=='quotes' and isinstance(z,list):
                    for i,q in enumerate(z):quotecheck(q,eid,path+'/quotes/'+str(i))
                else:walk(z,path+'/'+k,eid)
        elif isinstance(x,list):
            for i,z in enumerate(x):walk(z,path+'/'+str(i),eid)
    walk(v)
    actual=inp['target'];given=v.get('observed_score_alignment',{}).get('observed_target_scores',{})
    expected={'Overall':actual['Overall'],**actual['Traits']};got={'Overall':given['Overall']} if 'Overall' in given else {};got.update(given.get('Traits',{}))
    missing=[k for k in expected if k not in got];wrong=[dict(dimension=k,value=got[k],expected=expected[k]) for k in expected if k in got and (isinstance(got[k],bool) or got[k]!=expected[k])]
    return dict(strict_json=res['json_valid'],structure=res['schema_valid'],quotes=quotes,quote_counts=dict(__import__('collections').Counter(q['category'] for q in quotes)),score_missing=missing,score_wrong=wrong,score_extra=[k for k in got if k not in expected],all_observed_scores_equal=not missing and not wrong and set(got)==set(expected),history_score_errors=history_score_errors,history_role_errors=history_role_errors,suspicions=scan(v['score_free_analysis']),pattern_count=len(v['score_free_analysis']['history_patterns']),target_evidence_count=len(v['score_free_analysis']['target_evidence']))
def main():
    all_results={}
    for version,root in [('v1_0',r.OLD),('v1_1',OUT)]:
        all_results[version]={}
        for c in r.cases():
            for rid in r.ids(c):
                if (root/'stage1'/rid/'result.json').exists():all_results[version][rid]=metric(root,rid)
    r.save(OUT/'common_mechanical_audit.json',dict(timestamp=r.now(),method='Same exact-substring, whitespace-only, escaped-character and wording/punctuation categories for both versions. No generated text changed; semantic classifications require Codex review.',versions=all_results))
    print(json.dumps({v:{k:{a:b for a,b in m.items() if a not in ['quotes','suspicions']} for k,m in data.items()} for v,data in all_results.items()},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
