(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function artifactRegistry() {
    if (!window.Artifacts?.registry) {
      throw new Error("Artifact registry is not loaded");
    }
    return window.Artifacts.registry;
  }

  function artifactRenderKind(artifact = {}, { document } = {}) {
    return artifactRegistry().artifactRenderKind(artifact, { document });
  }

  function artifactStagePlan(artifact = {}, options = {}) {
    return artifactRegistry().artifactStagePlan(artifact, options);
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
    return artifactRegistry().artifactReadout({
      artifact,
      imageNaturalWidth,
      imageNaturalHeight,
      markdownContent,
      documentContent,
      markdown,
      document,
    });
  }

  function artifactToolbarPlan(options = {}) {
    return artifactRegistry().artifactToolbarPlan(artifactReadoutPlan(options));
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
