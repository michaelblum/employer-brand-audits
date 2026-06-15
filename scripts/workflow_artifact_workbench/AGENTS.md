# Workflow Artifact Workbench DOX

## Purpose

Browser-loaded workflow artifact workbench app assets: HTML, CSS, icon sprite,
and app shell JavaScript.

## Ownership

- Owns `app.js`, `index.html`, `styles.css`, and `icons.svg`.
- Does not own reusable primitives in `scripts/artifact_primitives/`, server
  routes, or Playwright smoke snippets.

## Local Contracts

- Viewer code owns interaction, centering, and zoom bounds.
- Keep app shell responsibilities distinct from reusable artifact primitives.
- The managed workbench should reuse an existing `eba-workbench` browser session
  without resizing or repositioning it.
- Workbench assets must remain compatible with the server asset manifest and
  stale-server detection.

## Work Guidance

- When reducing `app.js`, move coherent responsibilities with tests rather than
  spreading state across anonymous callbacks.
- Preserve keyboard/mouse interaction behavior when extracting controllers or
  primitives.
- Keep visible UI text concise and operational.

## Verification

- Run `node --check scripts/workflow_artifact_workbench/app.js` for app changes.
- Run `./eba dev demo --fixture easy-audit --json` for tangible workbench changes.
- Run relevant Playwright snippets from `scripts/playwright-snippets/` for live
  smoke proof.
- Run `./eba dev validate` before checkpointing substantive workbench changes.

## Child DOX Index

No child AGENTS.md files yet.
