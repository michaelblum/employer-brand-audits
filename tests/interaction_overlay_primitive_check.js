const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));

const overlay = window.ArtifactPrimitives.interactionOverlay;

assert.equal(typeof overlay.editorLabels, "function");
assert.equal(typeof overlay.newAnnotation, "function");
assert.equal(typeof overlay.appendAnnotation, "function");
assert.equal(typeof overlay.updateAnnotation, "function");
assert.equal(typeof overlay.deleteAnnotation, "function");
assert.equal(typeof overlay.displayRectForAnchor, "function");
assert.equal(typeof overlay.placeOverlayBox, "function");
assert.equal(typeof overlay.createEditorSession, "function");
assert.equal(typeof overlay.editEditorSession, "function");
assert.equal(typeof overlay.closedEditorSession, "function");
assert.equal(typeof overlay.mooredEditorAnchor, "function");
assert.equal(typeof overlay.annotationOverlayTarget, "function");
assert.equal(typeof overlay.existingOverlayEditorPlan, "function");
assert.equal(typeof overlay.mooredActiveMarkerAnchor, "function");
assert.equal(typeof overlay.commitOverlayEditorIntent, "function");
assert.equal(typeof overlay.secondaryOverlayEditorIntent, "function");
assert.equal(typeof overlay.beginOverlayDraft, "function");
assert.equal(typeof overlay.completeOverlayDraft, "function");
assert.equal(typeof overlay.runOverlayEditorIntent, "function");
assert.equal(typeof overlay.runOverlayDraftStart, "function");
assert.equal(typeof overlay.runOverlayDraftCompletion, "function");

assert.deepEqual(overlay.editorLabels({ subtype: "annotation", mode: "create" }), {
  primary: "Add Comment",
  secondary: "Cancel",
});
assert.deepEqual(overlay.editorLabels({ subtype: "annotation", mode: "edit" }), {
  primary: "Update",
  secondary: "Delete",
});

const anchor = {
  type: "image_region",
  coordinate_space: "natural_image",
  rect: { x: 10, y: 12, width: 30, height: 40 },
};
const created = overlay.newAnnotation({
  artifact: { id: "hero" },
  anchor,
  comment: "  Needs tighter crop  ",
  nowMs: 1781422000123,
});

assert.deepEqual(created, {
  id: `hero-${(1781422000123).toString(36)}`,
  artifact_id: "hero",
  kind: "comment",
  anchor,
  comment: "Needs tighter crop",
  created_at_epoch: 1781422000,
  updated_at_epoch: null,
});

const annotations = {
  hero: [
    {
      id: "hero-old",
      artifact_id: "hero",
      kind: "comment",
      anchor,
      comment: "Old",
      created_at_epoch: 1,
      updated_at_epoch: null,
    },
  ],
};

const appended = overlay.appendAnnotation({ annotations, artifactId: "hero", note: created });
assert.equal(appended.hero.length, 2);
assert.equal(annotations.hero.length, 1);
assert.equal(appended.hero[1].comment, "Needs tighter crop");

const updated = overlay.updateAnnotation({
  annotations: appended,
  artifactId: "hero",
  noteId: created.id,
  comment: "  Stronger headline  ",
  nowEpoch: 1781422010,
});
assert.equal(updated.hero[1].comment, "Stronger headline");
assert.equal(updated.hero[1].updated_at_epoch, 1781422010);
assert.equal(appended.hero[1].comment, "Needs tighter crop");

const deleted = overlay.deleteAnnotation({
  annotations: updated,
  artifactId: "hero",
  noteId: "hero-old",
});
assert.deepEqual(deleted.hero.map((note) => note.id), [created.id]);

assert.equal(overlay.isBlankComment("   "), true);
assert.equal(overlay.isBlankComment(" Keep "), false);

assert.deepEqual(
  overlay.displayRectForAnchor({
    anchor,
    imageRegionRect: (rect) => ({ ...rect, source: "image" }),
    textRangeRect: () => {
      throw new Error("text resolver should not be used for image anchors");
    },
  }),
  { x: 10, y: 12, width: 30, height: 40, source: "image" },
);

