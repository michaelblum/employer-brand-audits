# Spike: Capture Primitive (Issue #4)

**Date:** 2026-06-11  
**Status:** Complete — one finding forces a capture-handoff pivot (does **not** block Plan 1).

## What was tested

How Claude in Chrome's `computer` screenshot/`zoom` behave, and specifically whether `save_to_disk` hands the Python MCP server a readable file path for the multi-tile stitch.

## Findings

| # | Question | Result |
|---|---|---|
| 1 | Does `computer` screenshot include browser/OS chrome? | **No — page-only**, origin = viewport (0,0), uniform scale. (Confirmed design-phase via corner markers.) |
| 2 | Is `zoom` `region` CSS-px and element-exact? | **Yes** — passed CSS rect, got an element-exact crop at ~2× res. |
| 3 | Is the capture scale fixed? | **No — display-dependent.** 1512-CSS-px viewport captured at 1485px (~0.982×) on a scaled retina display. Must be *measured* (`S = px_width/inner_width`), never assumed. |
| 4 | Is `read_page` a pixel source? | **No** — accessibility tree only. |
| 5 | **Does `save_to_disk` give a server-readable path?** | **NO.** The result returns an `ID` (`ss_…`) + an inline image, **no filesystem path**. No image file is discoverable in `~/.claude`, `/private/tmp/claude-503`, `local-agent-mode-sessions`, `~/Library/Application Support/Claude{,-3p}`, `~/Library/Containers`, `~/Downloads`, or `$TMPDIR` (searched by recent mtime + by ID/`screenshot` name). Bash can see *other* recent Claude files (Cookies, sentry), so it's not a sandbox blind spot. **The screenshot returns inline to the agent only.** |
| 6 | `zoom` max region size; screenshot rate limits | Deprioritized — finding #5 reframes the handoff before these matter. Revisit during Plan 5. |

## Decision

**The disk-handoff premise (Python `stitch_images` reads tiles from `save_to_disk` paths) is not viable.** `save_to_disk` exposes no path, and routing tile bytes back out through the agent is impossible anyway (multi-MB base64 exceeds the output-token ceiling — the same wall as Drive upload, per ADR-006).

**Recommended pivot — server-side OS capture.** The Python MCP server grabs pixels itself via macOS `screencapture` (window/region) to a file it owns. Claude in Chrome still drives the page (navigate, scroll, hide overlays, inject corner markers) via `javascript_tool`; only the *pixel grab* moves to `screencapture`. The corner-marker calibration already designed (ADR-005) locates the page viewport within the captured image and derives `S`, handling any chrome inclusion. Properties:
- Bytes stay entirely server-side, on disk — no model routing, no token wall.
- Invisible to the site (OS-level capture) — *strengthens* the anti-detection posture (ADR-003).
- Costs: one-time macOS screen-recording permission; Chrome window must be visible/foreground; window-bounds → viewport coordination (solved by markers).

For **L2 analysis** specifically, no disk is needed — the agent views the (downscaled) screenshot inline via vision. The disk path only matters for the **report/archival image** that gets published.

**Alternatives if `screencapture` is rejected:** probe the `Claude-3p` dir / other Claude-in-Chrome tools (`gif_creator`, `file_upload`) for a save path; or a native-messaging companion that writes to a known dir.

## Scope impact

- **Does not block Plan 1** (tasks 1–6): the pure image functions operate on image files at given paths regardless of how they're produced.
- **Affects Plan 5** (orchestration / capture) and **ADR-005 / ADR-006** (capture handoff). Carry the `screencapture` pivot into Plan 5; update ADR-005/006 once the approach is confirmed.
- **Issue #4** stays open with this finding; items 1–4 are resolved, #5 resolved (negative), #6 deferred.
