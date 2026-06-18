const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/html_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_interactions.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/zoom_surface.js"));
require(path.join(__dirname, "../scripts/artifacts/core/artifact_common.js"));
require(path.join(__dirname, "../scripts/artifacts/core/zoom_controls.js"));
require(path.join(__dirname, "../scripts/artifacts/artifact_registry.js"));

assert.equal(typeof window.Artifacts.registerType, "function");
assert.equal(typeof window.Artifacts.registry.registeredArtifactTypes, "function");
assert.deepEqual(window.Artifacts.registry.registeredArtifactTypes(), []);

require(path.join(__dirname, "../scripts/artifacts/types/image_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/types/markdown_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/types/html_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/types/document_artifact.js"));

const registry = window.Artifacts.registry;

assert.equal(typeof registry.resolveArtifactComponent, "function");
assert.equal(typeof registry.artifactRenderKind, "function");
assert.equal(typeof registry.artifactStagePlan, "function");
assert.equal(typeof registry.artifactReadout, "function");
assert.equal(typeof registry.artifactToolbarPlan, "function");
assert.deepEqual(registry.registeredArtifactTypes().map((component) => component.kind), [
  "markdown",
  "html",
  "document",
  "image",
]);

assert.equal(registry.resolveArtifactComponent({ type: "image" }).kind, "image");
assert.equal(registry.resolveArtifactComponent({ type: "markdown" }).kind, "markdown");
assert.equal(registry.resolveArtifactComponent({ type: "html" }).kind, "html");
assert.equal(registry.resolveArtifactComponent({ type: "json" }).kind, "document");
assert.equal(registry.resolveArtifactComponent({ type: "unknown" }).kind, "image");
assert.equal(
  registry.resolveArtifactComponent({ type: "image" }),
  registry.registeredArtifactTypes().find((component) => component.kind === "image"),
);
assert.equal(typeof registry.resolveArtifactComponent({ type: "html" }).capabilities, "function");
assert.equal(typeof registry.artifactCapabilities, "function");
assert.deepEqual(registry.artifactCapabilities({ type: "image" }), {
  artifactZoom: true,
  imageRegionAnnotations: true,
  imageZoom: true,
});
assert.deepEqual(registry.artifactCapabilities({ type: "markdown" }), {
  markdownEditing: true,
  textRangeAnnotations: true,
});
assert.deepEqual(registry.artifactCapabilities({ type: "html" }), {
  htmlElementAnnotations: true,
});
assert.deepEqual(registry.artifactCapabilities({ type: "html", kind: "web_snapshot" }), {
  artifactZoom: true,
  htmlElementAnnotations: true,
});
assert.deepEqual(registry.artifactCapabilities({ type: "json" }), {});

assert.equal(registry.artifactRenderKind({ type: "markdown" }), "markdown");
assert.equal(registry.artifactRenderKind({ type: "html" }), "html");
assert.equal(registry.artifactRenderKind({ type: "json" }), "document");
assert.equal(registry.artifactRenderKind({ type: "text" }), "document");
assert.equal(registry.artifactRenderKind({ type: "log" }), "document");
assert.equal(registry.artifactRenderKind({ type: "file" }), "document");
assert.equal(registry.artifactRenderKind({ type: "image" }), "image");
assert.equal(registry.artifactRenderKind({ type: "unknown" }), "image");
assert.equal(registry.artifactRenderKind({}), "image");

assert.equal(
  registry.artifactRenderKind(
    { type: "pdf" },
    { document: { isDocumentArtifact: () => true } },
  ),
  "document",
);
assert.equal(
  registry.artifactRenderKind(
    { type: "markdown" },
    { document: { isDocumentArtifact: () => true } },
  ),
  "markdown",
);

