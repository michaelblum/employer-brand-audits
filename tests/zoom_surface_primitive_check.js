const assert = require("node:assert/strict");
const path = require("node:path");

global.window = {
  getComputedStyle: () => ({
    paddingLeft: "0",
    paddingRight: "0",
    paddingTop: "0",
    paddingBottom: "0",
  }),
};

require(path.join(__dirname, "../scripts/artifact_primitives/zoom_surface.js"));

const zoom = window.ArtifactPrimitives.zoomSurface;

[
  "applyZoom",
  "defaultZoomState",
  "formatZoomPercent",
  "smartFit",
  "smartFitZoom",
  "stageFitZoom",
].forEach((name) => {
  assert.equal(typeof zoom[name], "function", `${name} should be public`);
});

assert.deepEqual(
  zoom.defaultZoomState({
    id: "web",
    type: "html",
    kind: "web_snapshot",
    facets: { zoom_default: "100%" },
  }),
  { zoomMode: "actual-size", zoomPercent: 100 },
);
assert.deepEqual(
  zoom.defaultZoomState({
    id: "web",
    type: "html",
    kind: "web_snapshot",
    facets: { zoom_default: "stage-fit" },
  }),
  { zoomMode: "stage-fit", zoomPercent: 100 },
);
assert.deepEqual(
  zoom.defaultZoomState({
    id: "web",
    type: "html",
    kind: "web_snapshot",
    facets: { zoom_default: "125%" },
  }),
  { zoomMode: "manual", zoomPercent: 125 },
);

const classNames = new Set();
const targetStyle = {};
const wrapStyle = {};
const targetEl = { style: targetStyle };
const wrapEl = {
  classList: {
    toggle(name, enabled) {
      if (enabled) classNames.add(name);
      else classNames.delete(name);
    },
  },
  style: wrapStyle,
};
const inputEl = {};
const stageEl = { clientWidth: 500, clientHeight: 300 };

const fitZoom = zoom.stageFitZoom({
  contentWidth: 1000,
  contentHeight: 600,
  stageEl,
  viewerConfig: { actualSizePercent: 100 },
});
assert.equal(fitZoom, 50);

const result = zoom.applyZoom({
  targetEl,
  wrapEl,
  stageEl,
  zoomInputEl: inputEl,
  contentWidth: 1000,
  contentHeight: 600,
  viewerConfig: { maxZoomOutPercent: 10, maxZoomInPercent: 400 },
  value: fitZoom,
  mode: "stage-fit",
});

assert.deepEqual(result, { zoomPercent: 50, zoomMode: "stage-fit" });
assert.equal(inputEl.value, "50%");
assert.equal(targetStyle.width, "1000px");
assert.equal(targetStyle.height, "600px");
assert.equal(targetStyle.transform, "scale(0.5)");
assert.equal(wrapStyle.width, "500px");
assert.equal(wrapStyle.height, "300px");
assert.equal(classNames.has("centered"), true);

const imageStyle = {};
const imageEl = { naturalWidth: 1000, naturalHeight: 600, style: imageStyle };
const imageWrapStyle = {};
const imageWrapClassNames = new Set();
const imageWrapEl = {
  classList: {
    toggle(name, enabled) {
      if (enabled) imageWrapClassNames.add(name);
      else imageWrapClassNames.delete(name);
    },
  },
  style: imageWrapStyle,
};
const imageZoomInputEl = {};

assert.equal(
  zoom.stageFitZoom({
    imageEl,
    stageEl,
    viewerConfig: { actualSizePercent: 100 },
  }),
  50,
);
assert.deepEqual(
  zoom.applyZoom({
    imageEl,
    wrapEl: imageWrapEl,
    stageEl,
    zoomInputEl: imageZoomInputEl,
    viewerConfig: { maxZoomOutPercent: 10, maxZoomInPercent: 400 },
    value: 50,
    mode: "stage-fit",
  }),
  { zoomPercent: 50, zoomMode: "stage-fit" },
);
assert.equal(imageZoomInputEl.value, "50%");
assert.equal(imageStyle.width, "500px");
assert.equal(imageWrapClassNames.has("centered"), true);

assert.deepEqual(
  zoom.smartFit({
    contentWidth: 1000,
    contentHeight: 600,
    stageEl,
    viewerConfig: { actualSizePercent: 100 },
    currentZoomMode: "manual",
  }),
  { value: 50, mode: "stage-fit" },
);
