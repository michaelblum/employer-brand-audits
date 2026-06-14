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
    overlay = ROOT.interactionOverlay,
    effects = {},
  } = {}) {
    const editorEffects = effects.editor || {};
    const editorShellEffects = effects.editorShell || {};
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
      openCreateEditor({
        pendingAnchor,
        displayRect,
        relativeTo = "image",
      } = {}) {
        if (!overlay) return false;
        if (typeof editorShellEffects.setEditorSession === "function") {
          editorShellEffects.setEditorSession(overlay.createEditorSession({
            anchor: pendingAnchor,
          }));
        }
        if (typeof editorShellEffects.setCommentValue === "function") {
          editorShellEffects.setCommentValue("");
        }
        if (typeof editorShellEffects.setActionLabels === "function") {
          editorShellEffects.setActionLabels(overlay.editorLabels({
            subtype: "annotation",
            mode: "create",
          }));
        }
        if (typeof editorShellEffects.openComment === "function") {
          editorShellEffects.openComment(displayRect, relativeTo);
        }
        return true;
      },
      openExistingEditor({ note, markdownMode } = {}) {
        if (!overlay) return false;
        const plan = overlay.existingOverlayEditorPlan({ note, markdownMode });
        if (!plan) return false;
        if (typeof editorShellEffects.setEditorSession === "function") {
          editorShellEffects.setEditorSession({
            editorMode: plan.editorMode,
            editing: plan.editing,
            pendingAnchor: plan.pendingAnchor,
          });
        }
        if (typeof editorShellEffects.setCommentValue === "function") {
          editorShellEffects.setCommentValue(plan.comment);
        }
        if (typeof editorShellEffects.setActionLabels === "function") {
          editorShellEffects.setActionLabels(overlay.editorLabels({
            subtype: plan.subtype,
            mode: plan.actionMode,
          }));
        }
        if (plan.placement?.type === "image_region") {
          if (typeof editorShellEffects.afterImageReady === "function") {
            editorShellEffects.afterImageReady(() => {
              if (typeof editorShellEffects.scrollRectIntoView === "function") {
                editorShellEffects.scrollRectIntoView(plan.placement.rect);
              }
              if (typeof editorShellEffects.requestAnimationFrame === "function") {
                editorShellEffects.requestAnimationFrame(() => {
                  if (typeof editorShellEffects.placeSelectionForAnchor === "function") {
                    editorShellEffects.placeSelectionForAnchor(plan.anchor);
                  }
                  if (typeof editorShellEffects.placePopoverForAnchor === "function") {
                    editorShellEffects.placePopoverForAnchor(plan.anchor);
                  }
                });
              }
            });
          }
          return true;
        }
        if (plan.placement?.type === "text_range") {
          if (
            plan.placement.ensurePreview
            && typeof editorShellEffects.ensureMarkdownPreview === "function"
          ) {
            editorShellEffects.ensureMarkdownPreview();
          }
          if (typeof editorShellEffects.scrollTextRangeIntoView === "function") {
            editorShellEffects.scrollTextRangeIntoView(plan.anchor);
          }
          if (typeof editorShellEffects.requestAnimationFrame === "function") {
            editorShellEffects.requestAnimationFrame(() => {
              if (typeof editorShellEffects.renderMarkdownHighlights === "function") {
                editorShellEffects.renderMarkdownHighlights();
              }
              if (typeof editorShellEffects.placeSelectionForAnchor === "function") {
                editorShellEffects.placeSelectionForAnchor(plan.anchor);
              }
              if (typeof editorShellEffects.placePopoverForAnchor === "function") {
                editorShellEffects.placePopoverForAnchor(plan.anchor);
              }
            });
          }
          return true;
        }
        return true;
      },
      closeEditor() {
        if (!overlay) return false;
        if (typeof editorShellEffects.setEditorSession === "function") {
          editorShellEffects.setEditorSession(overlay.closedEditorSession());
        }
        if (typeof editorShellEffects.hidePopover === "function") editorShellEffects.hidePopover();
        if (typeof editorShellEffects.hideSelection === "function") editorShellEffects.hideSelection();
        if (typeof editorShellEffects.hideMarkdownMarker === "function") {
          editorShellEffects.hideMarkdownMarker();
        }
        return true;
      },
    };
  }

  ROOT.interactionOverlayController = {
    createInteractionOverlayController,
  };
}());
