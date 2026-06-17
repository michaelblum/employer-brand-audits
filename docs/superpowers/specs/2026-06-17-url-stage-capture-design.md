# URL Stage Capture Design

## Purpose

Create a reusable workbench artifact mode that can load any URL through the
Playwright CLI boundary, freeze the visible page state as a durable artifact,
and let a user communicate intent to an agent by pointing at semantic regions
on that frozen page.

This is not a remote iframe. The stage is a captured visual state plus a
semantic target map. It exists for demos, presentations, playback, and
agent-user intent alignment.

## Core Contract

- The visual artifact is authoritative: a screenshot represents the frozen page
  state the user and agent are discussing.
- The intent spine is primary: annotations and interaction overlays capture the
  user's natural-language intent against regions of that visual state.
- Selector candidates are advisory: selectors, roles, text, labels, and DOM
  paths are evidence and replay hints, not durable truth.
- Playwright CLI remains the only browser engine for page load, capture,
  inspection, and any later replay.
- The workbench must not depend on cross-origin iframe access or remote page
  framing headers.

## Artifact Shape

The reusable capture emits a manifest under:

```text
artifacts/url-stage/<slug>/latest/manifest.json
```

Primary files:

- `web-snapshot`: the staged page artifact shown in the workbench.
- `page-screenshot`: viewport or full-page image bytes on disk.
- `web-snapshot-data`: one canonical JSON file with normalized source trees,
  projection descriptors, derived projections, and curated UI view descriptors.
- `capture-log`: mechanical trace for debugging failed captures.

The workbench projects `web-snapshot` as the primary `type: html`,
`kind: web_snapshot` artifact and `web-snapshot-data` as the single supporting
`kind: web_snapshot_data` JSON artifact. The screenshot remains a disk file
linked from the data object rather than a separate sidebar artifact.

`web-snapshot-data` contains:

- `visual`: screenshot path, dimensions, coordinate space, viewport, document
  size, and capture context;
- `source_trees`: normalized DOM and AX/source-tree slots, with separate trees
  and join links when available instead of pretending the browser gives one
  perfect tree;
- `projection_catalog`: machine-readable projection descriptors;
- `projections`: derived shapes such as target map, visible text, structure,
  and page snapshot;
- `ui_views`: the curated subset of projections exposed as stage toolbar modes;
- `replay_policy`: snapshot replay coordinates are authoritative inside the
  frozen workbench artifact; live-page replay treats selectors and semantics as
  primary and coordinates as advisory.

## Target Map

The target map is a projection inside `web-snapshot-data`, not a separate
artifact. Each target record stores:

- stable capture coordinates: `{x, y, width, height}` in screenshot coordinate
  space;
- source page URL and viewport metadata;
- human-facing labels: role, accessible name, visible text, title, alt text;
- selector candidates and DOM path hints;
- target kind hints such as `link`, `button`, `input`, `heading`, `section`,
  `image`, or `text`;
- confidence and extraction notes when a target is approximate.

The coordinate record is what makes overlays and scripted presentations durable
inside the frozen web snapshot. Selector data is intelligence-mining material
for agents that later operate the live site through Playwright CLI.

## Workbench Behavior

The stage uses the HTML artifact pipeline but renders the synthetic page as the
root stage surface, without the generic document/article wrapper. It resolves
against captured geometry instead of a live remote DOM:

- Hovering a target region draws a rect outline over the screenshot.
- Clicking a target region opens the configured overlay workflow.
- Default mode is `annotate`: click creates an annotation anchored to the
  target record and rect.
- Other modes can route clicks to `inspect`, `present`, or future `action`
  behavior by mapping toolbar modes to `ui_views` in `web-snapshot-data`
  without changing the capture format.
- Saved overlays retain both the region coordinates and the matched target
  record so the intent remains readable even if a later live page changes.

## Command Surface

Initial command:

```bash
./eba dev stage-url <url> --name <slug>
```

Expected behavior:

1. Start or reuse a Playwright CLI session scoped to the capture.
2. Navigate to the URL with deterministic viewport defaults.
3. Settle animations and hide obvious sticky blockers using checked-in snippets.
4. Capture screenshot, visible text, snapshot metadata, and normalized target
   evidence.
5. Write a manifest compatible with the artifact workbench projection.
6. Print the manifest path and, when requested, prepare the managed workbench.

## First Implementation Slice

Build the reusable artifact path before live replay:

1. Add the `stage-url` command and a capture helper module.
2. Add target-map extraction from Playwright CLI `run-code`.
3. Add a `web_snapshot` workbench artifact path that uses synthetic same-origin
   HTML over the screenshot and adds semantic hit testing.
4. Add projection support for URL stage manifests.
5. Add focused tests for manifest shape, projection shape, target-map anchors,
   and a local-fixture live smoke.

## Deferred Work

- Live replay of an overlay action against a fresh page load.
- Multi-step demonstration playback with scripted callouts.
- Authenticated/session-state capture.
- Mobile and responsive capture sets.
- Cross-page intent stories stitched from multiple URL captures.

## Verification

- Unit tests for URL stage manifest generation, web-snapshot data shape, and
  projection.
- Node checks for the new artifact component and target-map hit testing.
- Playwright CLI smoke against a local fixture URL.
- `./eba dev validate` before checkpointing implementation changes.
