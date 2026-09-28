from __future__ import annotations
import re
from config import FLOOR_POSITIVE, FLOOR_NEGATIVE

_LEVEL_RE = re.compile(r'\bLEVEL\s*[-#:]?\s*([A-Z0-9]+)\b', re.I)
_AREA_RE = re.compile(r'\bAREA\s*[-:]?\s*([A-Z0-9]+)\b', re.I)
_SHEET_RE = re.compile(r'\bA\d+(?:\.\d+)?[A-Z]?\b', re.I)


def classify_sheet(text: str):
    up=' '.join(text.upper().split())
    negatives=[k for k in FLOOR_NEGATIVE if k in up]
    positives=[k for k in FLOOR_POSITIVE if k in up]
    # FLOOR PLAN is decisive unless the sheet is explicitly another plan type.
    is_floor=bool(positives) and not any(k in up for k in ('REFLECTED CEILING','ROOF PLAN','FINISH PLAN','DEMOLITION PLAN'))
    kind='floor_plan' if is_floor else ('non_floor' if negatives else 'unknown')
    detail='enlarged' if 'ENLARGED' in up else ('overall' if 'OVERALL' in up else 'standard')
    level=None
    ms=list(_LEVEL_RE.finditer(up))
    if ms: level=ms[-1].group(1).upper()
    area=None
    ma=list(_AREA_RE.finditer(up))
    if ma: area=ma[-1].group(1).upper()
    sheet=None
    sh=list(_SHEET_RE.finditer(up))
    if sh: sheet=sh[-1].group(0).upper()
    return {
        'kind':kind,'detail':detail,'level':level,'area':area,'sheet_number':sheet,
        'positive_hits':positives,'negative_hits':negatives,
    }
