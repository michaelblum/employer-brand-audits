const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay_controller.js"));

const controllerApi = window.ArtifactPrimitives.interactionOverlayController;

assert.equal(typeof controllerApi.createInteractionOverlayController, "function");

const calls = [];
const controller = controllerApi.createInteractionOverlayController({
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
assert.equal(typeof controller.openCreateEditor, "function");
assert.equal(typeof controller.openExistingEditor, "function");
assert.equal(typeof controller.closeEditor, "function");
assert.equal(typeof controller.showAnnotationMarker, "function");
assert.equal(typeof controller.selectAnnotation, "function");

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

  require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));
  const shellCalls = [];
  const overlay = window.ArtifactPrimitives.interactionOverlay;
  const shellController = controllerApi.createInteractionOverlayController({
    overlay,
    effects: {
      editorShell: {
        setEditorSession: (session) => shellCalls.push(["setEditorSession", session]),
        setCommentValue: (value) => shellCalls.push(["setCommentValue", value]),
        setActionLabels: (labels) => shellCalls.push(["setActionLabels", labels]),
        openComment: (displayRect, relativeTo) => shellCalls.push(["openComment", displayRect, relativeTo]),
        hidePopover: () => shellCalls.push(["hidePopover"]),
        hideSelection: () => shellCalls.push(["hideSelection"]),
        hideMarkdownMarker: () => shellCalls.push(["hideMarkdownMarker"]),
        afterImageReady: (callback) => {
          shellCalls.push(["afterImageReady"]);
          callback();
        },
        scrollRectIntoView: (rect) => shellCalls.push(["scrollRectIntoView", rect]),
        requestAnimationFrame: (callback) => {
          shellCalls.push(["requestAnimationFrame"]);
          callback();
        },
        placeSelectionForAnchor: (anchor) => shellCalls.push(["placeSelectionForAnchor", anchor]),
        placePopoverForAnchor: (anchor) => shellCalls.push(["placePopoverForAnchor", anchor]),
        ensureMarkdownPreview: () => shellCalls.push(["ensureMarkdownPreview"]),
        scrollTextRangeIntoView: (anchor) => shellCalls.push(["scrollTextRangeIntoView", anchor]),
        renderMarkdownHighlights: () => shellCalls.push(["renderMarkdownHighlights"]),
      },
      annotationTarget: {
        setActiveMarker: (marker) => shellCalls.push(["setActiveMarker", marker]),
        setArtifact: (artifactIndex) => shellCalls.push(["setArtifact", artifactIndex]),
        setIndex: (artifactIndex) => shellCalls.push(["setIndex", artifactIndex]),
        render: () => shellCalls.push(["render"]),
        requestAnimationFrame: (callback) => {
          shellCalls.push(["targetRequestAnimationFrame"]);
          callback();
        },
        afterImageReady: (callback) => {
          shellCalls.push(["targetAfterImageReady"]);
          callback();
        },
        isImageArtifact: () => true,
        placeMarkerForAnchor: (anchor) => shellCalls.push(["placeMarkerForAnchor", anchor]),
        openExistingEditor: (note) => shellCalls.push(["openExistingEditor", note]),
      },
    },
  });

  const imageAnchor = {
    type: "image_region",
    coordinate_space: "natural_image",
    rect: { x: 10, y: 20, width: 30, height: 40 },
  };
  const textAnchor = {
    type: "text_range",
    coordinate_space: "markdown_source",
    start: { line: 2, column: 1 },
    end: { line: 3, column: 8 },
  };

  assert.equal(
    shellController.openCreateEditor({
      pendingAnchor: imageAnchor,
      displayRect: { x: 1, y: 2, width: 30, height: 40 },
      relativeTo: "image",
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setEditorSession", { editorMode: "create", editing: null, pendingAnchor: imageAnchor }],
    ["setCommentValue", ""],
    ["setActionLabels", { primary: "Add Comment", secondary: "Cancel" }],
    ["openComment", { x: 1, y: 2, width: 30, height: 40 }, "image"],
  ]);

  assert.equal(
    shellController.openExistingEditor({
      note: { id: "note-1", anchor: imageAnchor, comment: "Crop this" },
      markdownMode: "source",
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setEditorSession", {
      editorMode: "edit",
      editing: { id: "note-1", anchor: imageAnchor, comment: "Crop this" },
      pendingAnchor: null,
    }],
    ["setCommentValue", "Crop this"],
    ["setActionLabels", { primary: "Update", secondary: "Delete" }],
    ["afterImageReady"],
    ["scrollRectIntoView", imageAnchor.rect],
    ["requestAnimationFrame"],
    ["placeSelectionForAnchor", imageAnchor],
    ["placePopoverForAnchor", imageAnchor],
  ]);

  assert.equal(
    shellController.openExistingEditor({
      note: { id: "note-2", anchor: textAnchor, comment: "Source note" },
      markdownMode: "source",
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setEditorSession", {
      editorMode: "edit",
      editing: { id: "note-2", anchor: textAnchor, comment: "Source note" },
      pendingAnchor: null,
    }],
    ["setCommentValue", "Source note"],
    ["setActionLabels", { primary: "Update", secondary: "Delete" }],
    ["ensureMarkdownPreview"],
    ["scrollTextRangeIntoView", textAnchor],
    ["requestAnimationFrame"],
    ["renderMarkdownHighlights"],
    ["placeSelectionForAnchor", textAnchor],
    ["placePopoverForAnchor", textAnchor],
  ]);

  assert.equal(shellController.openExistingEditor({ note: null }), false);

  assert.equal(shellController.closeEditor(), true);
  assert.deepEqual(shellCalls.splice(0), [
    ["setEditorSession", { editorMode: "create", editing: null, pendingAnchor: null }],
    ["hidePopover"],
    ["hideSelection"],
    ["hideMarkdownMarker"],
  ]);

  const annotationNote = { id: "note-3", anchor: imageAnchor, comment: "Marker note" };
  assert.equal(
    shellController.showAnnotationMarker({
      artifactId: "hero",
      annotationId: "note-3",
      artifactIndex: 2,
      currentIndex: 1,
      note: annotationNote,
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setActiveMarker", { artifactId: "hero", annotationId: "note-3" }],
    ["setArtifact", 2],
    ["setActiveMarker", { artifactId: "hero", annotationId: "note-3" }],
    ["targetRequestAnimationFrame"],
    ["targetAfterImageReady"],
    ["placeMarkerForAnchor", imageAnchor],
  ]);

  assert.equal(
    shellController.showAnnotationMarker({
      artifactId: "hero",
      annotationId: "note-3",
      artifactIndex: 1,
      currentIndex: 1,
      note: annotationNote,
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setActiveMarker", { artifactId: "hero", annotationId: "note-3" }],
    ["placeMarkerForAnchor", imageAnchor],
  ]);

  assert.equal(
    shellController.selectAnnotation({
      artifactId: "hero",
      annotationId: "note-3",
      artifactIndex: 2,
      currentIndex: 1,
      note: annotationNote,
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["setIndex", 2],
    ["render"],
    ["targetRequestAnimationFrame"],
    ["openExistingEditor", annotationNote],
  ]);

  assert.equal(
    shellController.selectAnnotation({
      artifactId: "hero",
      annotationId: "note-3",
      artifactIndex: 1,
      currentIndex: 1,
      note: annotationNote,
    }),
    true,
  );
  assert.deepEqual(shellCalls.splice(0), [
    ["openExistingEditor", annotationNote],
  ]);

  assert.equal(
    shellController.selectAnnotation({
      artifactId: "hero",
      annotationId: "missing",
      artifactIndex: 1,
      currentIndex: 1,
      note: null,
    }),
    false,
  );
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
