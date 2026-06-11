# ADR-005: Screenshot Capture Strategy

**Date:** 2026-06-10  
**Status:** Accepted  

---

## Context

The audit needs four kinds of image capture: (1) a crop to a single DOM element, (2) a full-page scan, (3) an element taller than the viewport, (4) the content of a nested `overflow:auto/scroll` container that exceeds its own box. We also need to add a padding "border" around a clip or trim pixels off its edges.

The DRAW scrapyard solved all of these in production, but as a **Chrome extension** using `chrome.tabs.captureVisibleTab` — a privileged page-capture API that returns viewport-exact pixels scaled cleanly by `window.devicePixelRatio`. Our stack is different: we drive the user's real Chrome through **Claude in Chrome**, which exposes no `chrome.tabs.*` APIs and (per [ADR-003](ADR-003-browser-layer.md)) is not CDP. So we inherit DRAW's *geometry* but not its *capture primitive*. This ADR records both the strategy and what an empirical spike established about our primitive.

## Decision

### 1. Crop-and-stitch over direct element capture (Strategy B, not A)

Capture pixels from a viewport/region screenshot, then crop/stitch by computed geometry. Do **not** attempt to capture an element's pixels directly via injected JS (`html2canvas`, `element.toDataURL`, SVG `foreignObject`, canvas `drawImage` of the element).

DRAW never used direct capture, deliberately: a real browser screenshot is GPU-composited and pixel-perfect across iframes, `<canvas>`, WebGL, shadow DOM, and hardware-accelerated layers — all known failure modes of `html2canvas`. The cost is scroll-stitch complexity, which is well-understood and ported below.

### 2. Two capture primitives from Claude in Chrome

- **`zoom` (region) for in-viewport element crops.** A spike confirmed `zoom`'s `region` is **CSS-pixel, viewport-relative**, returns an **element-exact** crop, at **~2× (near-retina) resolution**. So "crop to element" = scroll element into view → `zoom` to its `getBoundingClientRect`. No full capture, no Pillow crop. Padding/trim (below) = expand/shrink the region.
- **`screenshot` (tiled) + Pillow stitch for full-page / tall-element / inner-scroll.** A spike confirmed plain `screenshot` is **page-only (no browser/OS chrome)** with **origin = viewport (0,0)** and **uniform scale**. Tiles are stitched in Python with DRAW's overlap correction.

### 3. Scale is measured, never assumed — "page as ruler"

`computer` screenshot is a **display-region capture**, so its pixel scale is a property of the monitor the Chrome window is on, not of the page. (Verified: a 1512-CSS-px viewport captured at 1485 px ≈ 0.982× on a scaled retina display; a lower-DPI extended display would differ; `× devicePixelRatio` would be wrong by ~2×.) Therefore:

```
S = capture_pixel_width / window.innerWidth
```

measured from each capture sequence. Do **not** detect the display or query its DPI (brittle under multi-monitor, macOS scaled modes, and mid-run window drags). Validate `S` against `capture_pixel_height / window.innerHeight`; if they disagree, the window likely straddles two displays — abort and re-capture. `zoom` element crops need no calibration (CSS in, element out).

### 4. Division of labor

- **Injected JS (`javascript_tool`)** — all page-context work, returning small JSON: measure rects (`getBoundingClientRect`), classify scroll mode, drive scrolling, hide obscuring elements, suppress scrollbars/rounding, wait for settle. (Ports from DRAW `content.js`.)
- **`computer` `zoom` / `screenshot`** — the pixels.
- **Python MCP (Pillow)** — crop from stitched images, stitch tiles with overlap correction, applying the measured `S`. (Ports from DRAW `clipUtils.js`.)

### 5. Frame, trim, and context-margin are three distinct operations

Do **not** conflate these into one signed parameter (an earlier draft did):

