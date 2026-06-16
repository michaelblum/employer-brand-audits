# Artifact Workbench DOX

## Purpose

Browser-loaded artifact workbench app assets: HTML, CSS, icon sprite,
and app shell JavaScript.

## Ownership

- Owns `app.js`, `artifact_toolbar.js`, `index.html`, `styles.css`, and
  `icons.svg`.
- Does not own reusable primitives in `scripts/artifact_primitives/`, server
  routes, or Playwright smoke snippets.

## Local Contracts

- Viewer code owns interaction, centering, and zoom bounds.
- Keep app shell responsibilities distinct from reusable artifact primitives.
- The workspace and artifact toolbar are shell-owned mount points. The selected
  artifact component owns type-specific stage, readout, controls, and control
  binding inside those mount points through `scripts/artifacts/`.
- Keep shared slot rendering generic in this folder; do not hardcode image,
  markdown, or future artifact-type toolbar controls in the app shell.
- Workbench assets must remain compatible with the server asset manifest and
  stale-server detection.

## Work Guidance

- When reducing `app.js`, move coherent responsibilities with tests rather than
  spreading state across anonymous callbacks.
- Preserve keyboard/mouse interaction behavior when extracting controllers or
  primitives.
- Keep visible UI text concise and operational.

## Verification

- Run `node --check scripts/artifact_workbench/app.js` for app changes.
- Run `node --check scripts/artifact_workbench/artifact_toolbar.js`
  and `node tests/artifact_toolbar_check.js` for toolbar changes.
- Run `node tests/artifact_registry_check.js` when toolbar ownership or
  artifact component behavior changes.
- Run `./eba dev demo --fixture easy-audit --json` for tangible workbench changes.
- Run relevant Playwright snippets from `scripts/playwright-snippets/` for live
  smoke proof.
- Run `./eba dev validate` before checkpointing substantive workbench changes.

## Child DOX Index

No child AGENTS.md files yet.
