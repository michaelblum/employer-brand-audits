const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {};

require(path.join(__dirname, "../scripts/artifact_workbench/artifact_toolbar.js"));

const toolbar = window.WorkbenchArtifactToolbar;

assert.equal(typeof toolbar.renderToolbarHtml, "function");
assert.equal(typeof toolbar.mountToolbar, "function");

const source = require("node:fs").readFileSync(
  path.join(__dirname, "../scripts/artifact_workbench/artifact_toolbar.js"),
  "utf-8",
);
assert.doesNotMatch(source, /renderImageZoomControls|renderMarkdownControls/);
assert.doesNotMatch(source, /image-controls|markdown-controls|zoom-control/);

const imageHtml = toolbar.renderToolbarHtml({
  kind: "image",
  readout: [
    { id: "image-dimensions", label: "Dimensions", value: "1000 x 720 px" },
  ],
  controls: [
    {
      id: "image-zoom",
      html: '<div class="image-controls" id="image-controls"><div class="zoom-control" id="zoom-control"><div class="zoom-steps"><button id="zoom-in"></button><button id="zoom-out"></button></div></div></div>',
    },
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

const emptyReadoutHtml = toolbar.renderToolbarHtml({
  kind: "image",
  readout: [
    { id: "image-dimensions", label: "Dimensions", value: "" },
  ],
  controls: [],
});
assert.match(emptyReadoutHtml, /id="artifact-readout"/);
assert.doesNotMatch(emptyReadoutHtml, /data-readout-id="image-dimensions"/);
assert.doesNotMatch(emptyReadoutHtml, /title="Dimensions:/);

const markdownHtml = toolbar.renderToolbarHtml({
  kind: "markdown",
  readout: [
    { id: "markdown-diagnostics", label: "Markdown", value: "3 lines · 4 words · 1 headings" },
  ],
  controls: [
    {
      id: "markdown-controls",
      html: '<div class="markdown-controls" id="markdown-controls"><button id="markdown-preview-mode"></button><button id="markdown-source-mode"></button><button id="markdown-save"></button></div>',
    },
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
