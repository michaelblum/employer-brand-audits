# Project: Employer Brand Audits

## Stack — Python only, no Node.js

This project is a **Claude Cowork plugin**. The runtime is Python (ships with macOS).
Node.js is explicitly not part of the stack and must not be introduced.

- All MCP server code: Python (`mcp-server/`)
- All scripts and spikes: Python (`scripts/`)
- All tests: Python (`mcp-server/tests/`)
- Dependencies managed via `mcp-server/.venv` and `mcp-server/requirements.txt`

**Run anything from the venv:**
```
source mcp-server/.venv/bin/activate
python scripts/some_script.py
pytest mcp-server/tests/
```

Do not write `.js` files. Do not use `node`, `npm`, or `npx`.
The Playwright CLI (`playwright`) on this machine is the Node.js version — ignore it.
Use `playwright` via the Python package (`pip install playwright`), already in the venv.

## Key decisions

All architectural decisions live in `docs/decisions/ADR-*.md`. Read them before
making changes to browser layer, capture strategy, image pipeline, or manifest schema.

Critical ones:
- **ADR-003** — why Claude in Chrome (real browser profile), not Playwright headless
- **ADD-005** — capture strategy: `mss` for tile grabs, `zoom` for element crops
- **ADR-006** — image bytes never route through the model (no base64 in tool args/results)

## Capture primitive

Server-side capture uses `mss` (Python). Do not revert to `screencapture` CLI or
any Node.js-based capture. See `docs/superpowers/spikes/2026-06-11-mss-capture-spike.md`.

Playwright-over-CDP (Python) is a deferred alternative — tracked in `docs/decisions/ADR-003.md`.
If evaluating it, use `scripts/spike_playwright_indeed.py` as the starting point.

## Session naming

Name sessions after what they're doing (2-3 words). Ask if unsure.
