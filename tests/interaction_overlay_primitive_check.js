const assert = require("node:assert/strict");
const path = require("node:path");

global.window = { ArtifactPrimitives: {} };

require(path.join(__dirname, "../scripts/artifact_primitives/interaction_overlay.js"));

const overlay = window.ArtifactPrimitives.interactionOverlay;

[
  "annotationReorderPlan",
  "annotationOverlayTarget",
  "annotationOverlays",
  "annotationText",
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
const htmlAnchor = {
  type: "html_element",
  coordinate_space: "html_document",
  selector_candidates: ["#apply", "a#apply.cta.primary"],
  tag: "a",
  id: "apply",
  classes: ["cta", "primary"],
  role: "button",
  accessible_name: "Apply now",
  text: "Apply now for robotics roles",
  rect: { x: 20, y: 30, width: 140, height: 44 },
};
const editingNote = {
  id: "note-1",
  subtype: "annotation",
  subject: { kind: "artifact", id: "hero" },
  anchor: textAnchor,
  body: { kind: "comment", text: "Review this" },
};
const persistedNote = {
  id: "hero-note-1",
  subtype: "annotation",
  subject: { kind: "artifact", id: "hero" },
  anchor: imageAnchor,
  body: { kind: "comment", text: "Needs work" },
  created_at_epoch: 10,
  updated_at_epoch: null,
};
const persistedInteractionOverlays = [persistedNote];

assert.deepEqual(overlay.supportedOverlaySubtypes(), ["annotation"]);
assert.deepEqual(overlay.overlaySubtypeModel("annotation"), {
  subtype: "annotation",
  editorModes: ["create", "edit"],
  anchorTypes: ["image_region", "text_range", "html_element"],
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
assert.deepEqual(
  overlay.displayRectForAnchor({
    anchor: htmlAnchor,
    htmlElementRect: (resolvedAnchor) => ({
      ...resolvedAnchor.rect,
      source: "html",
    }),
  }),
  { x: 20, y: 30, width: 140, height: 44, source: "html" },
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
    note: { id: "note-2", anchor: imageAnchor, body: { kind: "comment", text: "Crop this" } },
    markdownMode: "source",
  }),
  {
    subtype: "annotation",
    editorMode: "edit",
    editing: { id: "note-2", anchor: imageAnchor, body: { kind: "comment", text: "Crop this" } },
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
assert.deepEqual(
  overlay.existingOverlayEditorPlan({
    note: { id: "note-html", anchor: htmlAnchor, body: { kind: "comment", text: "Annotate CTA" } },
  }).placement,
  {
    type: "html_element",
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
    interactionOverlays: persistedInteractionOverlays,
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
  interactionOverlays: persistedInteractionOverlays,
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
assert.equal(updateIntent.interactionOverlays[0].body.text, "Updated comment");
assert.equal(updateIntent.interactionOverlays[0].updated_at_epoch, 1781423000);
assert.equal(persistedInteractionOverlays[0].body.text, "Needs work");

const appendIntent = overlay.commitOverlayEditorIntent({
  interactionOverlays: persistedInteractionOverlays,
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
assert.equal(appendIntent.note.id, `overlay-hero-${(1781423000456).toString(36)}`);
assert.equal(appendIntent.note.body.text, "New source note");
assert.equal(appendIntent.note.anchor, textAnchor);
assert.deepEqual(
  appendIntent.interactionOverlays.map((note) => note.id),
  ["hero-note-1", appendIntent.note.id],
);
assert.equal(persistedInteractionOverlays.length, 1);

const reorderOverlays = [
  { id: "note-a", subtype: "annotation", subject: { kind: "artifact", id: "hero" }, body: { text: "First" } },
  { id: "note-b", subtype: "annotation", subject: { kind: "artifact", id: "hero" }, body: { text: "Second" } },
  { id: "note-c", subtype: "annotation", subject: { kind: "artifact", id: "hero" }, body: { text: "Third" } },
  { id: "other-note", subtype: "annotation", subject: { kind: "artifact", id: "other" }, body: { text: "Other" } },
];
assert.deepEqual(
  overlay.annotationReorderPlan({
    interactionOverlays: reorderOverlays,
    artifactId: "hero",
    sourceArtifactId: "hero",
    sourceAnnotationId: "note-c",
    targetAnnotationId: "note-a",
  }),
  {
    artifactId: "hero",
    interactionOverlays: [reorderOverlays[2], reorderOverlays[0], reorderOverlays[1], reorderOverlays[3]],
  },
);
assert.deepEqual(
  reorderOverlays.map((note) => note.id),
  ["note-a", "note-b", "note-c", "other-note"],
);
assert.equal(
  overlay.annotationReorderPlan({
    interactionOverlays: reorderOverlays,
    artifactId: "hero",
    sourceArtifactId: "other",
    sourceAnnotationId: "other-note",
    targetAnnotationId: "note-a",
  }),
  null,
);
assert.equal(
  overlay.annotationReorderPlan({
    interactionOverlays: reorderOverlays,
    artifactId: "hero",
    sourceArtifactId: "hero",
    sourceAnnotationId: "note-a",
    targetAnnotationId: "note-a",
  }),
  null,
);
assert.equal(
  overlay.annotationReorderPlan({
    interactionOverlays: reorderOverlays,
    artifactId: "hero",
    sourceArtifactId: "hero",
    sourceAnnotationId: "missing",
    targetAnnotationId: "note-a",
  }),
  null,
);

const deleteIntent = overlay.secondaryOverlayEditorIntent({
  interactionOverlays: persistedInteractionOverlays,
  editorMode: "edit",
  editing: persistedNote,
});
assert.equal(deleteIntent.subtype, "annotation");
assert.equal(deleteIntent.action, "delete");
assert.equal(deleteIntent.toast, "Comment deleted");
assert.deepEqual(deleteIntent.interactionOverlays, []);
assert.equal(persistedInteractionOverlays.length, 1);

assert.deepEqual(
  overlay.secondaryOverlayEditorIntent({
    interactionOverlays: persistedInteractionOverlays,
    editorMode: "create",
    editing: null,
  }),
  {
    subtype: "annotation",
    action: "cancel",
    interactionOverlays: persistedInteractionOverlays,
    closeEditor: true,
    syncInteractionOverlays: false,
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
