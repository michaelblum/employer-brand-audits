const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {};

require(path.join(__dirname, "../scripts/workflow_artifact_workbench/artifact_toolbar.js"));

const toolbar = window.WorkbenchArtifactToolbar;

assert.equal(typeof toolbar.renderToolbarHtml, "function");
assert.equal(typeof toolbar.mountToolbar, "function");

const imageHtml = toolbar.renderToolbarHtml({
  kind: "image",
  readout: [
    { id: "image-dimensions", label: "Dimensions", value: "1000 x 720 px" },
  ],
  controls: [
    { id: "image-zoom", kind: "image-zoom" },
  ],
});
assert.match(imageHtml, /id="artifact-readout"/);
assert.match(imageHtml, /data-slot="readout"/);
assert.match(imageHtml, /data-readout-id="image-dimensions"/);
assert.match(imageHtml, /1000 x 720 px/);
assert.match(imageHtml, /id="artifact-controls"/);
assert.match(imageHtml, /data-slot="controls"/);
assert.match(imageHtml, /id="image-controls"/);
assert.match(imageHtml, /id="zoom-control"/);
assert.match(imageHtml, /class="zoom-steps"/);
assert.match(imageHtml, /id="zoom-in"[\s\S]*id="zoom-out"/);
assert.doesNotMatch(imageHtml, /markdown-controls/);

const markdownHtml = toolbar.renderToolbarHtml({
  kind: "markdown",
  readout: [
    { id: "markdown-diagnostics", label: "Markdown", value: "3 lines · 4 words · 1 headings" },
  ],
  controls: [
    { id: "markdown-controls", kind: "markdown-controls" },
  ],
});
assert.match(markdownHtml, /id="markdown-controls"/);
assert.match(markdownHtml, /id="markdown-preview-mode"/);
assert.match(markdownHtml, /id="markdown-source-mode"/);
assert.match(markdownHtml, /id="markdown-save"/);
assert.doesNotMatch(markdownHtml, /image-controls/);

const documentHtml = toolbar.renderToolbarHtml({
  kind: "document",
  readout: [
    { id: "document-summary", label: "Document", value: "json · 1 lines · 42 bytes" },
  ],
  controls: [],
});
assert.match(documentHtml, /json · 1 lines · 42 bytes/);
assert.doesNotMatch(documentHtml, /image-controls|markdown-controls|zoom-control/);
