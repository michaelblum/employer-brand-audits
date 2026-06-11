from PIL import Image
from imaging.scale import measure_scale


def stitch_with_overlap(tiles, viewport, output_path):
    """Vertically stitch viewport tiles, trimming the duplicated overlap.

    Scale is derived from the first tile (page-as-ruler, ADR-005):
    measure_scale(first_tile, inner_width, inner_height). Then
    overlap_css = (prev.scroll_top + client_height) - cur.scroll_top
    (a partial final scroll leaves the previous viewport's bottom visible in
    the current tile; chop overlap_css * scale px off the current tile's top).
    Port of clipUtils.stitchImagesWithOverlap. Returns {"output_path", "scale"}.

    viewport = {"inner_width", "inner_height", "client_height"} (CSS px).
    """
    if not tiles:
        raise ValueError("stitch_with_overlap: tiles is empty")
    ordered = sorted(tiles, key=lambda t: t["scroll_top"])
    scale = measure_scale(ordered[0]["path"], viewport["inner_width"], viewport["inner_height"])
    client_h = viewport["client_height"]

    pieces, prev_scroll, width = [], None, None
    for idx, t in enumerate(ordered):
        with Image.open(t["path"]) as raw:
            img = raw.convert("RGB")
        if width is None:
            width = img.width
        if idx == 0:
            pieces.append(img)
        else:
            overlap_css = (prev_scroll + client_h) - t["scroll_top"]
            overlap_px = min(max(0, round(overlap_css * scale)), img.height)
            pieces.append(img.crop((0, overlap_px, img.width, img.height)))
        prev_scroll = t["scroll_top"]

    total_h = sum(p.height for p in pieces)
    canvas = Image.new("RGB", (width, total_h))
    y = 0
    for p in pieces:
        canvas.paste(p, (0, y))
        y += p.height
    canvas.save(output_path)
    return {"output_path": output_path, "scale": scale}
