const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/workflow_sidebar.js"));

const sidebar = window.ArtifactPrimitives.workflowSidebar;

assert.equal(typeof sidebar.visibleArtifactIndexes, "function");
assert.equal(typeof sidebar.renderSidebarHtml, "function");

const artifacts = [
  { id: "hero", name: "Hero <Shot>", path: "hero.png", type: "image" },
  { id: "summary", name: "Summary", path: "summary.md", type: "markdown" },
  { id: "raw", name: "Raw", path: "raw.json", type: "json" },
];
const projectedArtifactsById = {
  hero: {
    id: "hero",
    produced_by_step_id: "capture",
    slot: "landing-page",
    source_page: { slug: "home" },
    status: "ok",
    facets: { artifact_type: "image" },
  },
  summary: {
    id: "summary",
    produced_by_step_id: "analyze",
    slot: "workflow-summary",
    source_page: { slug: "home" },
    status: "ok",
    facets: { artifact_type: "markdown" },
  },
  raw: {
    id: "raw",
    produced_by_step_id: "capture",
    slot: "diagnostics",
    source_page: { slug: "home" },
    status: "warning",
    facets: { artifact_type: "json" },
  },
};
const projectedStepsById = {
  capture: { id: "capture", name: "Capture Page", status: "complete" },
  analyze: { id: "analyze", name: "Analyze Brand", status: "complete" },
};
const projectedSlotsByValue = {
  "landing-page": { value: "landing-page", label: "Landing page" },
  "workflow-summary": { value: "workflow-summary", label: "Workflow summary" },
};
const projectedGroupsById = {
  visible: { id: "visible", label: "Visible bundle", artifact_ids: ["hero", "summary"] },
};
const annotations = {
  hero: [
    {
      id: "note-1",
      comment: "Contrast <needs> work",
      anchor: { type: "image_region", rect: { x: 10, y: 20, width: 30, height: 40 } },
    },
  ],
  summary: [
    {
      id: "note-2",
      comment: "Rewrite heading",
      anchor: {
        type: "text_range",
        start: { line: 2, column: 1 },
        end: { line: 4, column: 1 },
      },
    },
  ],
};

const context = {
  artifacts,
  annotations,
  activeIndex: 1,
  filters: { stepId: "capture", slot: null, compositeId: "visible" },
  projectedArtifactsById,
  projectedStepsById,
  projectedSlotsByValue,
  projectedGroupsById,
  workbenchProjection: {
    workflow: { name: "Easy Audit", status: "ready", steps: [{}, {}] },
  },
  iconHref: (name) => `/icons.svg#${name}`,
};

assert.deepEqual(sidebar.visibleArtifactIndexes(context), [0]);
assert.equal(sidebar.filterSummaryText({ total: 3, visible: 1 }), "1 of 3 artifacts");

const html = sidebar.renderSidebarHtml(context);
assert.match(html, /Easy Audit/);
assert.match(html, /1 of 3 artifacts/);
assert.match(html, /data-filter-kind="clear"/);
assert.match(html, /Hero &lt;Shot&gt;/);
assert.match(html, /Contrast &lt;needs&gt; work/);
assert.match(html, /image 10,20 30x40/);
assert.doesNotMatch(html, /Summary/);

const unfilteredHtml = sidebar.renderSidebarHtml({
  ...context,
  activeIndex: 1,
  filters: { stepId: null, slot: null, compositeId: null },
});
assert.match(unfilteredHtml, /Workflow summary/);
assert.match(unfilteredHtml, /lines 2-4/);
assert.match(unfilteredHtml, /artifact-row active/);
