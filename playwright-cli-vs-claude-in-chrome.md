# Playwright CLI vs. Claude in Chrome for `employer-brand-audits`

## Executive Summary

For a plugin that needs repeatable browser visits, targeted screenshots, and visible-text extraction, **Playwright CLI is the execution engine**.

Claude-in-Chrome/browser-controlled Claude workflows are historical context for this repo and are disabled for audit execution so agents do not pick the wrong browser path.

## Option A: Playwright CLI

Playwright CLI is the better fit for a production-style audit pipeline.

### Token efficiency and context usage

Playwright keeps the heavy work outside the model context. The browser state, screenshots, and page navigation live on disk or in the browser process, not in the prompt. That matters because audits can touch multiple pages, scroll positions, and screenshots without forcing the model to carry full accessibility trees or page HTML in context.

For large audit runs, this is materially cheaper and easier to scale. The model can work from compact artifacts:

- saved screenshots
- extracted text snapshots
- selected DOM or accessibility summaries
- per-page logs or JSON output

That is a better fit than streaming a live browser state into context on every action.

### Determinism and repeatability

Playwright is designed for reproducible automation. The same script can run in CI, cron, or a local shell, with the same browser flags, viewport, locale, and device emulation.

That is the right shape for scheduled employer-brand audits:

- same URLs
- same viewport sizes
- same wait conditions
- same screenshot naming
- same output directory structure

If a page changes, the diff is visible in artifacts rather than being hidden in a conversational interaction. That makes regressions easier to triage and easier to compare over time.

### Screenshot fidelity and control

Playwright gives direct control over the capture surface:

- viewport screenshots
- full-page screenshots
- element-specific screenshots
- mobile and desktop emulation
- explicit browser choice
- deterministic sizing and device scale factor

For audit use cases, that is critical. Career pages often have sticky headers, lazy-loaded job lists, cookie banners, and responsive breakpoints. Playwright lets you standardize those conditions and capture exactly the region you want.

### Environment constraints

Playwright is strongest when Node and the CLI are available. If the environment is a normal macOS workstation, CI runner, or scheduled job, that is a small constraint for a large gain in reliability.

If Node or the CLI is unavailable, Playwright is not the right runtime. In that case, you either need a browser-native approach or a hosted automation layer. But if you can install the CLI, it is the better automation substrate.

## Option B: Claude in Chrome (disabled)

Claude-in-Chrome style control is better understood as an interactive browser-assistance surface than as a batch automation engine.

### Token efficiency and context usage

This approach tends to spend more context on the browser itself. If the browser state, accessibility tree, visible text, or screenshots are streamed into the model repeatedly, the model budget gets consumed by inspection overhead rather than analysis.

That tradeoff can be acceptable for one-off investigations, but it is not ideal for a recurring audit system. The more pages and interactions you add, the less efficient it becomes.

### Determinism and repeatability

A browser-driven conversational workflow is usually less deterministic. It is good at adapting to surprises, but weaker as a scheduled pipeline.

Typical sources of variance include:

- different browsing sessions
- manual intervention
- UI state not being reset cleanly
- ad/cookie/interstitial differences
- inconsistent navigation timing

That makes it harder to treat as a stable audit harness.

### Screenshot fidelity and control

Claude-in-Chrome can capture what a human sees, which is useful for exploratory review. But it usually gives less direct control over:

- exact viewport size
- exact capture region
- repeatable emulation profiles
- batch capture naming and storage

It is more useful for “look at this page with me” than for “run the same audit every Monday and diff the result.”

### Environment constraints

The main advantage is accessibility. If the user only has a browser-based Claude session, or cannot install Node/CLI tooling, then browser-native control may be the only viable path in general, but not for this repo's automated audit path.

That makes it historical fallback context, not an allowed audit engine.

## Recommendation

**Use Playwright CLI for automated audits. Do not fall back to Claude-in-Chrome for audit execution.**

For `employer-brand-audits`, that means:

- use Playwright CLI for scheduled crawling, screenshots, and extraction
- store outputs as artifacts on disk for later analysis
- treat Claude-in-Chrome findings as historical context only

That division gives you the best combination of repeatability, screenshot control, and low context cost.

## Smoke Harness

Run the no-behavior-change Playwright CLI smoke through the repository wrapper:

```bash
python3 scripts/playwright_cli_smoke.py
```

The smoke uses the named session `eba-smoke`, opens `https://example.com`,
resizes the browser to `1280x900`, writes a boxed snapshot, writes viewport and
full-page screenshots, runs
`scripts/playwright-snippets/extract-visible-text.js`, captures that snippet's
stdout to disk, and closes the session.

Deterministic outputs are replaced on each run under:

```text
artifacts/playwright-cli-smoke/latest/
```
