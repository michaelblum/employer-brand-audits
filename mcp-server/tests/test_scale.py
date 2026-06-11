import pytest
from imaging.scale import measure_scale


def test_uniform_scale_returns_ratio(solid):
    p = solid("img.png", 1000, 500, "white")
    assert measure_scale(p, inner_width=2000, inner_height=1000) == pytest.approx(0.5)


def test_retina_scaled_capture(solid):
    # 1512x827 CSS viewport captured at 1485x812 (observed on a scaled retina display)
    p = solid("img.png", 1485, 812, "white")
    assert measure_scale(p, inner_width=1512, inner_height=827) == pytest.approx(0.982, abs=0.001)


def test_non_uniform_scale_raises(solid):
    # width ratio 0.5, height ratio 1.25 -> window straddling two displays
    p = solid("img.png", 1000, 500, "white")
    with pytest.raises(ValueError, match="straddle"):
        measure_scale(p, inner_width=2000, inner_height=400)
