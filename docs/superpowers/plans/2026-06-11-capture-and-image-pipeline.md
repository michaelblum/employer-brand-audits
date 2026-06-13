# Capture & Image Pipeline Implementation Plan

> Historical note: this plan predates [ADR-008](../../decisions/ADR-008-playwright-cli-browser-engine.md). Its pure Python image operations remain useful, but its Claude-in-Chrome `computer`/`zoom` capture primitive is superseded. New browser automation must use Playwright CLI or thin repo wrappers around it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and unit-test the pure-Python image operations the audit's capture path depends on (scale measurement, overlap-stitch, crop, rendition), expose them as MCP tools, and de-risk the browser-side capture primitive with a spike — before any pipeline glue is written.

**Architecture:** A `mcp-server/` Python package with a focused `imaging/` module of pure functions (path-in → path-out, no audit/manifest coupling), unit-tested with synthetic Pillow fixtures, then wrapped as stdio MCP tools. The capture primitive (Claude in Chrome `computer` screenshot/`zoom`) is validated by a one-off spike whose findings gate the disk-handoff design.

**Tech Stack:** Python 3 (ships with macOS), Pillow (image ops), `mcp` (official MCP Python SDK, stdio server), pytest.

---

## Plan sequence (this is Plan 1 of ~6)

This spec was decomposed into self-contained plans. Each produces working, testable software:

1. **Capture & image pipeline** ← *this plan* — pure image ops + MCP scaffold + capture spike.
2. **Manifest & audit lifecycle** — `create_audit`, `save_artifact` (+ `kilos-l2`/`l3-synthesis` schema validation), `get_audit_status`, `set_step_status`; the `card` field; wires the Plan-1 image tools to write into the audit dir. (ADR-002, ADR-007)
3. **KILOS analysis & synthesis (skill-side)** — the brand-audit SKILL.md L2/L3 logic: eager card + `kilos_map` + salience, weighted L3 roll-up, confluence re-inference. (ADR-007)
4. **Report generation & publishing** — `generate_report` (Jinja2), `publish_image` (git push to public assets repo), GitHub raw embedding + base64 fallback. (ADR-006)
5. **Plugin packaging & orchestration** — `plugin.json`, `.mcp.json`, SKILL.md intake wizard + L0→L4 orchestration, first-run venv setup.
6. **End-to-end POC** — run the full pipeline on one company, fix integration gaps.

Decisions of record: ADR-001…ADR-007 in `docs/decisions/`.

---

## File Structure (Plan 1)

```
mcp-server/
├── requirements.txt            # Pillow, mcp, pytest
├── imaging/
│   ├── __init__.py             # re-exports the four functions
│   ├── scale.py                # measure_scale()  — "page as ruler" (ADR-005)
│   ├── stitch.py               # stitch_with_overlap()  — clipUtils port (ADR-005)
│   ├── crop.py                 # crop_to_rect()  — clipUtils port; trim + matte (ADR-005/006)
│   └── rendition.py            # make_rendition()  — analysis/archival downscale (ADR-006)
├── server.py                   # stdio MCP server; exposes stitch_images / crop_image / make_rendition
└── tests/
    ├── __init__.py
    ├── conftest.py             # synthetic-image fixtures
    ├── test_scale.py
    ├── test_stitch.py
    ├── test_crop.py
    ├── test_rendition.py
    └── test_server.py          # tool-wiring smoke test
docs/superpowers/spikes/
└── 2026-06-11-capture-primitive-spike.md   # Task 0 findings
```

Each `imaging/*.py` file owns one operation. `scale.py` is imported by `stitch.py` and `crop.py` (single source of the scale-derivation rule). The MCP wrappers in `server.py` take **explicit paths** — no audit/manifest coupling yet (that arrives in Plan 2).

---

## Task 0: Capture-primitive spike (Issue #4)

