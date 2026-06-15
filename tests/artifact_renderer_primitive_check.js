const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/artifact_renderer.js"));

const renderer = window.ArtifactPrimitives.artifactRenderer;

assert.equal(typeof renderer.artifactRenderKind, "function");

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
