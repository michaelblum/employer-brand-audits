from PIL import Image

from imaging.normalization import normalize_image_artifact, policy_for_subtype


def test_default_caps_rendered_height_at_4000(solid, tmp_path):
    src = solid("tall.png", 1000, 5000, "blue")
    result = normalize_image_artifact(src, artifact_subtype="full_page")

    with Image.open(result["output_path"]) as im:
        assert (im.width, im.height) == (800, 4000)
        assert im.format == "PNG"
    assert result["resized"] is True
    assert result["source_dimensions"] == {"width": 1000, "height": 5000}
    assert result["output_dimensions"] == {"width": 800, "height": 4000}


def test_does_not_upscale_short_image(solid):
    src = solid("short.png", 1000, 1200, "blue")
    result = normalize_image_artifact(src, artifact_subtype="viewport")

    with Image.open(result["output_path"]) as im:
        assert (im.width, im.height) == (1000, 1200)
    assert result["resized"] is False


def test_subtype_override_refines_height_and_codec(solid, tmp_path):
    src = solid("element.png", 1200, 3000, "blue")
    result = normalize_image_artifact(
        src,
        artifact_subtype="element",
        policy={
            "max_rendered_height": 4000,
            "codec": "source",
            "subtypes": {
                "element": {
                    "max_rendered_height": 1500,
                    "codec": "jpeg",
                    "quality": 70,
                }
            },
        },
    )

    assert result["output_path"].endswith(".jpg")
    assert result["codec"] == "jpeg"
    with Image.open(result["output_path"]) as im:
        assert (im.width, im.height) == (600, 1500)
        assert im.format == "JPEG"


def test_policy_for_subtype_does_not_leak_subtypes_to_effective_policy():
    policy = policy_for_subtype(
        "full_page",
        {"quality": 90, "subtypes": {"full_page": {"compression_level": 9}}},
    )
    assert policy["quality"] == 90
    assert policy["compression_level"] == 9
    assert "subtypes" not in policy
