const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/document_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/markdown_renderer.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/artifact_components.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/artifact_renderer.js"));

const renderer = window.ArtifactPrimitives.artifactRenderer;

assert.equal(typeof renderer.artifactRenderKind, "function");
assert.equal(typeof renderer.artifactStagePlan, "function");
assert.equal(typeof renderer.artifactReadout, "function");
assert.equal(typeof renderer.artifactReadoutPlan, "function");
assert.equal(typeof renderer.artifactToolbarPlan, "function");
assert.equal(typeof renderer.artifactErrorHtml, "function");
assert.equal(typeof renderer.artifactSelectionPlan, "function");
assert.equal(typeof renderer.documentLoadPlan, "function");
assert.equal(typeof renderer.documentLoadResultPlan, "function");
assert.equal(typeof renderer.documentRenderPayload, "function");
assert.equal(typeof renderer.markdownLoadPlan, "function");
assert.equal(typeof renderer.markdownLoadResultPlan, "function");
assert.equal(typeof renderer.renderArtifact, "function");
assert.equal(typeof renderer.artifactFallbackPlan, "function");
assert.equal(typeof renderer.markdownModePlan, "function");
assert.equal(typeof renderer.markdownInputPlan, "function");
assert.equal(typeof renderer.markdownSavePlan, "function");
assert.equal(typeof renderer.markdownRevertPlan, "function");

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

assert.deepEqual(
  renderer.artifactStagePlan({ type: "markdown" }),
  {
    renderKind: "markdown",
    stage: { markdownStage: true, resetScroll: false },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: null,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: null,
      markdownSourceHidden: null,
    },
  },
);
assert.deepEqual(
  renderer.artifactStagePlan({ type: "json" }),
  {
    renderKind: "document",
    stage: { markdownStage: true, resetScroll: true },
    surfaces: {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
    },
  },
);
assert.deepEqual(
  renderer.artifactStagePlan({ type: "image" }),
  {
    renderKind: "image",
    stage: { markdownStage: false, resetScroll: true },
    surfaces: {
      imageWrapHidden: false,
      markdownWrapHidden: true,
      selectionHidden: true,
      markdownMarkerHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
      markdownPreviewHidden: null,
      markdownSourceHidden: null,
    },
  },
);

assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "cached", type: "json" },
    { hasCachedContent: true, cachedContent: "{\"ok\":true}", url: "/artifact/cached.json" },
  ),
  { action: "use-cache", content: "{\"ok\":true}" },
);
assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "binary", type: "file" },
    { hasCachedContent: false, cachedContent: "ignored", url: "/artifact/binary.bin" },
  ),
  { action: "use-empty-content", content: "" },
);
assert.deepEqual(
  renderer.documentLoadPlan(
    { id: "raw", type: "json" },
    { hasCachedContent: false, url: "/artifact/raw.json" },
  ),
  {
    action: "fetch-text",
    url: "/artifact/raw.json",
    cache: "no-store",
    errorPrefix: "Artifact fetch failed",
  },
);
assert.deepEqual(
  renderer.documentLoadResultPlan(
    { action: "use-cache", content: "{\"cached\":true}" },
    { fetchedContent: "{\"ignored\":true}" },
  ),
  { content: "{\"cached\":true}", cacheContent: null },
);
assert.deepEqual(
  renderer.documentLoadResultPlan(
    { action: "use-empty-content", content: "" },
    { fetchedContent: "{\"ignored\":true}" },
  ),
  { content: "", cacheContent: "" },
);
assert.deepEqual(
  renderer.documentLoadResultPlan(
    { action: "fetch-text" },
    { fetchedContent: "{\"fetched\":true}" },
  ),
  { content: "{\"fetched\":true}", cacheContent: "{\"fetched\":true}" },
);

assert.deepEqual(
  renderer.markdownLoadPlan(
    { id: "cached-md" },
    { hasCachedContent: true, cachedContent: "# Cached", url: "/artifact/cached.md" },
  ),
  { action: "use-cache", content: "# Cached" },
);
assert.deepEqual(
  renderer.markdownLoadPlan(
    { id: "fresh-md" },
    { hasCachedContent: false, url: "/artifact/fresh.md" },
  ),
  {
    action: "fetch-text",
    url: "/artifact/fresh.md",
    cache: "no-store",
    errorPrefix: "Markdown fetch failed",
  },
);
assert.deepEqual(
  renderer.markdownLoadResultPlan({ content: "# Fresh" }),
  {
    content: "# Fresh",
    savedContent: "# Fresh",
    dirty: false,
  },
);

