"""Deterministic display assembly. Invalid selections fail; never choose a fallback."""
TOKEN='[REPRESENTATIVE_EVIDENCE]'
def assemble(value,payload):
    import re
    errors=[];key=value.get('representative_observation_key');index=value.get('representative_quote_index');template=value.get('feedback_paragraph_template')
    if not isinstance(template,str):return dict(pass_=False,errors=['template is not a string'],feedback_paragraph=None)
    obs={o['observation_key']:o for o in payload.get('verified_observations',[])};sentence=None;quote=None;eid=None
    if key is None:
        if index is not None:errors.append('no representative requires null quote index')
        if template.count(TOKEN)!=0:errors.append('no representative requires zero placeholders')
    else:
        if not isinstance(key,str) or key not in obs:errors.append('unknown representative observation key')
        if isinstance(index,bool) or not isinstance(index,int) or index<0:errors.append('quote index must be a nonnegative integer')
        if template.count(TOKEN)!=1:errors.append('representative requires exactly one placeholder')
        if TOKEN in template:
            left,right=template.split(TOKEN,1)
            if (left and not left[-1].isspace()) or (right and not right[0].isspace()):errors.append('placeholder is not a standalone sentence slot')
            if re.search(r'["“”\x27]\s*'+re.escape(TOKEN)+r'\s*["“”\x27]',template):errors.append('placeholder surrounded by quotes')
            if re.match(r'\s*[.!?]',right):errors.append('punctuation appended to placeholder')
        if isinstance(key,str) and key in obs:
            o=obs[key];quotes=o.get('quotes',[])
            if isinstance(index,int) and not isinstance(index,bool) and 0<=index<len(quotes):
                quote=quotes[index];eid=o.get('target_essay_id')
                if not isinstance(quote,str) or not isinstance(eid,str):errors.append('invalid source quote or target ID')
            elif isinstance(index,int) and not isinstance(index,bool):errors.append('quote index out of range')
    if not errors and key is not None:sentence=f'In essay {eid}, the relevant excerpt is “{quote}”.'
    paragraph=None if errors else template.replace(TOKEN,sentence) if sentence is not None else template
    return dict(pass_=not errors,errors=errors,representative_observation_key=key,representative_quote_index=index,target_essay_id=eid,exact_quote=quote,evidence_sentence=sentence,feedback_paragraph=paragraph,source='programmatic exact lookup, not model generation')
