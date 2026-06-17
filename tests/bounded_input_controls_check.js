const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { Artifacts: {} };

require(path.join(__dirname, "../scripts/artifacts/core/artifact_common.js"));
require(path.join(__dirname, "../scripts/artifacts/core/bounded_input_controls.js"));

const boundedInputControls = window.Artifacts.boundedInputControls;

assert.equal(typeof boundedInputControls.definitionsForArtifact, "function");
assert.equal(typeof boundedInputControls.valueForDefinition, "function");
assert.equal(typeof boundedInputControls.optionRecord, "function");
assert.equal(typeof boundedInputControls.selectedOptionRecord, "function");
assert.equal(typeof boundedInputControls.renderControlHtml, "function");
assert.equal(typeof boundedInputControls.renderLayerHtml, "function");
assert.equal(typeof boundedInputControls.definitionForControl, "function");
assert.equal(typeof boundedInputControls.bindControls, "function");

const definitions = [
  {
    step_id: "l0-seed-intake",
    input_id: "company",
    input_type: "text",
    label: "Company <Name>",
    placeholder: "Acme <Robotics>",
    value: "Default Co",
    anchor: { artifact_id: "l0-intake-flow" },
  },
  {
    step_id: "l0-seed-intake",
    input_id: "workflow_template",
    input_type: "select",
    label: "Workflow template",
    value: "foundational",
    options: [
      { value: "foundational", label: "Foundational audit" },
      "tech-talent-audit",
      { label: "No explicit value" },
    ],
    anchor: { artifact_id: "l0-intake-flow" },
  },
  {
    step_id: "other-step",
    input_id: "ignored",
    anchor: { artifact_id: "other-artifact" },
  },
];

assert.deepEqual(
  boundedInputControls.definitionsForArtifact(definitions, { id: "l0-intake-flow" }).map((definition) => definition.input_id),
  ["company", "workflow_template"],
);
assert.deepEqual(boundedInputControls.definitionsForArtifact("bad", { id: "l0-intake-flow" }), []);

assert.equal(
  boundedInputControls.valueForDefinition(definitions[0], { "l0-seed-intake.company": "Saved Co" }),
  "Saved Co",
);
assert.equal(boundedInputControls.valueForDefinition(definitions[0], {}), "Default Co");
assert.equal(boundedInputControls.valueForDefinition({ step_id: "x", input_id: "y", value: null }, {}), "");

assert.deepEqual(
  definitions[1].options.map(boundedInputControls.optionRecord),
  [
    { value: "foundational", label: "Foundational audit" },
    { value: "tech-talent-audit", label: "tech-talent-audit" },
    { value: "No explicit value", label: "No explicit value" },
  ],
);
assert.deepEqual(
  boundedInputControls.selectedOptionRecord(
    definitions[1].options.map(boundedInputControls.optionRecord),
    "missing",
  ),
  { value: "foundational", label: "Foundational audit" },
);

const inputHtml = boundedInputControls.renderControlHtml(definitions[0], { "l0-seed-intake.company": "Saved <Co>" });
assert.match(inputHtml, /data-bounded-input-control/);
assert.match(inputHtml, /data-step-id="l0-seed-intake"/);
assert.match(inputHtml, /data-input-id="company"/);
assert.match(inputHtml, /aria-label="Company &lt;Name&gt;"/);
assert.match(inputHtml, /value="Saved &lt;Co&gt;"/);
assert.match(inputHtml, /placeholder="Acme &lt;Robotics&gt;"/);

const selectHtml = boundedInputControls.renderControlHtml(
  definitions[1],
  { "l0-seed-intake.workflow_template": "tech-talent-audit" },
);
assert.match(selectHtml, /data-bounded-input-select-trigger/);
assert.match(selectHtml, /value="tech-talent-audit"/);
assert.match(selectHtml, />tech-talent-audit<\/span>/);
assert.match(selectHtml, /role="listbox"/);
assert.match(selectHtml, /aria-selected="true"[\s\S]*tech-talent-audit/);

const layerHtml = boundedInputControls.renderLayerHtml(
  boundedInputControls.definitionsForArtifact(definitions, { id: "l0-intake-flow" }),
  {
    "l0-seed-intake.company": "Saved Co",
    "l0-seed-intake.workflow_template": "foundational",
  },
);
assert.match(layerHtml, /class="bounded-input-panel"/);
assert.match(layerHtml, /Intake inputs/);
assert.match(layerHtml, /Company &lt;Name&gt;/);
assert.match(layerHtml, /Workflow template/);
assert.equal(boundedInputControls.renderLayerHtml([], {}), "");

assert.equal(
  boundedInputControls.definitionForControl(definitions, {
    dataset: { stepId: "l0-seed-intake", inputId: "company" },
  }),
  definitions[0],
);
assert.equal(
  boundedInputControls.definitionForControl(definitions, {
    dataset: { stepId: "missing", inputId: "company" },
  }),
  null,
);

