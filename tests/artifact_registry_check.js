const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_interactions.js"));
require(path.join(__dirname, "../scripts/artifacts/core/artifact_common.js"));
require(path.join(__dirname, "../scripts/artifacts/types/image_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/types/markdown_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/types/document_artifact.js"));
require(path.join(__dirname, "../scripts/artifacts/artifact_registry.js"));

const registry = window.Artifacts.registry;

assert.equal(typeof registry.resolveArtifactComponent, "function");
assert.equal(typeof registry.artifactRenderKind, "function");
assert.equal(typeof registry.artifactStagePlan, "function");
assert.equal(typeof registry.artifactReadout, "function");
assert.equal(typeof registry.artifactToolbarPlan, "function");

assert.equal(registry.resolveArtifactComponent({ type: "image" }).kind, "image");
assert.equal(registry.resolveArtifactComponent({ type: "markdown" }).kind, "markdown");
assert.equal(registry.resolveArtifactComponent({ type: "json" }).kind, "document");
assert.equal(registry.resolveArtifactComponent({ type: "unknown" }).kind, "image");
assert.deepEqual(registry.resolveArtifactComponent({ type: "image" }).capabilities, {
  imageRegionAnnotations: true,
  imageZoom: true,
});
assert.deepEqual(registry.resolveArtifactComponent({ type: "markdown" }).capabilities, {
  markdownEditing: true,
  textRangeAnnotations: true,
});
assert.deepEqual(registry.resolveArtifactComponent({ type: "json" }).capabilities, {});

assert.equal(registry.artifactRenderKind({ type: "markdown" }), "markdown");
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
    stage: { markdownStage: true, resetScroll: false },
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
assert.equal(imageToolbar.controls[0].id, "image-zoom");
assert.match(imageToolbar.controls[0].html, /id="image-controls"/);
assert.match(imageToolbar.controls[0].html, /id="zoom-in"[\s\S]*id="zoom-out"/);
assert.doesNotMatch(imageToolbar.controls[0].html, /markdown-controls/);
assert.equal(typeof registry.resolveArtifactComponent({ type: "image" }).bindControls, "function");

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
