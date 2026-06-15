# Scripts DOX

## Purpose

Project command surface, browser/capture helpers, projection code, workflow
artifact workbench implementation, and checked-in Playwright snippets.

## Ownership

- Owns `eba_cli.py`, `eba_control_plane.py`, capture/smoke scripts, projection
  scripts, workbench server/gate scripts, and child script folders.
- Does not own MCP imaging internals or repo-level tests.

## Local Contracts

- Prefer `./eba dev ...` routes for repeated project mechanisms.
- Playwright CLI and thin repo wrappers are the browser boundary.
- Checked-in JavaScript snippets executed through Playwright CLI are allowed
  when CLI commands are not expressive enough.
- Image bytes stay on disk; do not route base64 through model prompts, tool
  arguments, or tool results.
- Viewer code owns interaction, centering, and zoom bounds. Artifact processing
  owns image normalization, rendered-height caps, codec policy, and subtype
  overrides.

## Work Guidance

- Keep command routes typed, small, and honest; do not add routes that are not
  wired or validated.
- Preserve managed `eba-workbench` session behavior: reuse should not resize or
  reposition a human-moved native browser window. Viewport-emulation sync may
  target the current display's visible bounds after the managed window opens or
  moves displays, and must not choose arbitrary dimensions.
- Keep fixture generation separate from generated runtime output.

## Verification

- Run focused syntax checks for changed Python or JavaScript files.
- Run `./eba dev validate` before checkpointing substantive script changes.
- Run `./eba dev demo` and relevant Playwright smoke snippets when workbench
  behavior is tangible.

## Child DOX Index

- `scripts/artifact_primitives/AGENTS.md` - reusable workbench primitives.
- `scripts/playwright-snippets/AGENTS.md` - checked-in snippets for Playwright
  CLI `run-code`.
- `scripts/workflow_artifact_workbench/AGENTS.md` - browser-loaded workbench app
  shell, styles, icons, and page assets.

`scripts/playwright-fixtures/` remains owned here until it grows local rules.
