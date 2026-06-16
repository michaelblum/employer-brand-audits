# Scripts DOX

## Purpose

Project command surface, browser/capture helpers, projection code, artifact
workbench implementation, and checked-in Playwright snippets.

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
- `./eba sig`, `./eba dev trace`, `./eba dev gh`, and `./eba dev hooks` own the
  repo-private provenance signature surface; keep GitHub prose and commit
  message signing automatic where possible.
- Route routine workbench browser behavior through named management helpers in
  `playwright_cli_workbench_gate.py`; keep focus, maximize, and viewport sync as
  separate operations so tests can guard their side effects.
- Keep fixture generation separate from generated runtime output.

## Verification

- Run focused syntax checks for changed Python or JavaScript files.
- Run `./eba dev validate` before checkpointing substantive script changes.
- Run `./eba dev demo` and relevant Playwright smoke snippets when workbench
  behavior is tangible.

## Child DOX Index

- `scripts/artifacts/AGENTS.md` - artifact-level registry, type components,
  shared artifact helpers, and navigation planning.
- `scripts/artifact_primitives/AGENTS.md` - lower-level workbench renderer and
  interaction primitives.
- `scripts/playwright-snippets/AGENTS.md` - checked-in snippets for Playwright
  CLI `run-code`.
- `scripts/artifact_workbench/AGENTS.md` - browser-loaded workbench app
  shell, styles, icons, and page assets.

`scripts/playwright-fixtures/` remains owned here until it grows local rules.
