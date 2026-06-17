(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};
  const ANNOTATION_OVERLAY_SUBTYPE = "annotation";
  const BOUNDED_INPUT_OVERLAY_SUBTYPE = "bounded_input";
  const OVERLAY_SUBTYPE_MODELS = {
    [ANNOTATION_OVERLAY_SUBTYPE]: {
      subtype: ANNOTATION_OVERLAY_SUBTYPE,
      editorModes: ["create", "edit"],
      anchorTypes: ["image_region", "text_range", "html_element"],
      draftTypes: ["image", "markdown"],
      intentActions: ["append", "update", "delete", "cancel"],
    },
    [BOUNDED_INPUT_OVERLAY_SUBTYPE]: {
      subtype: BOUNDED_INPUT_OVERLAY_SUBTYPE,
      editorModes: ["fill"],
      anchorTypes: ["workflow_input"],
      draftTypes: [],
      intentActions: ["set", "clear"],
    },
  };

  function overlaySubtypeModel(subtype = ANNOTATION_OVERLAY_SUBTYPE) {
    const model = OVERLAY_SUBTYPE_MODELS[subtype];
    if (!model) return null;
    return {
      subtype: model.subtype,
      editorModes: [...model.editorModes],
      anchorTypes: [...model.anchorTypes],
      draftTypes: [...model.draftTypes],
      intentActions: [...model.intentActions],
    };
  }

  function supportedOverlaySubtypes() {
    return Object.keys(OVERLAY_SUBTYPE_MODELS);
  }

  function normalizeComment(value) {
    return String(value || "").trim();
  }

  function isBlankComment(value) {
    return !normalizeComment(value);
  }

  function annotationEditorLabels({ mode } = {}) {
    if (mode === "edit") {
      return { primary: "Update", secondary: "Delete" };
    }
    return { primary: "Add Comment", secondary: "Cancel" };
  }

  function editorLabels({ subtype = ANNOTATION_OVERLAY_SUBTYPE, mode } = {}) {
    const model = overlaySubtypeModel(subtype);
    if (!model) {
      return { primary: "Apply", secondary: "Cancel" };
    }
    if (model.subtype === ANNOTATION_OVERLAY_SUBTYPE) {
      return annotationEditorLabels({ mode });
    }
    if (model.subtype === BOUNDED_INPUT_OVERLAY_SUBTYPE) {
      return { primary: "Save", secondary: "Clear" };
    }
    return { primary: "Apply", secondary: "Cancel" };
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
      id: `overlay-${artifactId}-${Number(nowMs).toString(36)}`,
      subtype: ANNOTATION_OVERLAY_SUBTYPE,
      subject: { kind: "artifact", id: artifactId },
      anchor,
      body: { kind: "comment", text: normalizeComment(comment) },
      created_at_epoch: epochFromMilliseconds(nowMs),
      updated_at_epoch: null,
    };
  }

  function copyInteractionOverlays(interactionOverlays = []) {
    return [...(interactionOverlays || [])];
  }

  function overlaySubjectArtifactId(overlay = {}) {
    return overlay.subject?.kind === "artifact" ? overlay.subject.id || "" : "";
  }

  function annotationText(overlay = {}) {
    return overlay.body?.kind === "comment" ? overlay.body.text || "" : "";
  }

  function annotationOverlays(interactionOverlays = [], artifactId = null) {
    return (interactionOverlays || []).filter((overlay) => (
      overlay?.subtype === ANNOTATION_OVERLAY_SUBTYPE
      && (!artifactId || overlaySubjectArtifactId(overlay) === artifactId)
    ));
  }

  function boundedInputOverlayKey({ stepId, inputId } = {}) {
    if (!stepId || !inputId) return "";
    return `${stepId}.${inputId}`;
  }

  function boundedInputOverlayAnchorKey(overlay = {}) {
    return boundedInputOverlayKey({
      stepId: overlay.anchor?.step_id,
      inputId: overlay.anchor?.input_id,
    });
  }

  function boundedInputOverlays(interactionOverlays = [], stepId = null) {
    return (interactionOverlays || []).filter((overlay) => (
      overlay?.subtype === BOUNDED_INPUT_OVERLAY_SUBTYPE
      && overlay.anchor?.type === "workflow_input"
      && (!stepId || overlay.anchor?.step_id === stepId)
    ));
  }

  function boundedInputOverlayValues(interactionOverlays = []) {
    const values = {};
    for (const overlay of boundedInputOverlays(interactionOverlays)) {
      const key = boundedInputOverlayAnchorKey(overlay);
      if (key) values[key] = String(overlay.body?.value || "");
    }
    return values;
  }

  function appendAnnotation({ interactionOverlays = [], note } = {}) {
    return [...copyInteractionOverlays(interactionOverlays), note];
  }

  function updateAnnotation({
    interactionOverlays = [],
    noteId,
    comment,
    nowEpoch = epochFromMilliseconds(Date.now()),
  } = {}) {
    return copyInteractionOverlays(interactionOverlays).map((note) => (
      note.id === noteId
        ? { ...note, body: { kind: "comment", text: normalizeComment(comment) }, updated_at_epoch: nowEpoch }
        : note
    ));
  }

  function deleteAnnotation({ interactionOverlays = [], noteId } = {}) {
    return copyInteractionOverlays(interactionOverlays).filter((note) => note.id !== noteId);
  }

  function upsertBoundedInputOverlay({
    interactionOverlays = [],
    definition,
    value,
    nowMs = Date.now(),
  } = {}) {
    if (!definition?.step_id || !definition?.input_id || !definition?.anchor?.artifact_id) {
      return copyInteractionOverlays(interactionOverlays);
    }
    const normalized = String(value ?? "").trim();
    const key = boundedInputOverlayKey({
      stepId: definition.step_id,
      inputId: definition.input_id,
    });
    const nowEpoch = epochFromMilliseconds(nowMs);
    const next = [];
    let replaced = false;
    for (const overlay of interactionOverlays || []) {
      if (
        overlay?.subtype === BOUNDED_INPUT_OVERLAY_SUBTYPE
        && boundedInputOverlayAnchorKey(overlay) === key
      ) {
        replaced = true;
        if (normalized) {
          next.push({
            ...overlay,
            body: { kind: "input_value", value: normalized },
            updated_at_epoch: nowEpoch,
          });
        }
        continue;
      }
      next.push(overlay);
    }
    if (!replaced && normalized) {
      next.push({
        id: definition.id || `input:${definition.step_id}:${definition.input_id}`,
        subtype: BOUNDED_INPUT_OVERLAY_SUBTYPE,
        subject: definition.subject || { kind: "workflow_step", id: definition.step_id },
        anchor: {
          type: "workflow_input",
          coordinate_space: "workflow_graph",
          artifact_id: definition.anchor.artifact_id,
          step_id: definition.step_id,
          input_id: definition.input_id,
        },
        body: { kind: "input_value", value: normalized },
        created_at_epoch: nowEpoch,
        updated_at_epoch: null,
      });
    }
    return next;
  }

  function annotationReorderPlan({
    interactionOverlays = [],
    artifactId,
    sourceArtifactId,
    sourceAnnotationId,
    targetAnnotationId,
  } = {}) {
    if (!artifactId || sourceArtifactId !== artifactId) return null;
    if (!sourceAnnotationId || !targetAnnotationId || sourceAnnotationId === targetAnnotationId) return null;
    const notes = annotationOverlays(interactionOverlays, artifactId);
    const from = notes.findIndex((note) => note.id === sourceAnnotationId);
    const to = notes.findIndex((note) => note.id === targetAnnotationId);
    if (from < 0 || to < 0) return null;
    const [moved] = notes.splice(from, 1);
    notes.splice(to, 0, moved);
    const reorderedIds = new Set(notes.map((note) => note.id));
    const next = [];
    let inserted = false;
    for (const overlay of interactionOverlays || []) {
      if (reorderedIds.has(overlay.id)) {
        if (!inserted) {
          next.push(...notes);
          inserted = true;
        }
        continue;
      }
      next.push(overlay);
    }
    return { artifactId, interactionOverlays: next };
  }

  function selectorCandidatesForAnchor(anchor = {}) {
    if (Array.isArray(anchor.selector_candidates)) {
      return anchor.selector_candidates.map((selector) => String(selector || "").trim()).filter(Boolean);
    }
    if (anchor.selector) return [String(anchor.selector).trim()].filter(Boolean);
    return [];
  }

  function elementForDomElementAnchor({ anchor, rootEl } = {}) {
    if (!rootEl || typeof rootEl.querySelector !== "function") return null;
    for (const selector of selectorCandidatesForAnchor(anchor)) {
      try {
        const match = rootEl.querySelector(selector);
        if (match) return match;
      } catch (_error) {
        // Selector candidates are fallbacks; invalid candidates should not block later selectors.
      }
    }
    return null;
  }

  function displayRectForDomElementAnchor({
    anchor,
    rootEl,
    relativeToEl,
  } = {}) {
    const element = elementForDomElementAnchor({ anchor, rootEl });
    if (!element || typeof element.getBoundingClientRect !== "function") return null;
    const elementRect = element.getBoundingClientRect();
    const relativeRect = typeof relativeToEl?.getBoundingClientRect === "function"
      ? relativeToEl.getBoundingClientRect()
      : { left: 0, top: 0 };
    const width = Number.isFinite(elementRect.width) ? elementRect.width : elementRect.right - elementRect.left;
    const height = Number.isFinite(elementRect.height) ? elementRect.height : elementRect.bottom - elementRect.top;
    return {
      x: elementRect.left - relativeRect.left,
      y: elementRect.top - relativeRect.top,
      width,
      height,
    };
  }

  function numberForPath(value) {
    const rounded = Math.round(Number(value) * 1000) / 1000;
    return Number.isFinite(rounded) ? String(rounded).replace(/\.0+$/, "") : "0";
  }

  function rectCenter(rect = {}) {
    return {
      x: Number(rect.x || 0) + (Number(rect.width || 0) / 2),
      y: Number(rect.y || 0) + (Number(rect.height || 0) / 2),
    };
  }

  function connectorPathBetweenRects({ fromRect, toRect } = {}) {
    if (!fromRect || !toRect) return null;
    const fromCenter = rectCenter(fromRect);
    const toCenter = rectCenter(toRect);
    const leftToRight = fromCenter.x <= toCenter.x;
    const start = {
      x: leftToRight ? Number(fromRect.x || 0) + Number(fromRect.width || 0) : Number(fromRect.x || 0),
      y: fromCenter.y,
    };
    const end = {
      x: leftToRight ? Number(toRect.x || 0) : Number(toRect.x || 0) + Number(toRect.width || 0),
      y: toCenter.y,
    };
    const controlDistance = Math.max(8, Math.abs(end.x - start.x) / 2);
    const controlSign = leftToRight ? 1 : -1;
    const c1 = { x: start.x + (controlDistance * controlSign), y: start.y };
    const c2 = { x: end.x - (controlDistance * controlSign), y: end.y };
    return {
      d: `M${numberForPath(start.x)} ${numberForPath(start.y)} C${numberForPath(c1.x)} ${numberForPath(c1.y)} ${numberForPath(c2.x)} ${numberForPath(c2.y)} ${numberForPath(end.x)} ${numberForPath(end.y)}`,
      start,
      end,
    };
  }

  function displayRectForAnchor({
    anchor,
    resolvers = {},
    htmlElementRect,
    imageRegionRect,
    textRangeRect,
    domElementRect,
    rootEl,
    relativeToEl,
  } = {}) {
    const customResolver = anchor?.type ? resolvers[anchor.type] : null;
    if (typeof customResolver === "function") {
      return customResolver(anchor);
    }
    if (anchor?.type === "image_region" && anchor.rect && typeof imageRegionRect === "function") {
      return imageRegionRect(anchor.rect);
    }
    if (anchor?.type === "html_element" && typeof htmlElementRect === "function") {
      return htmlElementRect(anchor);
    }
    if (anchor?.type === "text_range" && typeof textRangeRect === "function") {
      return textRangeRect(anchor);
    }
    if (anchor?.type === "dom_element") {
      if (typeof domElementRect === "function") return domElementRect(anchor);
      return displayRectForDomElementAnchor({ anchor, rootEl, relativeToEl });
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
      subtype: ANNOTATION_OVERLAY_SUBTYPE,
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
    } else if (anchor?.type === "html_element") {
      placement = { type: "html_element" };
    } else if (anchor?.type === "text_range") {
      placement = { type: "text_range", ensurePreview: markdownMode !== "preview" };
    }
    return {
      subtype: ANNOTATION_OVERLAY_SUBTYPE,
      ...editEditorSession({ note }),
      actionMode: "edit",
      comment: annotationText(note),
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
    interactionOverlays,
    note,
    toast,
    syncInteractionOverlays = true,
    renderSidebar = true,
  } = {}) {
    const effect = {
      subtype: ANNOTATION_OVERLAY_SUBTYPE,
      action,
      interactionOverlays,
      closeEditor: true,
      syncInteractionOverlays,
      renderSidebar,
      toast: toast || null,
    };
    if (note) effect.note = note;
    return effect;
  }

  function commitOverlayEditorIntent({
    interactionOverlays = [],
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
        interactionOverlays: updateAnnotation({
          interactionOverlays,
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
      interactionOverlays: appendAnnotation({ interactionOverlays, note }),
      note,
      toast: "Comment added",
    });
  }

  function secondaryOverlayEditorIntent({
    interactionOverlays = [],
    editorMode,
    editing,
  } = {}) {
    if (editorMode === "edit" && editing) {
      return annotationEditorEffect({
        action: "delete",
        interactionOverlays: deleteAnnotation({
          interactionOverlays,
          noteId: editing.id,
        }),
        toast: "Comment deleted",
      });
    }
    return annotationEditorEffect({
      action: "cancel",
      interactionOverlays,
      toast: null,
      syncInteractionOverlays: false,
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

  function completeResolvedOverlayDraft({
    type,
    displayRect,
    resolveAnchor,
    minSize = 8,
  } = {}) {
    const draft = completeOverlayDraft({ type, displayRect, minSize });
    if (!draft || draft.action !== "resolve-anchor") return draft;
    const anchor = typeof resolveAnchor === "function"
      ? resolveAnchor({ type, displayRect })
      : null;
    return completeOverlayDraft({
      type,
      displayRect,
      anchorResolved: true,
      anchor,
      minSize,
    });
  }

  ROOT.interactionOverlay = {
    annotationReorderPlan,
    annotationOverlayTarget,
    annotationOverlays,
    annotationText,
    beginOverlayDraft,
    boundedInputOverlayValues,
    boundedInputOverlays,
    closedEditorSession,
    connectorPathBetweenRects,
    completeOverlayDraft,
    completeResolvedOverlayDraft,
    commitOverlayEditorIntent,
    createEditorSession,
    displayRectForDomElementAnchor,
    displayRectForAnchor,
    editorLabels,
    existingOverlayEditorPlan,
    mooredActiveMarkerAnchor,
    mooredEditorAnchor,
    placeOverlayBox,
    secondaryOverlayEditorIntent,
    supportedOverlaySubtypes,
    overlaySubtypeModel,
    upsertBoundedInputOverlay,
  };
}());
