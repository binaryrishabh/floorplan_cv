# cross sheet sanity check. the same physical door should not show up
# on two enlarged sheets, if it does thats a dup for a human to eyeball

from collections import defaultdict


def reconcile(pages_doors):
    counts = defaultdict(list)
    for pno, doors in pages_doors.items():
        for d in doors:
            if d["tag"]:
                counts[d["tag"]].append(pno)
    dupes = {t: p for t, p in counts.items() if len(p) > 1}
    return {
        "unique_tags": len(counts),
        "tags_on_multiple_sheets": dupes,
    }