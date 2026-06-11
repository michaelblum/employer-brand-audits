# Project: Employer Brand Audits

## Stack

This project is a Claude Cowork plugin with a Python mechanical layer and
Playwright CLI as the browser engine.

- All MCP server code: Python (`mcp-server/`)
- All tests: Python (`mcp-server/tests/`)
- Dependencies managed via `mcp-server/.venv` and `mcp-server/requirements.txt`
- Browser automation: `playwright-cli` only, or thin repo wrappers around it

**Run anything from the venv:**
```
source mcp-server/.venv/bin/activate
python scripts/some_script.py
pytest mcp-server/tests/
```

Do not use Claude in Chrome / Claude browser-control tooling for audit execution.
Do not use `computer` screenshot / `zoom` or `javascript_tool` as capture
primitives. Playwright CLI is the browser boundary; checked-in JavaScript
snippets executed with `playwright-cli run-code` are allowed when CLI commands
are not expressive enough.

## Key decisions

All architectural decisions live in `docs/decisions/ADR-*.md`. Read them before
making changes to browser layer, capture strategy, image pipeline, or manifest schema.

Critical ones:
- **ADR-008** — Playwright CLI is the browser engine; Claude in Chrome is disabled for audit execution
- **ADR-003** — superseded historical Claude in Chrome decision
- **ADR-005** — capture strategy principles; Claude-specific primitives amended by ADR-008
- **ADR-006** — image bytes never route through the model (no base64 in tool args/results)

## Browser automation

Use named Playwright CLI sessions and write browser artifacts to disk:

```
playwright-cli -s=eba open --browser chrome --headed --persistent --profile ./chrome-profile <url>
playwright-cli -s=eba goto <url>
playwright-cli -s=eba snapshot --boxes --filename <path>
playwright-cli -s=eba screenshot --filename <path>
playwright-cli -s=eba screenshot --full-page --filename <path>
playwright-cli -s=eba run-code --filename <script>
playwright-cli -s=eba close
```

Use `state-save` / `state-load` for storage state and `close-all` / `kill-all`
for stale sessions. Persistent profiles are allowed, but only one audit run may
own a profile at a time.

## Capture primitives

Prefer Playwright CLI screenshots for viewport, full-page, and element capture.
Use `run-code` snippets for animation settling, overlay removal, custom clip
regions, own-background frame padding, and restoration. Keep Python/Pillow
`stitch_images`, `crop_image`, and `make_rendition` for post-processing disk
artifacts.

`mss` is historical fallback context from the Claude-in-Chrome path. Do not use
it unless a concrete Playwright CLI limitation is proven and documented.

## Session naming

Name sessions after what they're doing (2-3 words). Ask if unsure.