This is investigation, not TDD. The design-phase spike already confirmed: `computer` screenshot is page-only with origin (0,0); scale is display-dependent (~0.982× on scaled retina) so it must be *measured*; `zoom` region is CSS-px and element-exact; `read_page` is an a11y tree. **This task resolves only the still-open unknowns** that gate the disk handoff, then records a decision.

**Files:**
- Create: `docs/superpowers/spikes/2026-06-11-capture-primitive-spike.md`

- [ ] **Step 1: Confirm Claude in Chrome is connected**

Run (via the Claude in Chrome MCP): `tabs_context_mcp({createIfEmpty: true})`.
Expected: a tab group + tabId returned. If not connected, stop and surface to the user.

- [ ] **Step 2: Capture a known page to disk and locate the file**

Navigate the tab to `https://example.com`. Call `computer({action: "screenshot", tabId, save_to_disk: true})`.
Record verbatim: the returned text, including whether it contains a **filesystem path** or only an `ID`.
Then search likely locations for the saved file (run in a normal shell, not sandboxed if possible):
```bash
find "$HOME/Library/Application Support/Claude" "$HOME/Library/Caches/Claude" "$TMPDIR" /tmp -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' \) -mmin -3 2>/dev/null
```
Expected: either a path is surfaced/found (→ disk handoff viable) or nothing is locatable (→ fallback needed).

- [ ] **Step 3: Verify a separate process can read it**

If a path was found, confirm a non-Claude process can open it:
```bash
python3 -c "from PIL import Image; im=Image.open('<PATH>'); print(im.format, im.size)"
```
Expected: prints format + dimensions. Record the on-disk dimensions vs. the dimensions the screenshot tool reported (they may differ — preview vs. saved).

- [ ] **Step 4: Probe `zoom` max region and rate limits**

Call `computer({action: "zoom", tabId, region: [0,0,1512,827], save_to_disk: true})` (full-viewport-sized region).
Expected: either a full-viewport high-res crop (→ zoom usable for whole tiles) or an error/cap (→ zoom is small-region only). Then fire 8 rapid `screenshot` calls in a row; record any rate-limit error or throttling.

- [ ] **Step 5: Record findings and the handoff decision**

Write `docs/superpowers/spikes/2026-06-11-capture-primitive-spike.md` capturing, for each step, the observed result and one of these decisions:
- **Disk handoff confirmed** — `stitch_images` reads tiles from the saved paths (the Plan assumes this).
- **Fallback: configurable save dir** — if the path isn't surfaced but files land in a discoverable dir, the MCP server is configured to read from it.
- **Fallback: inline tiles** — if neither, tiles come back inline through the agent (note the token cost; cap tile count).
Close `docs/decisions` Issue #4 items that are now answered (leave the rest open with the findings noted).

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/spikes/2026-06-11-capture-primitive-spike.md
git commit -m "spike: resolve capture-primitive open questions (Issue #4)"
```

> **Gate:** the rest of this plan (pure image ops) does not depend on the spike's outcome — the functions take explicit paths regardless. The spike only decides *how paths are produced* in Plan 5's orchestration. Proceed to Task 1 in parallel if desired.

---

## Task 1: Project scaffold

**Files:**
- Create: `mcp-server/requirements.txt`
- Create: `mcp-server/imaging/__init__.py` (empty for now)
- Create: `mcp-server/tests/__init__.py` (empty)
- Create: `mcp-server/tests/conftest.py`

- [ ] **Step 1: Write requirements.txt**

```
Pillow>=10.0
mcp>=1.0
pytest>=8.0
```

- [ ] **Step 2: Create the venv and install**

Run:
```bash
cd mcp-server && python3 -m venv .venv && ./.venv/bin/pip install -q -r requirements.txt && ./.venv/bin/python -c "import PIL, mcp, pytest; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 3: Write the fixture helpers**

`mcp-server/tests/conftest.py`:
```python
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
```

- [ ] **Step 4: Verify pytest collects (no tests yet)**

