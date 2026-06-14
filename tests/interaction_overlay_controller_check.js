const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));
require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay_controller.js"));

const overlay = window.ArtifactPrimitives.interactionOverlay;
const controllerApi = window.ArtifactPrimitives.interactionOverlayController;

assert.equal(typeof controllerApi.createInteractionOverlayController, "function");

const calls = [];
const controller = controllerApi.createInteractionOverlayController({
  overlay,
  effects: {
    editor: {
      setAnnotations: (annotations) => calls.push(["setAnnotations", annotations]),
      closeEditor: () => calls.push(["closeEditor"]),
      syncAnnotations: async () => calls.push(["syncAnnotations"]),
      renderSidebar: () => calls.push(["renderSidebar"]),
      showToast: (message) => calls.push(["showToast", message]),
    },
    draftStart: {
      setDrag: (drag) => calls.push(["setDrag", drag]),
      setPendingAnchor: (pendingAnchor) => calls.push(["setPendingAnchor", pendingAnchor]),
      setPopoverHidden: (hidden) => calls.push(["setPopoverHidden", hidden]),
    },
    draftCompletion: {
      setDrag: (drag) => calls.push(["setDrag", drag]),
      hideSelection: () => calls.push(["hideSelection"]),
      hideMarkdownMarker: () => calls.push(["hideMarkdownMarker"]),
      setPendingAnchor: (pendingAnchor) => calls.push(["setPendingAnchor", pendingAnchor]),
      renderMarkdownHighlights: () => calls.push(["renderMarkdownHighlights"]),
      setPopoverHidden: (hidden) => calls.push(["setPopoverHidden", hidden]),
      openCreateEditor: (displayRect, relativeTo) => calls.push(["openCreateEditor", displayRect, relativeTo]),
    },
  },
});

assert.equal(typeof controller.runEditorIntent, "function");
assert.equal(typeof controller.runDraftStart, "function");
assert.equal(typeof controller.runDraftCompletion, "function");

(async () => {
  await controller.runEditorIntent({
    annotations: { hero: [] },
    closeEditor: true,
    syncAnnotations: true,
    renderSidebar: true,
    toast: "Saved",
  });
  assert.deepEqual(calls.splice(0), [
    ["setAnnotations", { hero: [] }],
    ["closeEditor"],
    ["syncAnnotations"],
    ["renderSidebar"],
    ["showToast", "Saved"],
  ]);

  controller.runDraftStart({
    drag: { type: "image", startX: 1, startY: 2 },
    pendingAnchor: null,
    popoverHidden: true,
    displayRect: { x: 1, y: 2, width: 0, height: 0 },
  }, (displayRect) => calls.push(["placeSelection", displayRect]));
  assert.deepEqual(calls.splice(0), [
    ["setDrag", { type: "image", startX: 1, startY: 2 }],
    ["setPendingAnchor", null],
    ["setPopoverHidden", true],
    ["placeSelection", { x: 1, y: 2, width: 0, height: 0 }],
  ]);

  const handled = controller.runDraftCompletion({
    action: "create",
    drag: null,
    pendingAnchor: { type: "text_range" },
    displayRect: { x: 4, y: 5, width: 40, height: 20 },
    relativeTo: "markdown",
    renderMarkdownHighlights: true,
    hidePopover: true,
  });
  assert.equal(handled, true);
  assert.deepEqual(calls.splice(0), [
    ["setDrag", null],
    ["setPendingAnchor", { type: "text_range" }],
    ["renderMarkdownHighlights"],
    ["setPopoverHidden", true],
    ["openCreateEditor", { x: 4, y: 5, width: 40, height: 20 }, "markdown"],
  ]);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
