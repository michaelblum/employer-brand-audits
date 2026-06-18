(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

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
    displayRectFromNatural,
    dragDisplayRect,
    hideHoverMarker,
    imagePoint,
    naturalRect,
    openAnchoredPopover,
    placeHoverMarker,
    placeSelection,
    resetHoverMarker,
    scrollRectIntoView,
    showHoverMarker,
  };
}());