assert.deepEqual(
  renderer.documentRenderPayload(
    {
      id: "raw",
      name: "Raw",
      type: "json",
      path: "raw.json",
      mime_type: "application/json",
      size_bytes: 1536,
    },
    { content: "{\"ok\":true}", url: "/artifact/raw.json" },
  ),
  {
    id: "raw",
    name: "Raw",
    type: "json",
    path: "raw.json",
    mime_type: "application/json",
    size_bytes: 1536,
    content: "{\"ok\":true}",
    url: "/artifact/raw.json",
    mimeType: "application/json",
    sizeBytes: 1536,
  },
);
assert.deepEqual(
  renderer.documentRenderPayload(
    {
      id: "camel",
      name: "Camel",
      type: "json",
      mimeType: "application/json",
      sizeBytes: 2048,
    },
    { content: "{\"ok\":true}", url: "/artifact/camel.json" },
  ),
  {
    id: "camel",
    name: "Camel",
    type: "json",
    mimeType: "application/json",
    sizeBytes: 2048,
    content: "{\"ok\":true}",
    url: "/artifact/camel.json",
  },
);

assert.equal(
  renderer.artifactReadout({
    artifact: { type: "image", dimensions: { width: 640, height: 480 } },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "640 x 480 px",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "image" },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
  }),
  "800 x 600 px",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "markdown" },
    markdownContent: "# Heading\n\nBody words",
    markdown: window.ArtifactPrimitives.markdown,
  }),
  "3 lines · 4 words · 1 headings",
);
assert.equal(
  renderer.artifactReadout({
    artifact: { type: "json", size_bytes: 42 },
    documentContent: "{\"ok\":true}",
    document: window.ArtifactPrimitives.document,
  }),
  "json · 1 lines · 42 bytes",
);
assert.deepEqual(
  renderer.artifactReadoutPlan({
    artifact: { id: "md", type: "markdown" },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
    markdownContentById: { md: "# Heading" },
    documentContentById: { doc: "{\"ok\":true}" },
    markdown: window.ArtifactPrimitives.markdown,
    document: window.ArtifactPrimitives.document,
  }),
  {
    artifact: { id: "md", type: "markdown" },
    imageNaturalWidth: 800,
    imageNaturalHeight: 600,
    markdownContent: "# Heading",
    documentContent: "",
    markdown: window.ArtifactPrimitives.markdown,
    document: window.ArtifactPrimitives.document,
  },
);
const imageToolbarPlan = renderer.artifactToolbarPlan({
  artifact: { id: "image", type: "image", dimensions: { width: 1000, height: 720 } },
  imageNaturalWidth: 1000,
  imageNaturalHeight: 720,
});
assert.equal(imageToolbarPlan.kind, "image");
assert.deepEqual(imageToolbarPlan.readout, [
  { id: "image-dimensions", label: "Dimensions", value: "1000 x 720 px" },
]);
assert.equal(imageToolbarPlan.controls[0].id, "image-zoom");
assert.match(imageToolbarPlan.controls[0].html, /id="image-controls"/);

const markdownToolbarPlan = renderer.artifactToolbarPlan({
  artifact: { id: "md", type: "markdown" },
  markdownContentById: { md: "# Heading\n\nBody words" },
  markdown: window.ArtifactPrimitives.markdown,
});
assert.equal(markdownToolbarPlan.kind, "markdown");
assert.deepEqual(markdownToolbarPlan.readout, [
  { id: "markdown-diagnostics", label: "Markdown", value: "3 lines · 4 words · 1 headings" },
]);
assert.equal(markdownToolbarPlan.controls[0].id, "markdown-controls");
assert.match(markdownToolbarPlan.controls[0].html, /id="markdown-controls"/);
assert.deepEqual(
  renderer.artifactToolbarPlan({
    artifact: { id: "doc", type: "json", size_bytes: 42 },
    documentContentById: { doc: "{\"ok\":true}" },
    document: window.ArtifactPrimitives.document,
  }),
  {
    kind: "document",
    readout: [
      { id: "document-summary", label: "Document", value: "json · 1 lines · 42 bytes" },
    ],
    controls: [],
  },
);
assert.deepEqual(
  renderer.artifactSelectionPlan({ requestedIndex: -1, artifactCount: 3 }),
  {
    activeIndex: 2,
    canSelect: true,
    closeEditor: true,
    hideAnnotationMarker: true,
    render: true,
  },
);
assert.deepEqual(
  renderer.artifactSelectionPlan({ requestedIndex: 4, artifactCount: 3 }),
  {
    activeIndex: 1,
    canSelect: true,
    closeEditor: true,
    hideAnnotationMarker: true,
    render: true,
  },
);
assert.deepEqual(
  renderer.artifactSelectionPlan({ requestedIndex: 2, artifactCount: 0 }),
  {
    activeIndex: 0,
    canSelect: false,
    closeEditor: false,
    hideAnnotationMarker: false,
    render: false,
  },
);

assert.equal(
  renderer.artifactErrorHtml({ renderKind: "markdown", error: new Error("Bad <markdown>") }),
  "<p>Failed to load markdown: Bad &lt;markdown&gt;</p>",
);
assert.equal(
  renderer.artifactErrorHtml({ renderKind: "document", error: new Error("Bad <artifact>") }),
  "<p>Failed to load artifact: Bad &lt;artifact&gt;</p>",
);

