from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw
from config import MARKER_RADIUS_PX
from output_utils import safe_write_bytes


def annotate_page(pix, space, doors, page_no, out_dir, review_candidates=None):
    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    draw = ImageDraw.Draw(img)
    for d in doors:
        px, py = space.raw_to_pixel(d['x'], d['y'])
        r = MARKER_RADIUS_PX
        draw.ellipse((px-r, py-r, px+r, py+r), outline=(220,30,30), width=3)
        # Only true fitted swing arcs have a meaningful hinge. For leaf-only
        # recovery symbols a misleading hinge vector is worse than no vector.
        if d.get('method') == 'swing_arc':
            hx, hy = space.raw_to_pixel(d['hinge_x'], d['hinge_y'])
            draw.line((hx, hy, px, py), fill=(220,30,30), width=2)
        if d.get('tag'):
            draw.text((px+r+3, py-r), d['tag'], fill=(220,30,30))
    for d in (review_candidates or []):
        px, py = space.raw_to_pixel(d['x'], d['y'])
        r = MARKER_RADIUS_PX
        draw.ellipse((px-r, py-r, px+r, py+r), outline=(235,140,20), width=2)
        draw.text((px+r+3, py-r), 'review', fill=(235,140,20))

    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    preferred = out / f'page_{page_no:02d}_doors.png'

    # Encode first, then use our Windows-safe writer. This avoids Pillow
    # directly opening a stale/locked destination path.
    buf = BytesIO()
    img.save(buf, format='PNG')
    actual = safe_write_bytes(preferred, buf.getvalue())
    return str(actual)
