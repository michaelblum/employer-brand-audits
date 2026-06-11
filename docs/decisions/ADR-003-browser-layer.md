# ADR-003: Browser Layer — Claude in Chrome

**Date:** 2026-06-10  
**Status:** Superseded by [ADR-008: Playwright CLI Is The Browser Engine](ADR-008-playwright-cli-browser-engine.md)

---

## Supersession Note

This ADR records the original V1 browser-layer decision. It is no longer the active browser-engine decision. [ADR-008](ADR-008-playwright-cli-browser-engine.md) supersedes it and requires Playwright CLI as the browser engine for automated audits. Agents must not use Claude in Chrome for audit execution.

## Context

The audit collects pages from sites that actively detect and block headless automation — Indeed, Glassdoor, LinkedIn, Kununu. Three forces shaped the browser-layer choice:

1. **Distribution.** Day-one users are non-developers on macOS (some Windows later). There is no clean single-binary distribution story for a Node/Playwright stack today: Bun compile is broken with Playwright, pkg/nexe are abandoned, Electron is 200MB+. Any Node-based browser layer pushes a real install burden onto non-technical users.
2. **Anti-bot posture.** The target sites fingerprint browsers and challenge headless sessions with captchas. A real browser with a real, logged-in session is the strongest possible posture.
3. **Existing assets.** The DRAW scrapyard already contains production-grade scroll-and-stitch, animation-settling, and obscuring-element-hiding logic that can be injected into a page.

During the session, empirical tests confirmed that driving the user's real Chrome reached Indeed and Kununu pages that historically threw captchas — without challenges.

## Decision

**Claude in Chrome (the Anthropic browser extension) is the V1 browser layer.** It drives the user's real Chrome via native messaging, inheriting the user's fingerprint, cookies, and authenticated sessions. DRAW techniques are injected through its `javascript_tool`. Full-page captures are taken as viewport tiles via the `computer` screenshot action with `save_to_disk`, then stitched by the Python MCP server from disk paths.

## Alternatives considered

| Option | Why rejected for V1 |
|---|---|
| **Playwright MCP + persistent profile** | Requires Node.js (non-dev install burden); headless Chromium is more detectable on authed sites; two browser stacks to maintain. Kept as a deferred *headless fallback* — [Issue #1](https://github.com/michaelblum/employer-brand-audits/issues/1). |
| **Chrome extension fork of DRAW** | Must be built, distributed, and kept in sync; needs a local WebSocket bridge to the MCP server. Claude in Chrome already exists and is installed — no build, no distribution, no bridge. |
| **Firecrawl / cloud scraping API** | Per-page cost, an API key to provision, and still detectable as non-browser traffic on the hardest sites. Not ruled out forever, but it loses the real-session advantage that makes the hard sites tractable. |

## Consequences

- **Zero distribution and zero browser credentials.** The extension is already present; there is nothing to ship or key.
- **Chrome must be open and the session interactive.** V1 is not headless and not unattended. Acceptable for the analyst-in-the-loop POC; the headless gap is tracked in [Issue #1](https://github.com/michaelblum/employer-brand-audits/issues/1).
- **Single-user, single-session.** One Chrome session at a time. Batch/parallel runs are out of scope for V1.
- **Chrome-only.** Not Safari/Firefox. Acceptable given the user base.
- **Captcha handling is human-in-the-loop.** A real session rarely triggers them; when it does, the user solves it in their own browser and the run continues.
- **DRAW logic is injected, not ported (mostly).** The capture/settle/hide scripts run as injected JS. Only the *stitching* math (`clipUtils.stitchImagesWithOverlap`) is ported to Python/Pillow, because stitching happens server-side from disk tiles — see the design spec's L1 image-handoff constraint.

## Related

- [Issue #1: Headless fallback — Playwright MCP + persistent profile](https://github.com/michaelblum/employer-brand-audits/issues/1)
- [Issue #2: V2 — browser as collaborative agent-human surface](https://github.com/michaelblum/employer-brand-audits/issues/2)
- Design spec: `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md`
