from __future__ import annotations
import math, re

# Registration anchors are deliberately broader than door tags: room numbers and
# equipment/space identifiers survive across overall/enlarged views and let us
# register cropped views without assuming fixed page coordinates.
ANCHOR_RE=re.compile(r'^\d{3,5}[A-Z]?$')


def find_text_anchors(spans):
    grouped={}
    for s in spans:
        t=s['text'].strip().upper()
        if not ANCHOR_RE.match(t): continue
        if not (4.0<=s['size']<=20.0): continue
        arr=grouped.setdefault(t,[])
        # PDF exports often duplicate identical text on two graphics layers.
        if not any(math.hypot(x-s['x'],y-s['y'])<=2.0 for x,y in arr):
            arr.append((s['x'],s['y']))
    # Only unique occurrences on a sheet are safe correspondence anchors.
    return {t:pts[0] for t,pts in grouped.items() if len(pts)==1}
