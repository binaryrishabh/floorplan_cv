# ties tags, swings and wall gaps together into door records. a door
# is strongest when two or three of the evidences agree on location

import math
from config import MATCH_RADIUS_PT


def _dist(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def _nearest(point, pool, radius, used):
    best = None
    best_d = radius
    for i, p in enumerate(pool):
        if i in used:
            continue
        d = _dist(point, p)
        if d < best_d:
            best_d = d
            best = i
    return best


def match_doors(tags, arcs, gaps):
    doors = []
    used_arcs = set()
    used_gaps = set()
    for t in tags:
        arc_idx = _nearest(t, arcs, MATCH_RADIUS_PT, used_arcs)
        gap_idx = _nearest(t, gaps, MATCH_RADIUS_PT, used_gaps)
        if arc_idx is not None:
            used_arcs.add(arc_idx)
        if gap_idx is not None:
            used_gaps.add(gap_idx)
        doors.append({
            "tag": t["tag"],
            "x": round(t["x"], 1),
            "y": round(t["y"], 1),
            "swing_arc": arc_idx is not None,
            "wall_gap": gap_idx is not None,
            "evidence": 1 + (arc_idx is not None) + (gap_idx is not None),
        })
    # lone swings with no tag nearby still mean an opening exists,
    # report them as untaged so the estimator can eyeball them later
    for i, a in enumerate(arcs):
        if i not in used_arcs:
            doors.append({
                "tag": None,
                "x": round(a["x"], 1),
                "y": round(a["y"], 1),
                "swing_arc": True,
                "wall_gap": False,
                "evidence": 1,
            })
    return doors