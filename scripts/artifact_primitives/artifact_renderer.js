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

  function documentLoadResultPlan(plan = {}, { fetchedContent = "" } = {}) {
    if (plan.action === "use-cache") {
      return { content: String(plan.content || ""), cacheContent: null };
    }
    if (plan.action === "use-empty-content") {
      const content = String(plan.content || "");
      return { content, cacheContent: content };
    }
    const content = String(fetchedContent ?? "");
    return { content, cacheContent: content };
  }

  function markdownLoadPlan(artifact = {}, {
    hasCachedContent = false,
    cachedContent = "",
    url = "",
  } = {}) {
    if (hasCachedContent) {
      return { action: "use-cache", content: String(cachedContent || "") };
    }
    return {
      action: "fetch-text",
      url,
      cache: "no-store",
      errorPrefix: "Markdown fetch failed",
    };
  }

  function markdownLoadResultPlan({ content = "" } = {}) {
    const nextContent = String(content ?? "");
    return {
      content: nextContent,
      savedContent: nextContent,
      dirty: false,
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

  function artifactReadoutPlan({
    artifact = {},
    imageNaturalWidth = null,
    imageNaturalHeight = null,
    markdownContentById = {},
    documentContentById = {},
    markdown = ROOT.markdown,
    document = ROOT.document,
  } = {}) {
    return {
      artifact,
      imageNaturalWidth,
      imageNaturalHeight,
      markdownContent: markdownContentById[artifact.id] || "",
      documentContent: documentContentById[artifact.id] || "",
      markdown,
      document,
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

  function artifactToolbarPlan(options = {}) {
    const readoutPlan = artifactReadoutPlan(options);
    const kind = artifactRenderKind(readoutPlan.artifact, { document: readoutPlan.document });
    const readoutValue = artifactReadout(readoutPlan);
    const readoutId = kind === "image"
      ? "image-dimensions"
      : kind === "markdown"
        ? "markdown-diagnostics"
        : "document-summary";
    const readoutLabel = kind === "image"
      ? "Dimensions"
      : kind === "markdown"
        ? "Markdown"
        : "Document";
    const controls = kind === "image"
      ? [{ id: "image-zoom", kind: "image-zoom" }]
      : kind === "markdown"
        ? [{ id: "markdown-controls", kind: "markdown-controls" }]
        : [];
    return {
      kind,
      readout: readoutValue ? [{ id: readoutId, label: readoutLabel, value: readoutValue }] : [],
      controls,
    };
  }

  function artifactSelectionPlan({ requestedIndex = 0, artifactCount = 0 } = {}) {
    const count = Number(artifactCount || 0);
    if (count <= 0) {
      return {
        activeIndex: 0,
        canSelect: false,
        closeEditor: false,
        hideAnnotationMarker: false,
        render: false,
      };
    }
    const requested = Number(requestedIndex || 0);
    return {
      activeIndex: ((requested % count) + count) % count,
      canSelect: true,
      closeEditor: true,
      hideAnnotationMarker: true,
      render: true,
    };
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

  function artifactFallbackPlan({ renderKind = "document", error } = {}) {
    return {
      renderKind,
      html: artifactErrorHtml({ renderKind, error }),
      surfaces: renderKind === "markdown"
        ? { markdownPreviewHidden: false, markdownSourceHidden: true }
        : {},
      updateReadout: renderKind === "document",
    };
  }

  function markdownModePlan(mode) {
    const nextMode = mode === "source" ? "source" : "preview";
    return {
      mode: nextMode,
      renderBody: true,
      focusSource: nextMode === "source",
    };
  }

  function markdownInputPlan({ content = "", savedContent = "" } = {}) {
    const nextContent = String(content ?? "");
    const dirty = nextContent !== String(savedContent ?? "");
    return {
      content: nextContent,
      dirty,
      saveDisabled: !dirty,
      updateReadout: true,
    };
  }

  function markdownSavePlan({ content = "", responseOk = false } = {}) {
    if (!responseOk) {
      return {
        status: "failed",
        toast: "Markdown save failed",
        renderBody: false,
      };
    }
    return {
      status: "saved",
      savedContent: String(content ?? ""),
      dirty: false,
      renderBody: true,
      toast: "Markdown saved",
    };
  }

  function markdownRevertPlan({ savedContent = "" } = {}) {
    return {
      content: String(savedContent || ""),
      dirty: false,
      renderBody: true,
      toast: "Markdown reverted",
    };
  }

  function requiredEffect(effects, name) {
    const effect = effects?.[name];
    if (typeof effect !== "function") {
      throw new Error(`Artifact render effect missing: ${name}`);
    }
    return effect;
  }

  async function renderArtifact({
    artifact = {},
    stagePlan = null,
    effects = {},
    options = {},
  } = {}) {
    const plan = stagePlan || artifactStagePlan(artifact, options);
    const renderKind = plan.renderKind || artifactRenderKind(artifact, options);
    requiredEffect(effects, "applyStagePlan")(plan);

    if (renderKind === "image") {
      await requiredEffect(effects, "renderImage")({ artifact, stagePlan: plan, renderKind });
      return { renderKind, status: "rendered" };
    }

    try {
      if (renderKind === "markdown") {
        const content = await requiredEffect(effects, "loadMarkdown")(artifact);
        await requiredEffect(effects, "renderMarkdown")({ artifact, content, stagePlan: plan, renderKind });
        return { renderKind, status: "rendered" };
      }

      const content = await requiredEffect(effects, "loadDocument")(artifact);
      await requiredEffect(effects, "renderDocument")({ artifact, content, stagePlan: plan, renderKind });
      return { renderKind, status: "rendered" };
    } catch (error) {
      await requiredEffect(effects, "renderArtifactError")({ artifact, error, stagePlan: plan, renderKind });
      return { renderKind, status: "fallback" };
    }
  }

  ROOT.artifactRenderer = {
    artifactFallbackPlan,
    artifactErrorHtml,
    artifactReadoutPlan,
    artifactReadout,
    artifactToolbarPlan,
    artifactSelectionPlan,
    artifactStagePlan,
    artifactRenderKind,
    documentLoadPlan,
    documentLoadResultPlan,
    documentRenderPayload,
    markdownLoadPlan,
    markdownLoadResultPlan,
    markdownInputPlan,
    markdownModePlan,
    markdownRevertPlan,
    markdownSavePlan,
    renderArtifact,
  };
}());
