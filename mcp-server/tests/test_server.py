import asyncio
import json
from server import handle_call_tool, list_tool_names, _serialize


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


def test_stitch_wire_result_includes_scale(band_tiles, tmp_path):
    paths = band_tiles(100, 50)
    spec = [{"path": paths[0], "scroll_top": 0}, {"path": paths[1], "scroll_top": 50}]
    result = asyncio.run(handle_call_tool("stitch_images", {
        "tiles": spec,
        "viewport": {"inner_width": 100, "inner_height": 50, "client_height": 50},
        "output_path": str(tmp_path / "s.png"),
    }))
    wire = _serialize(result)
    payload = json.loads(wire[0].text)
    assert payload["scale"] == 1.0
    assert payload["output_path"].endswith("s.png")
