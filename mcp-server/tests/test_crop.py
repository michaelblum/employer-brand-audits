from PIL import Image
from imaging.crop import crop_to_rect


def test_crop_applies_scale(solid, tmp_path):
    # 1000px-wide image, innerWidth 500 -> scale 2x
    src = solid("src.png", 1000, 800, "white")
    out = crop_to_rect(
        src, css_rect={"x": 10, "y": 10, "w": 100, "h": 50},
        inner_width=500, output_path=str(tmp_path / "c.png"),
    )
    with Image.open(out) as im:
        assert (im.width, im.height) == (200, 100)  # 100*2 x 50*2


def test_trim_shrinks_inward(solid, tmp_path):
    src = solid("src.png", 1000, 800, "white")
    out = crop_to_rect(
        src, css_rect={"x": 0, "y": 0, "w": 100, "h": 100},
        inner_width=1000, output_path=str(tmp_path / "c.png"),
        trim={"top": 5, "bottom": 5, "left": 10, "right": 10},
    )
    with Image.open(out) as im:
        # scale 1x: 100x100 -> minus 20 wide, minus 10 tall
        assert (im.width, im.height) == (80, 90)


def test_matte_adds_solid_border(solid, tmp_path):
    src = solid("src.png", 100, 100, "white")
    out = crop_to_rect(
        src, css_rect={"x": 0, "y": 0, "w": 100, "h": 100},
        inner_width=100, output_path=str(tmp_path / "c.png"),
        matte={"width": 10, "color": "black"},
    )
    with Image.open(out) as im:
        assert (im.width, im.height) == (120, 120)
        assert im.getpixel((0, 0)) == (0, 0, 0)        # matte corner is black
        assert im.getpixel((60, 60)) == (255, 255, 255)  # center is original white


def test_crop_normalizes_with_subtype_policy(solid, tmp_path):
    src = solid("src.png", 1000, 3000, "white")
    out = crop_to_rect(
        src,
        css_rect={"x": 0, "y": 0, "w": 1000, "h": 3000},
        inner_width=1000,
        output_path=str(tmp_path / "c.png"),
        normalization_policy={"subtypes": {"crop": {"max_rendered_height": 1500}}},
    )
    with Image.open(out) as im:
        assert (im.width, im.height) == (500, 1500)
