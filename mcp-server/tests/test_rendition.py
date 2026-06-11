from PIL import Image
from imaging.rendition import make_rendition


def test_downscales_long_edge(solid, tmp_path):
    src = solid("src.png", 2000, 1000, "blue")
    out = make_rendition(src, max_edge=1000, output_path=str(tmp_path / "out.jpg"))
    with Image.open(out) as im:
        assert (im.width, im.height) == (1000, 500)
        assert im.format == "JPEG"


def test_does_not_upscale(solid, tmp_path):
    src = solid("src.png", 800, 600, "blue")
    out = make_rendition(src, max_edge=1000, output_path=str(tmp_path / "out.jpg"))
    with Image.open(out) as im:
        assert (im.width, im.height) == (800, 600)


def test_portrait_uses_height_as_long_edge(solid, tmp_path):
    src = solid("src.png", 500, 2000, "blue")
    out = make_rendition(src, max_edge=1000, output_path=str(tmp_path / "out.jpg"))
    with Image.open(out) as im:
        assert (im.width, im.height) == (250, 1000)
