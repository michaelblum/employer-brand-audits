# Scripts DOX

## Purpose

Project command surface, browser/capture helpers, projection code, artifact
workbench implementation, and checked-in Playwright snippets.

## Ownership

- Owns `eba_cli.py`, `eba_control_plane.py`, capture/smoke scripts, projection
  scripts, bounded-input helpers, workbench server/gate scripts, and child
  script folders.
- Does not own MCP imaging internals or repo-level tests.

## Local Contracts

- Prefer `./eba dev ...` routes for repeated project mechanisms.
- Playwright CLI and thin repo wrappers are the browser boundary.
- Checked-in JavaScript snippets executed through Playwright CLI are allowed
  when CLI commands are not expressive enough.
- Image bytes stay on disk; do not route base64 through model prompts, tool
  arguments, or tool results.
- Viewer code owns interaction, centering, and zoom bounds. Artifact processing
  owns image normalization, rendered-height caps, codec policy, and subtype
  overrides.
- `./eba dev stage-url <url>` captures a live URL through the Playwright CLI
  boundary into `artifacts/url-stage/<slug>/latest/manifest.json`. It writes a
  disk screenshot, one canonical `web-snapshot-data.json`, a capture log, and a
  same-origin synthetic `web-snapshot.html`.
- URL-stage capture treats the screenshot as the proof boundary. Page settling,
  obscuring-element hiding, page snapshotting, visible-text extraction, and
  blueprint extraction are bounded best-effort steps; full-page screenshot
  failure falls back to a viewport screenshot before the capture is considered
  failed.
- URL-stage projection emits the staged page as `type: html`,
  `kind: web_snapshot` plus one supporting `kind: web_snapshot_data` JSON
  artifact; the app shell must not need URL-stage-specific component
  registration. Target-map rects stay in screenshot coordinate space inside the
  data file. Selector candidates remain advisory replay/mining hints, while
  annotations and overlays are the natural-language intent spine. Web-snapshot
  artifacts declare their default zoom policy with `facets.zoom_default`.
- URL-stage support files such as `page_screenshot` and `capture_log` project as
  file resources for provenance/debugging, not as workbench-visible sidebar
  artifacts.
- Generated URL-stage web-snapshot proxy targets stay transparent until
  hover/focus-visible, then show an animated chase-gradient border without
  changing target geometry or screenshot pixels.
- `workbench_bounded_input.py` owns bounded workflow-input projection
  definitions and saved-state sanitization helpers. Projection code delegates
  definition creation there; the workbench server delegates bounded-input state
  cleaning and summaries there while keeping annotation cleaning local.
- `scripts/artifacts/core/bounded_input_controls.js` owns browser-side bounded
  input control value resolution, HTML rendering, and control event wiring.
  The workbench app shell still owns overlay persistence, sync calls, and
  lifecycle scheduling.
- `scripts/artifact_primitives/zoom_surface.js` owns reusable artifact zoom
  defaults, fit calculations, clamping, image width scaling, and
  transform-based zoom application. `scripts/artifacts/core/zoom_controls.js`
  owns the shared browser toolbar controls for artifact zoom.
- Artifact type modules load through `scripts/artifacts/types/manifest.json`.
  Server assets, rendered workbench HTML, and validation commands should read
  that manifest instead of hard-coding concrete type script files.
- The workbench server's mutating local HTTP endpoints must reject browser
  cross-origin writes, bound request bodies, return clean JSON client errors,
  and send `X-Content-Type-Options: nosniff` on typed responses.
- `./eba dev demo --fixture publication-pipeline` generates a deterministic
  publication-pipeline ADR-002 manifest from tracked KILOS data and fixture
  records. It must not depend on local-only `reference_publications/` files.
- Publication-pipeline manifests start with `p0-pipeline-intake`, a
  workbench-visible `pipeline_intake` artifact that records the client,
  objective, source seeds, competitors, ontology, desired outputs, and review
  requirements driving downstream records.
- `./eba dev demo --fixture segment-tvp-audit` generates a deterministic
  segment-specific TVP ADR-002 manifest from the tracked ADT reference profile
  and KILOS data. It must support arbitrary project profiles without inheriting
  ADT competitor labels, job URLs, or social-source defaults.
- `./eba dev demo --fixture competitor-messaging-workbook` generates a
  deterministic workbook-normalization ADR-002 manifest from the tracked
  HarbourVest workbook reference profile. It models effective sheet ranges,
  wide matrix cells, evidence cells, partner organizations, and partner
  activations without depending on local-only workbook files at runtime.