- **Frame — breathing room in the element's own background.** When an element has little/no padding, its content sits flush to the crop edge. Expanding the crop rect would just capture adjacent page content, not a frame. The correct fix is a **capture-time DOM mutation**: inject CSS padding onto the element (filled by the element's own background), re-measure its now-larger `getBoundingClientRect`, `zoom`, then restore the original styles. *Additive; the only way to frame with the element's own background.* Ports from DRAW `apply_clip_padding` / `restore_clip_styles` (`content.js:2744`). (Note: under `box-sizing:border-box`, added padding pushes content inward rather than growing the box — still yields a frame; the DRAW helper manipulates computed padding directly.)
- **Trim — remove [x] px off [top\|right\|bottom\|left].** *Subtractive:* shrink the `zoom` region inward, or crop inward in Pillow (`crop_image`). On a multi-tile stitch, top/bottom trim is a post-stitch crop.
- **Context margin — element *plus* surrounding page.** Expand the capture rect *outward* (DRAW rect-expansion in `taskExecutors.js`). Captures adjacent page content by design — available if a recipe needs the element in context, but it is **not** a clean frame.

## DRAW port targets (durable inventory)

Geometry/logic to port, with source locations in `/Users/Michael/Documents/GitHub/DRAW/draw-extension/`:

| Function | Source | Role |
|---|---|---|
| `cropToElement(img, rect, scale)` | `server/helpers/clipUtils.js:176` | Crop image to rect (apply measured `S`, not dpr) |
| `stitchImagesWithOverlap({imageParts, clientHeight, ...})` | `server/helpers/clipUtils.js:63` | Overlap-corrected vertical stitch: `overlap = (prevScrollTop + clientHeight) − curScrollTop` |
| `stitchImages(buffers)` | `server/helpers/clipUtils.js:17` | Simple equal-height stitch |
| `prepare_next_capture(rule)` | `.../content/content.js:1306` | Measure rect + classify scrollMode (`window`/`internal`) + `isBodyTarget` |
| `scroll_active_element(amount, mode)` | `.../content/content.js:1404` | Scroll window or inner element, `behavior:'instant'`, report `atBottom` + rect |
| `_hideObscuringElements(target)` | `.../content/content.js:1491` | Hide fixed/sticky globally + `elementsFromPoint` corner hit-test; reversible |
| `_suppressScrollbarsAndRounding(el)` | `.../content/content.js:1245` | Kill scrollbar/border-radius seam artifacts before stitch |
| `apply_clip_padding` / `restore_clip_styles` | `.../content/content.js:2744` | JIT-inject CSS padding to frame an element with its own background before capture; reversible |
| `_waitForScrollCompletion(target)` | `.../content/content.js:3039` | Poll scroll pos, 3 stable reads |
| `_waitForAnimations(el)` | `.../content/content.js:2302` | Await `getAnimations({subtree:true})` |
| `isVisible(el)` | `.../content/content.js:5451` | Visibility incl. `IMG.naturalWidth>0` race exception |

Three scroll-stitch paths to reproduce: **window/body** (scroll page, full tiles), **window/element** (element > viewport: crop each tile to the element's viewport intersection), **internal** (`target.scrollBy()`, crop the fixed rect each step).

## Consequences

- Element evidence crops are one high-res `zoom` call — cheap and detailed.
- Full-page / tall / inner-scroll go through scroll-tile-stitch with ported, battle-tested math.
- The pipeline is **display-independent by construction** (measured `S`), which directly solves the multi-monitor/DPI problem.
- **Open implementation spike:** `save_to_disk` returned an image inline plus an `ID`, not a confirmed filesystem path. Single `zoom` crops return inline (fine — one image). The many-tile stitch wants tiles on disk to avoid pushing N images through the agent context; whether `save_to_disk` gives the MCP server a readable path, or we need a fallback (configurable save dir, fewer/larger tiles, or accept inline), is tracked in [Issue #4](https://github.com/michaelblum/employer-brand-audits/issues/4).
- **V1 limitations (documented, acceptable for vertical employer-brand pages):** horizontal scroll (element wider than viewport) and two-axis inner-scroll are not handled. DRAW solved neither.

## Related

- [ADR-003: Browser Layer — Claude in Chrome](ADR-003-browser-layer.md)
- [Issue #4: Capture primitive implementation spikes](https://github.com/michaelblum/employer-brand-audits/issues/4)
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
