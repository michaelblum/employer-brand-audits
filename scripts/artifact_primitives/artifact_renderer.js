(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const DOCUMENT_TYPES = ["json", "text", "log", "file"];

  function fallbackIsDocumentArtifact(artifact = {}) {
    return DOCUMENT_TYPES.includes(String(artifact.type || "").toLowerCase());
  }

  function artifactRenderKind(artifact = {}, { document } = {}) {
    const type = String(artifact.type || "").toLowerCase();
    if (type === "markdown") return "markdown";
    const documentPrimitive = document || ROOT.document;
    const isDocument = typeof documentPrimitive?.isDocumentArtifact === "function"
      ? documentPrimitive.isDocumentArtifact(artifact)
      : fallbackIsDocumentArtifact(artifact);
    return isDocument ? "document" : "image";
  }

  function artifactStagePlan(artifact = {}, options = {}) {
    const renderKind = artifactRenderKind(artifact, options);
    const shared = {
      selectionHidden: true,
      resetHoverMarker: true,
      commentPopoverHidden: true,
    };
    if (renderKind === "markdown") {
      return {
        renderKind,
        stage: { markdownStage: true, resetScroll: false },
        surfaces: {
          imageWrapHidden: true,
          markdownWrapHidden: false,
          imageControlsDisplay: "none",
          markdownControlsVisible: true,
          ...shared,
          markdownMarkerHidden: null,
          markdownPreviewHidden: null,
          markdownSourceHidden: null,
        },
      };
    }
    if (renderKind === "document") {
      return {
        renderKind,
        stage: { markdownStage: true, resetScroll: true },
        surfaces: {
          imageWrapHidden: true,
          markdownWrapHidden: false,
          imageControlsDisplay: "none",
          markdownControlsVisible: false,
          ...shared,
          markdownMarkerHidden: true,
          markdownPreviewHidden: false,
          markdownSourceHidden: true,
        },
      };
    }
    return {
      renderKind,
      stage: { markdownStage: false, resetScroll: true },
      surfaces: {
        imageWrapHidden: false,
        markdownWrapHidden: true,
        imageControlsDisplay: "flex",
        markdownControlsVisible: false,
        ...shared,
        markdownMarkerHidden: true,
        markdownPreviewHidden: null,
        markdownSourceHidden: null,
      },
    };
  }

  function documentLoadPlan(artifact = {}, {
    hasCachedContent = false,
    cachedContent = "",
    url = "",
  } = {}) {
    if (hasCachedContent) {
      return { action: "use-cache", content: String(cachedContent || "") };
    }
    if (String(artifact.type || "").toLowerCase() === "file") {
      return { action: "use-empty-content", content: "" };
    }
    return {
      action: "fetch-text",
      url,
      cache: "no-store",
      errorPrefix: "Artifact fetch failed",
    };
  }

  function documentRenderPayload(artifact = {}, { content = "", url = "" } = {}) {
    return {
      ...artifact,
      content,
      url,
      mimeType: artifact.mime_type ?? artifact.mimeType,
      sizeBytes: artifact.size_bytes ?? artifact.sizeBytes,
    };
  }

  function artifactReadout({
    artifact = {},
    imageNaturalWidth = null,
    imageNaturalHeight = null,
    markdownContent = "",
    documentContent = "",
    markdown = ROOT.markdown,
    document = ROOT.document,
  } = {}) {
    const renderKind = artifactRenderKind(artifact, { document });
    if (renderKind === "document" && typeof document?.documentReadout === "function") {
      return document.documentReadout(artifact, documentContent);
    }
    if (renderKind === "markdown" && typeof markdown?.markdownDiagnostics === "function") {
      const diagnostics = markdown.markdownDiagnostics(markdownContent);
      return `${diagnostics.line_count} lines · ${diagnostics.word_count} words · ${diagnostics.heading_count} headings`;
    }
    const dimensions = artifact.dimensions || {};
    const width = dimensions.width || imageNaturalWidth || "unknown";
    const height = dimensions.height || imageNaturalHeight || "unknown";
    return `${width} x ${height} px`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function artifactErrorHtml({ renderKind = "document", error } = {}) {
    const prefix = renderKind === "markdown" ? "Failed to load markdown" : "Failed to load artifact";
    return `<p>${prefix}: ${escapeHtml(error?.message || error || "Unknown error")}</p>`;
  }

  ROOT.artifactRenderer = {
    artifactErrorHtml,
    artifactReadout,
    artifactStagePlan,
    artifactRenderKind,
    documentLoadPlan,
    documentRenderPayload,
  };
}());
