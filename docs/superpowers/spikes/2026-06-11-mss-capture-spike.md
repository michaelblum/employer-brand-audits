# Spike: mss Capture Validation

**Date:** 2026-06-11  
**Status:** Complete — mss confirmed viable; three integration notes documented below.

## Goal

Validate `mss` (Python screen-capture library) as the server-side pixel source for Plan 2, before building any manifest/lifecycle machinery. The prior capture-primitive spike ([2026-06-11-capture-primitive-spike.md](2026-06-11-capture-primitive-spike.md)) ruled out `save_to_disk` and recommended server-side OS capture; this spike chooses and confirms the specific implementation.

## Method

1. Added `mss>=9.0` to `mcp-server/requirements.txt`; installed (`mss 10.2.0`).
2. Added `validate_capture(screen_x, screen_y, width, height, output_path, [sample_x, sample_y])` to `mcp-server/server.py` — grabs a screen region via `mss.MSS`, saves as PNG, returns `{width, height, file_size_bytes, scale, pixel_at_sample}`.
3. Injected a 40×40 `position:fixed` div at CSS (300, 200) with `background:#FF00FF` (pure magenta) into `https://example.com` via `javascript_tool`.
4. Derived the viewport's screen position empirically: captured the full display (monitor 1), searched for the magenta cluster, found it at screen (300–339, 355–394) → viewport top = screen y 155.
5. Called `validate_capture` with the known marker coordinates and sampled the center pixel.

## Findings

| # | Question | Result |
|---|---|---|
| 1 | Is mss TCC-blocked (black frames)? | **No** — grabs real pixels from this process context (Claude Code / terminal subprocess). The trivial grab at screen center returned non-black content. |
| 2 | What is mss's output scale? | **S = 1.0 exactly.** mss returns logical/CSS pixels, NOT retina. A 100×100 request returns 100×100 px. Full display = 1512×982 (matching `window.screen.width/height`). `screencapture` CLI returns 2× (3024×1964). |
| 3 | Is geometry pixel-accurate? | **Yes.** The 40×40 CSS marker was captured as exactly 40×40 pixels at the correct X position. CSS coordinates map directly to mss coordinates with no scale factor — `getBoundingClientRect()` output is directly usable. |
| 4 | What is the color fidelity? | **Color profile offset.** CSS `#FF00FF` (sRGB magenta) is captured as RGB (234, 88, 245) — macOS Display P3 rendering. This is expected on a P3 display: mss reads the raw framebuffer in the display's native color space. For the audit use case (archival screenshots and vision analysis) this is fine; the images are pixel-accurate in geometry and visually correct. |
| 5 | Chrome frontmost requirement? | **Chrome must be the foreground window.** When Claude Code was frontmost, mss captured Claude Code's UI — no marker found. After activating Chrome via `osascript -e 'tell application "Google Chrome" to activate'`, the marker appeared correctly. This is an operational constraint for Plan 2/5. |
| 6 | Does `window.outerHeight` work for coordinate math? | **No — always 0 in Chrome 100+** (privacy restriction). `window.screenX/Y` are also unreliable. Use a calibration step: inject a marker at known viewport coords, capture full screen, find the cluster → derive `viewport_top_screen = marker_screen_y - marker_css_y`. On this machine: viewport top = screen y 155. |
| 7 | Launch context / TCC grant portability | **Not yet verified for Claude Code MCP subprocess.** The current grant applies to the terminal. When the MCP server runs as a stdio subprocess of Claude Code, it inherits the grant from the Claude Code app — which may or may not have Screen Recording permission. **Verify before Plan 5 wiring.** |

## Coordinate Formula

```
screen_x = marker_css_x   (window.screenX ≈ 0 in this setup; verify per-session)
screen_y = viewport_top_screen + marker_css_y
```

`viewport_top_screen` is found once per Chrome session:
1. Inject a calibration marker at CSS (0, 0).
2. Call `validate_capture` on a full-screen grab.
3. Find the marker cluster → `viewport_top_screen = cluster_y_min`.

Alternatively: `AppleScript window bounds top + chrome_toolbar_height`. The toolbar height on this session is ~155px (menu bar ≈ 25px + Chrome tabs/address/bookmarks ≈ 130px).

## Decision

**mss is confirmed as the capture primitive for Plan 2.** Rationale:

- In-process (no shell-out to `screencapture` CLI), returns a `ScreenShot` object with `.raw` BGRA bytes — zero temp files.
- Scale 1.0 with CSS logical pixels: `getBoundingClientRect()` coordinates are used directly, simplifying the geometry vs. the retina-compensated flow designed for `screencapture` (ADR-005 §3).
- Non-blocking: returns in ~10ms for viewport-sized regions.
- Cross-platform (future-proofing, if the audit ever runs on Linux/Windows).
- TCC granted in the current process context; the constraint (Chrome must be frontmost) is manageable and expected for any screen-recording approach.

**vs `screencapture` CLI:** mss wins on ergonomics (in-process, no temp file management, direct byte access) and on coordinate simplicity (1× not 2×). The only advantage of `screencapture` is retina resolution — not needed for this use case.

## Impact on ADR-005

Update §2 / §3 / §4:
- Replace `computer` `screenshot` + Pillow stitch with mss-based tile grab.
- Scale S = 1.0 for mss on logical-pixel displays. The `measure_scale` function still works (open image, compute ratio) but will return ≈1.0; keep it for cross-display safety.
- Add calibration-marker step to the capture workflow.
- Note Chrome-frontmost requirement and `viewport_top_screen` derivation.

## Open items for Plan 5

- Verify TCC grant transfers to Claude Code MCP subprocess launch context.
- Implement calibration step (inject (0,0) marker, derive `viewport_top_screen`).
- Implement Chrome-activate / capture / restore-focus sequence.
- Decide retina strategy: mss at 1× is simpler; if higher-res archival is needed, `screencapture` can be offered as an option.
