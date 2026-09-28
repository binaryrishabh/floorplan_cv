# pulls door tag candidates out of the text layer. because the bid
# sets are vector pdfs straight from cad the text is exact, no ocr

from config import TAG_PATTERN


def find_tags(spans):
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
        tags.append({
            "tag": s["text"],
            "x": s["x"],
            "y": s["y"],
            "font_size": round(s["size"], 2),
        })
    return tags