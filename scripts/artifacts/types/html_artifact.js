(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;

  function htmlPrimitive(options = {}) {
    return options.html || window.ArtifactPrimitives?.html;
  }

  function fallbackIsHtmlArtifact(artifact = {}) {
    const type = String(artifact.type || "").toLowerCase();
    const mimeType = String(artifact.mime_type || artifact.mimeType || "").toLowerCase();
    const path = String(artifact.path || "").toLowerCase();
    return type === "html" || mimeType === "text/html" || path.endsWith(".html") || path.endsWith(".htm");
  }

  function isHtmlArtifact(artifact = {}, options = {}) {
    const html = htmlPrimitive(options);
    return typeof html?.isHtmlArtifact === "function"
      ? html.isHtmlArtifact(artifact)
      : fallbackIsHtmlArtifact(artifact);
  }

  function isWebSnapshotArtifact(artifact = {}) {
    return String(artifact.kind || artifact.facets?.artifact_kind || "").toLowerCase() === "web_snapshot";
  }

  function stagePlan(artifact = {}) {
    const surfaces = {
      imageWrapHidden: true,
      markdownWrapHidden: false,
      ...common.sharedStageSurfaces(),
      markdownMarkerHidden: true,
      markdownPreviewHidden: false,
      markdownSourceHidden: true,
    };
    if (isWebSnapshotArtifact(artifact)) {
      surfaces.markdownPreviewBodyClass = "web-snapshot-preview-body";
    }
    return {
      renderKind: "html",
      stage: { markdownStage: true, resetScroll: true },
      surfaces,
    };
  }

  function readout({ artifact = {}, documentContent = "", html = window.ArtifactPrimitives?.html } = {}) {
    return typeof html?.htmlReadout === "function" ? html.htmlReadout(artifact, documentContent) : "";
  }

  function toolbarPlan(options = {}) {
    return common.toolbarPlan({
      kind: "html",
      readoutId: "html-summary",
      readoutLabel: "HTML",
      readoutValue: readout(options),
      controls: [],
    });
  }

  function bindInspector({
    rootEl,
    artifact = {},
    sourceUrl = "",
    wrapEl = null,
    onHover,
    onLeave,
    onSelect,
    html = window.ArtifactPrimitives?.html,
  } = {}) {
    if (typeof html?.bindElementInspector !== "function") return common.noopUnbind;
    return html.bindElementInspector({
      rootEl,
      artifact,
      sourceUrl,
      wrapEl,
      onHover,
      onLeave,
      onSelect,
    });
  }

  ROOT.types.html = {
    bindInspector,
    capabilities: {
      htmlElementAnnotations: true,
    },
    kind: "html",
    matches: isHtmlArtifact,
    readout,
    stagePlan,
    toolbarPlan,
  };
}());
