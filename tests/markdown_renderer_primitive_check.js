const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));

const renderer = window.ArtifactPrimitives.markdown;

assert.equal(typeof renderer.renderMarkdown, "function");
assert.equal(typeof renderer.markdownDiagnostics, "function");

const html = renderer.renderMarkdown([
  "# Intake flow",
  "",
  "```mermaid",
  "flowchart TD",
  "  A --> B",
  "```",
].join("\n"));

assert.match(html, /data-artifact-renderer="mermaid"/);
assert.match(html, /data-mermaid-target/);
assert.doesNotMatch(html, /<figcaption/i);
assert.doesNotMatch(html, /Mermaid diagram/i);
