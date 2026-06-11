# ADR-005: Screenshot Capture Strategy

**Date:** 2026-06-10  
**Status:** Accepted, amended by [ADR-008: Playwright CLI Is The Browser Engine](ADR-008-playwright-cli-browser-engine.md)

---

## Amendment Note

[ADR-008](ADR-008-playwright-cli-browser-engine.md) supersedes the Claude-in-Chrome-specific capture primitives in this ADR. The durable principles remain binding: use browser-composited pixels instead of DOM-rendered approximations, keep frame/trim/context-margin distinct, keep bytes on disk, and preserve Python/Pillow post-processing where useful. The active browser capture engine is now Playwright CLI, not Claude in Chrome `computer`/`zoom` or `javascript_tool`.

## Context

The audit needs four kinds of image capture: (1) a crop to a single DOM element, (2) a full-page scan, (3) an element taller than the viewport, (4) the content of a nested `overflow:auto/scroll` container that exceeds its own box. We also need to add a padding "border" around a clip or trim pixels off its edges.

The DRAW scrapyard solved these cases in production as a Chrome extension using `chrome.tabs.captureVisibleTab`. This project now uses Playwright CLI as the browser engine ([ADR-008](ADR-008-playwright-cli-browser-engine.md)). We inherit DRAW's geometry, settling, overlay-hiding, scroll, and frame concepts, but the active capture primitives are Playwright CLI commands and `run-code` snippets that write artifacts to disk.

## Decision

### 1. Crop-and-stitch over direct element capture (Strategy B, not A)

Capture pixels from a viewport/region screenshot, then crop/stitch by computed geometry. Do **not** attempt to capture an element's pixels directly via injected JS (`html2canvas`, `element.toDataURL`, SVG `foreignObject`, canvas `drawImage` of the element).

DRAW never used direct capture, deliberately: a real browser screenshot is GPU-composited and pixel-perfect across iframes, `<canvas>`, WebGL, shadow DOM, and hardware-accelerated layers — all known failure modes of `html2canvas`. The cost is scroll-stitch complexity, which is well-understood and ported below.

### 2. Active Playwright CLI capture primitives

- **Viewport screenshot:** `playwright-cli -s=<session> screenshot --filename <path>`.
- **Full-page screenshot:** `playwright-cli -s=<session> screenshot --full-page --filename <path>` for pages where Playwright's built-in full-page capture preserves the required visual behavior.
- **Element screenshot:** `playwright-cli -s=<session> screenshot <target> --filename <path>`, where `<target>` is a stable selector or a snapshot element ref.
- **Custom capture:** `playwright-cli -s=<session> run-code --filename <script>` for clip regions, animation options, masking, padding-based frame operations, or scroll-tile flows that the basic CLI command cannot express.
- **Post-processing:** Python/Pillow `stitch_images`, `crop_image`, and `make_rendition` operate on disk artifacts produced by Playwright CLI.

### 3. Scale is measured, never assumed — "page as ruler"

For screenshots passed to Python post-processing:

```
S = capture_pixel_width / window.innerWidth
```

Do **not** assume S from display DPI. Validate against height ratio; mismatch means capture geometry is not uniform and the image should be re-captured. Direct Playwright element screenshots usually avoid manual scale math because Playwright owns the element-to-pixel capture.

### 4. Element targeting and geometry

Use `playwright-cli snapshot --boxes` to obtain element refs and viewport-relative CSS boxes. Boxes come from `getBoundingClientRect`, which is the coordinate system used by the existing crop/stitch math. Prefer direct Playwright element screenshots for in-viewport evidence crops. Use Python `crop_image` when the element is being cropped from an already stitched image.

### 5. Division of labor

- **Playwright CLI commands** — session creation, navigation, resizing, snapshots, screenshots, state save/load, and cleanup.
- **Playwright CLI `run-code` snippets** — page-context work returning small JSON or writing files via wrappers: measure rects, classify scroll mode, drive scrolling, hide obscuring elements, suppress scrollbars/rounding, wait for settle, apply and restore frame padding.
- **Python MCP (Pillow)** — crop from stitched images, stitch tiles with overlap correction, and produce analysis/archive renditions from disk artifacts.

### 5. Frame, trim, and context-margin are three distinct operations

Do **not** conflate these into one signed parameter (an earlier draft did):

- **Frame — breathing room in the element's own background.** When an element has little/no padding, its content sits flush to the crop edge. Expanding the crop rect would just capture adjacent page content, not a frame. The correct fix is a **capture-time DOM mutation**: use a Playwright `run-code` snippet to inject CSS padding onto the element, re-measure its now-larger `getBoundingClientRect`, capture with Playwright, then restore the original styles. *Additive; the only way to frame with the element's own background.* Ports from DRAW `apply_clip_padding` / `restore_clip_styles` (`content.js:2744`). (Note: under `box-sizing:border-box`, added padding pushes content inward rather than growing the box — still yields a frame; the DRAW helper manipulates computed padding directly.)
- **Trim — remove [x] px off [top\|right\|bottom\|left].** *Subtractive:* use a custom Playwright clip region via `run-code`, or crop inward in Pillow (`crop_image`). On a multi-tile stitch, top/bottom trim is a post-stitch crop.
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

- Element evidence crops are direct Playwright element screenshots unless custom frame/trim logic requires `run-code`.
- Full-page capture starts with Playwright's `--full-page` screenshot; tall elements and inner-scroll containers use wrapper-driven scroll-tile-stitch when direct capture is not equivalent.
- The pipeline is **display-independent by construction** (measured `S`), which directly solves the multi-monitor/DPI problem.
- **Capture primitive resolved:** Playwright CLI writes screenshot artifacts to disk directly. The old Claude `save_to_disk` and `mss` path is historical fallback context only.
- **V1 limitations (documented, acceptable for vertical employer-brand pages):** horizontal scroll (element wider than viewport) and two-axis inner-scroll are not handled. DRAW solved neither.

## Related

- [ADR-008: Playwright CLI Is The Browser Engine](ADR-008-playwright-cli-browser-engine.md)
- [ADR-003: Browser Layer — Claude in Chrome](ADR-003-browser-layer.md) — superseded historical context
- [Issue #4: Capture primitive implementation spikes](https://github.com/michaelblum/employer-brand-audits/issues/4)
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
