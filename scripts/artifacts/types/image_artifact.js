(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.types = ROOT.types || {};
  const common = ROOT.common;

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

  function renderZoomControls() {
    return `
      <div class="image-controls" id="image-controls" data-control-kind="image-zoom">
        <div class="zoom-control" id="zoom-control">
          <button class="zoom-fit" id="zoom-fit" type="button" aria-label="Smart fit" title="Smart fit">
            ${common.renderIconUse("icon-fit")}
          </button>
          <input id="zoom-input" type="text" inputmode="numeric" aria-label="Zoom percentage">
          <div class="zoom-steps">
            <button id="zoom-in" type="button" aria-label="Zoom in">+</button>
            <button id="zoom-out" type="button" aria-label="Zoom out">-</button>
          </div>
        </div>
      </div>
    `;
  }

  function toolbarPlan(options = {}) {
    return common.toolbarPlan({
      kind: "image",
      readoutId: "image-dimensions",
      readoutLabel: "Dimensions",
      readoutValue: readout(options),
      controls: [{ id: "image-zoom", html: renderZoomControls() }],
      controlPolicy: options.controlPolicy,
    });
  }

  function bindControls({ rootEl, actions = {} } = {}) {
    if (!rootEl) return common.noopUnbind;
    const scope = common.makeAbortScope();
    scope.add(rootEl, "click", (event) => {
      const button = common.closestElement(event.target, "button");
      if (!button || !rootEl.contains(button)) return;
      if (button.id === "zoom-in") actions.applyZoom?.(10, { relative: true });
      if (button.id === "zoom-out") actions.applyZoom?.(-10, { relative: true });
      if (button.id === "zoom-fit") actions.smartFit?.();
    });
    scope.add(rootEl, "change", (event) => {
      if (event.target?.id === "zoom-input") actions.applyZoom?.(event.target.value.replace("%", ""));
    });
    scope.add(rootEl, "wheel", (event) => {
      if (!common.closestElement(event.target, "#zoom-control")) return;
      event.preventDefault();
      actions.applyZoom?.(event.deltaY < 0 ? 5 : -5, { relative: true });
    }, { passive: false });
    return scope.done;
  }

  ROOT.types.image = {
    bindControls,
    capabilities: {
      imageRegionAnnotations: true,
      imageZoom: true,
    },
    kind: "image",
    matches: (artifact = {}) => String(artifact.type || "").toLowerCase() === "image",
    readout,
    stagePlan,
    toolbarPlan,
  };
}());
