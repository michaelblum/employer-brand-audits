from PIL import Image


def make_rendition(image_path, max_edge, output_path, quality=80):
    """Downscale so the long edge == max_edge (never upscale); save JPEG.

    Vision token cost scales with pixel area, so this — not JPEG quality —
    is the cost lever for the analysis rendition (ADR-006).
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        long_edge = max(img.width, img.height)
        if long_edge > max_edge:
            ratio = max_edge / long_edge
            img = img.resize(
                (round(img.width * ratio), round(img.height * ratio)),
                Image.LANCZOS,
            )
        img.save(output_path, "JPEG", quality=quality)
    return output_path