const textAnchor = {
  type: "text_range",
  coordinate_space: "markdown_source",
  start: { line: 2, column: 1 },
  end: { line: 4, column: 10 },
};
assert.deepEqual(
  overlay.displayRectForAnchor({
    anchor: textAnchor,
    imageRegionRect: () => {
      throw new Error("image resolver should not be used for text anchors");
    },
    textRangeRect: (resolvedAnchor) => ({
      x: resolvedAnchor.start.line,
      y: resolvedAnchor.end.line,
      width: 80,
      height: 30,
      source: "text",
    }),
  }),
  { x: 2, y: 4, width: 80, height: 30, source: "text" },
);

assert.equal(overlay.displayRectForAnchor({ anchor: { type: "unknown" } }), null);

const overlayEl = { style: {}, hidden: true };
overlay.placeOverlayBox({
  overlayEl,
  displayRect: { x: 2, y: 3, width: 40, height: 50 },
});
assert.deepEqual(overlayEl.style, {
  left: "2px",
  top: "3px",
  width: "40px",
  height: "50px",
});
assert.equal(overlayEl.hidden, false);

const createSession = overlay.createEditorSession({ anchor });
assert.deepEqual(createSession, {
  editorMode: "create",
  editing: null,
  pendingAnchor: anchor,
});

const editingNote = { id: "note-1", anchor: textAnchor, comment: "Review this" };
const editSession = overlay.editEditorSession({ note: editingNote });
assert.deepEqual(editSession, {
  editorMode: "edit",
  editing: editingNote,
  pendingAnchor: null,
});

assert.deepEqual(overlay.closedEditorSession(), {
  editorMode: "create",
  editing: null,
  pendingAnchor: null,
});

assert.equal(
  overlay.mooredEditorAnchor({
    editing: editingNote,
    pendingAnchor: anchor,
    editorMode: "create",
    popoverHidden: false,
  }),
  textAnchor,
);
assert.equal(
  overlay.mooredEditorAnchor({
    editing: null,
    pendingAnchor: anchor,
    editorMode: "create",
    popoverHidden: false,
  }),
  anchor,
);
assert.equal(
  overlay.mooredEditorAnchor({
    editing: null,
    pendingAnchor: anchor,
    editorMode: "create",
    popoverHidden: true,
  }),
  null,
);
assert.equal(
  overlay.mooredEditorAnchor({
    editing: null,
    pendingAnchor: anchor,
    editorMode: "edit",
    popoverHidden: false,
  }),
  null,
);

assert.equal(
  overlay.annotationOverlayTarget({
    artifactId: "hero",
    annotationId: "missing",
    artifactIndex: 1,
    currentIndex: 1,
    note: null,
  }),
  null,
);
assert.equal(
  overlay.annotationOverlayTarget({
    artifactId: "missing-artifact",
    annotationId: "note-1",
    artifactIndex: -1,
    currentIndex: 1,
    note: editingNote,
  }),
  null,
);

assert.deepEqual(
  overlay.annotationOverlayTarget({
    artifactId: "hero",
    annotationId: "note-1",
    artifactIndex: 1,
    currentIndex: 1,
    note: editingNote,
  }),
  {
    subtype: "annotation",
    artifactId: "hero",
    annotationId: "note-1",
    artifactIndex: 1,
    note: editingNote,
    activeMarker: { artifactId: "hero", annotationId: "note-1" },
    requiresArtifactSwitch: false,
  },
);

assert.deepEqual(
  overlay.annotationOverlayTarget({
    artifactId: "hero",
    annotationId: "note-1",
    artifactIndex: 2,
    currentIndex: 1,
    note: editingNote,
  }),
  {
    subtype: "annotation",
    artifactId: "hero",
    annotationId: "note-1",
    artifactIndex: 2,
    note: editingNote,
    activeMarker: { artifactId: "hero", annotationId: "note-1" },
    requiresArtifactSwitch: true,
  },
);

assert.equal(overlay.existingOverlayEditorPlan({ note: null }), null);

const imageNote = { id: "note-2", anchor, comment: "Crop this" };
assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: imageNote,
    markdownMode: "source",
  }),
  {
    subtype: "annotation",
    editorMode: "edit",
    editing: imageNote,
    pendingAnchor: null,
    actionMode: "edit",
    comment: "Crop this",
    anchor,
    placement: {
      type: "image_region",
      rect: anchor.rect,
    },
  },
);

assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: editingNote,
    markdownMode: "source",
  }),
  {
    subtype: "annotation",
    editorMode: "edit",
    editing: editingNote,
    pendingAnchor: null,
    actionMode: "edit",
    comment: "Review this",
    anchor: textAnchor,
    placement: {
      type: "text_range",
      ensurePreview: true,
    },
  },
);

assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: editingNote,
    markdownMode: "preview",
  }).placement,
  {
    type: "text_range",
    ensurePreview: false,
  },
);

const unknownAnchorNote = {
  id: "note-3",
  anchor: { type: "unknown" },
  comment: "Unknown",
};
assert.equal(
  overlay.existingOverlayEditorPlan({
    note: unknownAnchorNote,
    markdownMode: "preview",
  }).placement,
  null,
);

assert.equal(
  overlay.mooredActiveMarkerAnchor({
    activeMarker: null,
    note: editingNote,
    currentArtifactId: "hero",
  }),
  null,
);
assert.equal(
  overlay.mooredActiveMarkerAnchor({
    activeMarker: { artifactId: "hero", annotationId: "note-1" },
    note: null,
    currentArtifactId: "hero",
  }),
  null,
);
assert.equal(
  overlay.mooredActiveMarkerAnchor({
    activeMarker: { artifactId: "hero", annotationId: "note-1" },
    note: editingNote,
    currentArtifactId: "other",
  }),
  null,
);
assert.equal(
  overlay.mooredActiveMarkerAnchor({
    activeMarker: { artifactId: "hero", annotationId: "note-1" },
    note: editingNote,
    currentArtifactId: "hero",
  }),
  textAnchor,
);

const persistedNote = {
  id: "hero-note-1",
  artifact_id: "hero",
  kind: "comment",
  anchor,
  comment: "Needs work",
  created_at_epoch: 10,
  updated_at_epoch: null,
};
const persistedAnnotations = { hero: [persistedNote] };

assert.equal(
  overlay.commitOverlayEditorIntent({
    annotations: persistedAnnotations,
    artifact: { id: "hero" },
    editorMode: "create",
    editing: null,
    pendingAnchor: anchor,
    comment: "   ",
    nowMs: 1781423000123,
  }),
  null,
);
assert.equal(
  overlay.commitOverlayEditorIntent({
    annotations: persistedAnnotations,
    artifact: { id: "hero" },
    editorMode: "create",
    editing: null,
    pendingAnchor: null,
    comment: "New comment",
    nowMs: 1781423000123,
  }),
  null,
);

const updateIntent = overlay.commitOverlayEditorIntent({
  annotations: persistedAnnotations,
  artifact: { id: "hero" },
  editorMode: "edit",
  editing: persistedNote,
  pendingAnchor: null,
  comment: "  Updated comment  ",
  nowMs: 1781423000123,
});
assert.equal(updateIntent.subtype, "annotation");
assert.equal(updateIntent.action, "update");
assert.equal(updateIntent.toast, "Comment updated");
assert.equal(updateIntent.closeEditor, true);
assert.equal(updateIntent.syncAnnotations, true);
assert.equal(updateIntent.renderSidebar, true);
assert.equal(updateIntent.annotations.hero[0].comment, "Updated comment");
assert.equal(updateIntent.annotations.hero[0].updated_at_epoch, 1781423000);
assert.equal(persistedAnnotations.hero[0].comment, "Needs work");

const appendIntent = overlay.commitOverlayEditorIntent({
  annotations: persistedAnnotations,
  artifact: { id: "hero" },
  editorMode: "create",
  editing: null,
  pendingAnchor: textAnchor,
  comment: "  New source note  ",
  nowMs: 1781423000456,
});
assert.equal(appendIntent.subtype, "annotation");
assert.equal(appendIntent.action, "append");
assert.equal(appendIntent.toast, "Comment added");
assert.equal(appendIntent.closeEditor, true);
assert.equal(appendIntent.syncAnnotations, true);
assert.equal(appendIntent.renderSidebar, true);
assert.equal(appendIntent.note.id, `hero-${(1781423000456).toString(36)}`);
assert.equal(appendIntent.note.comment, "New source note");
assert.equal(appendIntent.note.anchor, textAnchor);
assert.deepEqual(
  appendIntent.annotations.hero.map((note) => note.id),
  ["hero-note-1", appendIntent.note.id],
);
assert.equal(persistedAnnotations.hero.length, 1);

