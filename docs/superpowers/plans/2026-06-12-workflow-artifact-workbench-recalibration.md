# Workflow Artifact Workbench Recalibration

**Date:** 2026-06-12

## Direction

The current workflow artifact workbench implementation should become a renderer over
workflow artifact manifests, not a purpose-built viewer for one Playwright
public-page matrix. Employer Brand Audit remains the flagship workflow pack,
but the durable product and architecture direction is a workflow artifact
workbench that can render steps, artifacts, resource files, facets, slots, and
provenance edges from a normalized payload.

This is a viewing, editing, creation, guided-input, bounded-mutation,
composite-drill-down, and agent-human collaboration surface over workflow
artifacts. "Review workbench" remains acceptable as the current implementation
or demo-surface alias. It should not be used as the canonical product concept
because it pulls future work toward report review only.

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

## Naming And Alias Boundary

- **Workflow artifact workbench** is the canonical direction for docs, plans,
  issues, and future architecture.
- **Workflow artifact workbench implementation** lives in
  `scripts/workflow_artifact_workbench/`. The earlier static-surface directory
  name has been retired.
- Legacy lower-level server and gate filenames remain compatibility wrappers
  around the current static surface and Playwright CLI validation path. They
  should not define artifact-model terminology.
- Do not rename CLI commands, branches, issues, or the repository as part of
  this recalibration plan. Propose those as separate migration work with their
  own compatibility and automation checks.

## Rendering Primitives Boundary

Artifact-type rendering capabilities that may be reused across surfaces live in
a shared primitive layer, not inside a consuming surface. Use
`scripts/artifact_primitives/` for browser-delivered artifact renderers and
their pinned static dependencies. For Mermaid, the first shared primitive is
`scripts/artifact_primitives/mermaid_renderer.js`.

The workflow artifact workbench may import or serve these primitives, but
`scripts/workflow_artifact_workbench/` owns only the shell, stage, sidebar, controls,
interaction or annotation chrome, and workbench-specific state wiring. Report
builders, diff viewers, composite editors, and future overlay tools should be
able to reuse the same artifact renderer without importing from the workflow
artifact workbench shell.

Rendering primitives expose small, data-oriented interfaces, accept host-owned
DOM containers, and return explicit render status objects. Vendored browser
dependencies for those primitives live under `scripts/artifact_primitives/vendor/`
as pinned, pre-built static assets; consuming surfaces must not fetch renderer
code from a CDN at runtime.

## Vocabulary

- **Workflow artifact workbench:** The broad surface for operating on workflow
  artifacts through viewing, editing, creation, guided input, bounded mutation,
  composite drill-down, and agent-human collaboration.
- **Subject:** The workflow, step, artifact, resource, or composite grouping
  currently in focus. This mirrors the reusable workbench-subject idea from the
  Agent OS pattern index without importing that system as authority.
- **Artifact view:** A renderer for one artifact or composite subject. The host
  owns shell, controls, and state wiring; primitives own artifact-type rendering.
- **Projection:** A generated normalized surface derived from durable source
  data. Projection output may add navigation, facets, groups, and display
  affordances without pretending they are already durable manifest records.
- **Primitive:** A reusable renderer or interaction unit with a stable,
  data-oriented interface and host-owned DOM container.
- **Interaction overlay:** The umbrella layer for comments, selections, guided
  prompts, bounded inputs, callouts, and agent-mediated edit requests anchored
  to a subject or artifact view.
- **Annotation:** One subtype of interaction overlay. Do not use annotation as
  the umbrella term for every overlay or input affordance.
- **Bounded mutation:** A user request anchored to subject/artifact context and
  executed by the agent or tooling. It is not free direct manipulation of the
  underlying workflow graph.
- **Composite subject:** A projection-only grouping or later durable bundle with
  drill-down semantics over existing artifacts and provenance edges.
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
- `artifact_groups`: canonical flat list of projection-only composite subjects; `facets.composites` was removed in the cleanup after the Mermaid/composite proof because it duplicated the same list.
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

- Do not rewrite the workflow artifact workbench UI in this pass.
- Do not rename CLI commands, branches, issues, or the repository in this pass.
- Do not update GitHub issues or labels without explicit approval.
- Do not move artifact height caps or compression policy into viewer zoom code.
- Do not alter ADR-001, ADR-002, or ADR-004.
- Do not implement the full audit manifest schema in the matrix adapter.
- Do not make the workbench a generic file browser.
- Do not replace the Employer Brand Audit workflow with an abstract demo workflow.
- Do not add direct-manipulation workflow editing.

## Migration Phases

1. **Projection foothold:** Add a matrix-to-workbench projection module and keep the current review server implementation behavior intact.
2. **Server boundary:** Have the current review server implementation expose both current `collection` state and projected workflow payload for inspection.
3. **Renderer adoption:** Move the workbench UI from flat collection assumptions toward workflow/artifact/resource/slot/facet concepts.
4. **Audit manifest adapter:** Add an ADR-002 manifest adapter alongside the matrix adapter.
5. **Flagship workflow pack:** Have Employer Brand Audit emit ADR-002-compatible manifests through the normal save path, then treat the matrix adapter as legacy capture support.
6. **Provenance tightening:** Replace placeholder matrix provenance with real artifact-to-artifact parent edges as the capture and analysis layers persist those relationships.

## Documentation Drift Inventory

This inventory records stale or overloaded terminology without authorizing broad
edits. Keep changes scoped and verify the current repo gate before modifying
ADRs, specs, SOP, issue trackers, or module names.

- `AGENTS.md` may describe the local surface as a workflow artifact workbench because that
  is the current implementation name. Pair that with the alias boundary above so
  startup instructions do not redefine the product concept.
- `docs/superpowers/specs/2026-06-10-employer-brand-audit-design.md` remains the
  approved flagship workflow spec. It can keep employer-brand and report
  language, but future workbench docs should not infer that the workbench is
  limited to employer-brand report review.
- `docs/superpowers/plans/2026-06-11-capture-and-image-pipeline.md` contains a
  superseded Claude-in-Chrome spike. Treat its Python image-operation work as
  reusable and its browser spike as historical only.
- ADR-001 uses annotation language for guided tours. Read that as an
  interaction-overlay subtype unless a later ADR intentionally narrows the
  overlay model back to comments only.

## Tracker Alignment Guidance

This section is local guidance only. Verify live GitHub issue state before any
remote mutation, and do not mutate issues, labels, PRs, or projects without
explicit approval.

- **Issue #8:** Current state is closed while it still carries `status:active`.
  Remove the active label or create/link a new open successor epic before future
  agents treat it as the active workstream.
- **Issue #2:** Keep as the broad V2 collaborative-surface vision. When a
  current open workbench epic exists, link it from #2 and translate older
  overlay language into the interaction-overlay vocabulary above.
- **Issue #10:** Title is already aligned around workbench render paths, but the
  body still frames the frontend as a workflow artifact workbench. Prefer wording around
  artifact views, normalized projection fields, and workflow artifact workbench
  shell adoption.
- **Issue #4:** The Claude-in-Chrome `computer`/`zoom` spike is superseded by
  ADR-008 and the current Playwright CLI boundary. Close as historical or
  rewrite only if a concrete Playwright-only capture validation remains.
- **Issue #1:** The Playwright MCP fallback framing is stale relative to the
  Playwright CLI browser engine. Close as obsolete or rewrite under the
  Playwright CLI persistent-profile posture if that work is still needed.
