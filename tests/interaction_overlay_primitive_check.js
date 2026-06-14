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
