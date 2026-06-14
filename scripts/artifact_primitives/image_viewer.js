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

  function pointInElement(event, element) {
    const rect = element.getBoundingClientRect();
    return {
      x: Math.min(Math.max(event.clientX - rect.left, 0), rect.width),
      y: Math.min(Math.max(event.clientY - rect.top, 0), rect.height),
    };
  }

  function imagePoint({ event, imageEl }) {
    return pointInElement(event, imageEl);
  }

  function dragDisplayRect({ drag, point }) {
    return {
      x: Math.min(drag.startX, point.x),
      y: Math.min(drag.startY, point.y),
      width: Math.abs(point.x - drag.startX),
      height: Math.abs(point.y - drag.startY),
    };
  }

  function displayRectFromNatural({ rect, imageEl }) {
    const imageRect = imageEl.getBoundingClientRect();
    const sx = imageRect.width / imageEl.naturalWidth;
    const sy = imageRect.height / imageEl.naturalHeight;
    return {
      x: rect.x * sx,
      y: rect.y * sy,
      width: rect.width * sx,
      height: rect.height * sy,
    };
  }

  function naturalRect({ displayRect, imageEl }) {
    const imageRect = imageEl.getBoundingClientRect();
    const sx = imageEl.naturalWidth / imageRect.width;
    const sy = imageEl.naturalHeight / imageRect.height;
    return {
      x: Math.round(displayRect.x * sx),
      y: Math.round(displayRect.y * sy),
      width: Math.round(displayRect.width * sx),
      height: Math.round(displayRect.height * sy),
    };
  }

  function placeSelection({ selectionEl, imageEl, wrapEl, displayRect }) {
    const imageRect = imageEl.getBoundingClientRect();
    const wrapRect = wrapEl.getBoundingClientRect();
    selectionEl.style.left = `${displayRect.x + imageRect.left - wrapRect.left}px`;
    selectionEl.style.top = `${displayRect.y + imageRect.top - wrapRect.top}px`;
    selectionEl.style.width = `${displayRect.width}px`;
    selectionEl.style.height = `${displayRect.height}px`;
    selectionEl.hidden = false;
  }

  function scrollRectIntoView({ rect, imageEl, wrapEl, stageEl }) {
    if (!imageEl.naturalWidth) return;
    const displayRect = displayRectFromNatural({ rect, imageEl });
    const targetLeft = wrapEl.offsetLeft + displayRect.x + displayRect.width / 2;
    const targetTop = wrapEl.offsetTop + displayRect.y + displayRect.height / 2;
    stageEl.scrollTo({
      left: Math.max(0, targetLeft - stageEl.clientWidth / 2),
      top: Math.max(0, targetTop - stageEl.clientHeight / 2),
      behavior: "auto",
    });
  }

  const markerTimers = new WeakMap();

  function clearMarkerTimers(markerEl) {
    for (const timer of markerTimers.get(markerEl) || []) clearTimeout(timer);
    markerTimers.set(markerEl, []);
  }

  function queueMarkerStep(markerEl, delay, callback) {
    const timer = setTimeout(() => {
      markerTimers.set(markerEl, (markerTimers.get(markerEl) || []).filter((item) => item !== timer));
      callback();
    }, delay);
    markerTimers.set(markerEl, [...(markerTimers.get(markerEl) || []), timer]);
  }

  function showHoverMarker(markerEl) {
    clearMarkerTimers(markerEl);
    markerEl.classList.remove("is-visible", "has-glow");
    markerEl.hidden = false;
    void markerEl.offsetWidth;
    markerEl.classList.add("is-visible");
    queueMarkerStep(markerEl, 350, () => markerEl.classList.add("has-glow"));
    queueMarkerStep(markerEl, 450, () => markerEl.classList.remove("has-glow"));
    queueMarkerStep(markerEl, 550, () => markerEl.classList.add("has-glow"));
  }

  function hideHoverMarker(markerEl) {
    clearMarkerTimers(markerEl);
    markerEl.classList.remove("has-glow", "is-visible");
    queueMarkerStep(markerEl, 250, () => {
      if (!markerEl.classList.contains("is-visible")) markerEl.hidden = true;
    });
  }

  function resetHoverMarker(markerEl) {
    clearMarkerTimers(markerEl);
    markerEl.classList.remove("has-glow", "is-visible");
    markerEl.hidden = true;
  }

  function placeHoverMarker({ markerEl, imageEl, wrapEl, rect }) {
    const displayRect = displayRectFromNatural({ rect, imageEl });
    const imageRect = imageEl.getBoundingClientRect();
    const wrapRect = wrapEl.getBoundingClientRect();
    markerEl.style.left = `${displayRect.x + displayRect.width / 2 + imageRect.left - wrapRect.left}px`;
    markerEl.style.top = `${displayRect.y + displayRect.height / 2 + imageRect.top - wrapRect.top}px`;
    showHoverMarker(markerEl);
  }

  function openAnchoredPopover({
    popoverEl,
    inputEl,
    displayRect,
    relativeToEl,
    minMargin = 14,
    maxWidthOffset = 434,
    maxHeightOffset = 190,
  }) {
    const baseRect = relativeToEl.getBoundingClientRect();
    const left = Math.min(baseRect.left + displayRect.x + displayRect.width + 10, window.innerWidth - maxWidthOffset);
    const top = Math.min(baseRect.top + displayRect.y, window.innerHeight - maxHeightOffset);
    popoverEl.style.left = `${Math.max(minMargin, left)}px`;
    popoverEl.style.top = `${Math.max(minMargin, top)}px`;
    popoverEl.hidden = false;
    inputEl?.focus();
  }

  ROOT.imageViewer = {
    applyZoom,
    displayRectFromNatural,
    dragDisplayRect,
    formatZoomPercent,
    hideHoverMarker,
    imagePoint,
    naturalRect,
    openAnchoredPopover,
    placeHoverMarker,
    placeSelection,
    renderedImageSize,
    resetHoverMarker,
    smartFit,
    smartFitZoom,
    scrollRectIntoView,
    showHoverMarker,
    stageFitZoom,
    stageViewportSize,
    updateAlignment,
  };
}());