assert.deepEqual(
  renderer.artifactFallbackPlan({ renderKind: "markdown", error: new Error("Bad <markdown>") }),
  {
    renderKind: "markdown",
    html: "<p>Failed to load markdown: Bad &lt;markdown&gt;</p>",
    surfaces: {
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
    },
    updateReadout: false,
  },
);
assert.deepEqual(
  renderer.artifactFallbackPlan({ renderKind: "document", error: new Error("Bad <artifact>") }),
  {
    renderKind: "document",
    html: "<p>Failed to load artifact: Bad &lt;artifact&gt;</p>",
    surfaces: {},
    updateReadout: true,
  },
);

assert.deepEqual(renderer.markdownModePlan("source"), {
  mode: "source",
  renderBody: true,
  focusSource: true,
});
assert.deepEqual(renderer.markdownModePlan("sideways"), {
  mode: "preview",
  renderBody: true,
  focusSource: false,
});

assert.deepEqual(
  renderer.markdownInputPlan({ content: "Edited", savedContent: "Saved" }),
  {
    content: "Edited",
    dirty: true,
    saveDisabled: false,
    updateReadout: true,
  },
);
assert.deepEqual(
  renderer.markdownInputPlan({ content: "Saved", savedContent: "Saved" }),
  {
    content: "Saved",
    dirty: false,
    saveDisabled: true,
    updateReadout: true,
  },
);

assert.deepEqual(
  renderer.markdownSavePlan({ content: "Edited", responseOk: false }),
  {
    status: "failed",
    toast: "Markdown save failed",
    renderBody: false,
  },
);
assert.deepEqual(
  renderer.markdownSavePlan({ content: "Edited", responseOk: true }),
  {
    status: "saved",
    savedContent: "Edited",
    dirty: false,
    renderBody: true,
    toast: "Markdown saved",
  },
);
assert.deepEqual(
  renderer.markdownRevertPlan({ savedContent: "Saved" }),
  {
    content: "Saved",
    dirty: false,
    renderBody: true,
    toast: "Markdown reverted",
  },
);

(async () => {
  async function recordControllerRun(artifact, effects = {}) {
    const calls = [];
    const stagePlan = renderer.artifactStagePlan(artifact);
    const result = await renderer.renderArtifact({
      artifact,
      stagePlan,
      effects: {
        applyStagePlan(plan) {
          calls.push(["applyStagePlan", plan.renderKind]);
        },
        renderImage(payload) {
          calls.push(["renderImage", payload.artifact.id, payload.stagePlan.renderKind]);
        },
        async loadMarkdown(item) {
          calls.push(["loadMarkdown", item.id]);
          if (effects.loadMarkdown) return effects.loadMarkdown(item);
          return "# Markdown";
        },
        renderMarkdown(payload) {
          calls.push(["renderMarkdown", payload.artifact.id, payload.content]);
        },
        async loadDocument(item) {
          calls.push(["loadDocument", item.id]);
          if (effects.loadDocument) return effects.loadDocument(item);
          return "{\"ok\":true}";
        },
        renderDocument(payload) {
          calls.push(["renderDocument", payload.artifact.id, payload.content]);
        },
        renderArtifactError(payload) {
          calls.push(["renderArtifactError", payload.artifact.id, payload.renderKind, payload.error.message]);
        },
      },
    });
    return { calls, result };
  }

  assert.deepEqual(
    await recordControllerRun({ id: "img", type: "image" }),
    {
      calls: [
        ["applyStagePlan", "image"],
        ["renderImage", "img", "image"],
      ],
      result: { renderKind: "image", status: "rendered" },
    },
  );

  assert.deepEqual(
    await recordControllerRun({ id: "md", type: "markdown" }),
    {
      calls: [
        ["applyStagePlan", "markdown"],
        ["loadMarkdown", "md"],
        ["renderMarkdown", "md", "# Markdown"],
      ],
      result: { renderKind: "markdown", status: "rendered" },
    },
  );

  assert.deepEqual(
    await recordControllerRun({ id: "doc", type: "json" }),
    {
      calls: [
        ["applyStagePlan", "document"],
        ["loadDocument", "doc"],
        ["renderDocument", "doc", "{\"ok\":true}"],
      ],
      result: { renderKind: "document", status: "rendered" },
    },
  );

  assert.deepEqual(
    await recordControllerRun(
      { id: "broken-md", type: "markdown" },
      {
        loadMarkdown() {
          throw new Error("fetch failed");
        },
      },
    ),
    {
      calls: [
        ["applyStagePlan", "markdown"],
        ["loadMarkdown", "broken-md"],
        ["renderArtifactError", "broken-md", "markdown", "fetch failed"],
      ],
      result: { renderKind: "markdown", status: "fallback" },
    },
  );

  assert.deepEqual(
    await recordControllerRun(
      { id: "broken-doc", type: "json" },
      {
        loadDocument() {
          throw new Error("document render failed");
        },
      },
    ),
    {
      calls: [
        ["applyStagePlan", "document"],
        ["loadDocument", "broken-doc"],
        ["renderArtifactError", "broken-doc", "document", "document render failed"],
      ],
      result: { renderKind: "document", status: "fallback" },
    },
  );
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
