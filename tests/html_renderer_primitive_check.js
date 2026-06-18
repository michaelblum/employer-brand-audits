const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/html_renderer.js"));

const renderer = window.ArtifactPrimitives.html;

[
  "displayRectForHtmlElementAnchor",
  "htmlElementAnchorForElement",
  "htmlReadout",
  "isHtmlArtifact",
  "renderHtmlArtifact",
].forEach((name) => {
  assert.equal(typeof renderer[name], "function", `${name} should be public`);
});

assert.equal(renderer.isHtmlArtifact({ type: "html" }), true);
assert.equal(renderer.isHtmlArtifact({ mime_type: "text/html" }), true);
assert.equal(renderer.isHtmlArtifact({ path: "report.html" }), true);
assert.equal(renderer.isHtmlArtifact({ type: "markdown", path: "report.md" }), false);

assert.equal(
  renderer.htmlReadout(
    { type: "html", size_bytes: 2048 },
    "<main><section><a>Apply now</a></section></main>",
  ),
  "3 elements · 2048 bytes",
);
assert.equal(
  renderer.htmlReadout(
    { type: "html" },
    "<main><br><hr><input></main>",
  ),
  "4 elements",
);

const iframe = { srcdoc: "", title: "", setAttribute(name, value) { this[name] = value; } };
const container = {
  innerHTML: "",
  querySelector(selector) {
    return selector === "[data-html-frame]" ? iframe : null;
  },
};
assert.deepEqual(
  renderer.renderHtmlArtifact({
    id: "report",
    name: "Audit <Report>",
    type: "html",
    content: "<!doctype html><html><body><h1>Report</h1><script>window.bad = true</script></body></html>",
    url: "/artifact/report.html",
  }, container),
  { ok: true, state: "complete", errorMessage: "" },
);
assert.match(container.innerHTML, /data-artifact-renderer="html"/);
assert.match(container.innerHTML, /sandbox="allow-same-origin"/);
assert.match(container.innerHTML, /scrolling="no"/);
assert.doesNotMatch(container.innerHTML, /allow-scripts/);
assert.match(container.innerHTML, /Audit &lt;Report&gt;/);
assert.doesNotMatch(container.innerHTML, /html-artifact-meta/);
assert.doesNotMatch(container.innerHTML, /text\/html/);
assert.doesNotMatch(container.innerHTML, /2048 bytes/);
assert.doesNotMatch(container.innerHTML, /report\.html/);
assert.match(iframe.srcdoc, /<h1>Report<\/h1>/);
assert.equal(iframe.scrolling, "no");

const webSnapshotIframe = { srcdoc: "", title: "", style: {}, setAttribute(name, value) { this[name] = value; } };
const webSnapshotContainer = {
  innerHTML: "",
  querySelector(selector) {
    return selector === "[data-html-frame]" ? webSnapshotIframe : null;
  },
};
assert.deepEqual(
  renderer.renderHtmlArtifact({
    id: "web-snapshot",
    name: "Careers web snapshot",
    type: "html",
    kind: "web_snapshot",
    content: "<!doctype html><html><body><div data-web-snapshot-stage=\"true\"></div></body></html>",
    facets: {
      visual_dimensions: { width: 1200, height: 1600 },
    },
  }, webSnapshotContainer),
  { ok: true, state: "complete", errorMessage: "" },
);
assert.match(webSnapshotContainer.innerHTML, /data-artifact-renderer="html"/);
assert.match(webSnapshotContainer.innerHTML, /data-web-snapshot-root="true"/);
assert.match(webSnapshotContainer.innerHTML, /data-zoom-wrap="web-snapshot"/);
assert.match(webSnapshotContainer.innerHTML, /data-zoom-target="web-snapshot-frame"/);
assert.doesNotMatch(webSnapshotContainer.innerHTML, /<article class="html-artifact"/);
assert.doesNotMatch(webSnapshotContainer.innerHTML, /<header>/);
assert.match(webSnapshotContainer.innerHTML, /width:1200px/);
assert.match(webSnapshotContainer.innerHTML, /height:1600px/);
assert.match(webSnapshotIframe.srcdoc, /data-web-snapshot-stage="true"/);

function classList(className) {
  return String(className || "").split(/\s+/).filter(Boolean);
}