assert.deepEqual(
  registry.artifactStagePlan({ type: "markdown" }),
  {
    renderKind: "markdown",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: null,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: null,
      markdownSourceHidden: null,
    },
  },
);
assert.deepEqual(
  registry.artifactStagePlan({ type: "json" }),
  {
    renderKind: "document",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
    },
  },
);
assert.deepEqual(
  registry.artifactStagePlan({ type: "html" }),
  {
    renderKind: "html",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
    },
  },
);
assert.deepEqual(
  registry.artifactStagePlan({ type: "html", kind: "web_snapshot" }),
  {
    renderKind: "html",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
      markdownPreviewBodyClass: "web-snapshot-preview-body",
    },
  },
);
assert.deepEqual(
  registry.artifactStagePlan({ type: "image" }),
  {
    renderKind: "image",
    stage: { markdownStage: false, resetScroll: true },
    surfaces: {
      imageWrapHidden: false,
      markdownWrapHidden: true,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: null,
      markdownSourceHidden: null,
    },
  },
);

const imageToolbar = registry.artifactToolbarPlan({
  artifact: { id: "image", type: "image", dimensions: { width: 1000, height: 720 } },
});
assert.equal(imageToolbar.kind, "image");
assert.deepEqual(imageToolbar.readout, [
  { id: "image-dimensions", label: "Dimensions", value: "1000 x 720 px" },
]);
assert.equal(imageToolbar.controls.length, 1);
assert.equal(imageToolbar.controls[0].id, "artifact-zoom");
assert.match(imageToolbar.controls[0].html, /id="artifact-zoom-controls"/);
assert.match(imageToolbar.controls[0].html, /id="zoom-in"[\s\S]*id="zoom-out"/);
assert.doesNotMatch(imageToolbar.controls[0].html, /markdown-controls/);
assert.equal(typeof registry.resolveArtifactComponent({ type: "image" }).bindControls, "function");

const readOnlyImageToolbar = registry.artifactToolbarPlan({
  artifact: { id: "image", type: "image", dimensions: { width: 1000, height: 720 } },
  controlPolicy: "read-only",
});
assert.equal(readOnlyImageToolbar.kind, "image");
assert.deepEqual(readOnlyImageToolbar.readout, imageToolbar.readout);
assert.equal(readOnlyImageToolbar.controls.length, 1);
assert.equal(readOnlyImageToolbar.controls[0].id, "artifact-zoom");

const markdownToolbar = registry.artifactToolbarPlan({
  artifact: { id: "md", type: "markdown" },
  markdownContentById: { md: "# Heading\n\nBody words" },
  markdown: window.ArtifactPrimitives.markdown,
});
assert.equal(markdownToolbar.kind, "markdown");
assert.deepEqual(markdownToolbar.readout, [
  { id: "markdown-diagnostics", label: "Markdown", value: "3 lines · 4 words · 1 headings" },
]);
assert.equal(markdownToolbar.controls.length, 1);
assert.equal(markdownToolbar.controls[0].id, "markdown-controls");
assert.match(markdownToolbar.controls[0].html, /id="markdown-controls"/);
assert.match(markdownToolbar.controls[0].html, /id="markdown-save"/);
assert.doesNotMatch(markdownToolbar.controls[0].html, /image-controls/);
assert.equal(typeof registry.resolveArtifactComponent({ type: "markdown" }).bindControls, "function");
assert.equal(typeof registry.resolveArtifactComponent({ type: "markdown" }).syncControls, "function");

const readOnlyMarkdownToolbar = registry.artifactToolbarPlan({
  artifact: { id: "md", type: "markdown" },
  controlPolicy: "read-only",
  markdownContentById: { md: "# Heading\n\nBody words" },
  markdown: window.ArtifactPrimitives.markdown,
});
assert.equal(readOnlyMarkdownToolbar.kind, "markdown");
assert.deepEqual(readOnlyMarkdownToolbar.readout, markdownToolbar.readout);
assert.deepEqual(readOnlyMarkdownToolbar.controls, []);

