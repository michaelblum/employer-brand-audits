(function () {
  const ROOT = window.Artifacts = window.Artifacts || {};
  ROOT.common = ROOT.common || {};
  const common = ROOT.common;

  function renderZoomControls() {
    return `
      <div class="artifact-zoom-controls" id="artifact-zoom-controls" data-control-kind="artifact-zoom">
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

  function zoomControlPlan() {
    return { id: "artifact-zoom", html: renderZoomControls(), readOnlyAllowed: true };
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

  function syncControls({ rootEl, state = {} } = {}) {
    const input = rootEl?.querySelector?.("#zoom-input");
    if (!input) return;
    const formatter = window.ArtifactPrimitives?.zoomSurface?.formatZoomPercent
      || window.ArtifactPrimitives?.imageViewer?.formatZoomPercent;
    input.value = typeof formatter === "function"
      ? formatter(state.zoomPercent || 100)
      : `${Math.round(Number(state.zoomPercent || 100))}%`;
  }

  ROOT.zoomControls = {
    bindControls,
    renderZoomControls,
    syncControls,
    zoomControlPlan,
  };
}());
