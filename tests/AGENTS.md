# Tests DOX

## Purpose

Repo-level validation checks for the control plane, easy-audit fixture, artifact
workbench browser control, and JavaScript primitive behavior.

## Ownership

- Owns files under `/tests`.
- Does not own MCP-local pytest tests under `mcp-server/tests`.

## Local Contracts

- Tests should exercise public command surfaces, primitive contracts, and
  workflow behavior without depending on provider-specific browser tools.
- Reusable artifact zoom behavior is covered by
  `tests/zoom_surface_primitive_check.js`; type wiring is covered by the
  artifact registry, binding, toolbar, and browser-control checks.
- Keep browser/workbench tests aligned with Playwright CLI and repo wrappers.
- Avoid broad brittle assertions when a smaller behavior contract is available.

## Work Guidance

- Add regression tests before changing shared behavior.
- Use the MCP venv Python for pytest if the shell Python lacks pytest:
  `mcp-server/.venv/bin/python -m pytest`.
- Keep Node checks runnable without network access.
- Repo-copy fixtures should ignore generated root runtime directories without
  excluding durable source directories that share names, such as
  `scripts/artifacts/`.

## Verification

- Run focused tests for changed behavior.
- Run `./eba dev validate` before checkpointing substantive changes.

## Child DOX Index

No child AGENTS.md files yet.
