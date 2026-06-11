from PIL import Image


def measure_scale(image_path, inner_width, inner_height, tolerance=0.02):
    """Derive capture scale S from the image itself (display-independent).

    S = image_pixel_width / window.innerWidth. Validated against the height
    ratio; a mismatch means the browser window straddles two displays.
    """
    with Image.open(image_path) as img:
        sx = img.width / inner_width
        sy = img.height / inner_height
    if abs(sx - sy) > tolerance:
        raise ValueError(
            f"Non-uniform scale (width {sx:.4f} vs height {sy:.4f}): "
            f"window may straddle two displays — re-capture"
        )
    return sx
