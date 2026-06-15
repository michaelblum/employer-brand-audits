const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));

const overlay = window.ArtifactPrimitives.interactionOverlay;

[
  "annotationOverlayTarget",
  "beginOverlayDraft",
  "closedEditorSession",
  "commitOverlayEditorIntent",
  "completeOverlayDraft",
  "completeResolvedOverlayDraft",
  "createEditorSession",
  "displayRectForAnchor",
  "editorLabels",
  "existingOverlayEditorPlan",
  "mooredActiveMarkerAnchor",
  "mooredEditorAnchor",
  "placeOverlayBox",
  "secondaryOverlayEditorIntent",
  "supportedOverlaySubtypes",
  "overlaySubtypeModel",
].forEach((name) => {
  assert.equal(typeof overlay[name], "function", `${name} should be public`);
});

[
  "appendAnnotation",
  "deleteAnnotation",
  "editEditorSession",
  "isBlankComment",
  "newAnnotation",
  "normalizeComment",
  "runOverlayDraftCompletion",
  "runOverlayDraftStart",
  "runOverlayEditorIntent",
  "updateAnnotation",
].forEach((name) => {
  assert.equal(overlay[name], undefined, `${name} should stay private`);
});

const imageAnchor = {
  type: "image_region",
  coordinate_space: "natural_image",
  rect: { x: 10, y: 12, width: 30, height: 40 },
};
const textAnchor = {
  type: "text_range",
  coordinate_space: "markdown_source",
  start: { line: 2, column: 1 },
  end: { line: 4, column: 10 },
};
const editingNote = {
  id: "note-1",
  artifact_id: "hero",
  anchor: textAnchor,
  comment: "Review this",
};
const persistedNote = {
  id: "hero-note-1",
  artifact_id: "hero",
  kind: "comment",
  anchor: imageAnchor,
  comment: "Needs work",
  created_at_epoch: 10,
  updated_at_epoch: null,
};
const persistedAnnotations = { hero: [persistedNote] };

assert.deepEqual(overlay.supportedOverlaySubtypes(), ["annotation"]);
assert.deepEqual(overlay.overlaySubtypeModel("annotation"), {
  subtype: "annotation",
  editorModes: ["create", "edit"],
  anchorTypes: ["image_region", "text_range"],
  draftTypes: ["image", "markdown"],
  intentActions: ["append", "update", "delete", "cancel"],
});
assert.equal(overlay.overlaySubtypeModel("unknown"), null);

assert.deepEqual(overlay.editorLabels({ subtype: "annotation", mode: "create" }), {
  primary: "Add Comment",
  secondary: "Cancel",
});
assert.deepEqual(overlay.editorLabels({ subtype: "annotation", mode: "edit" }), {
  primary: "Update",
  secondary: "Delete",
});

assert.deepEqual(
  overlay.displayRectForAnchor({
    anchor: imageAnchor,
    imageRegionRect: (rect) => ({ ...rect, source: "image" }),
    textRangeRect: () => {
      throw new Error("text resolver should not be used for image anchors");
    },
  }),
  { x: 10, y: 12, width: 30, height: 40, source: "image" },
);
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

assert.deepEqual(overlay.createEditorSession({ anchor: imageAnchor }), {
  editorMode: "create",
  editing: null,
  pendingAnchor: imageAnchor,
});
assert.deepEqual(overlay.closedEditorSession(), {
  editorMode: "create",
  editing: null,
  pendingAnchor: null,
});
assert.equal(
  overlay.mooredEditorAnchor({
    editing: editingNote,
    pendingAnchor: imageAnchor,
    editorMode: "create",
    popoverHidden: false,
  }),
  textAnchor,
);
assert.equal(
  overlay.mooredEditorAnchor({
    editing: null,
    pendingAnchor: imageAnchor,
    editorMode: "create",
    popoverHidden: false,
  }),
  imageAnchor,
);
assert.equal(
  overlay.mooredEditorAnchor({
    editing: null,
    pendingAnchor: imageAnchor,
    editorMode: "create",
    popoverHidden: true,
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
assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: { id: "note-2", anchor: imageAnchor, comment: "Crop this" },
    markdownMode: "source",
  }),
  {
    subtype: "annotation",
    editorMode: "edit",
    editing: { id: "note-2", anchor: imageAnchor, comment: "Crop this" },
    pendingAnchor: null,
    actionMode: "edit",
    comment: "Crop this",
    anchor: imageAnchor,
    placement: {
      type: "image_region",
      rect: imageAnchor.rect,
    },
  },
);
assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: editingNote,
    markdownMode: "source",
  }).placement,
  {
    type: "text_range",
    ensurePreview: true,
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

assert.equal(
  overlay.commitOverlayEditorIntent({
    annotations: persistedAnnotations,
    artifact: { id: "hero" },
    editorMode: "create",
    editing: null,
    pendingAnchor: imageAnchor,
    comment: "   ",
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
    anchor: imageAnchor,
  }),
  {
    action: "create",
    drag: null,
    pendingAnchor: imageAnchor,
    displayRect: { x: 2, y: 3, width: 40, height: 20 },
    relativeTo: "image",
    renderMarkdownHighlights: false,
    hidePopover: true,
  },
);

const resolvedDraftCalls = [];
assert.deepEqual(
  overlay.completeResolvedOverlayDraft({
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
    resolveAnchor: ({ type, displayRect }) => {
      resolvedDraftCalls.push({ type, displayRect });
      return textAnchor;
    },
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
assert.deepEqual(resolvedDraftCalls, [
  { type: "markdown", displayRect: { x: 1, y: 2, width: 40, height: 20 } },
]);
assert.deepEqual(
  overlay.completeResolvedOverlayDraft({
    type: "markdown",
    displayRect: { x: 1, y: 2, width: 40, height: 20 },
    resolveAnchor: () => null,
  }),
  {
    action: "discard",
    drag: null,
    hideSelection: false,
    hideMarkdownMarker: true,
  },
);
assert.deepEqual(
  overlay.completeResolvedOverlayDraft({
    type: "image",
    displayRect: { x: 2, y: 3, width: 40, height: 20 },
    resolveAnchor: () => imageAnchor,
  }),
  {
    action: "create",
    drag: null,
    pendingAnchor: imageAnchor,
    displayRect: { x: 2, y: 3, width: 40, height: 20 },
    relativeTo: "image",
    renderMarkdownHighlights: false,
    hidePopover: true,
  },
);
assert.deepEqual(
  overlay.completeResolvedOverlayDraft({
    type: "image",
    displayRect: { x: 1, y: 2, width: 7, height: 20 },
    resolveAnchor: () => {
      throw new Error("small drafts should not resolve anchors");
    },
  }),
  {
    action: "discard",
    drag: null,
    hideSelection: true,
    hideMarkdownMarker: true,
  },
);
