# Workflow Artifact Workbench Recalibration

**Date:** 2026-06-12

## Direction

The review workbench should become a renderer over workflow artifact manifests, not a purpose-built viewer for one Playwright public-page matrix. Employer Brand Audit remains the flagship workflow pack, but the durable surface is a workflow artifact workbench that can render steps, artifacts, resource files, facets, slots, and provenance edges from a normalized payload.

This follows the accepted direction in:

- [ADR-001: The Workflow Graph Is The UI](../../decisions/ADR-001-workflow-graph-as-ui.md)
- [ADR-002: Audit Manifest Schema](../../decisions/ADR-002-audit-manifest-schema.md)
- [ADR-004: Layered Artifact DAG](../../decisions/ADR-004-layered-artifact-dag.md)

## Projection Boundary

The workbench should read a normalized workbench payload. Source manifests are adapted into that payload before UI rendering. This keeps the UI aligned to workflow concepts while allowing temporary formats to exist during migration.

The boundary is:

```text
source manifest -> projection adapter -> normalized workbench payload -> renderer
```

For the current branch, the Playwright public-page matrix manifest is a temporary adapter input. It is not the long-term schema and should not define the renderer's vocabulary.

## Viewer And Artifact-Processing Boundary

Viewer configuration owns centering and interactive zoom bounds. The workbench may compute a per-image effective minimum zoom so a tall normalized artifact can fit inside the current stage, and it may enforce configured zoom-out and zoom-in limits so images do not become impractically tiny or extremely magnified.

Artifact processing owns image normalization. Screenshot, crop, stitched-scroll, full-page, and other composed image outputs are normalized before the manifest points the viewer at them. The default normalization policy caps rendered height at 4,000 px, preserves aspect ratio, and applies configurable compression behavior. Artifact subtypes can override that policy without adding subtype-specific viewer logic.

The viewer must not cap rendered height, recompress, resample, or mutate artifact bytes. It only displays the artifact it receives.

## Rendering Primitives Boundary

Artifact-type rendering capabilities that may be reused across surfaces live in
a shared primitive layer, not inside a consuming surface. Use
`scripts/artifact_primitives/` for browser-delivered artifact renderers and
their pinned static dependencies. For Mermaid, the first shared primitive is
`scripts/artifact_primitives/mermaid_renderer.js`.

The review workbench may import or serve these primitives, but
`scripts/review_workbench/` owns only the shell, stage, sidebar, controls,
annotation chrome, and workbench-specific state wiring. Report builders, diff
viewers, composite editors, and future annotation tools should be able to reuse
the same artifact renderer without importing from the review workbench.

Rendering primitives expose small, data-oriented interfaces, accept host-owned
DOM containers, and return explicit render status objects. Vendored browser
dependencies for those primitives live under `scripts/artifact_primitives/vendor/`
as pinned, pre-built static assets; consuming surfaces must not fetch renderer
code from a CDN at runtime.

## Vocabulary

- **Workflow:** A named run or pack with steps and status. For the current matrix adapter, the workflow is the public-page capture matrix.
- **Step:** A unit of work in the workflow graph. The matrix adapter projects a conservative discovery step plus per-page capture steps.
- **Artifact:** A rendered or reviewable output, such as a viewport screenshot, full-page screenshot, element screenshot, markdown review summary, text output, snapshot, or log.
- **Resource:** A source or supporting file that artifacts observe or depend on. Current resources include source URLs and local files.
- **Slot:** A stable role an artifact can fill in the workbench, such as `capture.viewport`, `capture.full_page`, `capture.element`, `page.summary`, or `debug.log`.
- **Facet:** A grouping or filtering axis derived from payload facts. Initial facets are host, page slug, artifact type, artifact kind, and slot.
- **Provenance edge:** A typed relationship between resources, steps, and artifacts. Current matrix edges are mostly placeholder-grade: source URL observed by capture artifacts, step produced artifact, and page source file supports projected page state.

## Normalized Payload Shape

The first normalized payload should distinguish:

- `workflow`: id, name, status, source manifest, and projected steps.
- `resources`: source URLs and local supporting files.
- `artifacts`: reviewable outputs with `slot`, `type`, `kind`, `path`, `mime_type`, `source_page`, and `facets`.
- `artifact_groups`: canonical flat list of projection-only composite review subjects; `facets.composites` was removed in the cleanup after the Mermaid/composite proof because it duplicated the same list.
- `edges`: conservative provenance placeholders such as `depends_on`, `observes`, and `produced_by`.
- `facets`: host and slot indexes for filtering and navigation.

This is deliberately smaller than full ADR-002. It creates a stable workbench render contract without pretending the matrix manifest already satisfies the accepted audit manifest schema.

## Temporary Matrix Adapter

The existing matrix manifest remains supported as an adapter input while the capture pipeline catches up to ADR-002. The adapter should:

- Preserve current artifact ids enough for the existing workbench concepts to map cleanly.
- Project matrix pages into workflow steps and URL resources.
- Project artifact keys into explicit slots.
- Emit empty or placeholder provenance edges where the matrix lacks full parent artifact data.
- Avoid inventing final audit semantics that are not present in the matrix manifest.

## Non-Goals

- Do not rewrite the review workbench UI in this pass.
- Do not move artifact height caps or compression policy into viewer zoom code.
- Do not alter ADR-001, ADR-002, or ADR-004.
- Do not implement the full audit manifest schema in the matrix adapter.
- Do not make the workbench a generic file browser.
- Do not replace the Employer Brand Audit workflow with an abstract demo workflow.
- Do not add direct-manipulation workflow editing.

## Migration Phases

1. **Projection foothold:** Add a matrix-to-workbench projection module and keep the current review server behavior intact.
2. **Server boundary:** Have the review server expose both current `collection` state and projected workflow payload for inspection.
3. **Renderer adoption:** Move the workbench UI from flat collection assumptions toward workflow/artifact/resource/slot/facet concepts.
4. **Audit manifest adapter:** Add an ADR-002 manifest adapter alongside the matrix adapter.
5. **Flagship workflow pack:** Have Employer Brand Audit emit ADR-002-compatible manifests through the normal save path, then treat the matrix adapter as legacy capture support.
6. **Provenance tightening:** Replace placeholder matrix provenance with real artifact-to-artifact parent edges as the capture and analysis layers persist those relationships.
