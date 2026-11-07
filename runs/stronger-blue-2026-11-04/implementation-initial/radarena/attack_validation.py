"""Conservative controlled-attribute edit validator, not a clinical validity oracle."""
import re
from .agents import apply_edits


def normalize(text):
    return re.sub(r'\s+',' ',re.sub(r'^(FINDINGS|IMPRESSION):\s*','',text,flags=re.I)).strip().lower()


def validate_attack_family(source, edits, family):
    candidate=apply_edits(source,edits)
    original={s.id:s.text for s in source}
    for edit in edits:
        before,after=normalize(original[edit.sentence_id]),normalize(edit.replacement)
        if family in {'severity','laterality'}:
            pattern=r'\b(mild|mildly|moderate|moderately|severe|severely|minimal|minimally|small|large)\b' if family=='severity' else r'\b(left|right)\b'
            a,b=re.findall(pattern,before),re.findall(pattern,after)
            if not a or not b or a==b or re.sub(pattern,'<attribute>',before)!=re.sub(pattern,'<attribute>',after):
                raise ValueError(f'{family} edit must change only the existing attribute; preserve finding presence and other claims')
        elif family=='presence_absence':
            # Controlled negation flips only. Broader novel edits require separate semantic adjudication.
            pattern=r'\b(no|not|without|absent|present)\b'
            if not (re.search(pattern,before) or re.search(pattern,after)):
                raise ValueError('Controlled presence/absence requires an explicit status change')
            if normalize(re.sub(pattern,'',before))!=normalize(re.sub(pattern,'',after)) or before==after:
                raise ValueError('Controlled presence/absence must preserve the remaining claim text')
        else:raise ValueError('Unknown controlled error family')
    return candidate
