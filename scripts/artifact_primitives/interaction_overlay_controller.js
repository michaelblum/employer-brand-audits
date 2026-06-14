(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function createInteractionOverlayController({
    overlay = ROOT.interactionOverlay,
    effects = {},
  } = {}) {
    const editorEffects = effects.editor || {};
    const draftStartEffects = effects.draftStart || {};
    const draftCompletionEffects = effects.draftCompletion || {};

    return {
      runEditorIntent(intent) {
        return overlay.runOverlayEditorIntent({
          intent,
          ...editorEffects,
        });
      },
      runDraftStart(draft, placeSelection) {
        return overlay.runOverlayDraftStart({
          draft,
          ...draftStartEffects,
          placeSelection,
        });
      },
      runDraftCompletion(intent) {
        return overlay.runOverlayDraftCompletion({
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
