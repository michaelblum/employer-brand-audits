(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  function formatZoomPercent(value) {
    const rounded = Math.round(Number(value || 0) * 10) / 10;
    return Number.isInteger(rounded) ? `${rounded}%` : `${rounded.toFixed(1)}%`;
  }

  function configuredZoomPercent(config, key, fallback) {
    const value = Number(config?.[key]);
    return Number.isFinite(value) && value > 0 ? value : fallback;
  }

  function stageViewportSize(stageEl) {
    if (!stageEl) return { width: 1, height: 1 };
    const style = typeof window.getComputedStyle === "function"
      ? window.getComputedStyle(stageEl)
      : {};
    const width = Number(stageEl.clientWidth || 0)
      - parseFloat(style.paddingLeft || 0)
      - parseFloat(style.paddingRight || 0);
    const height = Number(stageEl.clientHeight || 0)
      - parseFloat(style.paddingTop || 0)
      - parseFloat(style.paddingBottom || 0);
    return {
      width: Math.max(1, width),
      height: Math.max(1, height),
    };
  }

  function imageSize(imageEl) {
    const width = Number(imageEl?.naturalWidth || 0);
    const height = Number(imageEl?.naturalHeight || 0);
    if (!width || !height) return null;
    return { width, height };
  }

  function contentSize({ contentWidth, contentHeight, imageEl } = {}) {
    const naturalImageSize = imageSize(imageEl);
    if (naturalImageSize) return naturalImageSize;
    return {
      width: Math.max(1, Number(contentWidth || 1)),
      height: Math.max(1, Number(contentHeight || 1)),
    };
  }

  function stageFitZoom(options = {}) {
    const size = contentSize(options);
    const stageSize = stageViewportSize(options.stageEl);
    const smallerThanStageAt100 = size.width <= stageSize.width && size.height <= stageSize.height;
    if (smallerThanStageAt100) {
      return configuredZoomPercent(options.viewerConfig, "actualSizePercent", 100);
    }
    return Math.min(stageSize.width / size.width, stageSize.height / size.height) * 100;
  }

  function effectiveMinimumZoomPercent(options = {}) {
    const configuredZoomOut = configuredZoomPercent(options.viewerConfig, "maxZoomOutPercent", 10);
    return Math.min(configuredZoomOut, stageFitZoom(options));
  }

  function clampZoom(options = {}) {
    const next = Number(options.value) || configuredZoomPercent(options.viewerConfig, "actualSizePercent", 100);
    const minZoom = effectiveMinimumZoomPercent(options);
    const maxZoom = Math.max(minZoom, configuredZoomPercent(options.viewerConfig, "maxZoomInPercent", 400));
    return Math.min(maxZoom, Math.max(minZoom, next));
  }

  function updateAlignment({ wrapEl, stageEl, contentWidth, contentHeight, zoomPercent } = {}) {
    if (!wrapEl) return;
    const size = contentSize({ contentWidth, contentHeight });
    const stageSize = stageViewportSize(stageEl);
    const fitTolerance = 1;
    wrapEl.classList?.toggle?.(
      "centered",
      size.width * zoomPercent / 100 <= stageSize.width + fitTolerance
        && size.height * zoomPercent / 100 <= stageSize.height + fitTolerance,
    );
  }

  function applyZoom(options = {}) {
    const size = contentSize(options);
    const zoomPercent = clampZoom(options);
    const scale = zoomPercent / 100;
    const mode = options.mode || "manual";
    if (options.zoomInputEl) options.zoomInputEl.value = formatZoomPercent(zoomPercent);
    if (options.imageEl?.style && size.width && size.height) {
      options.imageEl.style.width = `${Math.max(1, size.width * scale)}px`;
    } else if (options.targetEl?.style) {
      options.targetEl.style.width = `${size.width}px`;
      options.targetEl.style.height = `${size.height}px`;
      options.targetEl.style.transformOrigin = "top left";
      options.targetEl.style.transform = `scale(${scale})`;
    }
    if (options.wrapEl?.style && !options.imageEl) {
      options.wrapEl.style.width = `${Math.max(1, size.width * scale)}px`;
      options.wrapEl.style.height = `${Math.max(1, size.height * scale)}px`;
    }
    updateAlignment({ ...options, ...size, zoomPercent });
    return { zoomPercent, zoomMode: mode };
  }

  function smartFitZoom(options = {}) {
    const size = contentSize(options);
    const stageSize = stageViewportSize(options.stageEl);
    const smallerThanStageAt100 = size.width <= stageSize.width && size.height <= stageSize.height;
    if (smallerThanStageAt100) {
      return configuredZoomPercent(options.viewerConfig, "actualSizePercent", 100);
    }
    const widthFitZoom = stageSize.width / size.width * 100;
    const widthFitHeight = size.height * widthFitZoom / 100;
    if (widthFitHeight > stageSize.height + 1) {
      return widthFitZoom;
    }
    return stageFitZoom(options);
  }

  function smartFit(options = {}) {
    const size = contentSize(options);
    const stageSize = stageViewportSize(options.stageEl);
    const smallerThanStageAt100 = size.width <= stageSize.width && size.height <= stageSize.height;
    if (smallerThanStageAt100 && options.currentZoomMode !== "actual-size") {
      return {
        value: configuredZoomPercent(options.viewerConfig, "actualSizePercent", 100),
        mode: "actual-size",
      };
    }
    return { value: smartFitZoom(options), mode: "stage-fit" };
  }

  function zoomDeclaration(artifact = {}) {
    return artifact.zoom?.default
      || artifact.facets?.zoom_default
      || artifact.facets?.default_zoom
      || artifact.default_zoom
      || artifact.zoom_default
      || "stage-fit";
  }

  function defaultZoomState(artifact = {}) {
    const declaration = String(zoomDeclaration(artifact) || "stage-fit").trim().toLowerCase();
    if (declaration === "actual-size" || declaration === "100%" || declaration === "1:1") {
      return { zoomMode: "actual-size", zoomPercent: 100 };
    }
    if (declaration === "stage-fit" || declaration === "viewport-fit" || declaration === "fit") {
      return { zoomMode: "stage-fit", zoomPercent: 100 };
    }
    const percentMatch = declaration.match(/^(\d+(?:\.\d+)?)%$/);
    if (percentMatch) {
      return { zoomMode: "manual", zoomPercent: Number(percentMatch[1]) };
    }
    return { zoomMode: "stage-fit", zoomPercent: 100 };
  }

  ROOT.zoomSurface = {
    applyZoom,
    defaultZoomState,
    formatZoomPercent,
    smartFit,
    smartFitZoom,
    stageFitZoom,
    stageViewportSize,
    updateAlignment,
  };
}());
