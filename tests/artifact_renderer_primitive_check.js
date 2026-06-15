const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/artifact_renderer.js"));

const renderer = window.ArtifactPrimitives.artifactRenderer;

assert.equal(typeof renderer.artifactRenderKind, "function");
assert.equal(typeof renderer.artifactStagePlan, "function");
assert.equal(typeof renderer.artifactReadout, "function");
assert.equal(typeof renderer.artifactErrorHtml, "function");
assert.equal(typeof renderer.documentLoadPlan, "function");
assert.equal(typeof renderer.documentRenderPayload, "function");

assert.equal(renderer.artifactRenderKind({ type: "markdown" }), "markdown");
assert.equal(renderer.artifactRenderKind({ type: "json" }), "document");
assert.equal(renderer.artifactRenderKind({ type: "text" }), "document");
assert.equal(renderer.artifactRenderKind({ type: "log" }), "document");
assert.equal(renderer.artifactRenderKind({ type: "file" }), "document");
assert.equal(renderer.artifactRenderKind({ type: "image" }), "image");
assert.equal(renderer.artifactRenderKind({ type: "unknown" }), "image");
assert.equal(renderer.artifactRenderKind({}), "image");

assert.equal(
  renderer.artifactRenderKind(
    { type: "pdf" },
    { document: { isDocumentArtifact: () => true } },
  ),
  "document",
);
assert.equal(
  renderer.artifactRenderKind(
    { type: "markdown" },
    { document: { isDocumentArtifact: () => true } },
  ),
  "markdown",
);

assert.deepEqual(
  renderer.artifactStagePlan({ type: "markdown" }),
  {
    renderKind: "markdown",
    stage: { markdownStage: true, resetScroll: false },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      imageControlsDisplay: "none",
      markdownControlsVisible: true,
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
  renderer.artifactStagePlan({ type: "json" }),
  {
    renderKind: "document",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      imageControlsDisplay: "none",
      markdownControlsVisible: false,
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
  renderer.artifactStagePlan({ type: "image" }),
  {
    renderKind: "image",
    stage: { markdownStage: false, resetScroll: true },
    surfaces: {
      imageWrapHidden: false,
      markdownWrapHidden: true,
      imageControlsDisplay: "flex",
      markdownControlsVisible: false,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: null,
      markdownSourceHidden: null,
    },
  },
);

assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "cached", type: "json" },
    { hasCachedContent: true, cachedContent: "{\"ok\":true}", url: "/artifact/cached.json" },
  ),
  { action: "use-cache", content: "{\"ok\":true}" },
);
assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "binary", type: "file" },
    { hasCachedContent: false, cachedContent: "ignored", url: "/artifact/binary.bin" },
  ),
  { action: "use-empty-content", content: "" },
);
assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "raw", type: "json" },
    { hasCachedContent: false, url: "/artifact/raw.json" },
  ),
  {
    action: "fetch-text",
    url: "/artifact/raw.json",
    cache: "no-store",
    errorPrefix: "Artifact fetch failed",
  },
);

assert.deepEqual(
  renderer.documentRenderPayload(
    {
      id: "raw",
      name: "Raw",
      type: "json",
      path: "raw.json",
      mime_type: "application/json",
      size_bytes: 1536,
    },
    { content: "{\"ok\":true}", url: "/artifact/raw.json" },
  ),
  {
    id: "raw",
    name: "Raw",
    type: "json",
    path: "raw.json",
    mime_type: "application/json",
    size_bytes: 1536,
    content: "{\"ok\":true}",
    url: "/artifact/raw.json",
    mimeType: "application/json",
    sizeBytes: 1536,
  },
);
assert.deepEqual(
  renderer.documentRenderPayload(
    {
      id: "camel",
      name: "Camel",
      type: "json",
      mimeType: "application/json",
      sizeBytes: 2048,
    },
    { content: "{\"ok\":true}", url: "/artifact/camel.json" },
  ),
  {
    id: "camel",
    name: "Camel",
    type: "json",
    mimeType: "application/json",
    sizeBytes: 2048,
    content: "{\"ok\":true}",
    url: "/artifact/camel.json",
  },
);

assert.equal(
  renderer.artifactReadout({
    artifact: { type: "image", dimensions: { width: 640, height: 480 } },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "640 x 480 px",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "image" },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "800 x 600 px",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "markdown" },
    markdownContent: "# Heading\n\nBody words",
    markdown: window.ArtifactPrimitives.markdown,
  }),
  "3 lines · 4 words · 1 headings",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "json", size_bytes: 42 },
    documentContent: "{\"ok\":true}",
    document: window.ArtifactPrimitives.document,
  }),
  "json · 1 lines · 42 bytes",
);

assert.equal(
  renderer.artifactErrorHtml({ renderKind: "markdown", error: new Error("Bad <markdown>") }),
  "<p>Failed to load markdown: Bad &lt;markdown&gt;</p>",
);
assert.equal(
  renderer.artifactErrorHtml({ renderKind: "document", error: new Error("Bad <artifact>") }),
  "<p>Failed to load artifact: Bad &lt;artifact&gt;</p>",
);
