(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;
  const DOCUMENT_TYPES = ["json", "text", "log", "file"];

  function documentPrimitive(options = {}) {
    return options.document || window.ArtifactPrimitives?.document;
  }

  function fallbackIsDocumentArtifact(artifact = {}) {
    return DOCUMENT_TYPES.includes(String(artifact.type || "").toLowerCase());
  }

  function isDocumentArtifact(artifact = {}, options = {}) {
    const document = documentPrimitive(options);
    return typeof document?.isDocumentArtifact === "function"
      ? document.isDocumentArtifact(artifact)
      : fallbackIsDocumentArtifact(artifact);
  }

  function stagePlan() {
    return {
      renderKind: "document",
      stage: { markdownStage: true, resetScroll: true },
      surfaces: {
        imageWrapHidden: true,
        markdownWrapHidden: false,
        ...common.sharedStageSurfaces(),
        markdownMarkerHidden: true,
        markdownPreviewHidden: false,
        markdownSourceHidden: true,
      },
    };
  }

  function readout({ artifact = {}, documentContent = "", document = window.ArtifactPrimitives?.document } = {}) {
    return typeof document?.documentReadout === "function"
      ? document.documentReadout(artifact, documentContent)
      : "";
  }

  function toolbarPlan(options = {}) {
    return common.toolbarPlan({
      kind: "document",
      readoutId: "document-summary",
      readoutLabel: "Document",
      readoutValue: readout(options),
      controls: [],
    });
  }

  ROOT.types.document = {
    capabilities: {},
    kind: "document",
    matches: isDocumentArtifact,
    readout,
    stagePlan,
    toolbarPlan,
  };
}());
