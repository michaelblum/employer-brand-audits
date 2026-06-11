import pytest
from PIL import Image


def _solid(path, width, height, color):
    Image.new("RGB", (width, height), color).save(path)
    return str(path)


@pytest.fixture
def solid(tmp_path):
    """make a solid-color PNG: solid('a.png', 100, 60, 'red') -> path"""
    def _make(name, width, height, color):
        return _solid(tmp_path / name, width, height, color)
    return _make


@pytest.fixture
def band_tiles(tmp_path):
    """Three equal-size solid tiles (red, green, blue) of the given size."""
    def _make(width, height):
        return [
            _solid(tmp_path / "t0.png", width, height, "red"),
            _solid(tmp_path / "t1.png", width, height, "green"),
            _solid(tmp_path / "t2.png", width, height, "blue"),
        ]
    return _make
