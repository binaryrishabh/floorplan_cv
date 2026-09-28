# cross sheet sanity check with the founders rule baked in: the overall
# plan is ignored for counting, only enlarged sheets vote.
# two kinds of conflicts actually matter:
#   same tag twice on one enlarged sheet -> double print or two leaves
#   same tag on two enlarged sheets -> real contradiction to eyeball
from collections import defaultdict
from config import OVERALL_PAGES


def reconcile(pages_doors):
    per_sheet = defaultdict(list)
    sheets_per_tag = defaultdict(set)
    for pno, doors in pages_doors.items():
        if pno in OVERALL_PAGES:
            continue
        for d in doors:
            if not d["tag"]:
                continue
            per_sheet[(pno, d["tag"])].append(d)
            sheets_per_tag[d["tag"]].add(pno)

    within_sheet = {
        f"sheet{pno}_tag{tag}": len(v)
        for (pno, tag), v in per_sheet.items() if len(v) > 1
    }
    cross_area = {
        tag: sorted(pages)
        for tag, pages in sheets_per_tag.items() if len(pages) > 1
    }
    return {
        "unique_tags_on_enlarged": len(sheets_per_tag),
        "tags_printed_twice_on_one_sheet": within_sheet,
        "tags_on_multiple_enlarged_sheets": cross_area,
    }