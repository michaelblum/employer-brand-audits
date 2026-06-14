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

  function createEditorSession({ anchor = null } = {}) {
    return {
      editorMode: "create",
      editing: null,
      pendingAnchor: anchor,
    };
  }

  function editEditorSession({ note } = {}) {
    return {
      editorMode: "edit",
      editing: note || null,
      pendingAnchor: null,
    };
  }

  function closedEditorSession() {
    return {
      editorMode: "create",
      editing: null,
      pendingAnchor: null,
    };
  }

  function mooredEditorAnchor({
    editing,
    pendingAnchor,
    editorMode,
    popoverHidden,
  } = {}) {
    if (editing?.anchor) return editing.anchor;
    if (pendingAnchor && editorMode === "create" && !popoverHidden) return pendingAnchor;
    return null;
  }

  function annotationOverlayTarget({
    artifactId,
    annotationId,
    artifactIndex,
    currentIndex,
    note,
  } = {}) {
    if (artifactIndex < 0 || !note) return null;
    return {
      subtype: "annotation",
      artifactId,
      annotationId,
      artifactIndex,
      note,
      activeMarker: { artifactId, annotationId },
      requiresArtifactSwitch: artifactIndex !== currentIndex,
    };
  }

  function existingOverlayEditorPlan({ note, markdownMode } = {}) {
    if (!note) return null;
    const anchor = note.anchor;
    let placement = null;
    if (anchor?.type === "image_region" && anchor.rect) {
      placement = { type: "image_region", rect: anchor.rect };
    } else if (anchor?.type === "text_range") {
      placement = { type: "text_range", ensurePreview: markdownMode !== "preview" };
    }
    return {
      subtype: "annotation",
      ...editEditorSession({ note }),
      actionMode: "edit",
      comment: note.comment || "",
      anchor,
      placement,
    };
  }

  function mooredActiveMarkerAnchor({
    activeMarker,
    note,
    currentArtifactId,
  } = {}) {
    if (!activeMarker || !note) return null;
    if (currentArtifactId !== activeMarker.artifactId) return null;
    return note.anchor || null;
  }

  function annotationEditorEffect({
    action,
    annotations,
    note,
    toast,
    syncAnnotations = true,
    renderSidebar = true,
  } = {}) {
    const effect = {
      subtype: "annotation",
      action,
      annotations,
      closeEditor: true,
      syncAnnotations,
      renderSidebar,
      toast: toast || null,
    };
    if (note) effect.note = note;
    return effect;
  }

  function commitOverlayEditorIntent({
    annotations = {},
    artifact,
    editorMode,
    editing,
    pendingAnchor,
    comment,
    nowMs = Date.now(),
  } = {}) {
    const normalized = normalizeComment(comment);
    if (!normalized) return null;
    if (editorMode === "edit" && editing) {
      return annotationEditorEffect({
        action: "update",
        annotations: updateAnnotation({
          annotations,
          artifactId: editing.artifact_id,
          noteId: editing.id,
          comment: normalized,
          nowEpoch: epochFromMilliseconds(nowMs),
        }),
        toast: "Comment updated",
      });
    }
    if (!artifact?.id || !pendingAnchor) return null;
    const note = newAnnotation({
      artifact,
      anchor: pendingAnchor,
      comment: normalized,
      nowMs,
    });
    return annotationEditorEffect({
      action: "append",
      annotations: appendAnnotation({ annotations, artifactId: artifact.id, note }),
      note,
      toast: "Comment added",
    });
  }

  function secondaryOverlayEditorIntent({
    annotations = {},
    editorMode,
    editing,
  } = {}) {
    if (editorMode === "edit" && editing) {
      return annotationEditorEffect({
        action: "delete",
        annotations: deleteAnnotation({
          annotations,
          artifactId: editing.artifact_id,
          noteId: editing.id,
        }),
        toast: "Comment deleted",
      });
    }
    return annotationEditorEffect({
      action: "cancel",
      annotations,
      toast: null,
      syncAnnotations: false,
      renderSidebar: false,
    });
  }

  function beginOverlayDraft({ type, point } = {}) {
    if (!type || !point) return null;
    return {
      drag: { type, startX: point.x, startY: point.y },
      pendingAnchor: null,
      popoverHidden: true,
      displayRect: { x: point.x, y: point.y, width: 0, height: 0 },
    };
  }

  function completeOverlayDraft({
    type,
    displayRect,
    anchorResolved = false,
    anchor = null,
    minSize = 8,
  } = {}) {
    if (!displayRect) return null;
    if (displayRect.width < minSize || displayRect.height < minSize) {
      return {
        action: "discard",
        drag: null,
        hideSelection: true,
        hideMarkdownMarker: true,
      };
    }
    if (!anchorResolved) {
      return {
        action: "resolve-anchor",
        drag: null,
        type,
        displayRect,
      };
    }
    if (!anchor) {
      return {
        action: "discard",
        drag: null,
        hideSelection: false,
        hideMarkdownMarker: type === "markdown",
      };
    }
    return {
      action: "create",
      drag: null,
      pendingAnchor: anchor,
      displayRect,
      relativeTo: type === "markdown" ? "markdown" : "image",
      renderMarkdownHighlights: type === "markdown",
      hidePopover: type !== "markdown",
    };
  }

  ROOT.interactionOverlay = {
    annotationOverlayTarget,
    beginOverlayDraft,
    closedEditorSession,
    completeOverlayDraft,
    commitOverlayEditorIntent,
    createEditorSession,
    displayRectForAnchor,
    editorLabels,
    existingOverlayEditorPlan,
    mooredActiveMarkerAnchor,
    mooredEditorAnchor,
    placeOverlayBox,
    secondaryOverlayEditorIntent,
  };
}());
