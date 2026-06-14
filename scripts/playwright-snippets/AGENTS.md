# Playwright Snippets DOX

## Purpose

Checked-in JavaScript snippets executed through the repo Playwright CLI wrapper
for capture, page preparation, extraction, and workbench smoke checks.

## Ownership

- Owns files under `scripts/playwright-snippets/`.
- Does not own the Playwright CLI wrapper implementation or workbench app code.

## Local Contracts

- Snippets must run through Playwright CLI or repo wrappers, not provider-specific
  browser-control tools.
- Snippets may inspect or manipulate browser pages but must keep image bytes on
  disk.
- Snippets used as smoke checks should return small structured results.

## Work Guidance

- Keep snippets deterministic and session-aware.
- Prefer clear DOM queries and explicit error messages over broad timeouts.
- Update the related workbench or capture tests when smoke semantics change.

## Verification

- Run `node --check` on changed snippets.
- For workbench snippets, run through
  `python3 scripts/playwright_cli_browser.py run-code --session eba-workbench <snippet>`
  after `./eba dev demo` prepares the surface.

## Child DOX Index

No child AGENTS.md files yet.