Run:
```bash
cd mcp-server && ./.venv/bin/pytest -q
```
Expected: `no tests ran` (exit code 5) — confirms pytest + conftest import cleanly.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/requirements.txt mcp-server/imaging/__init__.py mcp-server/tests/
git commit -m "chore: scaffold mcp-server image package + test fixtures"
```

---

## Task 2: `measure_scale` — the "page as ruler" rule (ADR-005)

**Files:**
- Create: `mcp-server/imaging/scale.py`
- Test: `mcp-server/tests/test_scale.py`

- [ ] **Step 1: Write the failing tests**

`mcp-server/tests/test_scale.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_scale.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'imaging.scale'`.

- [ ] **Step 3: Implement `measure_scale`**

`mcp-server/imaging/scale.py`:
```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_scale.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/imaging/scale.py mcp-server/tests/test_scale.py
git commit -m "feat: measure_scale (page-as-ruler scale derivation)"
```

---

## Task 3: `make_rendition` — analysis/archival downscale (ADR-006)

**Files:**
- Create: `mcp-server/imaging/rendition.py`
- Test: `mcp-server/tests/test_rendition.py`

- [ ] **Step 1: Write the failing tests**

`mcp-server/tests/test_rendition.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_rendition.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'imaging.rendition'`.

- [ ] **Step 3: Implement `make_rendition`**

`mcp-server/imaging/rendition.py`:
```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_rendition.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp-server/imaging/rendition.py mcp-server/tests/test_rendition.py
git commit -m "feat: make_rendition (long-edge downscale to JPEG)"
```

---

## Task 4: `crop_to_rect` — element crop with trim + matte (ADR-005/006)

**Files:**
- Create: `mcp-server/imaging/crop.py`
- Test: `mcp-server/tests/test_crop.py`

- [ ] **Step 1: Write the failing tests**

`mcp-server/tests/test_crop.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_crop.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'imaging.crop'`.

- [ ] **Step 3: Implement `crop_to_rect`**

`mcp-server/imaging/crop.py`:
```python
from PIL import Image
from imaging.scale import _scale_from_width


def crop_to_rect(image_path, css_rect, inner_width, output_path, trim=None, matte=None):
    """Crop to a CSS rect (scaled by S = width/inner_width), then optional
    trim (crop inward, CSS px) and matte (solid-color border).

    Note: matte is a solid color only. An element's *own-background* frame is a
    capture-time op (JIT padding), not available here (ADR-006 §5).
    """
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        s = _scale_from_width(img.width, inner_width)
        x, y = round(css_rect["x"] * s), round(css_rect["y"] * s)
        w, h = round(css_rect["w"] * s), round(css_rect["h"] * s)
        out = img.crop((x, y, x + w, y + h))

        if trim:
            t = {k: round(trim.get(k, 0) * s) for k in ("top", "right", "bottom", "left")}
            out = out.crop((t["left"], t["top"], out.width - t["right"], out.height - t["bottom"]))

        if matte:
            m, color = matte.get("width", 0), matte.get("color", "white")
            framed = Image.new("RGB", (out.width + 2 * m, out.height + 2 * m), color)
            framed.paste(out, (m, m))
            out = framed

        out.save(output_path)
    return output_path
```

- [ ] **Step 4: Add the shared scale helper**

Append to `mcp-server/imaging/scale.py`:
```python


def _scale_from_width(pixel_width, inner_width):
    """Scale factor from a known image width — used by crop/stitch where the
    caller has already validated uniformity (or doesn't have height handy)."""
    return pixel_width / inner_width
```

- [ ] **Step 5: Run to verify pass**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_crop.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add mcp-server/imaging/crop.py mcp-server/imaging/scale.py mcp-server/tests/test_crop.py
git commit -m "feat: crop_to_rect with scale + trim + matte"
```

---

## Task 5: `stitch_with_overlap` — overlap-corrected vertical stitch (ADR-005)

