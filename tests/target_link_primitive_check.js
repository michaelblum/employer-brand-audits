const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/target_link.js"));

const targetLink = window.ArtifactPrimitives.targetLink;
const interactionOverlay = window.ArtifactPrimitives.interactionOverlay;

[
  "DEFAULT_TARGET_LINK_OPTIONS",
  "createTargetLinkEffect",
  "mergeTargetLinkOptions",
  "normalizeTargetLinkOptions",
].forEach((name) => {
  assert.notEqual(targetLink[name], undefined, `${name} should be public`);
});

function fakeClassList() {
  const values = new Set();
  return {
    add: (value) => values.add(value),
    remove: (value) => values.delete(value),
    contains: (value) => values.has(value),
    values,
  };
}

function fakeStyle() {
  const values = {};
  return {
    values,
    setProperty: (name, value) => {
      values[name] = value;
    },
  };
}

function fakeElement({ query = {} } = {}) {
  const attrs = {};
  const element = {
    hidden: true,
    dataset: {},
    classList: fakeClassList(),
    style: fakeStyle(),
    attributes: attrs,
    querySelectorAll: (selector) => query[selector] || [],
    setAttribute: (name, value) => {
      attrs[name] = String(value);
    },
    getAttribute: (name) => attrs[name],
    removeAttribute: (name) => {
      delete attrs[name];
    },
  };
  return element;
}

function fakeGradientStop() {
  return fakeElement();
}

const stopA = fakeGradientStop();
const stopB = fakeGradientStop();
const stopC = fakeGradientStop();
const layerEl = fakeElement();
const highlightEl = fakeElement();
const connectorSvgEl = fakeElement({
  query: {
    "[data-target-link-gradient-stop=\"primary\"]": [stopA],
    "[data-target-link-gradient-stop=\"secondary\"]": [stopB],
    "[data-target-link-gradient-stop=\"accent\"]": [stopC],
  },
});
const connectorPathEl = fakeElement();
const targetEl = fakeElement();
const stageEl = { clientWidth: 900, clientHeight: 500 };

const effect = targetLink.createTargetLinkEffect({
  color: "#f97316",
  speed: 0.5,
  geometry: {
    highlightInset: 6,
    highlightRadius: 12,
    connectorWidth: 4,
  },
  targetClass: "form-linked",
});

assert.equal(effect.options.colors.primary, "#f97316");
assert.equal(effect.options.speed, 0.5);
assert.equal(effect.options.geometry.highlightInset, 6);
assert.equal(effect.options.geometry.connectorWidth, 4);

const rendered = effect.render({
  layerEl,
  highlightEl,
  connectorSvgEl,
  connectorPathEl,
  sourceRect: { x: 20, y: 30, width: 160, height: 60 },
  targetRect: { x: 500, y: 90, width: 220, height: 180 },
  targetEl,
  stageEl,
  interactionOverlay,
  dataset: { workflowStepId: "l0-seed-intake" },
  targetDataset: { pairing: "workflow-step" },
});

assert.equal(rendered.status, "rendered");
assert.equal(rendered.effect, "chase");
assert.equal(rendered.config.colors.primary, "#f97316");
assert.equal(rendered.config.durations.line, "3.6s");
assert.equal(rendered.config.durations.pulse, "6.6s");
assert.equal(rendered.config.durations.border, "7.8s");
assert.equal(layerEl.hidden, false);
assert.equal(highlightEl.hidden, false);
assert.equal(highlightEl.style.left, "14px");
assert.equal(highlightEl.style.top, "24px");
assert.equal(highlightEl.style.width, "172px");
assert.equal(highlightEl.style.height, "72px");
assert.equal(connectorSvgEl.getAttribute("viewBox"), "0 0 900 500");
assert.ok(connectorPathEl.getAttribute("d").includes("C"));
assert.equal(layerEl.dataset.workflowStepId, "l0-seed-intake");
assert.equal(highlightEl.dataset.targetLinkEffect, "chase");
assert.equal(targetEl.dataset.pairing, "workflow-step");
assert.equal(targetEl.classList.contains("form-linked"), true);
assert.equal(targetEl.style.values["--target-link-color-a"], "#f97316");
assert.equal(targetEl.style.values["--target-link-line-duration"], "3.6s");
assert.equal(targetEl.style.values["--target-link-highlight-radius"], "12px");
assert.equal(targetEl.style.values["--target-link-connector-width"], "4px");
assert.equal(stopA.getAttribute("stop-color"), "#f97316");
assert.equal(stopB.getAttribute("stop-color"), targetLink.DEFAULT_TARGET_LINK_OPTIONS.colors.secondary);
assert.equal(stopC.getAttribute("stop-color"), targetLink.DEFAULT_TARGET_LINK_OPTIONS.colors.accent);

effect.clear({
  layerEl,
  highlightEl,
  connectorPathEl,
  targetEl,
  datasetKeys: ["workflowStepId"],
  targetDatasetKeys: ["pairing"],
});

assert.equal(layerEl.hidden, true);
assert.equal(highlightEl.hidden, true);
assert.equal(connectorPathEl.getAttribute("d"), undefined);
assert.equal(targetEl.classList.contains("form-linked"), false);
assert.equal(layerEl.dataset.workflowStepId, undefined);
assert.equal(targetEl.dataset.pairing, undefined);
