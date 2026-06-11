import asyncio
from server import handle_call_tool, list_tool_names


def test_tools_are_registered():
    assert set(list_tool_names()) == {"stitch_images", "crop_image", "make_rendition"}


def test_make_rendition_tool_roundtrip(solid, tmp_path):
    src = solid("src.png", 2000, 1000, "blue")
    out = str(tmp_path / "out.jpg")
    result = asyncio.run(handle_call_tool(
        "make_rendition", {"source_path": src, "max_edge": 1000, "output_path": out}
    ))
    assert result["output_path"] == out
    from PIL import Image
    with Image.open(out) as im:
        assert max(im.width, im.height) == 1000
