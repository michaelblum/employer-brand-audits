# Prompt: Continue Playwright CLI Public Page Smoke

You are the next senior developer on the `employer-brand-audits` Playwright CLI migration.

Start from branch `migration/playwright-cli-engine`. The latest pushed commit should be:

```text
f427fb5 Add Playwright CLI capture modes smoke
```

Do a quick status check first:

```bash
git status --short --branch
git log --oneline -5
```

Expected local noise from the prior environment:

```text
 M scripts/spike_hitl_capture.py
?? example.png
```

Do not touch, stage, commit, or rely on those files unless the user explicitly asks. `scripts/spike_hitl_capture.py` had pre-existing local modifications outside the committed migration work.

## Authoritative Direction

Read these first, in order:

```text
docs/decisions/ADR-008-playwright-cli-browser-engine.md
docs/decisions/ADR-005-screenshot-capture-strategy.md
.claude/CLAUDE.md
playwright-cli-vs-claude-in-chrome.md
```

Operating rules:

- Playwright CLI is now the browser engine.
- Claude in Chrome / Claude browser-control tooling is disabled for audit execution.
- Do not use `computer` screenshot / `zoom` or `javascript_tool` as capture primitives.
- Use `playwright-cli` directly or the repo wrapper at `scripts/playwright_cli_browser.py`.
- Do not route image bytes through the model. Browser artifacts must be written to disk.
- Keep proof tiers narrow. Do not claim browser parity or audit readiness just because local smoke tests pass.

## Current Pushed Work

Three commits were added and pushed on top of `1e3a972`:

```text
e7c10a7 Add Playwright CLI smoke harness
36810d1 Expand Playwright CLI smoke proof
f427fb5 Add Playwright CLI capture modes smoke
```

Important committed files:

```text
scripts/playwright_cli_browser.py
scripts/playwright_cli_smoke.py
scripts/playwright_cli_capture_modes_smoke.py
scripts/playwright-fixtures/capture-modes.html
scripts/playwright-snippets/extract-visible-text.js
scripts/playwright-snippets/settle-page.js
scripts/playwright-snippets/hide-obscuring-elements.js
scripts/playwright-snippets/restore-page.js
playwright-cli-vs-claude-in-chrome.md
```

Existing smoke commands:

```bash
python3 scripts/playwright_cli_smoke.py
python3 scripts/playwright_cli_capture_modes_smoke.py
```

Their deterministic ignored artifact directories:

```text
artifacts/playwright-cli-smoke/latest/
artifacts/playwright-cli-capture-modes/latest/
```

Known limitations already found and handled:

- `playwright-cli run-code --filename` can print `### Error` while exiting `0`; `scripts/playwright_cli_browser.py` now treats that as failure.
- `playwright-cli run-code --filename` expects a function expression file and rejects a trailing semicolon in that expression.
- Playwright CLI blocks direct `file://` navigation, so the capture-modes smoke serves the local fixture on an ephemeral `127.0.0.1` HTTP port.

Current proof boundary:

- Navigation, resize, snapshot boxes, visible text extraction, viewport screenshot, full-page screenshot, `h1` element screenshot, setup/cleanup snippets, state save/load, and cleanup are proven through `scripts/playwright_cli_smoke.py` on `https://example.com`.
- Animation settle, nonzero overlay hiding, own-background frame, trim, context margin, internal-scroll expanded capture, restore, and cleanup are proven through `scripts/playwright_cli_capture_modes_smoke.py` against the local fixture.
- Browser parity with real employer-brand pages is not proven.
- Anti-bot behavior is not proven.
- Do not claim readiness.

## Next Task

Build a real-public-page smoke harness with a narrow proof claim.

Add:

```text
scripts/playwright_cli_public_page_smoke.py
```

Default behavior:

- Use a named session, for example `eba-public-page`.
- Use a configurable `--url`.
- Default to one stable, low-risk public careers/about page. Avoid Indeed, Glassdoor, LinkedIn, Kununu, and other anti-bot-heavy surfaces for this step.
- Use deterministic ignored output:

```text
artifacts/playwright-cli-public-page/latest/
```

Minimum browser proof:

- open URL
- resize desktop viewport
- run `settle-page.js`
- run `hide-obscuring-elements.js`
- write `snapshot --boxes`
- run `extract-visible-text.js`
- write viewport screenshot
- write full-page screenshot
- write one selector-based element screenshot
- run `restore-page.js`
- close session
- capture stdout/log files to disk

CLI contract:

- Reuse `scripts/playwright_cli_browser.py`; do not bypass it unless there is a concrete limitation and you document it.
- Support `--target` for the element screenshot.
- If `--target` is omitted, choose a conservative default such as `main`, `h1`, or `body` after verifying what works for the default URL.
- Keep all generated artifacts under `artifacts/playwright-cli-public-page/latest/`.

Documentation:

- Update `playwright-cli-vs-claude-in-chrome.md` with the exact command.
- Report the exact artifact paths in the final response.
- Document any limitations found, especially cookie/consent banners, lazy content, sticky headers, selector fragility, or Playwright CLI behavior that requires wrapper hardening.

Validation commands:

```bash
git diff --check
python3 -m py_compile scripts/playwright_cli_browser.py scripts/playwright_cli_smoke.py scripts/playwright_cli_capture_modes_smoke.py scripts/playwright_cli_public_page_smoke.py
cd mcp-server && ./.venv/bin/pytest -q
python3 scripts/playwright_cli_smoke.py
python3 scripts/playwright_cli_capture_modes_smoke.py
python3 scripts/playwright_cli_public_page_smoke.py
```

Commit and push only your scoped changes. Do not include generated `artifacts/`, `.playwright-cli/`, `example.png`, or the pre-existing `scripts/spike_hitl_capture.py` modification.
