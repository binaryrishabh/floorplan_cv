# pulls door tag candidates out of the text layer. because the bid
# sets are vector pdfs straight from cad the text is exact, no ocr.
# two filters stop room numbers from posing as door tags:
#   1. a real tag sits inside its little hexagon badge
#   2. a room number always has the room name printed right above it
from config import TAG_PATTERN
from badge_finder import tag_inside_badge


def _has_room_name_above(span, spans):
    # room label blocks are name lines then the number line, so an
    # alphabetic span a few points above at the same x means room number
    for s in spans:
        if s is span:
            continue
        if not any(ch.isalpha() for ch in s["text"]):
            continue
        dy = span["y"] - s["y"]
        if 3 <= dy <= 20 and abs(s["x"] - span["x"]) < 24:
            return True
    return False


def find_tags(spans, badges):
    tags = []
    for s in spans:
        if not TAG_PATTERN.match(s["text"]):
            continue
        # sometimes cad explodes a badge and the same number prints
        # twice a few points apart, collapse anything within 12pt
        dup = False
        for t in tags:
            if t["tag"] == s["text"] and abs(t["x"] - s["x"]) < 12 and abs(t["y"] - s["y"]) < 12:
                dup = True
                break
        if dup:
            continue
        in_badge = tag_inside_badge(s["x"], s["y"], badges)
        if not in_badge and _has_room_name_above(s, spans):
            # plain number under a room name = room number, not a door
            continue
        tags.append({
            "tag": s["text"],
            "x": s["x"],
            "y": s["y"],
            "font_size": round(s["size"], 2),
            "in_badge": in_badge,
        })
    return tags