"""Value-only, role-aware masking. Findings are retained; unsafe cases are quarantined."""
import copy,json,re
DIM=r'Overall|Cohesion|Syntax|Vocabulary|Phraseology|Grammar|Conventions'
NUM=r'(?:\d+(?:\.\d+)?|one|two|three|four|five)'
SCORE=re.compile(r'\b(?:(?:'+DIM+r')\s*(?:scores?|ratings?|bands?|levels?)?|scores?|ratings?|bands?|levels?|scored|rated)\s*(?:(?:of|is|was|at|as|between|from|equal\s+to)\s*|[:=]\s*)?(?P<values>'+NUM+r'(?:\s*(?:and|or|to|through|[-–—/])\s*'+NUM+r')*)\b',re.I)
POST=re.compile(r'\b(?P<values>'+NUM+r'(?:\s*(?:and|or|to|through|[-–—/])\s*'+NUM+r')*)[- ](?:point|band|level)\b',re.I)
N=re.compile(r'\b'+NUM+r'\b',re.I)
EQUIV=re.compile(r'\b(?:same|equal|identical|equivalent)\s+(?:observed\s+)?(?:overall\s+|trait\s+)?(?:score|rating|band|level)\b.{0,100}\bhistory\b|\b(?:same|equal|identical)\s+Overall\s+as\b|\b(?:matches|equals)\b.{0,50}\bhistory\b.{0,50}\bscore\b|\bhistory\b.{0,60}\bscore\b.{0,60}\b(?:equals|same as)\b.{0,30}\btarget\b',re.I)
CALC=re.compile(r'\d\s*[+*/=]\s*\d|\b(?:sum|average|mean|weighted sum|subtract|divided by|plus|minus)\b.{0,80}\b(?:target|Overall|score)\b|\b(?:target|Overall|score)\b.{0,80}\b(?:average of|sum of|divided by|plus|minus|subtract)\b',re.I)
NAMED=re.compile(r'\b(?:highest|lowest|top|bottom|native-like)\s+(?:rubric\s+)?(?:band|level|score)\b|\b(?:band|level)\s+(?:A1|A2|B1|B2|C1|C2|advanced|proficient|excellent)\b',re.I)
def mask_analysis(analysis,history,target):
    hist={h['essay_id']:h for h in history};source={**hist,target['essay_id']:target}
    changes=[];protected=[];issues=[]
    def issue(path,kind,text):issues.append(dict(path=path,kind=kind,text=text,action='quarantine; not automatically rewritten'))
    def textmask(text,path,role,eid):
        # Exact source quotation leaves and source IDs never enter this routine.
        explicit_target=bool(re.search(r'\btarget\b',text,re.I))
        if role=='invalid_history':return text
        if role=='history' and not explicit_target:
            protected.append(dict(path=path,reason='history-context prose tied to supplied history IDs; preserve history score values'));return text
        if EQUIV.search(text):issue(path,'recoverable_history_equivalence',text);return text
        if CALC.search(text):issue(path,'recoverable_calculation',text);return text
        if NAMED.search(text):issue(path,'unique_or_unspecified_named_band',text);return text
        if re.search(r'\b(?:unclear|unspecified|unknown|either)\b',text,re.I) and re.search(r'\btarget\b',text,re.I) and re.search(r'\bhistory\b',text,re.I):
            issue(path,'ambiguous_target_history_attribution',text);return text
        spans=[]
        for regex in [SCORE,POST]:
            for match in regex.finditer(text):
                # A clearly identified history-score clause remains unchanged even in target discussion.
                start=text.rfind('.',0,match.start())+1;end=text.find('.',match.end());end=len(text) if end<0 else end
                clause=text[start:end]
                history_before=re.search(r'\bhistory\s+essays?\s+([\w:.-]+)',text[start:match.start()],re.I)
                history_after=re.search(r'\bin\s+(?:the\s+)?history\s+essays?\b',text[match.end():end],re.I)
                if history_before and history_before.group(1).rstrip('.,') in hist or history_after:
                    protected.append(dict(path=path,span=[match.start(),match.end()],text=match.group(),reason='Explicitly attributed history score clause'));continue
                if re.search(r'\bhistory\s+(?:score|rating|band|level)\b',clause,re.I) and not re.search(r'\btarget\b',clause,re.I):
                    issue(path,'ambiguous_target_history_attribution',clause);continue
                for n in N.finditer(match.group('values')):
                    a=match.start('values')+n.start();b=match.start('values')+n.end()
                    spans.append((a,b))
        spans=sorted(set(spans));masked=text
        for a,b in reversed(spans):masked=masked[:a]+'□'+masked[b:]
        if spans:changes.append(dict(path=path,before=text,after=masked,value_spans=[dict(start=a,end=b,value=text[a:b],replacement='□') for a,b in spans],reason='Explicit target-attributed score or numbered performance band/range; replace values only'))
        return masked
    def walk(x,path='',role='target',eid=None):
        if isinstance(x,dict):
            result={}
            if 'history_essay_id' in x:
                eid=x['history_essay_id'];role='history' if eid in hist else 'invalid_history'
                if role=='invalid_history':issue(path+'/history_essay_id','invalid_history_reference',eid)
            for k,v in x.items():
                p=path+'/'+str(k)
                if k in ['history_essay_id','target_essay_id','essay_id','pattern_id','evidence_id','linked_history_pattern_ids','dimensions']:
                    result[k]=copy.deepcopy(v);protected.append(dict(path=p,reason='ID/dimension metadata preserved'))
                elif k=='quotes':
                    result[k]=copy.deepcopy(v);protected.append(dict(path=p,reason='Source quotations preserved verbatim'))
                    for q in v:
                        if eid and eid in source and q not in source[eid]['text']:
                            protected.append(dict(path=p,reason='Quotation not an exact substring; content finding, not repaired'))
                elif k=='relevant_observed_history_scores':
                    result[k]=copy.deepcopy(v)
                    if role!='history':issue(p,'unverified_history_score_attribution',json.dumps(v))
                    else:protected.append(dict(path=p,reason='Scores explicitly attributed to a valid supplied history ID'))
                elif isinstance(v,(int,float)) and not isinstance(v,bool) and re.search(r'(?:score|overall|trait|band|level|'+DIM+r')',k,re.I) and role!='history':
                    if role=='invalid_history':result[k]=v
                    else:
                        result[k]='□';changes.append(dict(path=p,before=v,after='□',value_spans=[],reason='Explicit numeric target score field; value only'))
                else:result[k]=walk(v,p,role,eid)
            return result
        if isinstance(x,list):
            result=[]
            for i,v in enumerate(x):
                p=path+'/'+str(i);r=role
                if path=='/history_patterns':
                    ids=[z.get('history_essay_id') for z in v.get('support',[])+v.get('counterevidence',[])] if isinstance(v,dict) else []
                    r='history' if ids and all(z in hist for z in ids) else 'invalid_history'
                    if not ids:issue(p,'unattributed_history_pattern','No supplied history ID anchors the proposed historical score statements')
                result.append(walk(v,p,r,eid))
            return result
        if isinstance(x,str):return textmask(x,path,role,eid)
        return copy.deepcopy(x)
    masked=walk(analysis,eid=target['essay_id'])
    # Mechanical invariant: only logged value characters may have changed.
    def at(x,path):
        for k in path.strip('/').split('/') if path else []:x=x[int(k)] if isinstance(x,list) else x[k]
        return x
    allowed={c['path']:c for c in changes}
    def verify(a,b,path=''):
        if path in allowed:
            c=allowed[path];assert a==c['before'] and b==c['after']
            if isinstance(a,str):
                s=a
                for z in reversed(c['value_spans']):s=s[:z['start']]+'□'+s[z['end']:]
                assert s==b
            return
        if isinstance(a,dict):
            assert set(a)==set(b)
            for k in a:verify(a[k],b[k],path+'/'+k)
        elif isinstance(a,list):
            assert len(a)==len(b)
            for i,(v,w) in enumerate(zip(a,b)):verify(v,w,path+'/'+str(i))
        else:assert a==b,(path,a,b)
    verify(analysis,masked)
    return dict(masked_analysis=masked,audit=dict(changes=changes,value_replacements=sum(len(c['value_spans']) or 1 for c in changes),changed_fields=len(changes),protected=protected,quarantine=issues,automatic_pass=not issues,value_only_invariant=True))
