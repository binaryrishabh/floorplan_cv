# thin wrapper around pymupdf so the rest of the code never touches
# fitz directly. if we ever swap pdf libs only this file changes
import pymupdf


def open_doc(pdf_path):
    return pymupdf.open(pdf_path)


def page_text_spans(page):
    # every text run with its bbox. vector pdfs from cad give us
    # perfect text here so we dont need to recieve anything from ocr.
    # bbox is kept because the visibility check needs to know where
    # on the rendered image the span claims to sit
    spans = []
    raw = page.get_text("dict")
    for block in raw.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                txt = span.get("text", "").strip()
                if not txt:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                spans.append({
                    "text": txt,
                    "x": (x0 + x1) / 2.0,
                    "y": (y0 + y1) / 2.0,
                    "bbox": (x0, y0, x1, y1),
                    "size": span.get("size", 0),
                })
    return spans


def page_drawings(page):
    # vector path items, cad exports put lines and curves in here
    return page.get_drawings()


def render_page(page, dpi):
    return page.get_pixmap(dpi=dpi)