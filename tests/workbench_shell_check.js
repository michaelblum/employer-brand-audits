const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const html = fs.readFileSync(
  path.join(__dirname, "../scripts/artifact_workbench/index.html"),
  "utf-8",
);
const css = fs.readFileSync(
  path.join(__dirname, "../scripts/artifact_workbench/styles.css"),
  "utf-8",
);
const app = fs.readFileSync(
  path.join(__dirname, "../scripts/artifact_workbench/app.js"),
  "utf-8",
);

assert.match(html, /<button class="overview-button" id="overview"/);
assert.match(html, /<div class="toolbar-middle" id="toolbar-middle">/);
assert.match(html, /<div class="artifact-title" id="artifact-title"><\/div>/);
assert.match(html, /<div class="sibling-nav" id="sibling-nav" aria-label="Artifact navigation">/);
assert.match(html, /<button class="icon-button" id="prev"/);
assert.match(html, /<button class="icon-button" id="next"/);
assert.match(html, /<div class="group toolbar-right">/);
assert.match(html, /id="menu-button"/);
assert.match(html, /id="toggle-sidebar"/);
assert.doesNotMatch(html, /<div class="top-spacer"><\/div>/);
assert.match(css, /\.artifact-subtype-icon\s*\{[\s\S]*cursor:\s*help;/);
assert.doesNotMatch(app, /web-snapshot-preview-body/);
assert.match(app, /function getZoomStateForArtifact/);
assert.match(app, /function setZoomStateForArtifact/);
assert.doesNotMatch(app, /function zoomStateForArtifact/);
assert.doesNotMatch(app, /app\.zoomMode\s*=/);
assert.doesNotMatch(app, /app\.zoomPercent\s*=/);
