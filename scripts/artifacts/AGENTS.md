# Artifacts DOX

## Purpose

Artifact-level browser modules for the workbench: shared artifact helpers,
artifact type components, artifact navigation, and the artifact registry.

## Ownership

- Owns files under `scripts/artifacts/`.
- Does not own low-level rendering primitives in `scripts/artifact_primitives/`,
  the workbench app shell, server routes, or Playwright smoke snippets.

## Local Contracts

- `core/` owns shared artifact helpers that are not specific to one artifact
  type.
- `core/bounded_input_controls.js` owns browser-side bounded-input control
  rendering, select-menu behavior, and control value extraction. The app shell
  still owns persisted overlay state and network sync.
- `core/workflow_pairing.js` owns pure workflow-pairing selection helpers:
  bounded-input definition selection, selector normalization, DOM-anchor
  shaping, and target-link option selection. The workbench app shell still owns
  DOM queries, lifecycle scheduling, and effect execution.
- `core/zoom_controls.js` owns shared artifact zoom toolbar HTML, event
  binding, and input syncing. Artifact types decide whether zoom controls are
  present and provide the zoom behavior hooks.
- `types/` owns artifact type components such as image, markdown, HTML,
  document, and future variants.
- `types/manifest.json` owns deterministic browser load order for artifact
  type modules.
- `navigation/` owns artifact list/tree/filter/navigation planning for the
  workbench, including the sidebar artifact-summary model and rendering
  contract.
- `artifact_registry.js` owns `registerType` and resolves registered artifact
  types; keep it small and free of concrete artifact type lists.
- Add type-specific workspace, stage, readout, toolbar, and control-binding
  behavior to the owning type module, not to the app shell or registry.
- Type modules that support zoom expose `artifactZoom` capability plus
  component hooks such as `applyZoom`, `smartFit`, `stageFitZoom`,
  `updateZoomSurface`, and `defaultZoomState`; the app shell routes generic
  zoom actions through those hooks.
- Type modules self-register with ordering and fallback metadata while keeping
  compatibility aliases on `window.Artifacts.types`.
- Type modules may emit class hooks for controls, but the static stylesheet
  currently stays in `scripts/artifact_workbench/styles.css`; do not duplicate
  per-type CSS here until a CSS asset boundary is deliberately introduced.
- Type toolbar plans must respect context control policy from the app shell.
  `controlPolicy: "read-only"` suppresses mutating controls without changing
  the artifact renderer, readout, or selected artifact type. View-only controls
  such as artifact zoom may opt in with `readOnlyAllowed`.
- Keep broad artifact abstractions here. Keep parser/viewer internals in
  `scripts/artifact_primitives/` until deliberately migrated.

## Work Guidance

- Prefer folders that describe artifact roles: `core`, `types`, `navigation`,
  and future composition/variant boundaries.
- Avoid grab-bag modules. If a file starts owning shared helpers plus multiple
  artifact types plus registry behavior, split it before it grows.
- Preserve compatibility with the workbench asset manifest when adding browser
  modules.
- Add new artifact type scripts to `types/manifest.json` so server assets,
  rendered HTML, and validation stay in sync.

## Verification

- Run `node --check` on changed artifact modules.
- Run relevant checks such as `node tests/artifact_registry_check.js` or
  `node tests/artifact_navigator_check.js`.
- Run `./eba dev validate` before checkpointing substantive artifact changes.

## Child DOX Index

No child AGENTS.md files yet.
