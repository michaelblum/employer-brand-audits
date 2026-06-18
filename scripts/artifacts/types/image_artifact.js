(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;
  const zoomControls = ROOT.zoomControls;

  function stagePlan() {
    return {
      renderKind: "image",
      stage: { markdownStage: false, resetScroll: true },
      surfaces: {
        imageWrapHidden: false,
        markdownWrapHidden: true,
        ...common.sharedStageSurfaces(),
        markdownMarkerHidden: true,
        markdownPreviewHidden: null,
        markdownSourceHidden: null,
      },
    };
  }

  function readout({ artifact = {}, imageNaturalWidth = null, imageNaturalHeight = null } = {}) {
    const dimensions = artifact.dimensions || {};
    const width = dimensions.width || imageNaturalWidth || "unknown";
    const height = dimensions.height || imageNaturalHeight || "unknown";
    return `${width} x ${height} px`;
  }

  function toolbarPlan(options = {}) {
    return common.toolbarPlan({
      kind: "image",
      readoutId: "image-dimensions",
      readoutLabel: "Dimensions",
      readoutValue: readout(options),
      controls: [zoomControls.zoomControlPlan()],
      controlPolicy: options.controlPolicy,
    });
  }

  function imageZoomOptions({ elements = {}, viewerConfig = {} } = {}) {
    return {
      imageEl: elements.imageEl,
      wrapEl: elements.imageWrapEl,
      stageEl: elements.stageEl,
      zoomInputEl: elements.zoomInputEl,
      viewerConfig,
    };
  }

  function applyZoom(options = {}) {
    return options.imageViewer.applyZoom({
      ...imageZoomOptions(options),
      value: options.value,
      mode: options.mode,
    });
  }

  function stageFitZoom(options = {}) {
    return options.imageViewer.smartFitZoom(imageZoomOptions(options));
  }

  function smartFit(options = {}) {
    return options.imageViewer.smartFit({
      ...imageZoomOptions(options),
      currentZoomMode: options.state?.zoomMode,
    });
  }

  function updateZoomSurface(options = {}) {
    options.imageViewer.updateAlignment({
      ...imageZoomOptions(options),
      zoomPercent: options.state?.zoomPercent || 100,
    });
  }

  function defaultZoomState({ artifact = {}, zoom = window.ArtifactPrimitives?.zoomSurface } = {}) {
    return typeof zoom?.defaultZoomState === "function"
      ? zoom.defaultZoomState(artifact)
      : { zoomMode: "stage-fit", zoomPercent: 100 };
  }

  const component = {
    applyZoom,
    bindControls: zoomControls.bindControls,
    capabilities: {
      artifactZoom: true,
      imageRegionAnnotations: true,
      imageZoom: true,
    },
    defaultZoomState,
    fallback: true,
    kind: "image",
    matches: (artifact = {}) => String(artifact.type || "").toLowerCase() === "image",
    order: 100,
    readout,
    smartFit,
    stagePlan,
    stageFitZoom,
    syncControls: zoomControls.syncControls,
    toolbarPlan,
    updateZoomSurface,
  };
  ROOT.types.image = typeof ROOT.registerType === "function" ? ROOT.registerType(component) : component;
}());
