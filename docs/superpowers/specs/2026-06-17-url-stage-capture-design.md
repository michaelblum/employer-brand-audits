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

Primary artifacts:

- `web-snapshot`: the staged page artifact shown in the workbench.
- `page-screenshot`: viewport or full-page image bytes on disk.
- `target-map`: JSON records for hit regions in screenshot coordinate space.
- `visible-text`: text extraction for agent context and user inspection.
- `page-snapshot`: Playwright snapshot or accessibility/box metadata.
- `capture-log`: mechanical trace for debugging failed captures.

The `web-snapshot` artifact links the screenshot and target map instead of
duplicating image bytes or large metadata in model-visible messages.

## Target Map

Each target record stores:

- stable capture coordinates: `{x, y, width, height}` in screenshot coordinate
  space;
- source page URL and viewport metadata;
- human-facing labels: role, accessible name, visible text, title, alt text;
- selector candidates and DOM path hints;
- target kind hints such as `link`, `button`, `input`, `heading`, `section`,
  `image`, or `text`;
- confidence and extraction notes when a target is approximate.

The coordinate record is what makes the overlay durable for the captured
artifact. Selector data is intelligence-mining material for agents that later
operate the live site through Playwright CLI.

## Workbench Behavior

The stage behaves like the current HTML artifact inspector, but resolves
against captured geometry instead of a live same-origin DOM:

- Hovering a target region draws a rect outline over the screenshot.
- Clicking a target region opens the configured overlay workflow.
- Default mode is `annotate`: click creates an annotation anchored to the
  target record and rect.
- Other modes can route clicks to `inspect`, `present`, or future `action`
  behavior without changing the capture format.
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
4. Capture screenshot, visible text, snapshot metadata, and target map files.
5. Write a manifest compatible with the artifact workbench projection.
6. Print the manifest path and, when requested, prepare the managed workbench.

## First Implementation Slice

Build the reusable artifact path before live replay:

1. Add the `stage-url` command and a capture helper module.
2. Add target-map extraction from Playwright CLI `run-code`.
3. Add a `web_snapshot` workbench artifact component that reuses the image
   viewer surface and adds semantic hit testing.
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

- Unit tests for URL stage manifest generation and projection.
- Node checks for the new artifact component and target-map hit testing.
- Playwright CLI smoke against a local fixture URL.
- `./eba dev validate` before checkpointing implementation changes.