function fakeElement({
  tagName,
  id = "",
  className = "",
  textContent = "",
  attrs = {},
  rect = { left: 0, top: 0, width: 1, height: 1, right: 1, bottom: 1 },
  parentElement = null,
} = {}) {
  return {
    tagName,
    id,
    className,
    classList: classList(className),
    textContent,
    parentElement,
    children: [],
    getAttribute(name) {
      if (name === "id") return id || null;
      if (name === "class") return className || null;
      return Object.prototype.hasOwnProperty.call(attrs, name) ? attrs[name] : null;
    },
    getBoundingClientRect() {
      return rect;
    },
  };
}

const section = fakeElement({
  tagName: "SECTION",
  id: "jobs",
  className: "panel",
  textContent: "Robotics roles",
  rect: { left: 4, top: 5, width: 400, height: 200, right: 404, bottom: 205 },
});
const link = fakeElement({
  tagName: "A",
  id: "apply",
  className: "cta primary",
  textContent: "Apply now for robotics roles",
  attrs: { role: "button", "aria-label": "Apply now" },
  rect: { left: 20, top: 30, width: 140, height: 44, right: 160, bottom: 74 },
  parentElement: section,
});
section.children = [link];

const anchor = renderer.htmlElementAnchorForElement(link, {
  sourceUrl: "https://acme.example/careers",
});
assert.equal(anchor.type, "html_element");
assert.equal(anchor.coordinate_space, "html_document");
assert.equal(anchor.tag, "a");
assert.equal(anchor.id, "apply");
assert.deepEqual(anchor.classes, ["cta", "primary"]);
assert.equal(anchor.role, "button");
assert.equal(anchor.accessible_name, "Apply now");
assert.equal(anchor.text, "Apply now for robotics roles");
assert.deepEqual(anchor.rect, { x: 20, y: 30, width: 140, height: 44 });
assert.deepEqual(anchor.selector_candidates.slice(0, 2), ["#apply", "a#apply.cta.primary"]);
assert.deepEqual(anchor.ancestor_trail, [
  { tag: "section", id: "jobs", classes: ["panel"] },
]);
assert.equal(anchor.source_url, "https://acme.example/careers");

const webTarget = fakeElement({
  tagName: "BUTTON",
  className: "web-target",
  textContent: "",
  attrs: {
    "data-web-target-id": "target-7",
    "data-web-target": JSON.stringify({
      id: "target-7",
      label: "Apply now",
      role: "link",
      tag: "a",
      target_kind: "link",
      rect: { x: 140, y: 260, width: 220, height: 52 },
      selector_candidates: ["#apply", "a.primary"],
    }),
  },
  rect: { left: 140, top: 260, width: 220, height: 52, right: 360, bottom: 312 },
});

const webTargetAnchor = renderer.htmlElementAnchorForElement(webTarget, {
  sourceUrl: "https://acme.example/careers",
});
assert.equal(webTargetAnchor.web_target_id, "target-7");
assert.equal(webTargetAnchor.target_kind, "link");
assert.deepEqual(webTargetAnchor.screenshot_rect, { x: 140, y: 260, width: 220, height: 52 });
assert.deepEqual(webTargetAnchor.target_map_selector_candidates, ["#apply", "a.primary"]);
assert.equal(webTargetAnchor.selector_candidates[0], '[data-web-target-id="target-7"]');
assert.equal(webTargetAnchor.selector_candidates[1], 'button[data-web-target-id="target-7"]');

assert.deepEqual(
  renderer.displayRectForHtmlElementAnchor({
    anchor,
    frameEl: { getBoundingClientRect: () => ({ left: 100, top: 200 }) },
    wrapEl: { getBoundingClientRect: () => ({ left: 80, top: 150 }) },
  }),
  { x: 40, y: 80, width: 140, height: 44 },
);
assert.deepEqual(
  renderer.displayRectForHtmlElementAnchor({
    anchor,
    frameEl: {
      offsetWidth: 1000,
      offsetHeight: 500,
      style: {},
      getBoundingClientRect: () => ({ left: 100, top: 200, width: 500, height: 250 }),
    },
    wrapEl: { getBoundingClientRect: () => ({ left: 80, top: 150 }) },
  }),
  { x: 30, y: 65, width: 70, height: 22 },
);
