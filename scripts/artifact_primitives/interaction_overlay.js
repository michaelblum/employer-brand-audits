(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function normalizeComment(value) {
    return String(value || "").trim();
  }

  function isBlankComment(value) {
    return !normalizeComment(value);
  }

  function editorLabels({ subtype = "annotation", mode } = {}) {
    if (subtype !== "annotation") {
      return { primary: "Apply", secondary: "Cancel" };
    }
    if (mode === "edit") {
      return { primary: "Update", secondary: "Delete" };
    }
    return { primary: "Add Comment", secondary: "Cancel" };
  }

  function epochFromMilliseconds(value) {
    return Math.floor(Number(value) / 1000);
  }

  function newAnnotation({
    artifact,
    anchor,
    comment,
    nowMs = Date.now(),
  } = {}) {
    const artifactId = artifact?.id || "";
    return {
      id: `${artifactId}-${Number(nowMs).toString(36)}`,
      artifact_id: artifactId,
      kind: "comment",
      anchor,
      comment: normalizeComment(comment),
      created_at_epoch: epochFromMilliseconds(nowMs),
      updated_at_epoch: null,
    };
  }

  function copyAnnotationsMap(annotations = {}) {
    const next = {};
    for (const [artifactId, notes] of Object.entries(annotations || {})) {
      next[artifactId] = [...(notes || [])];
    }
    return next;
  }

  function appendAnnotation({ annotations = {}, artifactId, note } = {}) {
    const next = copyAnnotationsMap(annotations);
    next[artifactId] = [...(next[artifactId] || []), note];
    return next;
  }

  function updateAnnotation({
    annotations = {},
    artifactId,
    noteId,
    comment,
    nowEpoch = epochFromMilliseconds(Date.now()),
  } = {}) {
    const next = copyAnnotationsMap(annotations);
    next[artifactId] = (next[artifactId] || []).map((note) => (
      note.id === noteId
        ? { ...note, comment: normalizeComment(comment), updated_at_epoch: nowEpoch }
        : note
    ));
    return next;
  }

  function deleteAnnotation({ annotations = {}, artifactId, noteId } = {}) {
    const next = copyAnnotationsMap(annotations);
    next[artifactId] = (next[artifactId] || []).filter((note) => note.id !== noteId);
    return next;
  }

  function displayRectForAnchor({
    anchor,
    imageRegionRect,
    textRangeRect,
  } = {}) {
    if (anchor?.type === "image_region" && anchor.rect && typeof imageRegionRect === "function") {
      return imageRegionRect(anchor.rect);
    }
    if (anchor?.type === "text_range" && typeof textRangeRect === "function") {
      return textRangeRect(anchor);
    }
    return null;
  }

  function placeOverlayBox({ overlayEl, displayRect } = {}) {
    if (!overlayEl || !displayRect) return;
    overlayEl.style.left = `${displayRect.x}px`;
    overlayEl.style.top = `${displayRect.y}px`;
    overlayEl.style.width = `${displayRect.width}px`;
    overlayEl.style.height = `${displayRect.height}px`;
    overlayEl.hidden = false;
  }

  ROOT.interactionOverlay = {
    appendAnnotation,
    deleteAnnotation,
    displayRectForAnchor,
    editorLabels,
    isBlankComment,
    newAnnotation,
    normalizeComment,
    placeOverlayBox,
    updateAnnotation,
  };
}());
