from PIL import Image
from imaging.stitch import stitch_with_overlap


def test_no_overlap_concatenates_full_tiles(band_tiles, tmp_path):
    paths = band_tiles(100, 50)  # 100x50 tiles; viewport 100x50 -> scale 1.0
    spec = [
        {"path": paths[0], "scroll_top": 0},
        {"path": paths[1], "scroll_top": 50},
        {"path": paths[2], "scroll_top": 100},
    ]
    result = stitch_with_overlap(
        spec, viewport={"inner_width": 100, "inner_height": 50, "client_height": 50},
        output_path=str(tmp_path / "s.png"),
    )
    assert result["scale"] == 1.0
    with Image.open(result["output_path"]) as im:
        assert (im.width, im.height) == (100, 150)
        assert im.getpixel((50, 25)) == (255, 0, 0)     # red band
        assert im.getpixel((50, 75)) == (0, 128, 0)     # green band
        assert im.getpixel((50, 125)) == (0, 0, 255)    # blue band


def test_partial_scroll_overlap_is_trimmed(band_tiles, tmp_path):
    paths = band_tiles(100, 50)
    # scroll advanced only 40px then 30px while client_height is 50 -> overlaps 10px, 20px
    spec = [
        {"path": paths[0], "scroll_top": 0},
        {"path": paths[1], "scroll_top": 40},
        {"path": paths[2], "scroll_top": 70},
    ]
    result = stitch_with_overlap(
        spec, viewport={"inner_width": 100, "inner_height": 50, "client_height": 50},
        output_path=str(tmp_path / "s.png"),
    )
    with Image.open(result["output_path"]) as im:
        # 50 + (50-10) + (50-20) = 120
        assert (im.width, im.height) == (100, 120)


def test_scale_multiplies_overlap(band_tiles, tmp_path):
    paths = band_tiles(100, 100)  # 100x100 tiles; viewport 50x50 -> scale 2.0
    spec = [
        {"path": paths[0], "scroll_top": 0},
        {"path": paths[1], "scroll_top": 40},  # overlap_css=(0+50)-40=10 -> 20px at scale 2
    ]
    result = stitch_with_overlap(
        spec, viewport={"inner_width": 50, "inner_height": 50, "client_height": 50},
        output_path=str(tmp_path / "s.png"),
    )
    assert result["scale"] == 2.0
    with Image.open(result["output_path"]) as im:
        assert (im.width, im.height) == (100, 180)  # 100 + (100-20)
