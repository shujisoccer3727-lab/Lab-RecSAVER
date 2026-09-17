"""Context-aware score disclosure and exploratory rater-attribute warnings."""
import re
import unicodedata

WORDS = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}


def score_disclosures(text, score):
    text = unicodedata.normalize('NFKC', text)
    number = rf'(?:{score}|{WORDS[score]})'
    context = r'(?:overall(?:\s+score)?|score|rating|rated|level|grade|predicted_overall|gold_overall|overall_score|final_score)'
    patterns = {
        'score_context': rf'\b{context}\b[\s\"\x27:=_-]*(?:(?:is|was|of|at|as|would be|should be|equals|assigned|given|a|an)\s+){{0,3}}{number}\b',
        'out_of_five': rf'\b{number}\s*(?:out of|/|of)\s*(?:5|five)\b',
        'reverse_score_context': rf'\b{number}[\s-]+(?:overall|points?|rating|score|level)\b',
        'awarded_number': rf'\b(?:deserves?|merits?|awarded|assigned|received|give|given|earns?)\s+(?:(?:it|this essay|an?|the|of)\s+){{0,3}}{number}\b',
        'standalone_number': rf'^\s*[\"\x27]?{number}[\"\x27.!]?\s*$',
    }
    return [label + ': ' + match.group(0) for label, pattern in patterns.items()
            for match in re.finditer(pattern, text, re.I)]


def leakage_audit(reasoning, raw, gold):
    gold_reasons = score_disclosures(reasoning, gold) + score_disclosures(raw, gold)
    other = [reason for score in range(1, 6) if score != gold
             for reason in score_disclosures(reasoning, score) + score_disclosures(raw, score)]
    return {'leaked': bool(gold_reasons), 'leakage_reason': '; '.join(dict.fromkeys(gold_reasons)),
            'other_score_disclosure': bool(other), 'other_score_reason': '; '.join(dict.fromkeys(other))}


def quality_warnings(reasoning):
    attributes = r'personality|nationality|teaching experience|background|hidden intentions?|native speaker|national origin'
    patterns = [rf'\b(?:rater|grader|teacher|scorer)\b.{{0,100}}\b(?:{attributes})\b',
                rf'\b(?:{attributes})\b.{{0,100}}\b(?:rater|grader|teacher|scorer)\b']
    return list(dict.fromkeys(match.group(0) for pattern in patterns for match in re.finditer(pattern, reasoning, re.I)))
