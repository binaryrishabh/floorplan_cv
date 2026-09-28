# some cad exports keep text in the pdf text layer that never actually
# renders on the sheet: clipped viewports, switched off layers, white
# ink, whatever. the only reliable judge is the rendered pixels at the
# spot where the span claims to sit, so we sample a small grid there.
#
# IMPORTANT: pix.samples copies the whole page buffer (~55mb at 150dpi)
# every single time you access it. touching it per pixel made the run
# crawl forever, so we copy once into a probe and reuse it for everything
def make_probe(pix):
    return {
        "buf": pix.samples,
        "w": pix.width,
        "h": pix.height,
        "stride": pix.stride,
        "n": pix.n,
    }


def _dark_at(probe, px, py):
    off = py * probe["stride"] + px * probe["n"]
    b = probe["buf"]
    return b[off] < 120 and b[off + 1] < 120 and b[off + 2] < 120


def span_is_visible(probe, bbox, scale, cols=6, rows=3, min_dark=2):
    x0, y0, x1, y1 = [v * scale for v in bbox]
    # clamp inside the image so wierd off-page coords dont explode
    x0 = max(0, min(x0, probe["w"] - 1))
    x1 = max(0, min(x1, probe["w"] - 1))
    y0 = max(0, min(y0, probe["h"] - 1))
    y1 = max(0, min(y1, probe["h"] - 1))
    if x1 - x0 < 2 or y1 - y0 < 2:
        return False
    dark = 0
    for ry in range(rows):
        py = int(y0 + (ry + 0.5) * (y1 - y0) / rows)
        for rx in range(cols):
            px = int(x0 + (rx + 0.5) * (x1 - x0) / cols)
            if _dark_at(probe, px, py):
                dark += 1
    return dark >= min_dark