class FakeElement {
  constructor({
    dataset = {},
    hidden = false,
    matches = [],
    textContent = "",
    value = "",
  } = {}) {
    this.dataset = dataset;
    this.hidden = hidden;
    this.matchesSet = new Set(matches);
    this.textContent = textContent;
    this.value = value;
    this.attributes = {};
    this.listeners = {};
    this.parent = null;
    this.queries = new Map();
    this.queryAll = new Map();
    this.focused = false;
  }

  addEventListener(type, listener) {
    this.listeners[type] = this.listeners[type] || [];
    this.listeners[type].push(listener);
  }

  closest(selector) {
    return this.matchesSet.has(selector) ? this : this.parent?.closest(selector) || null;
  }

  dispatch(type, event = {}) {
    const payload = {
      key: "",
      preventDefault: () => { payload.defaultPrevented = true; },
      stopPropagation: () => { payload.propagationStopped = true; },
      ...event,
    };
    (this.listeners[type] || []).forEach((listener) => listener(payload));
    return payload;
  }

  focus() {
    this.focused = true;
    global.document.activeElement = this;
  }

  matches(selector) {
    return this.matchesSet.has(selector);
  }

  querySelector(selector) {
    return this.queries.get(selector) || null;
  }

  querySelectorAll(selector) {
    return this.queryAll.get(selector) || [];
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] || "";
  }
}

global.document = { activeElement: null };

const textInput = new FakeElement({
  dataset: { stepId: "l0-seed-intake", inputId: "company" },
  value: "Draft Co",
});
const textLayer = new FakeElement();
textLayer.queryAll.set("[data-bounded-input-control]", [textInput]);
const textChanges = [];
boundedInputControls.bindControls({
  layerEl: textLayer,
  definitions,
  onChange: (change) => textChanges.push(change),
});
textInput.value = "Typed Co";
textInput.dispatch("input");
assert.equal(textChanges.length, 1);
assert.equal(textChanges[0].definition, definitions[0]);
assert.equal(textChanges[0].value, "Typed Co");

const selectRoot = new FakeElement({ matches: ["[data-bounded-input-select]"] });
const trigger = new FakeElement({
  dataset: { stepId: "l0-seed-intake", inputId: "workflow_template" },
  matches: ["[data-bounded-input-select-trigger]"],
  value: "foundational",
});
const label = new FakeElement({ textContent: "Foundational audit" });
const menu = new FakeElement({ hidden: true });
const optionA = new FakeElement({ dataset: { value: "foundational" }, textContent: "Foundational audit" });
const optionB = new FakeElement({ dataset: { value: "tech-talent-audit" }, textContent: "Tech talent audit" });
trigger.parent = selectRoot;
optionA.parent = selectRoot;
optionB.parent = selectRoot;
selectRoot.queries.set("[data-bounded-input-select-trigger]", trigger);
selectRoot.queries.set("[data-bounded-input-select-label]", label);
selectRoot.queries.set("[data-bounded-input-select-menu]", menu);
selectRoot.queryAll.set("[data-bounded-input-select-option]", [optionA, optionB]);
const selectLayer = new FakeElement();
selectLayer.queryAll.set("[data-bounded-input-control]", [trigger]);
selectLayer.queryAll.set("[data-bounded-input-select]", [selectRoot]);
const selectChanges = [];
boundedInputControls.bindControls({
  layerEl: selectLayer,
  definitions,
  onChange: (change) => selectChanges.push(change),
});

trigger.dispatch("click");
assert.equal(menu.hidden, false);
assert.equal(trigger.getAttribute("aria-expanded"), "true");
optionB.dispatch("click");
assert.equal(menu.hidden, true);
assert.equal(trigger.getAttribute("aria-expanded"), "false");
assert.equal(trigger.value, "tech-talent-audit");
assert.equal(label.textContent, "Tech talent audit");
assert.equal(optionA.getAttribute("aria-selected"), "false");
assert.equal(optionB.getAttribute("aria-selected"), "true");
assert.equal(trigger.focused, true);
assert.equal(selectChanges.length, 1);
assert.equal(selectChanges[0].definition, definitions[1]);
assert.equal(selectChanges[0].value, "tech-talent-audit");

trigger.dispatch("keydown", { key: "ArrowDown" });
assert.equal(menu.hidden, false);
assert.equal(global.document.activeElement, optionB);
optionB.dispatch("keydown", { key: "Enter" });
assert.equal(trigger.value, "tech-talent-audit");
assert.equal(selectChanges.length, 2);

trigger.dispatch("click");
optionA.focus();
optionA.dispatch("keydown", { key: "ArrowDown" });
assert.equal(global.document.activeElement, optionB);
