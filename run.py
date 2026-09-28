# entry point: python run.py floorplan.pdf
# prints a per sheet summary and drops annotated pngs + json in out/

import json
import os
import sys
import time

from config import OUT_DIR, RENDER_DPI
from pdf_reader import open_doc, page_text_spans, page_drawings, render_page
from tag_finder import find_tags
from shape_finder import find_swing_arcs, find_wall_gaps
from matcher import match_doors
from reconcile import reconcile
from visualizer import annotate_page


def main(pdf_path):
    started = time.perf_counter()
    doc = open_doc(pdf_path)
    pages_doors = {}
    report = []

    for pno in range(len(doc)):
        page = doc[pno]
        drawings = page_drawings(page)
        tags = find_tags(page_text_spans(page))
        arcs = find_swing_arcs(drawings)
        gaps = find_wall_gaps(drawings)
        doors = match_doors(tags, arcs, gaps)
        pages_doors[pno + 1] = doors

        pix = render_page(page, RENDER_DPI)
        img_path = annotate_page(pix, doors, pno + 1)
        tagged = sum(1 for d in doors if d["tag"])
        print(f"sheet {pno+1}: {len(tags)} tags, {len(arcs)} swings, "
              f"{len(gaps)} wall gaps -> {tagged} tagged doors, "
              f"{len(doors)-tagged} untaged openings")
        report.append({
            "page": pno + 1,
            "tags": len(tags),
            "swing_arcs": len(arcs),
            "wall_gaps": len(gaps),
            "tagged_doors": tagged,
            "untaged_openings": len(doors) - tagged,
            "image": img_path,
            "doors": doors,
        })

    recon = reconcile(pages_doors)
    elapsed = time.perf_counter() - started
    summary = {
        "pdf": os.path.basename(pdf_path),
        "sheets": len(doc),
        "total_unique_tagged_doors": recon["unique_tags"],
        "tags_on_multiple_sheets": recon["tags_on_multiple_sheets"],
        "runtime_seconds": round(elapsed, 2),
        "pages": report,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\ndone in {elapsed:.2f}s -> {OUT_DIR}\\summary.json + annotated pngs")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python run.py floorplan.pdf")
        sys.exit(1)
    main(sys.argv[1])