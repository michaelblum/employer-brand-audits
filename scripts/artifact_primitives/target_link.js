(function () {
  const ROOT = window.ArtifactPrimitives = window.ArtifactPrimitives || {};

  const DEFAULT_TARGET_LINK_OPTIONS = {
    effect: "chase",
    color: null,
    colors: {
      primary: "#38bdf8",
      secondary: "#93c5fd",
      accent: "#22d3ee",
      faint: "rgba(56, 189, 248, 0.08)",
      highlightBackground: "rgba(56, 189, 248, 0.08)",
      highlightShadow: "rgba(147, 197, 253, 0.22)",
      highlightShadowStrong: "rgba(147, 197, 253, 0.42)",
      glow: "rgba(56, 189, 248, 0.18)",
    },
    speed: 1,
    durations: {
      lineMs: 1800,
      pulseMs: 3300,
      borderMs: 3900,
    },
    geometry: {
      highlightInset: 8,
      highlightRadius: 10,
      borderWidth: 2,
      connectorWidth: 2.6,
      connectorDashArray: "12 10",
      connectorDashOffset: 44,
    },
    targetClass: "",
  };

  const CSS_VAR_NAMES = [
    "--target-link-color-a",
    "--target-link-color-b",
    "--target-link-color-c",
    "--target-link-color-faint",
    "--target-link-highlight-bg",
    "--target-link-highlight-shadow",
    "--target-link-highlight-shadow-strong",
    "--target-link-glow",
    "--target-link-line-duration",
    "--target-link-pulse-duration",
    "--target-link-border-duration",
    "--target-link-border-width",
    "--target-link-connector-width",
    "--target-link-connector-dasharray",
    "--target-link-connector-dashoffset",
    "--target-link-highlight-radius",
  ];

  function isPlainObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function clone(value) {
    if (Array.isArray(value)) return value.map(clone);
    if (isPlainObject(value)) {
      const copy = {};
      for (const [key, item] of Object.entries(value)) copy[key] = clone(item);
      return copy;
    }
    return value;
  }

  function mergeRawOptions(...parts) {
    const merged = clone(DEFAULT_TARGET_LINK_OPTIONS);
    for (const part of parts) {
      if (!isPlainObject(part)) continue;
      if (part.effect) merged.effect = String(part.effect);
      if (part.color) merged.colors.primary = String(part.color);
      if (isPlainObject(part.colors)) {
        merged.colors = { ...merged.colors, ...part.colors };
      }
      if (part.speed !== undefined) merged.speed = part.speed;
      if (isPlainObject(part.durations)) {
        merged.durations = { ...merged.durations, ...part.durations };
      }
      if (isPlainObject(part.geometry)) {
        merged.geometry = { ...merged.geometry, ...part.geometry };
      }
      if (part.targetClass !== undefined) merged.targetClass = String(part.targetClass || "");
    }
    return merged;
  }

  function positiveNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : fallback;
  }

  function cssNumber(value, fallback, unit = "px") {
    const number = positiveNumber(value, fallback);
    return `${number}${unit}`;
  }

  function cssDurationFromMs(ms) {
    const seconds = Math.round((Number(ms) / 1000) * 1000) / 1000;
    return `${seconds}s`;
  }

  function normalizedDuration(rawDurations, key, defaultMs, speed) {
    const direct = rawDurations[key];
    if (typeof direct === "string" && direct.trim()) return direct.trim();
    if (Number.isFinite(Number(direct)) && Number(direct) > 0) {
      return cssDurationFromMs(Number(direct));
    }
    const rawMs = rawDurations[`${key}Ms`];
    const baseMs = positiveNumber(rawMs, defaultMs);
    return cssDurationFromMs(baseMs / speed);
  }

  function normalizeTargetLinkOptions(options = {}) {
    const raw = mergeRawOptions(options);
    const speed = positiveNumber(raw.speed, DEFAULT_TARGET_LINK_OPTIONS.speed);
    const colors = { ...DEFAULT_TARGET_LINK_OPTIONS.colors, ...raw.colors };
    const geometry = {
      ...DEFAULT_TARGET_LINK_OPTIONS.geometry,
      ...raw.geometry,
    };
    return {
      effect: raw.effect || DEFAULT_TARGET_LINK_OPTIONS.effect,
      colors,
      speed,
      durations: {
        line: normalizedDuration(raw.durations, "line", DEFAULT_TARGET_LINK_OPTIONS.durations.lineMs, speed),
        pulse: normalizedDuration(raw.durations, "pulse", DEFAULT_TARGET_LINK_OPTIONS.durations.pulseMs, speed),
        border: normalizedDuration(raw.durations, "border", DEFAULT_TARGET_LINK_OPTIONS.durations.borderMs, speed),
      },
      geometry: {
        highlightInset: positiveNumber(geometry.highlightInset, DEFAULT_TARGET_LINK_OPTIONS.geometry.highlightInset),
        highlightRadius: positiveNumber(geometry.highlightRadius, DEFAULT_TARGET_LINK_OPTIONS.geometry.highlightRadius),
        borderWidth: positiveNumber(geometry.borderWidth, DEFAULT_TARGET_LINK_OPTIONS.geometry.borderWidth),
        connectorWidth: positiveNumber(geometry.connectorWidth, DEFAULT_TARGET_LINK_OPTIONS.geometry.connectorWidth),
        connectorDashArray: String(geometry.connectorDashArray || DEFAULT_TARGET_LINK_OPTIONS.geometry.connectorDashArray),
        connectorDashOffset: positiveNumber(
          geometry.connectorDashOffset,
          DEFAULT_TARGET_LINK_OPTIONS.geometry.connectorDashOffset,
        ),
      },
      targetClass: raw.targetClass || "",
    };
  }

  function mergeTargetLinkOptions(...parts) {
    return normalizeTargetLinkOptions(mergeRawOptions(...parts));
  }

  function styleSet(el, name, value) {
    if (!el?.style) return;
    if (typeof el.style.setProperty === "function") {
      el.style.setProperty(name, value);
    } else {
      el.style[name] = value;
    }
  }

  function styleRemove(el, name) {
    if (!el?.style) return;
    if (typeof el.style.removeProperty === "function") {
      el.style.removeProperty(name);
    } else if (el.style.values && Object.prototype.hasOwnProperty.call(el.style.values, name)) {
      delete el.style.values[name];
    }
  }

  function applyStyleVars(el, config) {
    if (!el) return;
    const vars = {
      "--target-link-color-a": config.colors.primary,
      "--target-link-color-b": config.colors.secondary,
      "--target-link-color-c": config.colors.accent,
      "--target-link-color-faint": config.colors.faint,
      "--target-link-highlight-bg": config.colors.highlightBackground,
      "--target-link-highlight-shadow": config.colors.highlightShadow,
      "--target-link-highlight-shadow-strong": config.colors.highlightShadowStrong,
      "--target-link-glow": config.colors.glow,
      "--target-link-line-duration": config.durations.line,
      "--target-link-pulse-duration": config.durations.pulse,
      "--target-link-border-duration": config.durations.border,
      "--target-link-border-width": cssNumber(config.geometry.borderWidth, DEFAULT_TARGET_LINK_OPTIONS.geometry.borderWidth),
      "--target-link-connector-width": cssNumber(config.geometry.connectorWidth, DEFAULT_TARGET_LINK_OPTIONS.geometry.connectorWidth),
      "--target-link-connector-dasharray": config.geometry.connectorDashArray,
      "--target-link-connector-dashoffset": String(config.geometry.connectorDashOffset * -1),
      "--target-link-highlight-radius": cssNumber(config.geometry.highlightRadius, DEFAULT_TARGET_LINK_OPTIONS.geometry.highlightRadius),
    };
    for (const [name, value] of Object.entries(vars)) {
      styleSet(el, name, String(value));
    }
  }

  function removeStyleVars(el) {
    for (const name of CSS_VAR_NAMES) styleRemove(el, name);
  }

  function applyDataset(el, dataset = {}) {
    if (!el?.dataset) return;
    for (const [key, value] of Object.entries(dataset || {})) {
      if (value === null || value === undefined || value === "") {
        delete el.dataset[key];
      } else {
        el.dataset[key] = String(value);
      }
    }
  }

  function deleteDatasetKeys(el, keys = []) {
    if (!el?.dataset) return;
    for (const key of keys || []) delete el.dataset[key];
  }

  function applyGradientStops(connectorSvgEl, config) {
    if (!connectorSvgEl || typeof connectorSvgEl.querySelectorAll !== "function") return;
    const roles = {
      primary: config.colors.primary,
      secondary: config.colors.secondary,
      accent: config.colors.accent,
    };
    for (const [role, color] of Object.entries(roles)) {
      const stops = connectorSvgEl.querySelectorAll(`[data-target-link-gradient-stop="${role}"]`);
      for (const stop of stops || []) {
        if (typeof stop.setAttribute === "function") stop.setAttribute("stop-color", color);
      }
    }
  }

  function inflateRect(rect, amount = 0) {
    if (!rect) return null;
    return {
      x: Number(rect.x || 0) - amount,
      y: Number(rect.y || 0) - amount,
      width: Number(rect.width || 0) + (amount * 2),
      height: Number(rect.height || 0) + (amount * 2),
    };
  }

  function fallbackPlaceOverlayBox({ overlayEl, displayRect } = {}) {
    if (!overlayEl || !displayRect) return;
    overlayEl.style.left = `${displayRect.x}px`;
    overlayEl.style.top = `${displayRect.y}px`;
    overlayEl.style.width = `${displayRect.width}px`;
    overlayEl.style.height = `${displayRect.height}px`;
    overlayEl.hidden = false;
  }

  function connectorPathHelper(interactionOverlay, connectorPathBetweenRects) {
    if (typeof connectorPathBetweenRects === "function") return connectorPathBetweenRects;
    if (typeof interactionOverlay?.connectorPathBetweenRects === "function") {
      return interactionOverlay.connectorPathBetweenRects;
    }
    if (typeof ROOT.interactionOverlay?.connectorPathBetweenRects === "function") {
      return ROOT.interactionOverlay.connectorPathBetweenRects;
    }
    return null;
  }

  function placeOverlayBoxHelper(interactionOverlay) {
    if (typeof interactionOverlay?.placeOverlayBox === "function") {
      return interactionOverlay.placeOverlayBox;
    }
    if (typeof ROOT.interactionOverlay?.placeOverlayBox === "function") {
      return ROOT.interactionOverlay.placeOverlayBox;
    }
    return fallbackPlaceOverlayBox;
  }

  function stageViewBox(stageEl, sourceRect, targetRect) {
    const width = Number(stageEl?.clientWidth) || Math.ceil(Math.max(
      Number(sourceRect.x || 0) + Number(sourceRect.width || 0),
      Number(targetRect.x || 0) + Number(targetRect.width || 0),
    ));
    const height = Number(stageEl?.clientHeight) || Math.ceil(Math.max(
      Number(sourceRect.y || 0) + Number(sourceRect.height || 0),
      Number(targetRect.y || 0) + Number(targetRect.height || 0),
    ));
    return `0 0 ${width} ${height}`;
  }

  function renderTargetLink({
    layerEl,
    highlightEl,
    connectorSvgEl,
    connectorPathEl,
    sourceRect,
    targetRect,
    targetEl,
    stageEl,
    interactionOverlay,
    connectorPathBetweenRects,
    options,
    dataset = {},
    targetDataset = {},
  } = {}) {
    const config = normalizeTargetLinkOptions(options);
    const linkConnectorPath = connectorPathHelper(interactionOverlay, connectorPathBetweenRects);
    if (!layerEl || !highlightEl || !connectorPathEl || !sourceRect || !targetRect || !linkConnectorPath) {
      return { status: "skipped", reason: "missing-target-link-input", config };
    }

    const highlightRect = inflateRect(sourceRect, config.geometry.highlightInset);
    const connector = linkConnectorPath({ fromRect: highlightRect, toRect: targetRect });
    if (!connector?.d) {
      return { status: "skipped", reason: "missing-connector-path", config };
    }

    const elementsForVars = [layerEl, highlightEl, connectorSvgEl, connectorPathEl, targetEl];
    for (const element of elementsForVars) applyStyleVars(element, config);
    applyGradientStops(connectorSvgEl, config);

    layerEl.hidden = false;
    applyDataset(layerEl, { targetLinkEffect: config.effect, ...dataset });
    applyDataset(highlightEl, { targetLinkEffect: config.effect, ...dataset });
    placeOverlayBoxHelper(interactionOverlay)({ overlayEl: highlightEl, displayRect: highlightRect });

    if (connectorSvgEl && typeof connectorSvgEl.setAttribute === "function") {
      connectorSvgEl.setAttribute("viewBox", stageViewBox(stageEl, highlightRect, targetRect));
      applyDataset(connectorSvgEl, { targetLinkEffect: config.effect, ...dataset });
    }
    connectorPathEl.setAttribute("d", connector.d);
    applyDataset(connectorPathEl, { targetLinkEffect: config.effect, ...dataset });

    if (targetEl) {
      targetEl.classList?.add("is-target-linked");
      if (config.targetClass) targetEl.classList?.add(config.targetClass);
      applyDataset(targetEl, { targetLinkEffect: config.effect, ...targetDataset });
    }
    return {
      status: "rendered",
      effect: config.effect,
      config,
      connector,
      highlightRect,
    };
  }

  function clearTargetLink({
    layerEl,
    highlightEl,
    connectorSvgEl,
    connectorPathEl,
    targetEl,
    options,
    datasetKeys = [],
    targetDatasetKeys = [],
  } = {}) {
    const config = normalizeTargetLinkOptions(options);
    if (layerEl) {
      layerEl.hidden = true;
      deleteDatasetKeys(layerEl, ["targetLinkEffect", ...datasetKeys]);
      removeStyleVars(layerEl);
    }
    if (highlightEl) {
      highlightEl.hidden = true;
      deleteDatasetKeys(highlightEl, ["targetLinkEffect", ...datasetKeys]);
      removeStyleVars(highlightEl);
    }
    if (connectorSvgEl) {
      deleteDatasetKeys(connectorSvgEl, ["targetLinkEffect", ...datasetKeys]);
      removeStyleVars(connectorSvgEl);
    }
    if (connectorPathEl) {
      connectorPathEl.removeAttribute("d");
      deleteDatasetKeys(connectorPathEl, ["targetLinkEffect", ...datasetKeys]);
      removeStyleVars(connectorPathEl);
    }
    if (targetEl) {
      targetEl.classList?.remove("is-target-linked");
      if (config.targetClass) targetEl.classList?.remove(config.targetClass);
      deleteDatasetKeys(targetEl, ["targetLinkEffect", ...targetDatasetKeys]);
      removeStyleVars(targetEl);
    }
    return { status: "cleared", config };
  }

  function createTargetLinkEffect(instanceOptions = {}) {
    const rawInstanceOptions = clone(instanceOptions);
    return {
      options: normalizeTargetLinkOptions(rawInstanceOptions),
      render(renderOptions = {}) {
        return renderTargetLink({
          ...renderOptions,
          options: mergeRawOptions(rawInstanceOptions, renderOptions.options || {}),
        });
      },
      clear(clearOptions = {}) {
        return clearTargetLink({
          ...clearOptions,
          options: mergeRawOptions(rawInstanceOptions, clearOptions.options || {}),
        });
      },
    };
  }

  ROOT.targetLink = {
    DEFAULT_TARGET_LINK_OPTIONS: clone(DEFAULT_TARGET_LINK_OPTIONS),
    createTargetLinkEffect,
    mergeTargetLinkOptions,
    normalizeTargetLinkOptions,
  };
}());
