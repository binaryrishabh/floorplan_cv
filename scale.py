from __future__ import annotations
import math, re

_SCALE_RE = re.compile(
    r'(?P<num>\d+(?:\s*/\s*\d+)?)\s*"\s*=\s*'
    r'(?P<feet>\d+)\s*\'\s*-\s*(?P<inch>\d+(?:\s*/\s*\d+)?)\s*"',
    re.I,
)
_SIMPLE_RE = re.compile(r'(?P<num>\d+(?:\s*/\s*\d+)?)\s*"\s*=\s*1\s*\'\s*-\s*0\s*"', re.I)


def _fraction(s: str) -> float:
    s = s.replace(' ', '')
    if '/' in s:
        a,b=s.split('/',1); return float(a)/float(b)
    return float(s)


def parse_scales(text: str):
    """Return candidate drawing scales as points per real-world foot."""
    out=[]
    for m in _SCALE_RE.finditer(text):
        paper_inches=_fraction(m.group('num'))
        feet=float(m.group('feet')) + _fraction(m.group('inch'))/12.0
        if paper_inches>0 and feet>0:
            # PDF points per real-world foot.
            ppf = 72.0 * paper_inches / feet
            if 1.0 <= ppf <= 144.0:
                out.append({'text':m.group(0), 'points_per_foot':ppf})
    return out


def choose_page_scale(text: str, default_ppf: float = 18.0):
    scales=parse_scales(text)
    if not scales:
        return {'points_per_foot':default_ppf,'source':'default','scale_text':None,'candidates':[]}
    # A repeated scale is usually the primary plan scale (title + view label).
    buckets={}
    for s in scales:
        k=round(s['points_per_foot'],3); buckets.setdefault(k,[]).append(s)
    ppf, vals=max(buckets.items(), key=lambda kv:(len(kv[1]), kv[0]))
    source='text_unique' if len(buckets)==1 else 'text_mode'
    return {'points_per_foot':ppf,'source':source,'scale_text':vals[0]['text'],'candidates':[x['points_per_foot'] for x in scales]}


def pt_from_ft(feet: float, ppf: float) -> float:
    return feet * ppf


def ft_from_pt(points: float, ppf: float) -> float:
    return points / ppf if ppf else math.inf
