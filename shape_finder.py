# geometry hunting: door swing arcs and the gaps doors leave in wall
# lines. pure vector math, no pixel work, which is why its so fast

from config import (ARC_MIN_PT, ARC_MAX_PT, ARC_RATIO_MIN, ARC_RATIO_MAX,
                    GAP_MIN_PT, GAP_MAX_PT, WALL_MIN_LEN_PT)


def find_swing_arcs(drawings):
    # quarter circle swings show up as curve items with a squarish bbox
    arcs = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] != "c":
                continue
            pts = item[1:]
            xs = [p.x for p in pts]
            ys = [p.y for p in pts]
            w = max(xs) - min(xs)
            h = max(ys) - min(ys)
            if w < ARC_MIN_PT or h < ARC_MIN_PT:
                continue
            if w > ARC_MAX_PT or h > ARC_MAX_PT:
                continue
            ratio = w / h if h else 0
            if ratio < ARC_RATIO_MIN or ratio > ARC_RATIO_MAX:
                continue
            arcs.append({
                "x": (min(xs) + max(xs)) / 2.0,
                "y": (min(ys) + max(ys)) / 2.0,
                "w": round(w, 1),
                "h": round(h, 1),
            })
    return arcs


def _collect_wall_lines(drawings):
    horiz = {}
    vert = {}
    for d in drawings:
        for item in d.get("items", []):
            if item[0] != "l":
                continue
            p1, p2 = item[1], item[2]
            dx = abs(p1.x - p2.x)
            dy = abs(p1.y - p2.y)
            if dy < 1.5 and dx > 20:
                y = round((p1.y + p2.y) / 2.0, 1)
                horiz.setdefault(y, []).append((min(p1.x, p2.x), max(p1.x, p2.x)))
            elif dx < 1.5 and dy > 20:
                x = round((p1.x + p2.x) / 2.0, 1)
                vert.setdefault(x, []).append((min(p1.y, p2.y), max(p1.y, p2.y)))
    return horiz, vert


def _merge(segs):
    out = []
    for start, end in segs:
        if out and start <= out[-1][1] + 2.0:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return out


def find_wall_gaps(drawings):
    # walk each wall line and report breaks that are door sized
    horiz, vert = _collect_wall_lines(drawings)
    gaps = []
    for y, segs in horiz.items():
        merged = _merge(sorted(segs))
        if merged[-1][1] - merged[0][0] < WALL_MIN_LEN_PT:
            continue
        for a, b in zip(merged, merged[1:]):
            hole = b[0] - a[1]
            if GAP_MIN_PT <= hole <= GAP_MAX_PT:
                gaps.append({"x": (a[1] + b[0]) / 2.0, "y": y, "w": round(hole, 1)})
    for x, segs in vert.items():
        merged = _merge(sorted(segs))
        if merged[-1][1] - merged[0][0] < WALL_MIN_LEN_PT:
            continue
        for a, b in zip(merged, merged[1:]):
            hole = b[0] - a[1]
            if GAP_MIN_PT <= hole <= GAP_MAX_PT:
                gaps.append({"x": x, "y": (a[1] + b[0]) / 2.0, "w": round(hole, 1)})
    return gaps