const deleteIntent = overlay.secondaryOverlayEditorIntent({
  annotations: persistedAnnotations,
  editorMode: "edit",
  editing: persistedNote,
});
assert.equal(deleteIntent.subtype, "annotation");
assert.equal(deleteIntent.action, "delete");
assert.equal(deleteIntent.toast, "Comment deleted");
assert.equal(deleteIntent.closeEditor, true);
assert.equal(deleteIntent.syncAnnotations, true);
assert.equal(deleteIntent.renderSidebar, true);
assert.deepEqual(deleteIntent.annotations.hero, []);
assert.equal(persistedAnnotations.hero.length, 1);

assert.deepEqual(
  overlay.secondaryOverlayEditorIntent({
    annotations: persistedAnnotations,
    editorMode: "create",
    editing: null,
  }),
  {
    subtype: "annotation",
    action: "cancel",
    annotations: persistedAnnotations,
    closeEditor: true,
    syncAnnotations: false,
    renderSidebar: false,
    toast: null,
  },
);

assert.equal(overlay.beginOverlayDraft({ type: "image", point: null }), null);
assert.deepEqual(
  overlay.beginOverlayDraft({
    type: "image",
    point: { x: 12, y: 20 },
  }),
  {
    drag: { type: "image", startX: 12, startY: 20 },
    pendingAnchor: null,
    popoverHidden: true,
    displayRect: { x: 12, y: 20, width: 0, height: 0 },
  },
);
assert.deepEqual(
  overlay.beginOverlayDraft({
    type: "markdown",
    point: { x: 4, y: 9 },
  }),
  {
    drag: { type: "markdown", startX: 4, startY: 9 },
    pendingAnchor: null,
    popoverHidden: true,
    displayRect: { x: 4, y: 9, width: 0, height: 0 },
  },
);

assert.deepEqual(
  overlay.completeOverlayDraft({
    type: "image",
    displayRect: { x: 1, y: 2, width: 7, height: 20 },
  }),
  {
    action: "discard",
    drag: null,
    hideSelection: true,
    hideMarkdownMarker: true,
  },
);
assert.deepEqual(
  overlay.completeOverlayDraft({
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
  }),
  {
    action: "resolve-anchor",
    drag: null,
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
  },
);
assert.deepEqual(
  overlay.completeOverlayDraft({
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
    anchorResolved: true,
    anchor: null,
  }),
  {
    action: "discard",
    drag: null,
    hideSelection: false,
    hideMarkdownMarker: true,
  },
);
assert.deepEqual(
  overlay.completeOverlayDraft({
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
    anchorResolved: true,
    anchor: textAnchor,
  }),
  {
    action: "create",
    drag: null,
    pendingAnchor: textAnchor,
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
    relativeTo: "markdown",
    renderMarkdownHighlights: true,
    hidePopover: false,
  },
);
assert.deepEqual(
  overlay.completeOverlayDraft({
    type: "image",
    displayRect: { x: 2, y: 3, width: 40, height: 20 },
    anchorResolved: true,
    anchor,
  }),
  {
    action: "create",
    drag: null,
    pendingAnchor: anchor,
    displayRect: { x: 2, y: 3, width: 40, height: 20 },
    relativeTo: "image",
    renderMarkdownHighlights: false,
    hidePopover: true,
  },
);

