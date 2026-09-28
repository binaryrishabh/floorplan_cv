# draws the findings back onto the rendered sheet so the output is
# something a human can judge in two seconds flat

import os
from PIL import Image, ImageDraw
from config import RENDER_DPI, OUT_DIR

SCALE = RENDER_DPI / 72.0  # pdf points -> pixels


def annotate_page(pix, doors, page_no):
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(img)
    for d in doors:
        px, py = d["x"] * SCALE, d["y"] * SCALE
        if d["tag"]:
            r = 10
            draw.ellipse([px - r, py - r, px + r, py + r], outline=(220, 30, 30), width=3)
            draw.text((px + 12, py - 8), d["tag"], fill=(220, 30, 30))
        else:
            # untaged swing, magenta so it pops againt the red tags
            r = 8
            draw.ellipse([px - r, py - r, px + r, py + r], outline=(200, 40, 200), width=3)
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"page_{page_no:02d}_doors.png")
    img.save(path)
    return path