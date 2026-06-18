(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;
  const zoomControls = ROOT.zoomControls;

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
    const controls = isWebSnapshotArtifact(options.artifact)
      ? [zoomControls.zoomControlPlan()]
      : [];
    return common.toolbarPlan({
      kind: "html",
      readoutId: "html-summary",
      readoutLabel: "HTML",
      readoutValue: readout(options),
      controls,
      controlPolicy: options.controlPolicy,
    });
  }

  function capabilities(artifact = {}) {
    return {
      htmlElementAnnotations: true,
      ...(isWebSnapshotArtifact(artifact) ? { artifactZoom: true } : {}),
    };
  }

  function webSnapshotDimensions(artifact = {}) {
    const dimensions = artifact.facets?.visual_dimensions || artifact.dimensions || {};
    return {
      contentWidth: Math.max(1, Number(dimensions.width || 1)),
      contentHeight: Math.max(1, Number(dimensions.height || 1)),
    };
  }

  function webSnapshotZoomOptions(options = {}) {
    return {
      targetEl: options.rootEl?.querySelector?.("[data-zoom-target='web-snapshot-frame']"),
      wrapEl: options.rootEl?.querySelector?.("[data-zoom-wrap='web-snapshot']"),
      stageEl: options.elements?.stageEl,
      zoomInputEl: options.elements?.zoomInputEl,
      viewerConfig: options.viewerConfig,
      ...webSnapshotDimensions(options.artifact),
    };
  }

  function applyZoom(options = {}) {
    if (!isWebSnapshotArtifact(options.artifact)) return null;
    return options.zoom.applyZoom({
      ...webSnapshotZoomOptions(options),
      value: options.value,
      mode: options.mode,
    });
  }

  function stageFitZoom(options = {}) {
    if (!isWebSnapshotArtifact(options.artifact)) return 100;
    return options.zoom.stageFitZoom(webSnapshotZoomOptions(options));
  }

  function smartFit(options = {}) {
    if (!isWebSnapshotArtifact(options.artifact)) return null;
    return options.zoom.smartFit({
      ...webSnapshotZoomOptions(options),
      currentZoomMode: options.state?.zoomMode,
    });
  }

  function updateZoomSurface(options = {}) {
    if (!isWebSnapshotArtifact(options.artifact)) return;
    options.zoom.updateAlignment({
      ...webSnapshotZoomOptions(options),
      zoomPercent: options.state?.zoomPercent || 100,
    });
  }

  function defaultZoomState({ artifact = {}, zoom = window.ArtifactPrimitives?.zoomSurface } = {}) {
    return typeof zoom?.defaultZoomState === "function"
      ? zoom.defaultZoomState(artifact)
      : { zoomMode: "stage-fit", zoomPercent: 100 };
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

  const component = {
    applyZoom,
    bindInspector,
    bindControls: zoomControls.bindControls,
    capabilities,
    defaultZoomState,
    kind: "html",
    matches: isHtmlArtifact,
    order: 20,
    readout,
    smartFit,
    stagePlan,
    stageFitZoom,
    syncControls: zoomControls.syncControls,
    toolbarPlan,
    updateZoomSurface,
  };
  ROOT.types.html = typeof ROOT.registerType === "function" ? ROOT.registerType(component) : component;
}());
