# door tags sit inside a little elongated hexagon badge on these sheets.
# room numbers and keynotes are plain text with no shape around them,
# so hunting for the badge shape is how we tell the two apart
from config import (BADGE_MIN_W_PT, BADGE_MAX_W_PT,
                    BADGE_MIN_H_PT, BADGE_MAX_H_PT, BADGE_PAD_PT)


def _bbox_of(items):
    xs = []
    ys = []
    for item in items:
        for p in item[1:]:
            if hasattr(p, "x"):
                xs.append(p.x)
                ys.append(p.y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def find_badges(drawings):
    badges = []
    for d in drawings:
        items = d.get("items", [])
        # a hexagon is a short closed polyline, 6-ish straight segments
        if not (4 <= len(items) <= 10):
            continue
        if any(item[0] != "l" for item in items):
            continue
        bb = _bbox_of(items)
        if bb is None:
            continue
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        if not (BADGE_MIN_W_PT <= w <= BADGE_MAX_W_PT):
            continue
        if not (BADGE_MIN_H_PT <= h <= BADGE_MAX_H_PT):
            continue
        # closed loop: last point walks back to the first one
        first = items[0][1]
        last = items[-1][2]
        if abs(first.x - last.x) > 1.0 or abs(first.y - last.y) > 1.0:
            continue
        badges.append(bb)
    return badges


def tag_inside_badge(x, y, badges):
    for (x0, y0, x1, y1) in badges:
        if (x0 - BADGE_PAD_PT <= x <= x1 + BADGE_PAD_PT
                and y0 - BADGE_PAD_PT <= y <= y1 + BADGE_PAD_PT):
            return True
    return False