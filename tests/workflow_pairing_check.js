const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { Artifacts: {} };

require(path.join(__dirname, "../scripts/artifacts/core/workflow_pairing.js"));

const workflowPairing = window.Artifacts.workflowPairing;

assert.equal(typeof workflowPairing.selectorCandidatesForDefinition, "function");
assert.equal(typeof workflowPairing.definitionForArtifact, "function");
assert.equal(typeof workflowPairing.domAnchorForDefinition, "function");
assert.equal(typeof workflowPairing.targetLinkOptionsForDefinition, "function");

const definitions = [
  {
    step_id: "ignored-no-selector",
    anchor: {
      artifact_id: "l0-intake-flow",
      selector_candidates: [],
    },
  },
  {
    step_id: "ignored-other-artifact",
    anchor: {
      artifact_id: "other-artifact",
      selector_candidates: ["#other"],
    },
  },
  {
    step_id: "l0-seed-intake",
    input_id: "company",
    anchor: {
      artifact_id: "l0-intake-flow",
      selector_candidates: ["  ", '[data-workflow-step-id="l0-seed-intake"]', "g.node[data-id='intake']"],
      target_link: { color: "#f97316" },
    },
  },
];

const selected = workflowPairing.definitionForArtifact(definitions, { id: "l0-intake-flow" });
assert.equal(selected.step_id, "l0-seed-intake");
assert.deepEqual(
  workflowPairing.selectorCandidatesForDefinition(selected),
  ['[data-workflow-step-id="l0-seed-intake"]', "g.node[data-id='intake']"],
);
assert.deepEqual(
  workflowPairing.domAnchorForDefinition(selected),
  {
    type: "dom_element",
    coordinate_space: "artifact_dom",
    artifact_id: "l0-intake-flow",
    selector_candidates: ['[data-workflow-step-id="l0-seed-intake"]', "g.node[data-id='intake']"],
  },
);
assert.deepEqual(
  workflowPairing.targetLinkOptionsForDefinition(selected),
  { color: "#f97316" },
);
assert.deepEqual(
  workflowPairing.targetLinkOptionsForDefinition({
    target_link: { speed: 0.5 },
    anchor: { target_link: { color: "#f97316" } },
  }),
  { speed: 0.5 },
);
assert.deepEqual(workflowPairing.targetLinkOptionsForDefinition({ target_link: "bad" }), {});
assert.equal(workflowPairing.definitionForArtifact(definitions, { id: "missing" }), null);
assert.equal(workflowPairing.domAnchorForDefinition({ step_id: "missing-selectors" }), null);
assert.deepEqual(workflowPairing.selectorCandidatesForDefinition(null), []);
