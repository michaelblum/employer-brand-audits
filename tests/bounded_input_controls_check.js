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
