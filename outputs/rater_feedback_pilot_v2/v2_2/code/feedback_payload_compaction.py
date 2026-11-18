"""本文を省略せず、繰り返される証拠オブジェクトだけを参照化する。"""
import copy
import collections
import json


def intern_payload(payload):
    """同一の配列・辞書・長い文字列も一度だけ格納。出力schemaは元payloadから作る。"""
    counts=collections.Counter()
    def signature(v):
        if not isinstance(v,(dict,list,str)): return None
        s=json.dumps(v,ensure_ascii=False,separators=(',',':'),sort_keys=True)
        return s if len(s)>=64 else None
    def scan(v):
        sig=signature(v)
        if sig: counts[sig]+=1
        if isinstance(v,dict):
            for x in v.values(): scan(x)
        elif isinstance(v,list):
            for x in v: scan(x)
    scan(payload);catalog={};names={}
    def children(v):
        if isinstance(v,dict): return {k:encode(x) for k,x in v.items()}
        if isinstance(v,list): return [encode(x) for x in v]
        return v
    def encode(v):
        sig=signature(v)
        if sig and counts[sig]>1:
            if sig not in names:
                name='D'+str(len(names)+1);names[sig]=name
                catalog[name]=children(v)
            return {'$ref':names[sig]}
        return children(v)
    result=dict(input=encode(payload),reference_catalog=catalog,
        serialization='Every {$ref: ID} substitutes the exact full value in reference_catalog, recursively. All original input information and full essay context are present; references only remove duplicate storage.')
    assert expand_interned(result)==payload
    return result


def expand_interned(payload):
    def visit(v):
        if isinstance(v,dict):
            if set(v)=={'$ref'}: return visit(payload['reference_catalog'][v['$ref']])
            return {k:visit(x) for k,x in v.items()}
        if isinstance(v,list): return [visit(x) for x in v]
        return v
    return visit(payload['input'])


def compact_payload(payload):
    catalog = {}
    def visit(value, key=None):
        if isinstance(value, dict):
            return {k: visit(v, k) for k, v in value.items()}
        if isinstance(value, list):
            if key in ('evidence', 'citations'):
                result = []
                for entry in value:
                    if isinstance(entry, dict) and {'span_id', 'text', 'start', 'end'} <= entry.keys():
                        sid = entry['span_id']
                        assert sid not in catalog or catalog[sid] == entry
                        catalog[sid] = copy.deepcopy(entry)
                        result.append({'span_id': sid, 'evidence_ref': sid})
                    else:
                        result.append(visit(entry))
                return result
            return [visit(v) for v in value]
        return value
    compact = visit(payload)
    if not catalog:
        return compact
    compact['_evidence_catalog'] = catalog
    compact['_serialization'] = 'evidence/citations entries with evidence_ref resolve to the complete original object in _evidence_catalog. No evidence, context, claim or condition is omitted.'
    assert expand_payload(compact) == payload
    return compact


def expand_payload(payload):
    catalog = payload.get('_evidence_catalog', {})
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {'span_id', 'evidence_ref'}:
                assert value['span_id'] == value['evidence_ref']
                return copy.deepcopy(catalog[value['evidence_ref']])
            return {k: visit(v) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v) for v in value]
        return value
    return visit({k: v for k, v in payload.items() if k not in ('_evidence_catalog', '_serialization')})
