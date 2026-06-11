from PIL import Image
from imaging.scale import _scale_from_width


def crop_to_rect(image_path, css_rect, inner_width, output_path, trim=None, matte=None):
    """Crop to a CSS rect (scaled by S = width/inner_width), then optional
    trim (crop inward, CSS px) and matte (solid-color border).

    Note: matte is a solid color only. An element's *own-background* frame is a
    capture-time op (JIT CSS padding) — NOT something Pillow can do post-hoc —
    so this function only offers solid-color matte, which is correct. (ADR-006 §5).
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        s = _scale_from_width(img.width, inner_width)
        x, y = round(css_rect["x"] * s), round(css_rect["y"] * s)
        w, h = round(css_rect["w"] * s), round(css_rect["h"] * s)
        out = img.crop((x, y, x + w, y + h))

        if trim:
            t = {k: round(trim.get(k, 0) * s) for k in ("top", "right", "bottom", "left")}
            out = out.crop((t["left"], t["top"], out.width - t["right"], out.height - t["bottom"]))

        if matte:
            m, color = matte.get("width", 0), matte.get("color", "white")
            framed = Image.new("RGB", (out.width + 2 * m, out.height + 2 * m), color)
            framed.paste(out, (m, m))
            out = framed

        out.save(output_path)
    return output_path
