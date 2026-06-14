(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  async function runEditorIntent({
    intent,
    setAnnotations,
    closeEditor,
    syncAnnotations,
    renderSidebar,
    showToast,
  } = {}) {
    if (!intent) return false;
    if (typeof setAnnotations === "function") setAnnotations(intent.annotations);
    if (intent.closeEditor && typeof closeEditor === "function") closeEditor();
    if (intent.syncAnnotations && typeof syncAnnotations === "function") {
      await syncAnnotations();
    }
    if (intent.renderSidebar && typeof renderSidebar === "function") renderSidebar();
    if (intent.toast && typeof showToast === "function") showToast(intent.toast);
    return true;
  }

  function runDraftStart({
    draft,
    setDrag,
    setPendingAnchor,
    setPopoverHidden,
    placeSelection,
  } = {}) {
    if (!draft) return false;
    if (typeof setDrag === "function") setDrag(draft.drag);
    if (typeof setPendingAnchor === "function") setPendingAnchor(draft.pendingAnchor);
    if (typeof setPopoverHidden === "function") setPopoverHidden(draft.popoverHidden);
    if (typeof placeSelection === "function") placeSelection(draft.displayRect);
    return true;
  }

  function runDraftCompletion({
    intent,
    setDrag,
    hideSelection,
    hideMarkdownMarker,
    setPendingAnchor,
    renderMarkdownHighlights,
    setPopoverHidden,
    openCreateEditor,
  } = {}) {
    if (!intent) return false;
    if (intent.action === "resolve-anchor") return false;
    if (typeof setDrag === "function") setDrag(intent.drag);
    if (intent.action === "discard") {
      if (intent.hideSelection && typeof hideSelection === "function") hideSelection();
      if (intent.hideMarkdownMarker && typeof hideMarkdownMarker === "function") {
        hideMarkdownMarker();
      }
      return true;
    }
    if (intent.action === "create") {
      if (typeof setPendingAnchor === "function") setPendingAnchor(intent.pendingAnchor);
      if (intent.renderMarkdownHighlights && typeof renderMarkdownHighlights === "function") {
        renderMarkdownHighlights();
      }
      if (intent.hidePopover && typeof setPopoverHidden === "function") setPopoverHidden(true);
      if (typeof openCreateEditor === "function") {
        openCreateEditor(intent.displayRect, intent.relativeTo);
      }
      return true;
    }
    return false;
  }

  function createInteractionOverlayController({
    effects = {},
  } = {}) {
    const editorEffects = effects.editor || {};
    const draftStartEffects = effects.draftStart || {};
    const draftCompletionEffects = effects.draftCompletion || {};

    return {
      runEditorIntent(intent) {
        return runEditorIntent({
          intent,
          ...editorEffects,
        });
      },
      runDraftStart(draft, placeSelection) {
        return runDraftStart({
          draft,
          ...draftStartEffects,
          placeSelection,
        });
      },
      runDraftCompletion(intent) {
        return runDraftCompletion({
          intent,
          ...draftCompletionEffects,
        });
      },
    };
  }

  ROOT.interactionOverlayController = {
    createInteractionOverlayController,
  };
}());
