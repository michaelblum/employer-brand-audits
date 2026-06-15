# Artifact Primitives DOX

## Purpose

Reusable browser-loaded JavaScript primitives for rendering workflow artifacts,
markdown, Mermaid, images, sidebars, and interaction overlays.

## Ownership

- Owns files under `scripts/artifact_primitives/`.
- Does not own the workbench app shell in `scripts/workflow_artifact_workbench/`
  or Playwright smoke snippets.

## Local Contracts

- Keep primitive APIs narrow and explicit.
- Primitives should not take over app-level routing, persistence, or generated
  artifact ownership unless that boundary is deliberately moved.
- Interaction overlay primitives expose subtype models and state helpers;
  controller code owns effect execution and annotation routing.
- Vendor code under `vendor/` should stay isolated from project-authored
  primitives.

## Work Guidance

- Prefer extracting real decision trees over moving callbacks for line-count
  reduction.
- Update primitive checks when public APIs or controller behavior changes.
- Avoid freezing incidental callback order unless order is a contract.

## Verification

- Run `node --check` on changed primitive files.
- Run relevant checks such as `node tests/interaction_overlay_primitive_check.js`,
  `node tests/document_renderer_primitive_check.js`,
  `node tests/artifact_renderer_primitive_check.js`,
  `node tests/interaction_overlay_controller_check.js`, or
  `node tests/workflow_sidebar_primitive_check.js`.
- Run `./eba dev validate` before checkpointing substantive primitive changes.

## Child DOX Index

No child AGENTS.md files yet.
