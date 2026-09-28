# kills the false positives that repeat on every sheet. title block
# symbols, north arrows and key plans print at identical coordnates on
# all pages, a real door opening never does that
from config import STATIC_MIN_PAGES, STATIC_SNAP_PT


def _key(d):
    return (round(d["x"] / STATIC_SNAP_PT), round(d["y"] / STATIC_SNAP_PT))


def drop_sheet_furniture(pages_doors):
    # pass 1: count how many sheets each untagged detection sits on
    seen = {}
    for pno, doors in pages_doors.items():
        for d in doors:
            if d["tag"]:
                continue
            seen.setdefault(_key(d), set()).add(pno)
    static_keys = {k for k, pages in seen.items() if len(pages) >= STATIC_MIN_PAGES}

    # pass 2: rebuild the door lists without the furniture
    cleaned = {}
    dropped = 0
    for pno, doors in pages_doors.items():
        keep = []
        for d in doors:
            if not d["tag"] and _key(d) in static_keys:
                dropped += 1
                continue
            keep.append(d)
        cleaned[pno] = keep
    return cleaned, dropped