**Files:**
- Create: `mcp-server/imaging/stitch.py`
- Test: `mcp-server/tests/test_stitch.py`

- [ ] **Step 1: Write the failing tests**

`mcp-server/tests/test_stitch.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_stitch.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'imaging.stitch'`.

- [ ] **Step 3: Implement `stitch_with_overlap`**

`mcp-server/imaging/stitch.py`:
```python
from PIL import Image
from imaging.scale import measure_scale


def stitch_with_overlap(tiles, viewport, output_path):
    """Vertically stitch viewport tiles, trimming the duplicated overlap.

    Scale is derived from the first tile (page-as-ruler, ADR-005):
    measure_scale(first_tile, inner_width, inner_height). Then
    overlap_css = (prev.scroll_top + client_height) - cur.scroll_top
    (a partial final scroll leaves the previous viewport's bottom visible in
    the current tile; chop overlap_css * scale px off the current tile's top).
    Port of clipUtils.stitchImagesWithOverlap. Returns {"output_path", "scale"}.

    viewport = {"inner_width", "inner_height", "client_height"} (CSS px).
    """
    ordered = sorted(tiles, key=lambda t: t["scroll_top"])
    scale = measure_scale(ordered[0]["path"], viewport["inner_width"], viewport["inner_height"])
    client_h = viewport["client_height"]

    pieces, prev_scroll, width = [], None, None
    for idx, t in enumerate(ordered):
        img = Image.open(t["path"]).convert("RGB")
        if width is None:
            width = img.width
        if idx == 0:
            pieces.append(img)
        else:
            overlap_css = (prev_scroll + client_h) - t["scroll_top"]
            overlap_px = min(max(0, round(overlap_css * scale)), img.height)
            pieces.append(img.crop((0, overlap_px, img.width, img.height)))
        prev_scroll = t["scroll_top"]

    total_h = sum(p.height for p in pieces)
    canvas = Image.new("RGB", (width, total_h))
    y = 0
    for p in pieces:
        canvas.paste(p, (0, y))
        y += p.height
    canvas.save(output_path)
    return {"output_path": output_path, "scale": scale}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_stitch.py -q`
Expected: 3 passed.

- [ ] **Step 5: Run the whole suite**

Run: `cd mcp-server && ./.venv/bin/pytest -q`
Expected: 12 passed.

- [ ] **Step 6: Commit**

```bash
git add mcp-server/imaging/stitch.py mcp-server/tests/test_stitch.py
git commit -m "feat: stitch_with_overlap (overlap-corrected vertical stitch)"
```

---

## Task 6: MCP server scaffold + tool exposure

**Files:**
- Modify: `mcp-server/imaging/__init__.py`
- Create: `mcp-server/server.py`
- Test: `mcp-server/tests/test_server.py`

- [ ] **Step 1: Re-export the functions**

`mcp-server/imaging/__init__.py`:
```python
from imaging.scale import measure_scale
from imaging.stitch import stitch_with_overlap
from imaging.crop import crop_to_rect
from imaging.rendition import make_rendition

__all__ = ["measure_scale", "stitch_with_overlap", "crop_to_rect", "make_rendition"]
```

- [ ] **Step 2: Write the failing wiring test**

`mcp-server/tests/test_server.py`:
```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_server.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'server'`.

- [ ] **Step 4: Implement the server**

