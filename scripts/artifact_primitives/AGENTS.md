# Artifact Primitives DOX

## Purpose

Reusable browser-loaded JavaScript primitives for rendering markdown, Mermaid,
images, documents, and interaction overlays.

## Ownership

- Owns files under `scripts/artifact_primitives/`.
- Does not own the workbench app shell in `scripts/workflow_artifact_workbench/`
  artifact-level modules in `scripts/artifacts/`, or Playwright smoke snippets.

## Local Contracts

- Keep primitive APIs narrow and explicit.
- Primitives should not take over app-level routing, persistence, or generated
  artifact ownership unless that boundary is deliberately moved.
- Artifact type registry, toolbar ownership, navigation planning, and shared
  artifact-level helpers live in `scripts/artifacts/`.
- Artifact render controller primitives may own render sequencing, fallback,
  selection, and content-cache decisions; the workbench app shell must still
  execute fetch, persistence, shared image-viewer, and shared markdown side
  effects through explicit callbacks or local state application.
- Markdown/document surface planners may own mode normalization, dirty-state,
  save/revert outcome, and fallback display plans; the workbench app shell must
  still execute DOM updates, focus, network writes, rendering, and toasts.
- Interaction overlay primitives expose subtype models and state helpers;
  controller code owns effect execution and annotation routing.
- Vendor code under `vendor/` should stay isolated from project-authored
  primitives.

## Work Guidance

- Prefer extracting real decision trees over moving callbacks for line-count
  reduction.
- For Issue #12-style primitive extraction, prefer PR-sized responsibility
  boundaries that remove coherent workbench orchestration from the app shell;
  avoid one-helper slices unless they eliminate a real orchestration branch.
- Update primitive checks when public APIs or controller behavior changes.
- Avoid freezing incidental callback order unless order is a contract.

## Verification

- Run `node --check` on changed primitive files.
- Run relevant checks such as `node tests/interaction_overlay_primitive_check.js`,
  `node tests/document_renderer_primitive_check.js`,
  `node tests/artifact_renderer_primitive_check.js`,
  or `node tests/interaction_overlay_controller_check.js`.
- Run `./eba dev validate` before checkpointing substantive primitive changes.

## Child DOX Index

No child AGENTS.md files yet.
