# ADR-008: Playwright CLI Is The Browser Engine

**Date:** 2026-06-11
**Status:** Accepted
**Supersedes:** [ADR-003: Browser Layer -- Claude in Chrome](ADR-003-browser-layer.md)
**Amends:** [ADR-005: Screenshot Capture Strategy](ADR-005-screenshot-capture-strategy.md)

---

## Context

[ADR-003](ADR-003-browser-layer.md) selected Claude in Chrome as the V1 browser layer because it minimized distribution work and inherited the user's real browser session. That decision was correct for the original zero-install Cowork-plugin premise, but it created a weak automation boundary:

- browser actions were conversational instead of scriptable;
- screenshot handoff depended on host-specific `computer`/`zoom` behavior;
- full-page capture needed a second OS-capture path (`mss`) to avoid routing image bytes through the model;
- agents could accidentally keep using Claude-in-Chrome tools because the docs described them as the browser layer.

The local Playwright CLI evaluation now establishes the new direction: repeatable browser visits, targeted screenshots, visible-text extraction, browser state management, and output files should be handled by `playwright-cli`, with the agent consuming disk artifacts rather than driving a browser through Claude in Chrome.

This is an architectural change, not a script refactor. The browser engine changes from a Claude-hosted browser extension flow to a CLI-owned Playwright browser session.

## Decision

**Playwright CLI is the browser engine for automated audits.**

All agent-orchestrated browser work must go through `playwright-cli` or a thin repository wrapper around it. Agents must not use Claude in Chrome / Claude browser-control tooling for audit collection, screenshot capture, page setup, element targeting, or navigation.

The Python MCP server remains the mechanical artifact layer: image post-processing, rendition generation, manifest writes, report generation, and publishing. Playwright CLI produces browser artifacts on disk; Python tools transform and record those artifacts.

## Required Browser Boundary

Allowed browser operations:

- `playwright-cli open`, `goto`, `resize`, `snapshot`, `eval`, `run-code`, `screenshot`, `state-save`, `state-load`, `attach`, `close`, `close-all`, and `kill-all`;
- checked-in thin wrappers that shell out to those commands;
- checked-in JavaScript snippets executed through `playwright-cli run-code`.

Disallowed browser operations:

- Claude in Chrome MCP/browser-extension control;
- `computer` screenshot / `zoom` as audit capture primitives;
- `javascript_tool` as the page-manipulation path;
- routing image bytes through model/tool arguments;
- ad hoc agent browser actions that bypass the repository wrapper once the wrapper exists.

## Capture Strategy Under Playwright CLI

The preserved principles from [ADR-005](ADR-005-screenshot-capture-strategy.md):

- capture browser-composited pixels, not DOM-rendered approximations such as `html2canvas`;
- keep frame, trim, and context margin as distinct operations;
- keep raw artifacts on disk and produce analysis/archive renditions separately;
- keep `crop_image`, `stitch_images`, and `make_rendition` as Python post-processing operations where they add value.

The changed capture primitives:

| Capability | Primary Playwright CLI path | Notes |
|---|---|---|
| Page navigation | `playwright-cli -s=<session> goto <url>` | Session naming is mandatory for automation runs. |
| Page setup / cleanup | `run-code` snippets | Hide overlays, settle animations, suppress scrollbars, restore mutations. |
| Visible text extraction | `eval` or `run-code --filename` | Write markdown/text output to disk via wrapper, not model context. |
| Snapshot / element discovery | `snapshot --boxes` | Boxes are viewport-relative CSS pixels from `getBoundingClientRect`. |
| Viewport screenshot | `screenshot --filename <path>` | Use after deterministic `resize` and setup. |
| Full-page screenshot | `screenshot --full-page --filename <path>` | First choice for simple pages; validate sticky/lazy behavior before retiring stitch paths. |
| Element screenshot | `screenshot <target> --filename <path>` | Use selector or snapshot element ref when stable. |
| Custom clip / masks / animation options | `run-code --filename <script>` | Required when CLI `screenshot` options are insufficient. |
| Tall element / internal scroll | wrapper + `run-code` + existing `stitch_images` | Preserve scroll-tile behavior where direct full-page capture is not equivalent. |
| Own-background frame | `run-code` applies padding, screenshots, restores | Pillow matte is only for solid borders. |

## Session and State

Use named sessions for all automated work:

```bash
playwright-cli -s=eba open --browser chrome --headed --persistent --profile ./chrome-profile <url>
```

State and cleanup are explicit:

```bash
playwright-cli -s=eba state-save artifacts/browser-state.json
playwright-cli -s=eba close
playwright-cli close-all
playwright-cli kill-all
```

Persistent profiles are allowed when a target needs logged-in or anti-bot state, but only one audit run may own a profile at a time.

## Consequences

- The project now has a Node/Playwright CLI dependency for browser automation. This supersedes the previous Python-only/no-Node browser-layer constraint.
- Claude in Chrome is demoted to historical context and must not be used by agents for audit execution.
- Anti-bot behavior must be re-proven under Playwright CLI, especially on Indeed, Glassdoor, LinkedIn, and Kununu. Until proven, those targets are not "ready"; they are migration validation targets.
- `mss` is no longer the default capture primitive. It may remain as a fallback only if a concrete Playwright CLI limitation is proven for a required capture mode.
- Existing Python image functions remain valid and should not be rewritten merely because the browser engine changed.

## Proof Boundaries

The migration is not ready until each required capture mode has a checked-in command or wrapper and a generated disk artifact:

- page navigation;
- text extraction;
- viewport screenshot;
- full-page screenshot;
- element screenshot;
- animation-settled capture;
- obscuring-element removal;
- own-background frame;
- trim;
- context margin;
- tall element or internal-scroll capture;
- session save/load and cleanup.

Do not claim parity with Claude in Chrome until those artifacts exist and are visually checked against representative employer-brand pages.

## Related

- [ADR-003: Browser Layer -- Claude in Chrome](ADR-003-browser-layer.md)
- [ADR-005: Screenshot Capture Strategy](ADR-005-screenshot-capture-strategy.md)
- [ADR-006: Report Image Hosting and Analysis Renditions](ADR-006-report-image-hosting.md)
- `playwright-cli-vs-claude-in-chrome.md`
- `playwright-cli-help.txt`