`mcp-server/server.py`:
```python
"""Employer-brand-audit MCP server — mechanical image utilities (Plan 1).

Exposes stitch_images / crop_image / make_rendition over stdio. Tools take
explicit file paths; audit/manifest coupling arrives in Plan 2.
"""
import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from imaging import stitch_with_overlap, crop_to_rect, make_rendition

app = Server("employer-brand-audit")

_TOOLS = {
    "stitch_images": {
        "description": "Stitch viewport tiles into a full-page image; derives scale from the first tile.",
        "inputSchema": {
            "type": "object",
            "required": ["tiles", "viewport", "output_path"],
            "properties": {
                "tiles": {"type": "array", "items": {
                    "type": "object", "required": ["path", "scroll_top"],
                    "properties": {"path": {"type": "string"},
                                   "scroll_top": {"type": "number"}}}},
                "viewport": {
                    "type": "object",
                    "required": ["inner_width", "inner_height", "client_height"],
                    "properties": {"inner_width": {"type": "number"},
                                   "inner_height": {"type": "number"},
                                   "client_height": {"type": "number"}},
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "crop_image": {
        "description": "Crop an image to a CSS rect (scaled), with optional trim and solid matte.",
        "inputSchema": {
            "type": "object",
            "required": ["source_path", "css_rect", "inner_width", "output_path"],
            "properties": {
                "source_path": {"type": "string"},
                "css_rect": {"type": "object"},
                "inner_width": {"type": "number"},
                "output_path": {"type": "string"},
                "trim": {"type": "object"},
                "matte": {"type": "object"},
            },
        },
    },
    "make_rendition": {
        "description": "Downscale an image to a max long edge as JPEG (analysis/archival rendition).",
        "inputSchema": {
            "type": "object",
            "required": ["source_path", "max_edge", "output_path"],
            "properties": {
                "source_path": {"type": "string"},
                "max_edge": {"type": "number"},
                "output_path": {"type": "string"},
                "quality": {"type": "number"},
            },
        },
    },
}


def list_tool_names():
    return list(_TOOLS.keys())


async def handle_call_tool(name, arguments):
    if name == "stitch_images":
        # returns {"output_path", "scale"}
        return stitch_with_overlap(
            arguments["tiles"], arguments["viewport"], arguments["output_path"],
        )
    if name == "crop_image":
        path = crop_to_rect(
            arguments["source_path"], arguments["css_rect"], arguments["inner_width"],
            arguments["output_path"], arguments.get("trim"), arguments.get("matte"),
        )
        return {"output_path": path}
    if name == "make_rendition":
        path = make_rendition(
            arguments["source_path"], arguments["max_edge"],
            arguments["output_path"], arguments.get("quality", 80),
        )
        return {"output_path": path}
    raise ValueError(f"unknown tool: {name}")


@app.list_tools()
async def _list_tools():
    return [Tool(name=n, description=t["description"], inputSchema=t["inputSchema"])
            for n, t in _TOOLS.items()]


@app.call_tool()
async def _call_tool(name, arguments):
    result = await handle_call_tool(name, arguments)
    return [TextContent(type="text", text=result["output_path"])]


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 5: Run the wiring test**

Run: `cd mcp-server && ./.venv/bin/pytest tests/test_server.py -q`
Expected: 2 passed.

- [ ] **Step 6: Smoke-test the server starts over stdio**

Run:
```bash
cd mcp-server && printf '' | timeout 2 ./.venv/bin/python server.py; echo "exit=$?"
```
Expected: starts, waits on stdin, exits on timeout (`exit=124`) with no import/traceback errors.

- [ ] **Step 7: Full suite + commit**

```bash
cd mcp-server && ./.venv/bin/pytest -q
```
Expected: 14 passed.
```bash
git add mcp-server/imaging/__init__.py mcp-server/server.py mcp-server/tests/test_server.py
git commit -m "feat: stdio MCP server exposing image tools"
```

---

## Definition of Done (Plan 1)

- `cd mcp-server && ./.venv/bin/pytest -q` → 14 passed.
- The four image functions are unit-tested against synthetic fixtures.
- The stdio MCP server exposes `stitch_images`, `crop_image`, `make_rendition`.
- The capture-primitive spike findings + handoff decision are recorded in `docs/superpowers/spikes/2026-06-11-capture-primitive-spike.md`, and resolved Issue #4 items are checked off.
- **Next:** Plan 2 (manifest & audit lifecycle) wires these tools to write into the audit directory under `audit_id`, adds `save_artifact`/schema validation, and the `card` field.
