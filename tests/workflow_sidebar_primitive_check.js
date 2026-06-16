const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/workflow_sidebar.js"));

const sidebar = window.ArtifactPrimitives.workflowSidebar;

assert.equal(typeof sidebar.visibleArtifactIndexes, "function");
assert.equal(typeof sidebar.renderSidebarHtml, "function");
assert.equal(typeof sidebar.workflowFilterPlan, "function");
assert.equal(typeof sidebar.workflowMovePlan, "function");
assert.equal(typeof sidebar.renderArtifactTitleHtml, "function");
assert.equal(typeof sidebar.renderOverviewHtml, "function");
assert.equal(typeof sidebar.workflowProjectionModel, "function");
assert.equal(typeof sidebar.workflowSidebarContext, "function");

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
const projectedWithoutSourcePage = {
  id: "raw",
  produced_by_step_id: "capture",
  slot: "diagnostics",
  status: "warning",
  facets: { artifact_type: "json" },
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
const interactionOverlays = [
  {
    id: "note-1",
    subtype: "annotation",
    subject: { kind: "artifact", id: "hero" },
    body: { kind: "comment", text: "Contrast <needs> work" },
    anchor: { type: "image_region", rect: { x: 10, y: 20, width: 30, height: 40 } },
  },
  {
    id: "note-2",
    subtype: "annotation",
    subject: { kind: "artifact", id: "summary" },
    body: { kind: "comment", text: "Rewrite heading" },
    anchor: {
      type: "text_range",
      start: { line: 2, column: 1 },
      end: { line: 4, column: 1 },
    },
  },
];

const projectionPayload = {
  workflow: {
    name: "Easy Audit",
    status: "ready",
    steps: [
      { id: "capture", name: "Capture Page", status: "complete" },
      { id: "analyze", name: "Analyze Brand", status: "complete" },
      { name: "Ignored missing id" },
    ],
  },
  artifacts: [
    projectedArtifactsById.hero,
    projectedArtifactsById.summary,
    { produced_by_step_id: "ignored" },
  ],
  facets: {
    slots: [
      projectedSlotsByValue["landing-page"],
      projectedSlotsByValue["workflow-summary"],
      { label: "Ignored missing value" },
    ],
  },
  artifact_groups: [
    projectedGroupsById.visible,
    { label: "Ignored missing id", artifact_ids: ["hero"] },
  ],
};

const projectionModel = sidebar.workflowProjectionModel(projectionPayload);
assert.deepEqual(Object.keys(projectionModel.projectedArtifactsById).sort(), ["hero", "summary"]);
assert.deepEqual(Object.keys(projectionModel.projectedStepsById).sort(), ["analyze", "capture"]);
assert.deepEqual(Object.keys(projectionModel.projectedSlotsByValue).sort(), ["landing-page", "workflow-summary"]);
assert.deepEqual(Object.keys(projectionModel.projectedGroupsById).sort(), ["visible"]);
assert.equal(projectionModel.workbenchProjection, projectionPayload);
assert.deepEqual(sidebar.workflowProjectionModel(null), {
  workbenchProjection: null,
  projectedArtifactsById: {},
  projectedStepsById: {},
  projectedSlotsByValue: {},
  projectedGroupsById: {},
});

const context = {
  artifacts,
  interactionOverlays,
  contexts: [
    { manifest: "artifacts/easy-audit/latest/manifest.json", label: "Easy Audit", subtitle: "Acme Robotics", active: true },
    { manifest: "artifacts/playwright-cli-public-page-matrix/latest/manifest.json", label: "Public Matrix", subtitle: "4 pages", active: false },
  ],
  context: { manifest: "artifacts/easy-audit/latest/manifest.json" },
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
assert.deepEqual(
  sidebar.workflowSidebarContext({
    artifacts,
    interactionOverlays,
    contexts: context.contexts,
    context: context.context,
    activeIndex: 1,
    filters: { stepId: null, slot: null, compositeId: null },
    projectionModel,
    iconHref: context.iconHref,
  }),
  {
    artifacts,
    interactionOverlays,
    contexts: context.contexts,
    context: context.context,
    activeIndex: 1,
    filters: { stepId: null, slot: null, compositeId: null },
    iconHref: context.iconHref,
    projectedArtifactsById: projectionModel.projectedArtifactsById,
    projectedGroupsById: projectionModel.projectedGroupsById,
    projectedSlotsByValue: projectionModel.projectedSlotsByValue,
    projectedStepsById: projectionModel.projectedStepsById,
    workbenchProjection: projectionPayload,
  },
);

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

const noEmptyProjectionPillHtml = sidebar.renderSidebarHtml({
  ...context,
  artifacts: [{ id: "raw", name: "Raw", path: "raw.json", type: "json" }],
  projectedArtifactsById: { raw: projectedWithoutSourcePage },
  activeIndex: 0,
  filters: { stepId: null, slot: null, compositeId: null },
});
assert.match(noEmptyProjectionPillHtml, /diagnostics/);
assert.match(noEmptyProjectionPillHtml, /complete/);
assert.doesNotMatch(noEmptyProjectionPillHtml, /<span><\/span>/);

assert.deepEqual(
  sidebar.workflowFilterPlan({
    ...context,
    activeIndex: 1,
    filters: { stepId: null, slot: null, compositeId: "visible" },
    filterKind: "step",
    filterValue: "capture",
  }),
  {
    filters: { stepId: "capture", slot: null, compositeId: "visible" },
    activeIndex: 0,
  },
);
assert.deepEqual(
  sidebar.workflowFilterPlan({
    ...context,
    activeIndex: 0,
    filters: { stepId: "capture", slot: "diagnostics", compositeId: "visible" },
    filterKind: "clear",
  }),
  {
    filters: { stepId: null, slot: null, compositeId: null },
    activeIndex: 0,
  },
);
assert.deepEqual(
  sidebar.workflowFilterPlan({
    ...context,
    activeIndex: 0,
    filters: { stepId: "capture", slot: null, compositeId: null },
    filterKind: "step",
    filterValue: "capture",
  }),
  {
    filters: { stepId: null, slot: null, compositeId: null },
    activeIndex: 0,
  },
);

assert.deepEqual(
  sidebar.workflowMovePlan({
    ...context,
    activeIndex: 0,
    filters: { stepId: null, slot: null, compositeId: null },
    delta: -1,
  }),
  { activeIndex: 2 },
);
assert.deepEqual(
  sidebar.workflowMovePlan({
    ...context,
    activeIndex: 99,
    filters: { stepId: "capture", slot: null, compositeId: null },
    delta: 1,
  }),
  { activeIndex: 2 },
);
assert.deepEqual(
  sidebar.workflowMovePlan({
    ...context,
    artifacts: [],
    activeIndex: 0,
    filters: { stepId: null, slot: null, compositeId: null },
    delta: 1,
  }),
  { activeIndex: 0 },
);

const titleHtml = sidebar.renderArtifactTitleHtml({
  ...context,
  activeIndex: 1,
  filters: { stepId: null, slot: null, compositeId: "visible" },
  formatTime: () => "now",
});
assert.match(titleHtml, /Easy Audit -&gt; Visible bundle/);
assert.match(titleHtml, /Summary/);
assert.match(titleHtml, /Workflow summary/);
assert.match(titleHtml, /\(now\)/);

const overviewHtml = sidebar.renderOverviewHtml({
  ...context,
  activeIndex: 2,
  filters: { stepId: null, slot: null, compositeId: null },
});
assert.match(overviewHtml, /data-context-select/);
assert.match(overviewHtml, /Easy Audit/);
assert.match(overviewHtml, /Public Matrix/);
assert.match(overviewHtml, /data-index="0"/);
assert.match(overviewHtml, /Hero &lt;Shot&gt;/);
assert.match(overviewHtml, /data-index="2"/);
assert.match(overviewHtml, /artifact-option active/);
assert.match(overviewHtml, /diagnostics · home · complete · raw\.json/);
