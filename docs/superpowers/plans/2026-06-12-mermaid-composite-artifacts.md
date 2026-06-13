# Mermaid And Composite Artifact Planning

**Date:** 2026-06-12

## Direction

Mermaid and composite artifacts should extend the workflow artifact workbench
through the normalized projection boundary first. Do not promote either one into
the ADR-002 audit manifest schema until real audit outputs need durable,
pipeline-written records.

This plan extends the direction in
[Workflow Artifact Workbench Recalibration](2026-06-12-workflow-artifact-workbench-recalibration.md)
and is constrained by:

- [ADR-001: The Workflow Graph Is The UI](../../decisions/ADR-001-workflow-graph-as-ui.md)
- [ADR-002: Audit Manifest Schema](../../decisions/ADR-002-audit-manifest-schema.md)
- [ADR-004: Layered Artifact DAG](../../decisions/ADR-004-layered-artifact-dag.md)
- [ADR-007: Eager Per-Artifact Extraction + Lazy Confluence Re-Inference](../../decisions/ADR-007-eager-extraction-lazy-reinference.md)

## Boundaries

- Python remains routing, orchestration, data prep, and disk IO only.
- Presentation lives in `scripts/review_workbench/` static assets.
- Repeated UI markup becomes a primitive before its second use.
- Mermaid rendering must preserve source deterministically; a failed render
  should keep the source inspectable and annotatable.
- The first composite model is a projection relationship, not a new workflow
  engine, file browser, or direct-manipulation builder.
- Browser proof uses Playwright CLI through the repo wrappers.

## Mermaid Model

Treat Mermaid as a capability facet over text-like artifacts before treating it
as a canonical artifact type.

Initial projection shape:

- Markdown artifacts that contain Mermaid fences remain `type: "markdown"` and
  gain a derived facet such as `diagram_kind: "mermaid"` plus the `render`
  capability.
- Standalone `.mmd` files may project as a workbench-only diagram artifact with
  `type: "diagram"`, `kind: "mermaid"`, `slot: "diagram.mermaid"`, and
  `mime_type: "text/vnd.mermaid"` if a fixture needs a standalone diagram.
- The ADR-002 manifest should not gain a `mermaid` or `diagram` artifact type
  in this branch unless an ADR or follow-up plan explicitly accepts that schema
  extension.

Recommended capabilities:

- Markdown with Mermaid fence: `view`, `edit`, `annotate`, `render`.
- Standalone Mermaid source: `view`, `edit`, `annotate`, `render`, `export`.
- Rendered preview export is a later capability; do not imply export until a
  disk artifact is actually written and recorded.

## Mermaid Rendering Surface

Use the markdown workbench path first. The preview/source toggle already matches
the needed mental model: source is the durable artifact, preview is a projection.

Renderer contract:

- Markdown rendering detects fenced code blocks with language `mermaid`.
- The generated DOM keeps source line attributes for annotation mooring.
- The Mermaid preview is rendered by a static workbench JS primitive, not by
  Python-generated HTML.
- The renderer shows four states: source preserved, render pending, render
  complete, render error.
- Invalid Mermaid source should produce an inline error state without losing
  edit or annotation capability.

Agent-OS pattern to copy, not import: preserve Mermaid source in a figure-like
block with `data-markdown-diagram="mermaid"` and source stored in an attribute
or child source block; keep renderer execution separate from Markdown parsing.

## Annotation Anchor Model

Source anchors are first-class for Mermaid V1.

- Mermaid inside Markdown uses existing `text_range` anchors with
  `coordinate_space: "markdown_source"` and source line numbers.
- Standalone Mermaid may use `text_range` with
  `coordinate_space: "mermaid_source"`.
- Rendered node or edge anchors are a later additive anchor type, for example
  `diagram_node` or `diagram_edge`, only after the renderer can provide stable
  ids from Mermaid source.
- Do not introduce direct graph editing or drag-to-rewire behavior. Selection
  can create comments; mutations remain agent-mediated.

## Composite Artifact Model

Composite artifacts should begin as projection edges and facet groups.

Initial projection shape:

- A composite is a review subject generated from existing artifacts and edges.
- The projection may expose `artifact_groups` or `facets.composites` with:
  `id`, `label`, `artifact_ids`, `edge_ids`, `source`, and optional `slot`.
- Edges should use explicit relationship kinds such as `contains`,
  `composes`, `derived_from`, or `supports`; avoid overloading `parent_ids`
  when the source manifest does not contain real artifact provenance.
- If a composite is persisted as a durable file later, then it becomes a normal
  ADR-002 artifact with `produced_by_step_id` and artifact-only `parent_ids`.

Do not model composites as workflow steps unless they represent real units of
pipeline work. A bundle view over existing artifacts is a subject/facet of the
workbench, not a new step.

## Composite Navigation

Prefer shallow navigation first:

- Header breadcrumb: workflow -> step or composite -> artifact.
- Sidebar grouping by step, slot, and composite facet.
- Artifact rows remain leaf rows until real workflow tree data justifies nested
  rows.

Avoid deep nested sidebars in this pass. The current matrix data does not yet
carry enough hierarchy to make nested navigation honest.

## Minimum Proof Path

1. Add a fixture that includes a Markdown artifact with a Mermaid fenced block.
2. Extend projection output with derived Mermaid capability/facet metadata.
3. Add a small static renderer primitive under `scripts/review_workbench/`.
4. Add workbench UI for Mermaid preview/source/error states without Python
   inline HTML or SVG.
5. Add a Playwright CLI smoke snippet that verifies:
   - the Mermaid row appears with the expected projection metadata;
   - preview/source mode keeps source editable;
   - invalid source produces an error state;
   - source-line annotation still works;
   - icon use remains through `/assets/review-workbench-icons.svg`.
6. For composites, start with projection-only groups and a sidebar/header
   proof before creating any persistent composite artifact.

## Non-Goals

- Do not change accepted ADRs in this branch.
- Do not make Mermaid a direct-manipulation flow editor.
- Do not fetch Mermaid rendering code from a CDN at runtime.
- Do not add inline HTML or SVG to Python handlers.
- Do not expand `app.js` with a second large rendering subsystem before
  extracting a primitive.
- Do not claim ADR-002 schema support for composites until the capture or
  analysis pipeline writes real parent artifact relationships.

## Implementation Order

1. Projection metadata for Mermaid capability/facets.
2. Static Mermaid renderer primitive and Markdown integration.
3. Workbench controls and error state.
4. Playwright CLI smoke for Mermaid.
5. Projection-only composite groups.
6. Composite navigation smoke.
7. ADR-002 adapter or schema extension only after real audit manifests need it.
