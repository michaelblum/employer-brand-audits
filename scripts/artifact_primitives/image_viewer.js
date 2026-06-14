(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function formatZoomPercent(value) {
    const rounded = Math.round(value * 10) / 10;
    return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(1)}%`;
  }

  function configuredZoomPercent(config, key, fallback) {
    const value = Number(config?.[key]);
    return Number.isFinite(value) && value > 0 ? value : fallback;
  }

  function stageViewportSize(stageEl) {
    const style = window.getComputedStyle(stageEl);
    const width = stageEl.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    const height = stageEl.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom);
    return {
      width: Math.max(1, width),
      height: Math.max(1, height),
    };
  }

  function renderedImageSize(imageEl, zoomPercent) {
    return {
      width: imageEl.naturalWidth * zoomPercent / 100,
      height: imageEl.naturalHeight * zoomPercent / 100,
    };
  }

  function stageFitZoom({ imageEl, stageEl, viewerConfig }) {
    if (!imageEl.naturalWidth || !imageEl.naturalHeight) return 100;
    const stageSize = stageViewportSize(stageEl);
    const smallerThanStageAt100 =
      imageEl.naturalWidth <= stageSize.width && imageEl.naturalHeight <= stageSize.height;
    if (smallerThanStageAt100) {
      return configuredZoomPercent(viewerConfig, "actualSizePercent", 100);
    }
    return Math.min(stageSize.width / imageEl.naturalWidth, stageSize.height / imageEl.naturalHeight) * 100;
  }

  function effectiveMinimumZoomPercent({ imageEl, stageEl, viewerConfig }) {
    const configuredZoomOut = configuredZoomPercent(viewerConfig, "maxZoomOutPercent", 10);
    if (!imageEl.naturalWidth || !imageEl.naturalHeight) {
      return configuredZoomOut;
    }
    return Math.min(configuredZoomOut, stageFitZoom({ imageEl, stageEl, viewerConfig }));
  }

  function clampZoom({ value, imageEl, stageEl, viewerConfig }) {
    const next = Number(value) || configuredZoomPercent(viewerConfig, "actualSizePercent", 100);
    const minZoom = effectiveMinimumZoomPercent({ imageEl, stageEl, viewerConfig });
    const maxZoom = Math.max(minZoom, configuredZoomPercent(viewerConfig, "maxZoomInPercent", 400));
    return Math.min(maxZoom, Math.max(minZoom, next));
  }

  function updateAlignment({ imageEl, wrapEl, stageEl, zoomPercent }) {
    if (!imageEl.naturalWidth) return;
    const stageSize = stageViewportSize(stageEl);
    const imageSize = renderedImageSize(imageEl, zoomPercent);
    const fitTolerance = 1;
    wrapEl.classList.toggle(
      "centered",
      imageSize.width <= stageSize.width + fitTolerance
        && imageSize.height <= stageSize.height + fitTolerance,
    );
  }

  function applyZoom({ imageEl, wrapEl, stageEl, zoomInputEl, viewerConfig, value, mode = "manual" }) {
    const zoomPercent = clampZoom({ value, imageEl, stageEl, viewerConfig });
    if (zoomInputEl) zoomInputEl.value = formatZoomPercent(zoomPercent);
    if (imageEl.naturalWidth) {
      imageEl.style.width = `${Math.max(1, imageEl.naturalWidth * zoomPercent / 100)}px`;
    }
    updateAlignment({ imageEl, wrapEl, stageEl, zoomPercent });
    return { zoomPercent, zoomMode: mode };
  }

  function smartFitZoom({ imageEl, stageEl, viewerConfig }) {
    if (!imageEl.naturalWidth || !imageEl.naturalHeight) return 100;
    const stageSize = stageViewportSize(stageEl);
    const smallerThanStageAt100 =
      imageEl.naturalWidth <= stageSize.width && imageEl.naturalHeight <= stageSize.height;
    if (smallerThanStageAt100) {
      return configuredZoomPercent(viewerConfig, "actualSizePercent", 100);
    }
    const widthFitZoom = stageSize.width / imageEl.naturalWidth * 100;
    const widthFitHeight = imageEl.naturalHeight * widthFitZoom / 100;
    if (widthFitHeight > stageSize.height + 1) {
      return widthFitZoom;
    }
    return stageFitZoom({ imageEl, stageEl, viewerConfig });
  }

  function smartFit({ imageEl, stageEl, viewerConfig, currentZoomMode }) {
    if (!imageEl.naturalWidth || !imageEl.naturalHeight) return null;
    const stageSize = stageViewportSize(stageEl);
    const smallerThanStageAt100 =
      imageEl.naturalWidth <= stageSize.width && imageEl.naturalHeight <= stageSize.height;
    if (smallerThanStageAt100 && currentZoomMode !== "actual-size") {
      return {
        value: configuredZoomPercent(viewerConfig, "actualSizePercent", 100),
        mode: "actual-size",
      };
    }
    return { value: smartFitZoom({ imageEl, stageEl, viewerConfig }), mode: "stage-fit" };
  }

  ROOT.imageViewer = {
    applyZoom,
    formatZoomPercent,
    renderedImageSize,
    smartFit,
    smartFitZoom,
    stageFitZoom,
    stageViewportSize,
    updateAlignment,
  };
}());