- `./eba dev demo --fixture dei-competitor-audit` generates a deterministic DEI
  competitor-audit ADR-002 manifest from the tracked HarbourVest reference
  profile. It models deck extraction, DEI activations, inclusion philosophies,
  partner organizations, coverage gaps, benchmark sources, and deck/L4 views.
- `scripts/publication_pipeline_fixture.py --project-profile <profile.json>`
  generates the generic EVP client immersion and competitor messaging audit
  shape for an arbitrary company profile: client plus competitors, report
  outline, source roster, capture pack, KILOS evidence matrix, survey signals,
  review snapshots, derived analysis findings, and report/deck/workbook/L4
  views. The bundled Northside seed is a tracked reference profile under
  `data/publication-pipeline-profiles/`, not a hard-coded business
  requirement.
- `scripts/publication_pipeline_fixture.py --url-stage-manifest <manifest>` may
  be repeated to import one or more existing URL-stage capture manifests as the
  publication capture-pack sources while preserving screenshot, text, and
  web-snapshot data paths on disk. `--url-stage-entity-id <entity-id>` may also
  be repeated once per manifest to pin each imported source to an entity. When
  URL-stage manifests are imported, `source-roster.json` is derived from the
  imported capture-pack sources so roster entities and source URLs match the
  evidence lineage. Imported sources without explicit entity IDs use neutral
  `source-<slug>` entity IDs inferred from URL-stage slugs instead of borrowing
  demo client or competitor IDs.

## Work Guidance

- Keep command routes typed, small, and honest; do not add routes that are not
  wired or validated.
- `./eba sig`, `./eba dev trace`, `./eba dev gh`, and `./eba dev hooks` own the
  repo-private provenance signature surface; keep GitHub prose and commit
  message signing automatic where possible.
- Route routine workbench browser behavior through named management helpers in
  `playwright_cli_workbench_gate.py`; keep tab cleanup, focus, maximize, and
  explicit viewport resize as separate operations so tests can guard their side
  effects. The default headed workbench uses the browser's native viewport;
  fixed Playwright viewport sizes belong to explicit/capture paths. Managed
  browser commands must be bounded and leave a `workbench-browser.log` trail on
  timeout.
- Keep fixture generation separate from generated runtime output.
- The deterministic easy-audit fixture treats `l4-final-report` as the single
  L4 report artifact and projects it as HTML. Keep Mermaid/markdown smoke
  coverage on markdown artifacts such as `l0-intake-flow`, not by restoring a
  markdown report duplicate.
- Keep URL-stage capture fixtures deterministic and local. Public URLs may be
  used manually, but validation should rely on the checked-in
  `scripts/playwright-fixtures/url-stage-basic.html` fixture.
- Keep public-site capture resilient to real-world page behavior such as
  infinite animations, slow semantic extraction, sticky overlays, and oversized
  full-page screenshots.
- URL-stage `web-snapshot-data.json` should carry data and projection
  descriptors, not executable transformation code. User-facing UI views are a
  curated subset of machine projections.

## Verification

- Run focused syntax checks for changed Python or JavaScript files.
- Run `./eba dev validate` before checkpointing substantive script changes.
- For workbench server hardening changes, run
  `python3 tests/test_workbench_server_hardening.py`.
- For workbench shell/toolbar structure changes, run
  `node tests/workbench_shell_check.js`.
- For reusable zoom behavior, run `node tests/zoom_surface_primitive_check.js`
  plus the relevant artifact registry/binding checks.
- Run `./eba dev demo` and relevant Playwright smoke snippets when workbench
  behavior is tangible. For browser-loaded workbench asset or app-shell changes,
  prefer `./eba dev workbench live-smoke --fixture easy-audit --json` as the
  bounded live runtime check.
- For URL-stage changes, run `python3 tests/test_url_stage_capture.py`,
  `python3 scripts/workbench_projection_shape_check.py`, `node --check
  scripts/playwright-snippets/artifact-workbench-web-snapshot-check.js`, and a
  live smoke of `artifact-workbench-web-snapshot-check.js` against a generated
  local fixture manifest.

## Child DOX Index

- `scripts/artifacts/AGENTS.md` - artifact-level registry, type components,
  shared artifact helpers, and navigation planning.
- `scripts/artifact_primitives/AGENTS.md` - lower-level workbench renderer and
  interaction primitives.
- `scripts/playwright-snippets/AGENTS.md` - checked-in snippets for Playwright
  CLI `run-code`.
- `scripts/artifact_workbench/AGENTS.md` - browser-loaded workbench app
  shell, styles, icons, and page assets.

`scripts/playwright-fixtures/` remains owned here until it grows local rules.
