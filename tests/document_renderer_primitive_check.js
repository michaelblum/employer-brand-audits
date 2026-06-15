const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));

const renderer = window.ArtifactPrimitives.document;

[
  "documentReadout",
  "isDocumentArtifact",
  "renderDocumentArtifact",
].forEach((name) => {
  assert.equal(typeof renderer[name], "function", `${name} should be public`);
});

assert.equal(renderer.isDocumentArtifact({ type: "json" }), true);
assert.equal(renderer.isDocumentArtifact({ type: "text" }), true);
assert.equal(renderer.isDocumentArtifact({ type: "log" }), true);
assert.equal(renderer.isDocumentArtifact({ type: "file" }), true);
assert.equal(renderer.isDocumentArtifact({ type: "image" }), false);
assert.equal(renderer.isDocumentArtifact({ type: "markdown" }), false);

assert.equal(
  renderer.documentReadout(
    { type: "json", size_bytes: 42 },
    '{\n  "brand": "Acme"\n}',
  ),
  "json · 3 lines · 42 bytes",
);
assert.equal(renderer.documentReadout({ type: "file" }, ""), "file");
assert.equal(renderer.documentReadout({}, ""), "file");

const jsonContainer = { innerHTML: "" };
assert.deepEqual(
  renderer.renderDocumentArtifact({
    id: "raw-json",
    name: "Raw <JSON>",
    type: "json",
    path: "raw.json",
    mimeType: "application/json",
    sizeBytes: 1536,
    content: '{"z":1,"a":2}',
    url: "/artifact/raw.json",
  }, jsonContainer),
  { ok: true, state: "complete", errorMessage: "" },
);
assert.match(jsonContainer.innerHTML, /data-document-type="json"/);
assert.match(jsonContainer.innerHTML, /Raw &lt;JSON&gt;/);
assert.match(jsonContainer.innerHTML, /1\.5 KB/);
assert.match(jsonContainer.innerHTML, /&quot;z&quot;: 1/);
assert.match(jsonContainer.innerHTML, /Open source file/);

const invalidJsonContainer = { innerHTML: "" };
assert.deepEqual(
  renderer.renderDocumentArtifact({
    id: "bad-json",
    name: "Bad JSON",
    type: "json",
    content: '{"broken"',
  }, invalidJsonContainer),
  { ok: true, state: "complete", errorMessage: "" },
);
assert.match(invalidJsonContainer.innerHTML, /JSON parse error:/);
assert.match(invalidJsonContainer.innerHTML, /\{&quot;broken&quot;/);

const fileContainer = { innerHTML: "" };
assert.deepEqual(
  renderer.renderDocumentArtifact({
    id: "binary",
    name: "Binary",
    type: "file",
    path: "binary.bin",
  }, fileContainer),
  { ok: true, state: "metadata", errorMessage: "" },
);
assert.match(fileContainer.innerHTML, /data-document-type="file"/);
assert.match(fileContainer.innerHTML, /No inline renderer is available/);
