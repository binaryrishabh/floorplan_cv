# entry point: python run.py floorplan.pdf
# two passes now: first collect doors per sheet, then kill the sheet
# furniture false positives, then render + annotate + reconcile
import json
import os
import sys
import time

from config import OUT_DIR, RENDER_DPI
from pdf_reader import open_doc, page_text_spans, page_drawings, render_page
from tag_finder import find_tags
from badge_finder import find_badges
from shape_finder import find_swing_arcs, find_wall_gaps
from matcher import match_doors
from noise import drop_sheet_furniture
from reconcile import reconcile
from visualizer import annotate_page


def main(pdf_path):
    started = time.perf_counter()
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = open_doc(pdf_path)

    # pass 1: pure extraction, no rendering yet
    pages_doors = {}
    raw_stats = {}
    for pno in range(len(doc)):
        page = doc[pno]
        drawings = page_drawings(page)
        spans = page_text_spans(page)
        badges = find_badges(drawings)
        tags = find_tags(spans, badges)
        arcs = find_swing_arcs(drawings)
        gaps = find_wall_gaps(drawings)
        pages_doors[pno + 1] = match_doors(tags, arcs, gaps)
        raw_stats[pno + 1] = (len(tags), len(badges), len(arcs), len(gaps))

    # pass 2: throw out curves that repeat on 3+ sheets (title block etc)
    cleaned, dropped = drop_sheet_furniture(pages_doors)

    # pass 3: render, annotate, report
    report = []
    for pno in sorted(cleaned):
        doors = cleaned[pno]
        tags_n, badges_n, arcs_n, gaps_n = raw_stats[pno]
        pix = render_page(doc[pno - 1], RENDER_DPI)
        img_path = annotate_page(pix, doors, pno)
        tagged = sum(1 for d in doors if d["tag"])
        print(f"sheet {pno}: {tags_n} tags ({badges_n} badges), {arcs_n} swings, "
              f"{gaps_n} wall gaps -> {tagged} tagged doors, "
              f"{len(doors) - tagged} untaged openings")
        report.append({
            "page": pno,
            "tags": tags_n,
            "badges": badges_n,
            "swing_arcs": arcs_n,
            "wall_gaps": gaps_n,
            "tagged_doors": tagged,
            "untaged_openings": len(doors) - tagged,
            "image": img_path,
            "doors": doors,
        })

    recon = reconcile(cleaned)
    elapsed = time.perf_counter() - started
    summary = {
        "pdf": os.path.basename(pdf_path),
        "sheets": len(doc),
        "furniture_false_positives_dropped": dropped,
        "unique_tags_on_enlarged_sheets": recon["unique_tags_on_enlarged"],
        "tags_printed_twice_on_one_sheet": recon["tags_printed_twice_on_one_sheet"],
        "tags_on_multiple_enlarged_sheets": recon["tags_on_multiple_enlarged_sheets"],
        "runtime_seconds": round(elapsed, 2),
        "pages": report,
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\ndropped {dropped} sheet-furniture false positives")
    print(f"unique door tags on enlarged sheets: {recon['unique_tags_on_enlarged']}")
    print(f"tags printed twice on one sheet: {len(recon['tags_printed_twice_on_one_sheet'])}")
    print(f"tags seen on multiple enlarged sheets: {len(recon['tags_on_multiple_enlarged_sheets'])}")
    print(f"\ndone in {elapsed:.2f}s -> {OUT_DIR}\\summary.json + annotated pngs")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python run.py floorplan.pdf")
        sys.exit(1)
    main(sys.argv[1])