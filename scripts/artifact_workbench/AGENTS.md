# Artifact Workbench DOX

## Purpose

Browser-loaded artifact workbench app assets: HTML, CSS, icon sprite,
and app shell JavaScript.

## Ownership

- Owns `app.js`, `artifact_toolbar.js`, `artifact_binding.js`, `index.html`,
  `styles.css`, and `icons.svg`.
- Does not own reusable primitives in `scripts/artifact_primitives/`, server
  routes, or Playwright smoke snippets.

## Local Contracts

- Viewer code owns interaction, centering, and zoom bounds.
- Keep app shell responsibilities distinct from reusable artifact primitives.
- The workspace and artifact toolbar are shell-owned mount points. The selected
  artifact component owns type-specific stage, readout, controls, and control
  binding inside those mount points through `scripts/artifacts/`.
- HTML artifacts use the shared document stage and annotation editor; the shell
  may route saved `html_element` anchors to the marker/popover, but HTML
  identity extraction and inspector binding stay with the HTML type/primitive.
- Bounded intake fields are rendered as `bounded_input` interaction overlays
  attached to projected workflow step/input ids. Persist them through the
  workbench state surface as overlay state plus an agent-readable
  `bounded_inputs` summary; do not collapse them into annotation comments.
- Stage-level workflow pairing overlays may visually connect bounded input
  panels to resolved artifact DOM/SVG targets. Keep those pairings selector- and
  anchor-driven through projection data and `scripts/artifacts/core/workflow_pairing.js`;
  do not hardcode Mermaid-generated element ids in the app shell. Render the
  visible chase highlight and connector through the reusable `target_link.js`
  primitive; the shell may execute DOM queries and supply per-instance options
  from projected `target_link` data.
- The stage is the shared vertical scroll boundary for rendered artifacts.
  Document-like artifact surfaces fill the stage height and must not introduce
  nested vertical preview scroll panes. Image artifacts keep zoom behavior and
  center within the stage only when the zoomed image fits without scrollbars.
- `styles.css` owns the static workbench stylesheet, including shared toolbar
  and current type-control classes, until a deliberate per-type CSS asset
  boundary exists. Do not add artifact-type behavior to the shell JavaScript to
  compensate for CSS staying here.
- Keep shared slot rendering generic in this folder; do not hardcode image,
  markdown, or future artifact-type toolbar controls in the app shell.
- Active workbench context may set presentation policy such as
  `artifact_control_policy: read-only` or
  `mermaid_source_visibility: preview-hidden`. The app shell passes those
  policies to artifact components and primitives; do not hardcode the behavior
  to one artifact type or fixture.
- Workbench assets must remain compatible with the server asset manifest and
  stale-server detection.
- `index.html` keeps the artifact type script placeholder; the workbench server
  injects concrete type scripts from `scripts/artifacts/types/manifest.json`.
  Do not hardcode concrete artifact type modules in the app shell or index.

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
- Run `node --check scripts/artifact_workbench/artifact_binding.js`
  and `node tests/artifact_binding_check.js` for artifact binding changes.
- Run `node tests/artifact_registry_check.js` when toolbar ownership or
  artifact component behavior changes.
- Run `./eba dev demo --fixture easy-audit --json` for tangible workbench changes.
- Run relevant Playwright snippets from `scripts/playwright-snippets/` for live
  smoke proof.
- Run `./eba dev validate` before checkpointing substantive workbench changes.

## Child DOX Index

No child AGENTS.md files yet.