(async () => {
  const callLog = [];
  const handled = await overlay.runOverlayEditorIntent({
    intent: {
      annotations: { hero: [] },
      closeEditor: true,
      syncAnnotations: true,
      renderSidebar: true,
      toast: "Saved",
    },
    setAnnotations: (annotationsValue) => callLog.push(["setAnnotations", annotationsValue]),
    closeEditor: () => callLog.push(["closeEditor"]),
    syncAnnotations: async () => callLog.push(["syncAnnotations"]),
    renderSidebar: () => callLog.push(["renderSidebar"]),
    showToast: (message) => callLog.push(["showToast", message]),
  });
  assert.equal(handled, true);
  assert.deepEqual(callLog, [
    ["setAnnotations", { hero: [] }],
    ["closeEditor"],
    ["syncAnnotations"],
    ["renderSidebar"],
    ["showToast", "Saved"],
  ]);

  const cancelLog = [];
  const cancelHandled = await overlay.runOverlayEditorIntent({
    intent: {
      annotations: { hero: [persistedNote] },
      closeEditor: true,
      syncAnnotations: false,
      renderSidebar: false,
      toast: null,
    },
    setAnnotations: () => cancelLog.push("setAnnotations"),
    closeEditor: () => cancelLog.push("closeEditor"),
    syncAnnotations: () => cancelLog.push("syncAnnotations"),
    renderSidebar: () => cancelLog.push("renderSidebar"),
    showToast: () => cancelLog.push("showToast"),
  });
  assert.equal(cancelHandled, true);
  assert.deepEqual(cancelLog, ["setAnnotations", "closeEditor"]);

  const missingHandled = await overlay.runOverlayEditorIntent({ intent: null });
  assert.equal(missingHandled, false);
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

const draftStartLog = [];
const draftStartHandled = overlay.runOverlayDraftStart({
  draft: {
    drag: { type: "image", startX: 1, startY: 2 },
    pendingAnchor: null,
    popoverHidden: true,
    displayRect: { x: 1, y: 2, width: 0, height: 0 },
  },
  setDrag: (drag) => draftStartLog.push(["setDrag", drag]),
  setPendingAnchor: (pendingAnchor) => draftStartLog.push(["setPendingAnchor", pendingAnchor]),
  setPopoverHidden: (hidden) => draftStartLog.push(["setPopoverHidden", hidden]),
  placeSelection: (displayRect) => draftStartLog.push(["placeSelection", displayRect]),
});
assert.equal(draftStartHandled, true);
assert.deepEqual(draftStartLog, [
  ["setDrag", { type: "image", startX: 1, startY: 2 }],
  ["setPendingAnchor", null],
  ["setPopoverHidden", true],
  ["placeSelection", { x: 1, y: 2, width: 0, height: 0 }],
]);
assert.equal(overlay.runOverlayDraftStart({ draft: null }), false);

const draftDiscardLog = [];
const draftDiscardHandled = overlay.runOverlayDraftCompletion({
  intent: {
    action: "discard",
    drag: null,
    hideSelection: true,
    hideMarkdownMarker: true,
  },
  setDrag: (drag) => draftDiscardLog.push(["setDrag", drag]),
  hideSelection: () => draftDiscardLog.push(["hideSelection"]),
  hideMarkdownMarker: () => draftDiscardLog.push(["hideMarkdownMarker"]),
});
assert.equal(draftDiscardHandled, true);
assert.deepEqual(draftDiscardLog, [
  ["setDrag", null],
  ["hideSelection"],
  ["hideMarkdownMarker"],
]);

const draftCreateLog = [];
const draftCreateHandled = overlay.runOverlayDraftCompletion({
  intent: {
    action: "create",
    drag: null,
    pendingAnchor: textAnchor,
    displayRect: { x: 4, y: 5, width: 40, height: 20 },
    relativeTo: "markdown",
    renderMarkdownHighlights: true,
    hidePopover: true,
  },
  setDrag: (drag) => draftCreateLog.push(["setDrag", drag]),
  setPendingAnchor: (pendingAnchor) => draftCreateLog.push(["setPendingAnchor", pendingAnchor]),
  renderMarkdownHighlights: () => draftCreateLog.push(["renderMarkdownHighlights"]),
  setPopoverHidden: (hidden) => draftCreateLog.push(["setPopoverHidden", hidden]),
  openCreateEditor: (displayRect, relativeTo) => draftCreateLog.push(["openCreateEditor", displayRect, relativeTo]),
});
assert.equal(draftCreateHandled, true);
assert.deepEqual(draftCreateLog, [
  ["setDrag", null],
  ["setPendingAnchor", textAnchor],
  ["renderMarkdownHighlights"],
  ["setPopoverHidden", true],
  ["openCreateEditor", { x: 4, y: 5, width: 40, height: 20 }, "markdown"],
]);

assert.equal(
  overlay.runOverlayDraftCompletion({
    intent: { action: "resolve-anchor", drag: null },
    setDrag: () => {
      throw new Error("resolve-anchor intent should not mutate draft state");
    },
  }),
  false,
);
