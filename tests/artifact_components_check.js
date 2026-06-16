const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_interactions.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/artifact_components.js"));

const components = window.ArtifactPrimitives.artifactComponents;

assert.equal(typeof components.resolveArtifactComponent, "function");
assert.equal(typeof components.artifactRenderKind, "function");
assert.equal(typeof components.artifactStagePlan, "function");
assert.equal(typeof components.artifactReadout, "function");
assert.equal(typeof components.artifactToolbarPlan, "function");

assert.equal(components.resolveArtifactComponent({ type: "image" }).kind, "image");
assert.equal(components.resolveArtifactComponent({ type: "markdown" }).kind, "markdown");
assert.equal(components.resolveArtifactComponent({ type: "json" }).kind, "document");
assert.equal(components.resolveArtifactComponent({ type: "unknown" }).kind, "image");

const imageToolbar = components.artifactToolbarPlan({
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
assert.equal(typeof components.resolveArtifactComponent({ type: "image" }).bindControls, "function");

const markdownToolbar = components.artifactToolbarPlan({
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
assert.equal(typeof components.resolveArtifactComponent({ type: "markdown" }).bindControls, "function");
assert.equal(typeof components.resolveArtifactComponent({ type: "markdown" }).syncControls, "function");

const documentToolbar = components.artifactToolbarPlan({
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
