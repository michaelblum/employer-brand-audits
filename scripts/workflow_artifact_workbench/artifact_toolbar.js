(function () {
  const ROOT = window.WorkbenchArtifactToolbar = window.WorkbenchArtifactToolbar || {};

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function renderReadoutItem(item = {}) {
    const id = escapeHtml(item.id || "readout");
    const label = String(item.label || "").trim();
    const value = String(item.value || "").trim();
    const tone = item.tone ? ` ${escapeHtml(item.tone)}` : "";
    const title = label ? ` title="${escapeHtml(`${label}: ${value}`)}"` : "";
    return `<span class="artifact-readout-item${tone}" data-readout-id="${id}"${title}>${escapeHtml(value)}</span>`;
  }

  function renderReadout(readout = []) {
    return `
      <div class="artifact-readout" id="artifact-readout" data-slot="readout">
        ${readout.map(renderReadoutItem).join("")}
      </div>
    `;
  }

  function renderControl(control = {}) {
    return String(control.html || "");
  }

  function renderControls(controls = []) {
    return `
      <div class="artifact-controls" id="artifact-controls" data-slot="controls">
        ${controls.map(renderControl).join("")}
      </div>
    `;
  }

  function renderToolbarHtml(plan = {}) {
    return `${renderReadout(plan.readout || [])}${renderControls(plan.controls || [])}`;
  }

  function mountToolbar(container, plan = {}) {
    if (!container) return;
    container.dataset.artifactKind = plan.kind || "";
    container.innerHTML = renderToolbarHtml(plan);
  }

  ROOT.renderToolbarHtml = renderToolbarHtml;
  ROOT.mountToolbar = mountToolbar;
}());
