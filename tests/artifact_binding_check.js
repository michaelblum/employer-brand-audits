const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {};

require(path.join(__dirname, "../scripts/artifact_workbench/artifact_binding.js"));

const bindingModule = window.WorkbenchArtifactBinding;

assert.equal(typeof bindingModule.createArtifactBinding, "function");

let unbound = false;
let mountedPlan = null;
let boundPayload = null;
let syncedPayload = null;

const components = {
  image: {
    kind: "image",
    capabilities: () => ({
      artifactZoom: true,
      imageRegionAnnotations: true,
      imageZoom: true,
    }),
    bindControls: (payload) => {
      boundPayload = payload;
      return () => {
        unbound = true;
      };
    },
    syncControls: (payload) => {
      syncedPayload = payload;
    },
  },
  document: {
    kind: "document",
    capabilities: {},
  },
};

const registry = {
  resolveArtifactComponent: (artifact) => (
    artifact.type === "image" ? components.image : components.document
  ),
  artifactToolbarPlan: (payload) => ({
    kind: payload.artifact.type,
    readout: [
      {
        id: "readout",
        label: "Readout",
        value: `${payload.artifact.id}:${payload.imageNaturalWidth}x${payload.imageNaturalHeight}`,
      },
    ],
    controls: payload.controlPolicy === "read-only" ? [] : [{ id: "editable-control", html: "<button>Edit</button>" }],
  }),
  artifactStagePlan: (artifact) => ({
    renderKind: artifact.type,
    stage: { resetScroll: true },
    surfaces: {},
  }),
};

const toolbarRoot = { id: "artifact-toolbar" };
const imageEl = { naturalWidth: 640, naturalHeight: 480 };
const imageArtifact = { id: "image-1", type: "image" };

const binding = bindingModule.createArtifactBinding({
  getDefaultArtifact: () => imageArtifact,
  registry: () => registry,
  toolbar: () => ({
    mountToolbar: (rootEl, plan) => {
      mountedPlan = { rootEl, plan };
    },
  }),
  elements: {
    toolbarRoot: () => toolbarRoot,
    image: () => imageEl,
  },
  documentRenderer: () => ({ kind: "document-renderer" }),
  markdown: () => ({ kind: "markdown" }),
  getContext: () => ({
    artifactDocumentTheme: "dark",
    markdownContentById: { "md-1": "# Title" },
    markdownDirty: { "md-1": true },
    markdownMode: "preview",
    zoomMode: "stage-fit",
    zoomPercent: 125,
    documentContentById: { "doc-1": "{}" },
  }),
  actions: () => ({
    applyZoom: () => {},
  }),
});

assert.equal(binding.selectedComponent().kind, "image");
assert.deepEqual(binding.capabilities(), {
  artifactZoom: true,
  imageRegionAnnotations: true,
  imageZoom: true,
});
assert.equal(binding.supports("artifactZoom"), true);
assert.equal(binding.supports("imageZoom"), true);
assert.equal(binding.supports("markdownEditing"), false);

assert.deepEqual(binding.toolbarPlan(), {
  kind: "image",
  readout: [
    {
      id: "readout",
      label: "Readout",
      value: "image-1:640x480",
    },
  ],
  controls: [{ id: "editable-control", html: "<button>Edit</button>" }],
});

const readOnlyBinding = bindingModule.createArtifactBinding({
  getDefaultArtifact: () => ({ id: "md-1", type: "markdown" }),
  registry: () => registry,
  toolbar: () => ({
    mountToolbar: (rootEl, plan) => {
      mountedPlan = { rootEl, plan };
    },
  }),
  elements: {
    toolbarRoot: () => toolbarRoot,
    image: () => imageEl,
  },
  documentRenderer: () => ({ kind: "document-renderer" }),
  markdown: () => ({ kind: "markdown" }),
  getContext: () => ({
    controlPolicy: "read-only",
    markdownContentById: { "md-1": "# Title" },
  }),
});

assert.deepEqual(readOnlyBinding.toolbarPlan(), {
  kind: "markdown",
  readout: [
    {
      id: "readout",
      label: "Readout",
      value: "md-1:640x480",
    },
  ],
  controls: [],
});

assert.deepEqual(binding.stagePlan(), {
  renderKind: "image",
  stage: { resetScroll: true },
  surfaces: {},
});

binding.updateToolbar();
assert.equal(mountedPlan.rootEl, toolbarRoot);
assert.equal(mountedPlan.plan.kind, "image");
assert.equal(boundPayload.rootEl, toolbarRoot);
assert.equal(boundPayload.artifact, imageArtifact);
assert.equal(boundPayload.state.artifactDocumentTheme, "dark");
assert.equal(boundPayload.state.zoomPercent, 125);
assert.equal(boundPayload.state.artifact, imageArtifact);
assert.equal(typeof boundPayload.actions.applyZoom, "function");
assert.equal(syncedPayload.rootEl, toolbarRoot);
assert.equal(syncedPayload.artifact, imageArtifact);

binding.bindControls({ id: "doc-1", type: "json" });
assert.equal(unbound, true);
assert.equal(boundPayload.artifact, imageArtifact);