const htmlToolbar = registry.artifactToolbarPlan({
  artifact: { id: "html", type: "html", size_bytes: 2048 },
  documentContentById: { html: "<main><section><a>Apply now</a></section></main>" },
  html: window.ArtifactPrimitives.html,
});
assert.equal(htmlToolbar.kind, "html");
assert.deepEqual(htmlToolbar.readout, [
  { id: "html-summary", label: "HTML", value: "3 elements · 2048 bytes" },
]);
assert.deepEqual(htmlToolbar.controls, []);
assert.equal(typeof registry.resolveArtifactComponent({ type: "html" }).bindInspector, "function");

const webSnapshotToolbar = registry.artifactToolbarPlan({
  artifact: {
    id: "web",
    type: "html",
    kind: "web_snapshot",
    size_bytes: 15335,
    facets: {
      target_count: 19,
      visual_dimensions: { width: 1365, height: 1228 },
      zoom_default: "stage-fit",
    },
  },
  documentContentById: { web: "<main></main>" },
  html: window.ArtifactPrimitives.html,
});
assert.equal(webSnapshotToolbar.kind, "html");
assert.deepEqual(webSnapshotToolbar.readout, [
  { id: "html-summary", label: "HTML", value: "19 targets · 1365 x 1228 px · 15335 bytes" },
]);
assert.equal(webSnapshotToolbar.controls.length, 1);
assert.equal(webSnapshotToolbar.controls[0].id, "artifact-zoom");
assert.match(webSnapshotToolbar.controls[0].html, /id="artifact-zoom-controls"/);
assert.doesNotMatch(webSnapshotToolbar.controls[0].html, /id="image-controls"/);

const readOnlyWebSnapshotToolbar = registry.artifactToolbarPlan({
  artifact: {
    id: "web",
    type: "html",
    kind: "web_snapshot",
    facets: { target_count: 19, visual_dimensions: { width: 1365, height: 1228 } },
  },
  controlPolicy: "read-only",
  documentContentById: { web: "<main></main>" },
  html: window.ArtifactPrimitives.html,
});
assert.equal(readOnlyWebSnapshotToolbar.controls.length, 1);
assert.equal(readOnlyWebSnapshotToolbar.controls[0].id, "artifact-zoom");

assert.equal(
  registry.artifactReadout({
    artifact: { type: "image", dimensions: { width: 640, height: 480 } },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "640 x 480 px",
);
assert.equal(
  registry.artifactReadout({
    artifact: { type: "image" },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "800 x 600 px",
);
assert.equal(
  registry.artifactReadout({
    artifact: { type: "markdown" },
    markdownContent: "# Heading\n\nBody words",
    markdown: window.ArtifactPrimitives.markdown,
  }),
  "3 lines · 4 words · 1 headings",
);
assert.equal(
  registry.artifactReadout({
    artifact: { type: "html", size_bytes: 2048 },
    documentContent: "<main><section><a>Apply now</a></section></main>",
    html: window.ArtifactPrimitives.html,
  }),
  "3 elements · 2048 bytes",
);
assert.equal(
  registry.artifactReadout({
    artifact: {
      type: "html",
      kind: "web_snapshot",
      size_bytes: 15335,
      facets: {
        artifact_kind: "web_snapshot",
        target_count: 19,
        visual_dimensions: { width: 1365, height: 1228 },
      },
    },
    documentContent: "<main></main>",
    html: window.ArtifactPrimitives.html,
  }),
  "19 targets · 1365 x 1228 px · 15335 bytes",
);
assert.equal(
  registry.artifactReadout({
    artifact: { type: "json", size_bytes: 42 },
    documentContent: "{\"ok\":true}",
    document: window.ArtifactPrimitives.document,
  }),
  "json · 1 lines · 42 bytes",
);

const documentToolbar = registry.artifactToolbarPlan({
  artifact: { id: "doc", type: "json", size_bytes: 42 },
  documentContentById: { doc: "{\"ok\":true}" },
  document: window.ArtifactPrimitives.document,
});
assert.deepEqual(documentToolbar, {
  kind: "document",
  readout: [
    { id: "document-summary", label: "Document", value: "json · 1 lines · 42 bytes" },
  ],
  controls: [],
});
